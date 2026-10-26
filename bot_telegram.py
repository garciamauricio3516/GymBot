"""Canal de Telegram. Colocar junto a chatbot_memoria.py y consulta_llm.py."""

import asyncio
import json
import logging
import os
from getpass import getpass
from urllib.error import HTTPError, URLError

from telegram import Update
from telegram.error import InvalidToken, NetworkError, TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from chatbot_memoria import nuevo_historial, procesar_turno

BIENVENIDA = (
    "¡Hola! Soy GymBot, el asistente virtual de tu gimnasio. "
    "Puedes consultar planes, precios, clases, servicios y disponibilidad. "
    "Escribe /help para ver ejemplos."
)
AYUDA = (
    "/start: mostrar la bienvenida.\n"
    "/help: ver esta ayuda.\n"
    "/reset: reiniciar esta conversación.\n\n"
    "Prueba: ¿Qué planes tiene GymBot y cuánto cuestan?\n"
    "O pregunta por disponibilidad indicando servicio y fecha, por ejemplo: ¿Hay cupo para Spinning el 2026-11-02?\n"
    "En esta versión las operaciones de reserva quedan sin ejecutar."
)


async def enviar_texto(mensaje, texto):
    for inicio in range(0, len(texto), 4000):
        await mensaje.reply_text(texto[inicio:inicio + 4000])


async def iniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is not None:
        context.chat_data.setdefault("historial", nuevo_historial())
        await enviar_texto(update.effective_message, BIENVENIDA)


async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is not None:
        await enviar_texto(update.effective_message, AYUDA)


async def reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_message is not None:
        context.chat_data["historial"] = nuevo_historial()
        await enviar_texto(
            update.effective_message,
            "Conversación reiniciada. Dime qué deseas consultar. Las reservas del negocio se conservan.",
        )


def formatear_resultado(resultado, plan):
    """Adapta las respuestas reales de GymBot para que sean legibles en Telegram."""
    if resultado.get("tipo") == "confirmacion":
        return (
            "Reconocí una operación de reserva, pero esta entrega de las clases 11–12 "
            "solo habilita consultas desde Telegram. No se creó, modificó ni canceló nada.\n\n"
            + str(resultado.get("mensaje", ""))
        )

    if resultado.get("tipo") == "faltan_datos":
        return str(resultado.get("mensaje", "Necesito más información para continuar."))

    if resultado.get("tipo") == "mensaje":
        return str(resultado.get("mensaje", ""))

    datos = resultado.get("datos")
    if not isinstance(datos, dict):
        return json.dumps(datos, ensure_ascii=False, indent=2)

    accion = plan.get("accion", "")
    if accion == "servicios":
        lineas = ["🏋️ GYMBOT — PLANES Y SERVICIOS"]
        for plan_gym in datos.get("planes", []):
            precio = plan_gym.get("precio")
            precio_txt = f"${precio:,.0f} COP".replace(",", ".") if isinstance(precio, (int, float)) else "Consultar precio"
            lineas.append(f"• {plan_gym.get('nombre', 'Plan')}: {precio_txt} al mes. {plan_gym.get('descripcion', '')}")
        clases = datos.get("clases", [])
        if clases:
            lineas.append("\n📅 CLASES GRUPALES")
            for clase in clases:
                lineas.append(f"• {clase.get('nombre')}: {clase.get('dias')} a las {clase.get('hora')} ({clase.get('duracion', 'duración no indicada')}).")
        valoraciones = datos.get("valoraciones", [])
        if valoraciones:
            lineas.append("\n💪 VALORACIONES")
            for v in valoraciones:
                lineas.append(f"• {v.get('nombre')}: {v.get('dias')}, de {v.get('hora_inicio')} a {v.get('hora_fin')}.")
        horarios = datos.get("horarios_gimnasio", {})
        if horarios:
            lineas.append("\n🕒 HORARIO DEL GIMNASIO")
            lineas.append(f"• Lunes a viernes: {horarios.get('lunes_a_viernes', 'No informado')}")
            lineas.append(f"• Sábado: {horarios.get('sabado', 'No informado')}")
            lineas.append(f"• Domingo: {horarios.get('domingo', 'No informado')}")
        return "\n".join(lineas)

    if accion == "disponibilidad":
        servicio = datos.get("servicio", plan.get("servicio", "Servicio"))
        fecha = datos.get("fecha", plan.get("fecha", "fecha solicitada"))
        if "disponible" in datos:
            if datos.get("disponible"):
                return (f"✅ Sí hay disponibilidad para {servicio} el {fecha} a las {datos.get('hora', plan.get('hora', ''))}. "
                        f"Cupos disponibles: {datos.get('cupos_disponibles', 'No informado')}. Duración: {datos.get('duracion_minutos', 60)} minutos.")
            return f"❌ No hay disponibilidad para {servicio} el {fecha} a las {datos.get('hora', plan.get('hora', ''))}. Puedes consultar otro horario."
        horarios = datos.get("horas_disponibles", [])
        if not horarios:
            return f"No encontré horarios disponibles para {servicio} el {fecha}. Intenta con otra fecha."
        lista = "\n".join(f"• {h.get('hora', 'Hora no informada')} — {h.get('cupos_disponibles', '?')} cupo(s)" for h in horarios)
        return f"📅 Disponibilidad de {servicio} para el {fecha}:\n{lista}"

    if accion == "consultar":
        return ("🔎 RESERVA ENCONTRADA\n"
                f"Código: {datos.get('codigo', 'No informado')}\n"
                f"Nombre: {datos.get('nombre', 'No informado')}\n"
                f"Servicio: {datos.get('clase', 'No informado')}\n"
                f"Fecha: {datos.get('fecha', 'No informada')} a las {datos.get('hora', 'No informada')}\n"
                f"Estado: {datos.get('estado', 'No informado')}")

    return json.dumps(datos, ensure_ascii=False, indent=2)


async def recibir_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = update.effective_message
    if mensaje is None or not mensaje.text or not mensaje.text.strip():
        return
    clave = context.bot_data.get("clave_modelo", "")
    modelo = context.bot_data.get("modelo", "")
    if not clave or not modelo:
        await enviar_texto(mensaje, "Falta configurar GROQ_API_KEY o GROQ_MODEL en el servidor del bot.")
        return
    historial = context.chat_data.get("historial")
    if historial is None:
        historial = nuevo_historial()
    try:
        resultado, actualizado, plan = await asyncio.to_thread(
            procesar_turno, mensaje.text.strip(), historial, clave, modelo
        )
        texto = formatear_resultado(resultado, plan)
    except HTTPError:
        await enviar_texto(mensaje, "El servicio rechazó la consulta. Revisa la configuración de FastAPI y los datos enviados.")
        return
    except RuntimeError as error:
        await enviar_texto(mensaje, f"No pude completar la consulta: {error}")
        return
    except (URLError, TimeoutError):
        await enviar_texto(mensaje, "No pude completar la conexión. Intenta la consulta más tarde.")
        return
    except (ValueError, KeyError, IndexError, TypeError):
        await enviar_texto(mensaje, "La respuesta del servicio no tiene el formato esperado.")
        return
    context.chat_data["historial"] = actualizado
    await enviar_texto(mensaje, texto)


async def comando_desconocido(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_texto(update.effective_message, "No conozco ese comando. Usa /start, /help o /reset.")


async def otro_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await enviar_texto(update.effective_message, "Por ahora recibo consultas escritas. Envíame un mensaje de texto.")


async def informar_error(update, context):
    # Registramos la clase del error sin imprimir credenciales ni URL del bot.
    logging.error("Error del bot: %s", type(context.error).__name__)


def registrar_handlers(aplicacion):
    privado = filters.ChatType.PRIVATE
    aplicacion.add_handler(CommandHandler("start", iniciar, filters=privado))
    aplicacion.add_handler(CommandHandler("help", ayuda, filters=privado))
    aplicacion.add_handler(CommandHandler("reset", reiniciar, filters=privado))
    aplicacion.add_handler(
        MessageHandler(privado & filters.TEXT & ~filters.COMMAND, recibir_texto)
    )
    aplicacion.add_handler(MessageHandler(privado & filters.COMMAND, comando_desconocido))
    aplicacion.add_handler(MessageHandler(privado & ~filters.TEXT, otro_mensaje))
    aplicacion.add_error_handler(informar_error)


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip() or getpass("Token de BotFather (oculto): ").strip()
    if not token:
        print("Necesito el token de Telegram para iniciar.")
        return
    try:
        aplicacion = Application.builder().token(token).build()
        aplicacion.bot_data["clave_modelo"] = os.getenv("GROQ_API_KEY", "").strip()
        aplicacion.bot_data["modelo"] = os.getenv("GROQ_MODEL", "").strip()
        registrar_handlers(aplicacion)
        if not aplicacion.bot_data["clave_modelo"] or not aplicacion.bot_data["modelo"]:
            print("Los comandos funcionarán. Configura GROQ_API_KEY y GROQ_MODEL para las consultas.")
        print("Bot en ejecución. Abre su conversación en Telegram. Para detenerlo: Ctrl+C.")
        aplicacion.run_polling(allowed_updates=["message"])
    except InvalidToken:
        print("Token inválido. Comprueba la credencial entregada por BotFather.")
    except NetworkError:
        print("No fue posible iniciar la conexión con Telegram. Revisa Internet e inténtalo otra vez.")
    except TelegramError as error:
        print(f"Telegram no completó el inicio: {type(error).__name__}.")


if __name__ == "__main__":
    main()
