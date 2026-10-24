"""Funciones de memoria y procesamiento por turno para GymBot/Gradio."""
import json
from consulta_llm import interpretar, ejecutar

def nuevo_historial():
    """Historial independiente de una sesión de Gradio."""
    return []

def _contexto(historial):
    lineas = []
    for mensaje in historial[-16:]:
        rol = mensaje.get("role", "")
        contenido = mensaje.get("content", "")
        etiqueta = "Usuario" if rol == "user" else "GymBot"
        lineas.append(f"{etiqueta}: {contenido}")
    return "\n".join(lineas)

def procesar_turno(mensaje, historial, clave, modelo):
    """Devuelve (resultado, historial_actualizado, plan).

    Solo interpreta y consulta la API para solicitudes normales.
    Para crear/modificar/cancelar devuelve un plan pendiente; Gradio
    exige pulsar Confirmar antes de ejecutar la operación.
    """
    contexto = _contexto(historial)
    if contexto:
        pregunta = (
            "Usa este contexto de la conversación para resolver el nuevo mensaje. "
            "Si faltan datos, pregunta por ellos. No inventes datos.\n\n"
            f"CONTEXTO:\n{contexto}\n\nMENSAJE ACTUAL:\n{mensaje}"
        )
    else:
        pregunta = mensaje
    plan = interpretar(pregunta, clave, modelo)
    resultado = ejecutar(plan)
    nuevo = list(historial)
    nuevo.append({"role": "user", "content": mensaje})
    if resultado.get("tipo") == "confirmacion":
        respuesta = resultado.get("mensaje", "Confirma la operación para continuar.")
    elif resultado.get("tipo") == "faltan_datos":
        respuesta = resultado.get("mensaje", "Necesito más información.")
    elif resultado.get("tipo") == "mensaje":
        respuesta = resultado.get("mensaje", "")
    elif resultado.get("tipo") == "resultado":
        datos = resultado.get("datos", {})
        if isinstance(datos, dict) and "mensaje" in datos:
            respuesta = str(datos["mensaje"])
        else:
            respuesta = json.dumps(datos, ensure_ascii=False, indent=2)
    else:
        respuesta = "No pude procesar la solicitud."
    nuevo.append({"role": "assistant", "content": respuesta})
    return resultado, nuevo, resultado.get("plan", plan)
