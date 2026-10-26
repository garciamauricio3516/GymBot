"""
GymBot - conexión entre Groq y FastAPI.

Groq interpreta la solicitud del usuario.
Python identifica la acción.
FastAPI ejecuta la operación real.

FastAPI sigue siendo responsable de validar y guardar
las reservas en SQLite.
"""

import json
import os

from getpass import getpass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


# ============================================================
# CONFIGURACIÓN
# ============================================================

API_BASE = os.getenv(
    "CHATBOT_API_URL",
    "http://127.0.0.1:8011"
).rstrip("/")


RUTAS = {
    "servicios": "/servicios",
    "disponibilidad": "/disponibilidad",
    "crear": "/reservas",
    "consultar": "/consultarReserva",
    "modificar": "/modificarReserva",
    "cancelar": "/cancelarReserva"
}


GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


# ============================================================
# ACCIONES PERMITIDAS
# ============================================================

ACCIONES = {
    "servicios",
    "disponibilidad",
    "crear",
    "consultar",
    "modificar",
    "cancelar",
    "fuera_de_alcance"
}


REQUERIDOS = {

    "disponibilidad": (
        "servicio",
        "fecha"
    ),

    "crear": (
        "cliente",
        "servicio",
        "fecha",
        "hora"
    ),

    "consultar": (
        "codigo",
    ),

   "modificar": (
    "codigo",
    "servicio",
    "fecha",
    "hora"
    ),

    "cancelar": (
        "codigo",
    )
}


# ============================================================
# INSTRUCCIONES PARA GROQ
# ============================================================

INSTRUCCIONES = """
Eres el componente que interpreta solicitudes del chatbot GymBot.

Tu función es identificar qué quiere hacer el usuario.

NO debes ejecutar reservas.
NO debes decir que una reserva fue creada, modificada o cancelada.

Debes devolver ÚNICAMENTE un objeto JSON válido con estas claves:

accion
cliente
servicio
fecha
hora
codigo

Las acciones permitidas son:

- servicios
- disponibilidad
- crear
- consultar
- modificar
- cancelar
- fuera_de_alcance

Usa fecha en formato AAAA-MM-DD.

Usa hora en formato HH:MM.

Si un dato no aparece en la pregunta, utiliza una cadena vacía.

NO inventes datos.

INFORMACIÓN DE GYMBOT:

Spinning:
lunes y miércoles a las 18:00.

Zumba:
martes y jueves a las 17:00.

Yoga:
miércoles y viernes a las 19:00.

Funcional:
lunes, miércoles y viernes a las 17:00.

Cross Training:
martes y jueves a las 19:00.

Valoración física:
lunes a viernes entre 08:00 y 12:00.

ACCIONES:

Si pregunta por planes, precios, horarios,
clases o servicios:
accion = "servicios"

Si pregunta por disponibilidad o cupos:
accion = "disponibilidad"

Si quiere crear o reservar:
accion = "crear"

Si quiere consultar, ver o revisar una reserva:
accion = "consultar"

Si quiere modificar, cambiar o mover una reserva:
accion = "modificar"

Si quiere cancelar una reserva:
accion = "cancelar"

Si la solicitud no corresponde a GymBot:
accion = "fuera_de_alcance"

No inventes códigos de reserva.

No inventes fechas.

No inventes horarios.

No afirmes que una operación fue realizada.
"""


# ============================================================
# PETICIÓN HTTP
# ============================================================

def peticion_json(url, metodo="GET", datos=None, headers=None):
    cuerpo = None

    if datos is not None:
        cuerpo = json.dumps(
            datos,
            ensure_ascii=False
        ).encode("utf-8")

    encabezados = {
        "User-Agent": "GymBot/1.0",
        "Accept": "application/json"
    }

    if cuerpo is not None:
        encabezados["Content-Type"] = "application/json"

    if headers:
        encabezados.update(headers)

    solicitud = Request(
        url,
        data=cuerpo,
        headers=encabezados,
        method=metodo
    )

    try:
        with urlopen(solicitud, timeout=30) as respuesta:
            contenido = respuesta.read().decode("utf-8")

            if not contenido:
                return {}

            return json.loads(contenido)

    except HTTPError as error:
        detalle = error.read().decode(
            "utf-8",
            errors="replace"
        )

        try:
            datos_error = json.loads(detalle)
            mensaje = datos_error.get("detail", detalle)
        except json.JSONDecodeError:
            mensaje = detalle

        raise RuntimeError(
            f"Error HTTP {error.code}: {mensaje}"
        ) from error
# ============================================================
# GROQ INTERPRETA LA PREGUNTA
# ============================================================

def interpretar(pregunta, clave, modelo):

    payload = {

        "model": modelo,

        "messages": [

            {
                "role": "system",
                "content": INSTRUCCIONES
            },

            {
                "role": "user",
                "content": pregunta
            }

        ],

        "temperature": 0,

        "stream": False
    }


    respuesta = peticion_json(

        GROQ_URL,

        "POST",

        payload,

        {
            "Authorization": f"Bearer {clave}"
        }
    )


    texto = respuesta[
        "choices"
    ][0][
        "message"
    ][
        "content"
    ].strip()


    # Si Groq devuelve ```json ... ```
    if texto.startswith("```"):

        texto = texto.replace(
            "```json",
            "",
            1
        )

        texto = texto.replace(
            "```",
            ""
        )

        texto = texto.strip()


    plan = json.loads(texto)


    if not isinstance(plan, dict):

        raise ValueError(
            "Groq no devolvió un objeto JSON."
        )


    if plan.get("accion") not in ACCIONES:

        raise ValueError(
            "Groq devolvió una acción no permitida."
        )


    campos = (
        "accion",
        "cliente",
        "servicio",
        "fecha",
        "hora",
        "codigo"
    )


    return {

        campo: str(
            plan.get(campo) or ""
        ).strip()

        for campo in campos
    }


# ============================================================
# EJECUTAR ACCIÓN
# ============================================================

def ejecutar(
    plan,
    confirmar=False,
    api_base=API_BASE
):

    accion = plan["accion"]


    if accion not in ACCIONES:

        raise ValueError(
            "Acción no permitida."
        )


    # --------------------------------------------------------
    # FUERA DE ALCANCE
    # --------------------------------------------------------

    if accion == "fuera_de_alcance":

        return {

            "tipo": "mensaje",

            "mensaje":
                "Puedo ayudarte con planes, "
                "servicios, disponibilidad "
                "y reservas del gimnasio."
        }


    # --------------------------------------------------------
    # COMPROBAR DATOS
    # --------------------------------------------------------

    faltan = [

        campo

        for campo in REQUERIDOS.get(
            accion,
            ()
        )

        if not plan.get(campo)
    ]


    if faltan:

        return {

            "tipo": "faltan_datos",

            "mensaje":
                "Necesito: "
                + ", ".join(faltan),

            "plan": plan
        }


    # --------------------------------------------------------
    # CONFIRMACIÓN
    # --------------------------------------------------------

    if accion in {
        "crear",
        "modificar",
        "cancelar"
    } and not confirmar:


        if accion == "crear":

            mensaje = (

                "Voy a crear esta reserva:\n"

                f"Nombre: "
                f"{plan['cliente']}\n"

                f"Servicio: "
                f"{plan['servicio']}\n"

                f"Fecha: "
                f"{plan['fecha']}\n"

                f"Hora: "
                f"{plan['hora']}\n\n"

                "¿Confirmas?"
            )


        elif accion == "modificar":

            mensaje = (

                "Voy a modificar la reserva "
                f"{plan['codigo']} "
                "con estos datos:\n"

                f"Nombre: "
                f"{plan['cliente']}\n"

                f"Servicio: "
                f"{plan['servicio']}\n"

                f"Fecha: "
                f"{plan['fecha']}\n"

                f"Hora: "
                f"{plan['hora']}\n\n"

                "¿Confirmas?"
            )


        else:

            mensaje = (

                "Voy a cancelar la reserva "
                f"{plan['codigo']}.\n\n"

                "¿Confirmas?"
            )


        return {

            "tipo": "confirmacion",

            "mensaje": mensaje,

            "plan": plan
        }


    # ========================================================
    # LLAMAR A FASTAPI
    # ========================================================

    base = api_base.rstrip("/")


    # --------------------------------------------------------
    # SERVICIOS
    # --------------------------------------------------------

    if accion == "servicios":

        datos = peticion_json(

            base + RUTAS["servicios"]
        )


    # --------------------------------------------------------
    # DISPONIBILIDAD
    # --------------------------------------------------------

    elif accion == "disponibilidad":

        parametros = urlencode({

            "clase": plan["servicio"],

            "fecha": plan["fecha"],

            "hora": plan["hora"]

        })


        datos = peticion_json(

            base
            + RUTAS["disponibilidad"]
            + "?"
            + parametros
        )


    # --------------------------------------------------------
    # CREAR
    # --------------------------------------------------------

    elif accion == "crear":

        tipo = "clase"

        if (
            plan["servicio"]
            .lower()
            == "valoración física"
        ):

            tipo = "valoracion"


        cuerpo = {

            "nombre":
                plan["cliente"],

            "tipo":
                tipo,

            "clase":
                plan["servicio"],

            "fecha":
                plan["fecha"],

            "hora":
                plan["hora"]
        }


        datos = peticion_json(

            base + RUTAS["crear"],

            "POST",

            cuerpo
        )


    # --------------------------------------------------------
    # CONSULTAR
    # --------------------------------------------------------

    elif accion == "consultar":

        cuerpo = {

            "codigo":
                plan["codigo"]
        }


        datos = peticion_json(

            base + RUTAS["consultar"],

            "POST",

            cuerpo
        )


    # --------------------------------------------------------
    # MODIFICAR
    # --------------------------------------------------------
    elif accion == "modificar":

        # Si no conocemos el nombre,
        # consultamos primero la reserva usando el código.

        if not plan["cliente"]:

            reserva_actual = peticion_json(
                base + RUTAS["consultar"],
                "POST",
                {
                    "codigo": plan["codigo"]
                }
            )

            if "nombre" not in reserva_actual:

                return {
                    "tipo": "mensaje",
                    "mensaje":
                        "No se encontró la reserva con el código indicado."
                }

            plan["cliente"] = reserva_actual["nombre"]

        cuerpo = {

            "codigo":
                plan["codigo"],

            "nombre":
                plan["cliente"],

            "clase":
                plan["servicio"],

            "fecha":
                plan["fecha"],

            "hora":
                plan["hora"]
        }

        datos = peticion_json(

            base + RUTAS["modificar"],

            "POST",

            cuerpo
        )


    # --------------------------------------------------------
    # CANCELAR
    # --------------------------------------------------------
    elif accion == "cancelar":

        cuerpo = {

            "codigo":
                plan["codigo"]
        }

        datos = peticion_json(

            base + RUTAS["cancelar"],

            "POST",

            cuerpo
        )
    return {

        "tipo": "resultado",

        "accion": accion,

        "datos": datos
    }


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    clave = (
        os.getenv(
            "GROQ_API_KEY",
            ""
        ).strip()

        or getpass(
            "API key de Groq: "
        ).strip()
    )


    modelo = (
        os.getenv(
            "GROQ_MODEL",
            ""
        ).strip()

        or input(
            "ID del modelo de Groq: "
        ).strip()
    )


    if not clave or not modelo:

        print(
            "Necesito la API key "
            "y el ID del modelo."
        )

        return


    print()
    print(
        "======================================"
    )
    print(
        "          GYMBOT - PYTHON"
    )
    print(
        "======================================"
    )

    print(
        "FastAPI:",
        API_BASE
    )

    print(
        "Modelo:",
        modelo
    )

    print()

    print(
        "Escribe una solicitud."
    )

    print(
        "Para terminar escribe SALIR."
    )


    while True:

        pregunta = input(
            "\nTú: "
        ).strip()


        if pregunta.casefold() == "salir":

            print(
                "Programa terminado."
            )

            break


        if not pregunta:
            continue


        try:

            # ================================================
            # 1. GROQ INTERPRETA
            # ================================================

            plan = interpretar(

                pregunta,

                clave,

                modelo
            )


            print()
            print(
                "Plan interpretado por Groq:"
            )

            print(
                json.dumps(
                    plan,
                    ensure_ascii=False,
                    indent=2
                )
            )


            # ================================================
            # 2. PYTHON EJECUTA
            # ================================================

            resultado = ejecutar(plan)


            # ================================================
            # FALTAN DATOS
            # ================================================

            if (
                resultado["tipo"]
                == "faltan_datos"
            ):

                print()

                print(
                    "Chatbot:",
                    resultado["mensaje"]
                )

                continue


            # ================================================
            # CONFIRMACIÓN
            # ================================================

            if (
                resultado["tipo"]
                == "confirmacion"
            ):

                print()

                print(
                    "Chatbot:"
                )

                print(
                    resultado["mensaje"]
                )


                respuesta = input(
                    "Confirmar (s/n): "
                ).strip().casefold()


                if respuesta in {
                    "s",
                    "si",
                    "sí"
                }:

                    resultado = ejecutar(

                        plan,

                        confirmar=True
                    )


                    print()

                    print(
                        "FastAPI:"
                    )

                    print(
                        json.dumps(
                            resultado["datos"],
                            ensure_ascii=False,
                            indent=2
                        )
                    )


                else:

                    print()

                    print(
                        "Operación cancelada "
                        "por el usuario."
                    )


                continue


            # ================================================
            # MENSAJE
            # ================================================

            if (
                resultado["tipo"]
                == "mensaje"
            ):

                print()

                print(
                    "Chatbot:",
                    resultado["mensaje"]
                )

                continue


            # ================================================
            # RESULTADO
            # ================================================

            print()

            print(
                "FastAPI:"
            )

            print(
                json.dumps(
                    resultado["datos"],
                    ensure_ascii=False,
                    indent=2
                )
            )


        except HTTPError as error:

            cuerpo = ""

            try:

                cuerpo = (
                    error
                    .read()
                    .decode("utf-8")
                )

            except Exception:
                pass


            print()

            print(
                f"Error HTTP {error.code}."
            )


            if cuerpo:

                print(cuerpo)


            if error.code == 429:

                print()

                print(
                    "Groq alcanzó un límite "
                    "de uso. Espera antes "
                    "de volver a intentar."
                )


        except URLError:

            print()

            print(
                "No pude conectar con "
                "FastAPI o Groq."
            )

            print(
                "Comprueba que FastAPI "
                "esté ejecutándose."
            )


        except (
            ValueError,
            KeyError,
            IndexError,
            TypeError
        ) as error:

            print()

            print(
                "No pude interpretar "
                "la respuesta."
            )

            print(
                "Detalle:",
                error
            )


# ============================================================
# INICIO
# ============================================================

if __name__ == "__main__":
    main()