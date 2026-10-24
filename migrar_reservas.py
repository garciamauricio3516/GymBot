"""Importa reservas.json a reservas.db sin borrar el archivo original."""
import json
from pathlib import Path
from almacen_sqlite import AgendaSQLite

BASE = Path(__file__).resolve().parent
negocio = json.loads((BASE / "negocio.json").read_text(encoding="utf-8-sig"))
agenda = AgendaSQLite(BASE / "reservas.db", negocio["servicios"])
resultado = agenda.importar_json(BASE / "reservas.json")
print(json.dumps(resultado, ensure_ascii=False, indent=2))
