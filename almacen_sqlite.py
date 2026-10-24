"""Almacenamiento de reservas de GymBot en SQLite."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

class ConflictoReserva(ValueError):
    pass

class ReservaNoEncontrada(ValueError):
    pass

def minutos(hora):
    try:
        h, m = map(int, hora.split(":"))
    except Exception as exc:
        raise ValueError("Usa la hora en formato HH:MM") from exc
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError("Hora inválida")
    return h * 60 + m

def texto_hora(valor):
    return f"{valor // 60:02d}:{valor % 60:02d}"

class AgendaSQLite:
    """Agenda adaptada a las clases y valoraciones de GymBot.

    Las clases grupales admiten hasta 10 reservas para el mismo servicio,
    fecha y hora. Una reserva de otro servicio no puede cruzarse en el tiempo.
    """
    def __init__(self, ruta, servicios, capacidad_clase=10):
        self.ruta = Path(ruta).resolve()
        self.servicios = servicios
        self.capacidad_clase = capacidad_clase
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self.conexion(escritura=True) as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS reservas (
                    codigo TEXT PRIMARY KEY,
                    cliente TEXT NOT NULL,
                    servicio TEXT NOT NULL,
                    fecha TEXT NOT NULL,
                    hora TEXT NOT NULL,
                    duracion_minutos INTEGER NOT NULL CHECK (duracion_minutos > 0),
                    estado TEXT NOT NULL CHECK (estado IN ('activa', 'cancelada'))
                )
            """)
            con.execute("CREATE INDEX IF NOT EXISTS idx_reservas_fecha_estado ON reservas(fecha, estado)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_reservas_servicio_fecha ON reservas(servicio, fecha, hora)")

    @contextmanager
    def conexion(self, escritura=False):
        con = sqlite3.connect(self.ruta, timeout=15, isolation_level=None)
        con.row_factory = sqlite3.Row
        try:
            if escritura:
                con.execute("BEGIN IMMEDIATE")
            yield con
            if escritura:
                con.commit()
        except Exception:
            if escritura:
                con.rollback()
            raise
        finally:
            con.close()

    def duracion(self, servicio):
        item = self.servicios.get(servicio)
        if not item:
            raise ValueError("El servicio solicitado no existe en el catálogo de GymBot")
        dur = item.get("duracion_minutos", 60)
        if type(dur) is not int or dur <= 0:
            raise ValueError("La duración del servicio debe ser un entero positivo")
        return dur

    def validar_fecha(self, fecha, permitir_pasado=False):
        try:
            valor = date.fromisoformat(fecha)
        except (TypeError, ValueError) as exc:
            raise ValueError("La fecha debe tener el formato AAAA-MM-DD") from exc
        if valor.isoformat() != fecha:
            raise ValueError("La fecha debe tener el formato AAAA-MM-DD")
        if not permitir_pasado and valor < date.today():
            raise ValueError("No se puede reservar una fecha pasada")
        return valor

    def validar_horario_servicio(self, servicio, fecha, hora, permitir_pasado=False):
        dia = self.validar_fecha(fecha, permitir_pasado).weekday()
        inicio = minutos(hora)
        item = self.servicios.get(servicio)
        if item is None:
            raise ValueError("El servicio solicitado no existe en GymBot")
        duracion = self.duracion(servicio)
        dias = item.get("dias_indices", [])
        if dia not in dias:
            raise ValueError(f"{servicio} no está disponible ese día")
        horas = item.get("horas")
        if horas is not None and hora not in horas:
            raise ValueError(f"{servicio} no está disponible a las {hora}")
        rango = item.get("rango_horas")
        if rango:
            desde, hasta = map(minutos, rango)
            if inicio < desde or inicio + duracion > hasta:
                raise ValueError(f"{servicio} solo está disponible entre {rango[0]} y {rango[1]}")
            if (inicio - desde) % item.get("paso_minutos", duracion) != 0:
                raise ValueError(f"Selecciona una hora válida para {servicio}")
        return inicio, duracion

    def ocupado(self, con, fecha, inicio, duracion, servicio, excluir=""):
        filas = con.execute(
            "SELECT codigo, servicio, hora, duracion_minutos FROM reservas "
            "WHERE fecha=? AND estado='activa' AND codigo<>?",
            (fecha, excluir)
        ).fetchall()
        fin = inicio + duracion
        for fila in filas:
            otro_inicio = minutos(fila["hora"])
            otro_fin = otro_inicio + fila["duracion_minutos"]
            se_cruzan = inicio < otro_fin and fin > otro_inicio
            if not se_cruzan:
                continue
            # Las clases grupales pueden compartir exactamente el mismo slot
            # hasta el límite definido, pero no solaparse con otro servicio.
            mismo_slot = fila["servicio"] == servicio and otro_inicio == inicio and otro_fin == fin
            if mismo_slot:
                cantidad = con.execute(
                    "SELECT COUNT(*) FROM reservas WHERE fecha=? AND hora=? AND servicio=? "
                    "AND estado='activa' AND codigo<>?",
                    (fecha, texto_hora(inicio), servicio, excluir)
                ).fetchone()[0]
                limite = self.capacidad_clase if self.servicios[servicio].get("tipo") == "clase" else 1
                if cantidad >= limite:
                    return True
                continue
            return True
        return False

    def disponibilidad(self, fecha, servicio, hora=""):
        inicio, duracion = self.validar_horario_servicio(servicio, fecha, hora or self.servicios[servicio].get("horas", [""])[0] if self.servicios.get(servicio, {}).get("horas") else hora or self.servicios[servicio]["rango_horas"][0])
        with self.conexion() as con:
            if hora:
                ocupadas = con.execute(
                    "SELECT COUNT(*) FROM reservas WHERE fecha=? AND hora=? AND servicio=? AND estado='activa'",
                    (fecha, hora, servicio)
                ).fetchone()[0]
                limite = self.capacidad_clase if self.servicios[servicio].get("tipo") == "clase" else 1
                disponible = ocupadas < limite and not self.ocupado(con, fecha, inicio, duracion, servicio)
                return {"fecha": fecha, "servicio": servicio, "hora": hora,
                        "duracion_minutos": duracion, "disponible": disponible,
                        "cupos_disponibles": max(0, limite - ocupadas)}
            horas = self.servicios[servicio].get("horas")
            if horas is None:
                desde, hasta = map(minutos, self.servicios[servicio]["rango_horas"])
                paso = self.servicios[servicio].get("paso_minutos", duracion)
                horas = [texto_hora(x) for x in range(desde, hasta - duracion + 1, paso)]
            resultado = []
            for h in horas:
                ini = minutos(h)
                ocupadas = con.execute(
                    "SELECT COUNT(*) FROM reservas WHERE fecha=? AND hora=? AND servicio=? AND estado='activa'",
                    (fecha, h, servicio)
                ).fetchone()[0]
                limite = self.capacidad_clase if self.servicios[servicio].get("tipo") == "clase" else 1
                disponible = ocupadas < limite and not self.ocupado(con, fecha, ini, duracion, servicio)
                if disponible:
                    resultado.append({"hora": h, "cupos_disponibles": max(0, limite-ocupadas)})
            return {"fecha": fecha, "servicio": servicio, "duracion_minutos": duracion, "horas_disponibles": resultado}

    def listar(self):
        with self.conexion() as con:
            return [dict(r) for r in con.execute("SELECT * FROM reservas ORDER BY fecha, hora, codigo")]

    def obtener(self, con, codigo):
        fila = con.execute("SELECT * FROM reservas WHERE codigo=?", (codigo.upper(),)).fetchone()
        if fila is None:
            raise ReservaNoEncontrada("No se encontró una reserva con ese código")
        return dict(fila)

    def consultar(self, codigo):
        with self.conexion() as con:
            return self.obtener(con, codigo)

    def crear(self, cliente, servicio, fecha, hora):
        if not isinstance(cliente, str) or len(cliente.strip()) < 2:
            raise ValueError("Indica el nombre completo del cliente")
        inicio, duracion = self.validar_horario_servicio(servicio, fecha, hora)
        codigo = "GYM" + uuid4().hex[:6].upper()
        with self.conexion(escritura=True) as con:
            if self.ocupado(con, fecha, inicio, duracion, servicio):
                raise ConflictoReserva("El horario está ocupado o alcanzó su capacidad")
            con.execute("INSERT INTO reservas VALUES (?, ?, ?, ?, ?, ?, 'activa')",
                        (codigo, cliente.strip(), servicio, fecha, hora, duracion))
            return self.obtener(con, codigo)

    def modificar(self, codigo, servicio, fecha, hora):
        inicio, duracion = self.validar_horario_servicio(servicio, fecha, hora)
        with self.conexion(escritura=True) as con:
            actual = self.obtener(con, codigo)
            if actual["estado"] != "activa":
                raise ConflictoReserva("No se puede modificar una reserva cancelada")
            if self.ocupado(con, fecha, inicio, duracion, servicio, excluir=codigo.upper()):
                raise ConflictoReserva("El nuevo intervalo está ocupado o alcanzó su capacidad")
            con.execute("UPDATE reservas SET servicio=?, fecha=?, hora=?, duracion_minutos=? WHERE codigo=?",
                        (servicio, fecha, hora, duracion, codigo.upper()))
            return self.obtener(con, codigo)

    def cancelar(self, codigo):
        with self.conexion(escritura=True) as con:
            actual = self.obtener(con, codigo)
            if actual["estado"] != "activa":
                raise ConflictoReserva("La reserva ya está cancelada")
            con.execute("UPDATE reservas SET estado='cancelada' WHERE codigo=?", (codigo.upper(),))
            return self.obtener(con, codigo)

    def importar_json(self, ruta):
        registros = json.loads(Path(ruta).read_text(encoding="utf-8-sig"))
        if isinstance(registros, dict):
            registros = registros.get("reservas")
        if not isinstance(registros, list):
            raise ValueError("reservas.json debe contener una lista de reservas")
        nuevos = existentes = 0
        with self.conexion(escritura=True) as con:
            for r in registros:
                codigo = str(r.get("codigo", "")).strip().upper()
                cliente = str(r.get("cliente", r.get("nombre", ""))).strip()
                servicio = str(r.get("servicio", r.get("clase", ""))).strip()
                fecha = str(r.get("fecha", "")).strip()
                hora = str(r.get("hora", "")).strip()
                estado_original = str(r.get("estado", "")).strip().casefold()
                estado = "cancelada" if estado_original in {"cancelada", "cancelado", "cancelled"} else "activa"
                if not all([codigo, cliente, servicio, fecha, hora]):
                    raise ValueError("Hay una reserva con campos vacíos; revisa reservas.json")
                if servicio not in self.servicios:
                    raise ValueError(f"El servicio {servicio!r} no coincide con el catálogo")
                self.validar_fecha(fecha, permitir_pasado=True)
                inicio = minutos(hora)
                duracion = int(r.get("duracion_minutos", self.duracion(servicio)))
                if duracion <= 0 or inicio + duracion > 1440:
                    raise ValueError(f"Duración u hora inválida en la reserva {codigo}")
                fila = (codigo, cliente, servicio, fecha, hora, duracion, estado)
                previa = con.execute("SELECT * FROM reservas WHERE codigo=?", (codigo,)).fetchone()
                if previa:
                    if tuple(previa) != fila:
                        raise ConflictoReserva(f"El código {codigo} ya existe con datos diferentes")
                    existentes += 1
                    continue
                con.execute("INSERT INTO reservas VALUES (?, ?, ?, ?, ?, ?, ?)", fila)
                nuevos += 1
        return {"importadas": nuevos, "ya_existentes": existentes}
