# GymBot — Chatbot para gimnasio

GymBot es un chatbot en español para consultar los planes y servicios de un gimnasio y gestionar reservas. El proyecto integra **Groq** para interpretar el lenguaje natural, **Python** para controlar la lógica, **FastAPI** para exponer las operaciones del negocio, **SQLite** para persistir las reservas y **Gradio** para ofrecer una interfaz web de chat.

> Este README explica cómo ejecutar el proyecto en un computador Windows desde un clon limpio del repositorio. Los nombres de variables de entorno y comandos pueden adaptarse a otros sistemas operativos.

## Tabla de contenido

- [Funciones](#funciones)
- [Tecnologías](#tecnologías)
- [Arquitectura y archivos](#arquitectura-y-archivos)
- [Requisitos previos](#requisitos-previos)
- [1. Descargar el proyecto](#1-descargar-el-proyecto)
- [2. Crear y activar el entorno virtual](#2-crear-y-activar-el-entorno-virtual)
- [3. Instalar dependencias](#3-instalar-dependencias)
- [4. Configurar Groq](#4-configurar-groq)
- [5. Preparar la base de datos](#5-preparar-la-base-de-datos)
- [6. Iniciar FastAPI](#6-iniciar-fastapi)
- [7. Iniciar Gradio](#7-iniciar-gradio)
- [8. Probar GymBot](#8-probar-gymbot)
- [Reglas de reservas](#reglas-de-reservas)
- [Persistencia y reinicio](#persistencia-y-reinicio)
- [Solución de problemas](#solución-de-problemas)
- [Seguridad antes de publicar en GitHub](#seguridad-antes-de-publicar-en-github)

## Funciones

- Consultar planes, precios, horarios y clases.
- Consultar disponibilidad para una fecha, servicio y hora.
- Solicitar la creación de una reserva y confirmarla explícitamente.
- Consultar, modificar y cancelar reservas mediante su código.
- Mantener el contexto de la conversación durante la sesión de chat.
- Guardar las reservas en una base de datos SQLite para conservarlas después de reiniciar la API.
- Validar los horarios y rechazar reservas que se crucen cuando no hay capacidad disponible.

## Tecnologías

- Python 3.11 o posterior (se recomienda Python 3.12 o 3.13).
- FastAPI y Uvicorn.
- Gradio 6.x.
- Pydantic.
- SQLite, incluido en la biblioteca estándar de Python.
- API de Groq y un modelo habilitado en la cuenta del usuario.

## Arquitectura y archivos

| Archivo | Responsabilidad |
|---|---|
| `main.py` | API FastAPI, endpoints y validación de solicitudes. |
| `almacen_sqlite.py` | Persistencia SQLite, consulta de disponibilidad y operaciones de reservas. |
| `app_gradio.py` | Interfaz web del chatbot, botones de confirmación, descarte y reinicio. |
| `chatbot_memoria.py` | Contexto conversacional y procesamiento de cada turno. |
| `consulta_llm.py` | Comunicación con Groq, interpretación de solicitudes y llamadas a FastAPI. |
| `servicios.json` | Catálogo visible de planes, clases, precios y horarios. |
| `negocio.json` | Reglas de agenda, duración y horarios permitidos por servicio. |
| `migrar_reservas.py` | Importación inicial del histórico de `reservas.json` a SQLite. |
| `consultar_sqlite.py` | Herramienta de consola para revisar las reservas guardadas en SQLite. |
| `requirements.txt` | Dependencias de Python. |
| `reservas.json` | Archivo histórico de origen para la migración inicial; no es la base principal después de migrar. |
| `reservas.db` | Base de datos SQLite creada localmente al ejecutar la migración o inicializar la API. No debe subirse al repositorio. |

La arquitectura general es:

```text
Usuario
  ↓
Interfaz Gradio (app_gradio.py)
  ↓
Memoria de conversación (chatbot_memoria.py)
  ↓
Groq: interpretación del mensaje
  ↓
Python: control de la acción y confirmación
  ↓
FastAPI (main.py)
  ↓
SQLite (reservas.db)
```

## Requisitos previos

1. Instalar Python desde [python.org](https://www.python.org/downloads/). En el instalador de Windows, marcar **Add Python to PATH**.
2. Tener acceso a internet para instalar dependencias y consultar la API de Groq.
3. Crear una cuenta en [Groq](https://console.groq.com/) y obtener una API key.
4. Tener el identificador de un modelo que esté habilitado en esa cuenta. El identificador exacto puede cambiar; se configura como variable de entorno y no se fija en el código.
5. Git, si se va a clonar el repositorio mediante la terminal. También se puede descargar el repositorio como ZIP desde GitHub.

Comprueba Python y Git en CMD:

```bat
python --version
git --version
```

## 1. Descargar el proyecto

### Opción A: clonar desde GitHub

Abre CMD o PowerShell en la carpeta donde quieras guardar el proyecto y ejecuta (reemplaza la URL por la URL real del repositorio):

```bat
git clone https://github.com/USUARIO/REPOSITORIO.git
cd REPOSITORIO
```

### Opción B: descargar ZIP

1. En GitHub, pulsa **Code → Download ZIP**.
2. Extrae el archivo en una carpeta local.
3. Abre una terminal dentro de la carpeta que contiene `main.py`, `app_gradio.py` y `requirements.txt`.

No copies el entorno virtual `venv` de otro computador. Cada persona debe crear su propio entorno local.

## 2. Crear y activar el entorno virtual

Desde la carpeta raíz del proyecto, ejecuta:

```bat
python -m venv .venv
.venv\Scripts\activate
```

Si la activación funcionó, la terminal mostrará `(.venv)` al principio de la línea.

Si Windows no encuentra Python, revisa la instalación y prueba `py -m venv .venv`. Luego activa con `.venv\Scripts\activate`.

## 3. Instalar dependencias

Con el entorno virtual activado:

```bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Comprueba que las dependencias se instalaron sin errores. No es necesario instalar SQLite por separado: viene incluido con Python.

## 4. Configurar Groq

GymBot requiere dos variables de entorno:

- `GROQ_API_KEY`: API key privada de Groq.
- `GROQ_MODEL`: identificador de un modelo habilitado en Groq.

También utiliza:

- `CHATBOT_API_URL`: dirección de FastAPI. En este proyecto será `http://127.0.0.1:8011`.

### Configuración recomendada en PowerShell

Abre PowerShell en la carpeta del proyecto. Las variables solo estarán disponibles en esa ventana y sus procesos hijos:

```powershell
$env:CHATBOT_API_URL = "http://127.0.0.1:8011"
$env:GROQ_MODEL = "PEGA_AQUI_EL_ID_DEL_MODELO_HABILITADO"
$secureKey = Read-Host "Introduce tu API key de Groq" -AsSecureString
$env:GROQ_API_KEY = [System.Net.NetworkCredential]::new('', $secureKey).Password
```

Sustituye `PEGA_AQUI_EL_ID_DEL_MODELO_HABILITADO` por el identificador real del modelo disponible en tu cuenta. No escribas literalmente ese texto como modelo.

La clave se solicita de forma oculta y no debe agregarse a los archivos Python, al README, a capturas de pantalla ni a GitHub. Si cierras esa ventana, tendrás que volver a definir las variables en una nueva sesión.

### Alternativa en CMD

En CMD puedes establecer la URL y el modelo así:

```bat
set CHATBOT_API_URL=http://127.0.0.1:8011
set GROQ_MODEL=PEGA_AQUI_EL_ID_DEL_MODELO_HABILITADO
```

Para evitar que la clave quede visible en el historial de comandos, es preferible usar PowerShell con el método anterior. Si el programa solicita la clave por consola, introdúcela cuando se pida.

## 5. Preparar la base de datos

### Primera ejecución con un histórico de reservas

1. Haz una copia de seguridad del archivo `reservas.json` que quieras importar.
2. Asegúrate de que `reservas.json` sea el archivo de datos correcto y tenga la estructura esperada por el proyecto.
3. Desde la raíz del proyecto y con el entorno virtual activo, ejecuta:

   ```bat
   python migrar_reservas.py
   ```

4. Revisa el resumen que imprime el script. La base `reservas.db` se creará en la carpeta del proyecto y las reservas se importarán conservando sus códigos y estados cuando el formato de origen sea válido.

**Ejecuta la migración solo cuando quieras importar el histórico inicial.** El proceso no elimina `reservas.json`. Si ya existe una base de datos con reservas, no la borres ni la sobrescribas sin hacer una copia de seguridad. Si no necesitas datos históricos, prepara un `reservas.json` de ejemplo sin información personal y con la estructura aceptada por el importador antes de ejecutar la migración.

Para revisar las reservas almacenadas:

```bat
python consultar_sqlite.py
```

### Importante para un clon nuevo

Los datos locales reales no deben viajar en el repositorio. En un repositorio público, mantén un `reservas.json` de ejemplo sin nombres ni reservas reales, o adapta la migración para que el archivo histórico sea opcional. Cada desarrollador tendrá su propia `reservas.db` local.

## 6. Iniciar FastAPI

Abre una primera terminal en la carpeta raíz del proyecto. Activa el entorno virtual y configura la URL de la API:

```bat
.venv\Scripts\activate
set CHATBOT_API_URL=http://127.0.0.1:8011
python -m uvicorn main:app --host 127.0.0.1 --port 8011
```

Deja esa terminal abierta mientras utilices el chatbot. Para comprobar la API, abre estas direcciones en el navegador:

- Documentación interactiva: <http://127.0.0.1:8011/docs>
- Comprobación básica: <http://127.0.0.1:8011/>

La documentación permite probar las rutas disponibles. Las operaciones que crean, modifican o cancelan reservas cambian datos, así que pruébalas con datos de demostración.

## 7. Iniciar Gradio

Abre una **segunda terminal** en la misma carpeta del proyecto. Activa el entorno virtual y define las variables de entorno en esa ventana también:

```bat
.venv\Scripts\activate
set CHATBOT_API_URL=http://127.0.0.1:8011
set GROQ_MODEL=PEGA_AQUI_EL_ID_DEL_MODELO_HABILITADO
```

Si utilizas CMD y no has configurado `GROQ_API_KEY` en esa ventana, puedes ejecutar el siguiente comando para establecerla temporalmente:

```bat
set GROQ_API_KEY=TU_CLAVE_PRIVADA_DE_GROQ
```

Reemplaza el texto por la clave real; no la compartas ni la subas al repositorio. Si prefieres evitar que aparezca en el historial, configura la variable desde PowerShell siguiendo la sección anterior y ejecuta Gradio desde esa misma sesión.

Inicia la interfaz:

```bat
python app_gradio.py
```

Cuando aparezca el mensaje de inicio, abre <http://127.0.0.1:7860>.

**Mantén abiertas las dos terminales:** una para FastAPI y otra para Gradio. Si cierras la terminal de FastAPI, el chat no podrá consultar ni guardar reservas.

## 8. Probar GymBot

Prueba estas solicitudes desde la interfaz Gradio:

1. **Consultar los planes:** `¿Qué planes tiene el gimnasio y cuánto cuestan?`
2. **Consultar una clase:** `¿Qué días y a qué hora hay Spinning?`
3. **Consultar disponibilidad:** `¿Hay disponibilidad para valoración física el lunes 19 de octubre de 2026 a las 08:00?`
4. **Crear una reserva:** `Quiero reservar Spinning el miércoles 21 de octubre de 2026 a las 18:00. Mi nombre es Persona de Prueba.`
5. Comprueba el resumen que presenta GymBot y pulsa **Confirmar operación** solo si los datos son correctos.
6. Anota el código devuelto y úsalo para probar una consulta o cancelación de esa reserva de demostración.
7. Intenta reservar una valoración física que se cruce con otra cita existente. La API debe rechazar la operación si no hay capacidad disponible.
8. Pulsa **Reiniciar conversación** y comprueba que se borra el contexto de la sesión de chat. Reiniciar la conversación no debe borrar las reservas guardadas en SQLite.

Usa fechas futuras válidas y respeta los días y horarios de cada servicio. Los resultados dependen de la fecha actual y de las reservas existentes en la base local.

## Reglas de reservas

Las reglas se definen en los archivos de configuración y en `almacen_sqlite.py`:

- Las clases grupales tienen una duración de 60 minutos y capacidad de hasta 10 reservas por clase y horario.
- Las valoraciones físicas duran 60 minutos, se ofrecen de lunes a viernes y deben iniciar dentro del rango de atención definido.
- Los horarios de las clases deben corresponder al calendario del servicio.
- No se deben crear reservas en fechas pasadas.
- Las operaciones de escritura comprueban la disponibilidad antes de guardar los cambios.
- Una reserva cancelada conserva su registro y cambia su estado; no se borra el histórico.
- Crear, modificar y cancelar requiere confirmar la operación desde la interfaz.

Si FastAPI responde con HTTP `409`, normalmente indica que la operación entra en conflicto con una reserva existente o con una regla de disponibilidad. Revisa el detalle devuelto por la API antes de volver a intentar la operación.

## Persistencia y reinicio

- **Conversación:** el estado del chat se mantiene en la sesión de Gradio. El botón de reinicio limpia ese contexto.
- **Reservas:** se guardan en `reservas.db`, por lo que sobreviven al cierre y reinicio de FastAPI.
- **Histórico original:** `reservas.json` se utiliza como fuente para la migración inicial y se conserva como archivo independiente.
- **Copia de seguridad:** detén FastAPI y copia `reservas.db` a una ubicación segura antes de realizar cambios importantes.

No borres `reservas.db` para solucionar errores: primero haz una copia y consulta el mensaje de error.

## Solución de problemas

### `python` no se reconoce

Instala Python y habilita **Add Python to PATH**. Cierra y vuelve a abrir la terminal. En Windows también puedes probar `py --version`.

### No se encuentra `.venv\Scripts\activate`

Verifica que la terminal esté en la carpeta raíz del proyecto. Si todavía no existe el entorno, créalo con `python -m venv .venv`.

### Error al instalar dependencias

Activa `.venv` y vuelve a ejecutar `python -m pip install -r requirements.txt`. Comprueba que tienes conexión a internet y una versión de Python compatible.

### Gradio no conecta con FastAPI

- Comprueba que FastAPI siga ejecutándose en el puerto `8011`.
- Abre <http://127.0.0.1:8011/docs>.
- Verifica que `CHATBOT_API_URL` sea `http://127.0.0.1:8011` en la terminal que inicia Gradio.

### Error de autenticación o modelo de Groq

Comprueba que `GROQ_API_KEY` tenga una clave válida y que `GROQ_MODEL` sea el identificador de un modelo habilitado en tu cuenta. Reinicia Gradio después de cambiar las variables.

### HTTP `409` al crear o modificar una reserva

La operación fue rechazada por un conflicto de disponibilidad. Revisa la fecha, la hora, la duración y las reservas existentes en <http://127.0.0.1:8011/docs>. No repitas una operación hasta comprobar si se guardó.

### El puerto ya está ocupado

Cierra la instancia anterior que esté usando el puerto o configura otro puerto y actualiza la URL de FastAPI en `CHATBOT_API_URL`.

### No aparece una reserva después de reiniciar

Comprueba que estás ejecutando la API desde la misma carpeta del proyecto y que `reservas.db` se encuentra allí. Ejecuta `python consultar_sqlite.py` para revisar el contenido.

## Seguridad antes de publicar en GitHub

Antes de subir el proyecto, revisa los archivos y configura `.gitignore`. **No subas**:

- `venv/` ni `.venv/`.
- `__pycache__/` y archivos `.pyc`.
- `reservas.db`, copias de seguridad de la base o bases con datos reales.
- `GROQ_API_KEY`, archivos `.env` ni otras credenciales.
- `memoria_chatbot.json` si contiene conversaciones reales.
- `reservas.json` si contiene nombres, códigos o datos reales de usuarios. Para el repositorio, usa datos ficticios o una plantilla vacía compatible con el importador.

Ejemplo de `.gitignore` recomendado:

```gitignore
# Entornos virtuales
venv/
.venv/

# Python
__pycache__/
*.py[cod]

# Secretos y configuración local
.env
.env.*
!.env.example

# Bases de datos y respaldos
*.db
*.sqlite
*.sqlite3
*.bak
*.backup

# Datos personales locales
memoria_chatbot.json
reservas.local.json
reservas_reales.json

# Sistema operativo / editor
.DS_Store
Thumbs.db
.vscode/
.idea/
```

Si `reservas.json` o `memoria_chatbot.json` ya fueron agregados a Git, añadirlos a `.gitignore` no los elimina del historial. Si contienen datos personales, retíralos del repositorio y considera que una eliminación de la versión más reciente no borra automáticamente las copias anteriores del historial de Git.

## Alcance

Esta configuración está pensada para desarrollo local y demostración académica. Para desplegar GymBot en internet se requiere una configuración adicional de seguridad, gestión de secretos, autenticación, HTTPS, copias de seguridad y control de acceso a las reservas.
