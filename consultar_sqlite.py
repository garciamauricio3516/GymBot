"""Muestra las reservas guardadas en reservas.db."""
import sqlite3
from pathlib import Path

ruta = Path(__file__).resolve().parent / "reservas.db"
if not ruta.exists():
    print("Todavía no existe reservas.db. Ejecuta primero: python migrar_reservas.py")
    raise SystemExit(0)
with sqlite3.connect(ruta) as con:
    con.row_factory = sqlite3.Row
    filas = con.execute(
        "SELECT codigo, cliente, servicio, fecha, hora, duracion_minutos, estado "
        "FROM reservas ORDER BY fecha, hora"
    ).fetchall()
    for fila in filas:
        print(dict(fila))
    print(f"\nTotal de reservas: {len(filas)}")
