"""Diagnóstico de Groq para GymBot.

Uso (en la MISMA terminal donde defines GROQ_API_KEY y GROQ_MODEL):
    python test_groq.py

No imprime la clave. Solo muestra el código HTTP y el mensaje de error de Groq.
"""

import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api.groq.com/openai/v1"
clave = os.getenv("GROQ_API_KEY", "").strip()
modelo = os.getenv("GROQ_MODEL", "").strip()

print("1) Variables de entorno en esta terminal")
print("   GROQ_API_KEY:", f"definida ({len(clave)} caracteres)" if clave else "NO definida")
print("   GROQ_MODEL  :", repr(modelo) if modelo else "NO definida")
if not clave:
    raise SystemExit("\nDefine GROQ_API_KEY y vuelve a ejecutar.")


def llamar(ruta, datos=None):
    cuerpo = json.dumps(datos).encode("utf-8") if datos is not None else None
    cabeceras = {
        "Authorization": f"Bearer {clave}",
        "User-Agent": "GymBot/1.0",
        "Accept": "application/json",
    }
    if cuerpo is not None:
        cabeceras["Content-Type"] = "application/json"
    peticion = Request(BASE + ruta, data=cuerpo, headers=cabeceras,
                       method="POST" if cuerpo is not None else "GET")
    with urlopen(peticion, timeout=30) as respuesta:
        return json.loads(respuesta.read().decode("utf-8"))


def mostrar_error(error):
    print(f"   -> HTTP {error.code}")
    try:
        print("   ->", error.read().decode("utf-8")[:600])
    except Exception:
        pass


print("\n2) ¿La clave es válida? Lista de modelos disponibles ahora mismo")
try:
    ids = sorted(m["id"] for m in llamar("/models")["data"])
    print("   OK. Modelos:")
    for i in ids:
        print("    -", i)
except HTTPError as error:
    mostrar_error(error)
    raise SystemExit("\nLa clave fue rechazada o hay un bloqueo. Mira el código de arriba.")
except URLError as error:
    raise SystemExit(f"\nSin conexión a Groq: {error.reason}")

print("\n3) ¿Tu GROQ_MODEL está en esa lista?")
if not modelo:
    raise SystemExit("   GROQ_MODEL no está definida.")
print("   Sí está." if modelo in ids else "   NO está: ese modelo ya no existe en Groq.")

print("\n4) Prueba real de chat con tu modelo")
try:
    r = llamar("/chat/completions", {
        "model": modelo,
        "messages": [{"role": "user", "content": "Responde solo: ok"}],
        "stream": False,
    })
    print("   OK. Respuesta:", r["choices"][0]["message"]["content"])
except HTTPError as error:
    mostrar_error(error)
