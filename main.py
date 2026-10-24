"""API de GymBot: catálogo y reservas persistidas en SQLite."""
import json
from datetime import date
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from almacen_sqlite import AgendaSQLite, ConflictoReserva, ReservaNoEncontrada

BASE = Path(__file__).resolve().parent
SERVICIOS_JSON = json.loads((BASE / "servicios.json").read_text(encoding="utf-8-sig"))

def construir_catalogo():
    catalogo = {}
    dias_clase = {
        "lunes": [0], "martes": [1], "miércoles": [2], "miercoles": [2],
        "jueves": [3], "viernes": [4], "sábado": [5], "sabado": [5], "domingo": [6]
    }
    for item in SERVICIOS_JSON.get("clases", []):
        dias = []
        texto = item["dias"].lower()
        for nombre, indice in dias_clase.items():
            if nombre in texto and indice[0] not in dias:
                dias.append(indice[0])
        catalogo[item["nombre"]] = {
            "tipo": "clase", "duracion_minutos": 60,
            "dias_indices": dias, "horas": [item["hora"]]
        }
    for item in SERVICIOS_JSON.get("valoraciones", []):
        catalogo[item["nombre"]] = {
            "tipo": "valoracion", "duracion_minutos": 60,
            "dias_indices": [0, 1, 2, 3, 4],
            "rango_horas": [item["hora_inicio"], item["hora_fin"]], "paso_minutos": 30
        }
    return catalogo

CATALOGO = construir_catalogo()
agenda = AgendaSQLite(BASE / "reservas.db", CATALOGO)
app = FastAPI(title="GymBot API", version="2.0.0")

class ReservaNueva(BaseModel):
    nombre: str = Field(min_length=2)
    tipo: str
    clase: str
    fecha: str
    hora: str

class ConsultaReserva(BaseModel):
    codigo: str = Field(min_length=1)

class ModificacionReserva(BaseModel):
    codigo: str
    nombre: str = ""
    clase: str
    fecha: str
    hora: str

def responder(funcion, *args):
    try:
        return funcion(*args)
    except ReservaNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConflictoReserva as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

def formato_cliente(registro):
    servicio = registro["servicio"]
    return {
        "codigo": registro["codigo"],
        "nombre": registro["cliente"],
        "tipo": "Valoracion" if CATALOGO[servicio]["tipo"] == "valoracion" else "clase",
        "clase": servicio,
        "fecha": registro["fecha"],
        "hora": registro["hora"],
        "estado": "Cancelada" if registro["estado"] == "cancelada" else "Confirmada",
        "duracion_minutos": registro["duracion_minutos"]
    }

@app.get("/")
def inicio():
    return {"mensaje": "GymBot API funcionando correctamente con SQLite"}

@app.get("/servicios")
def consultar_servicios():
    return SERVICIOS_JSON

@app.get("/reservas")
def listar_reservas():
    return [formato_cliente(r) for r in agenda.listar()]

@app.get("/disponibilidad")
def consultar_disponibilidad(clase: str, fecha: str, hora: str = ""):
    resultado = responder(agenda.disponibilidad, fecha, clase, hora)
    return resultado

@app.post("/reservas", status_code=201)
def crear_reserva(reserva: ReservaNueva):
    tipo_esperado = CATALOGO.get(reserva.clase, {}).get("tipo")
    if tipo_esperado is None:
        raise HTTPException(status_code=422, detail="La clase o servicio no existe")
    if reserva.tipo.casefold() not in {"clase", "valoracion", "valoración"}:
        raise HTTPException(status_code=422, detail="El tipo debe ser clase o valoracion")
    if (reserva.tipo.casefold() == "valoracion") != (tipo_esperado == "valoracion"):
        raise HTTPException(status_code=422, detail="El tipo no corresponde al servicio")
    registro = responder(agenda.crear, reserva.nombre, reserva.clase, reserva.fecha, reserva.hora)
    return formato_cliente(registro)

@app.post("/consultarReserva")
def consultar_reserva(datos: ConsultaReserva):
    return formato_cliente(responder(agenda.consultar, datos.codigo.strip().upper()))

@app.post("/modificarReserva")
def modificar_reserva(datos: ModificacionReserva):
    registro = responder(agenda.modificar, datos.codigo.strip().upper(), datos.clase, datos.fecha, datos.hora)
    # La API conserva el nombre original; el modelo de cliente espera nombre en respuesta.
    return formato_cliente(registro)

@app.post("/cancelarReserva")
def cancelar_reserva(datos: ConsultaReserva):
    return formato_cliente(responder(agenda.cancelar, datos.codigo.strip().upper()))
