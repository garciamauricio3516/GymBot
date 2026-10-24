# Bitácora de instalación y ejecución de GymBot

**Objetivo:** explicar visualmente cómo descargar GymBot desde GitHub,
configurar los datos propios, instalar dependencias y ejecutar el
chatbot en Windows.

**Arquitectura:** Usuario → Gradio → `chatbot_memoria.py` /
`consulta_llm.py` → Groq y FastAPI → SQLite (`reservas.db`).

## 1. Mapa general

``` text
Descargar proyecto de GitHub
          ↓
Abrir CMD en la carpeta GymBot
          ↓
Crear/activar entorno virtual e instalar dependencias
          ↓
Configurar API key y modelo de Groq
          ↓
Preparar SQLite o migrar datos existentes
          ↓
Iniciar FastAPI (puerto 8011)
          ↓
Iniciar Gradio (puerto 7860)
          ↓
Probar consultas, reservas y persistencia
```

## 2. Requisitos

-   Windows 10/11.
-   Python en una versión compatible con `requirements.txt`.
-   Conexión a Internet.
-   Cuenta de Groq, una API key propia y un modelo habilitado.
-   Archivos del proyecto descargados desde GitHub.

**Nunca publiques la API key, contraseñas, bases de datos con
información real ni conversaciones privadas.**

## 3. Descargar el repositorio

En GitHub, abre el repositorio y selecciona **Code → Download ZIP**.
Extrae el ZIP, por ejemplo, en:

``` text
C:\Users\TU_USUARIO\GymBot
```

También puedes clonar con Git, reemplazando los marcadores por los datos
reales:

``` bat
git clone https://github.com/USUARIO/REPOSITORIO.git
cd REPOSITORIO
```

`USUARIO` y `REPOSITORIO` son ejemplos: debes reemplazarlos por la
dirección real.

## 4. Abrir CMD en la carpeta

Abre la carpeta que contiene `main.py`, haz clic en la barra de
direcciones del Explorador, escribe `cmd` y pulsa Enter.

Comprueba los archivos:

``` bat
dir
```

Si necesitas entrar manualmente a la carpeta:

``` bat
cd /d "C:\Users\TU_USUARIO\GymBot"
```

Reemplaza `TU_USUARIO` por el usuario de Windows de esa computadora.

## 5. Crear/activar entorno e instalar dependencias

Si el entorno virtual aún no existe:

``` bat
python -m venv venv
```

Actívalo:

``` bat
venv\Scripts\activate
```

Si la carpeta se llama `.venv`, usa `.venv\Scripts\activate`. Si ya
existe un entorno funcional, no crees otro.

Instala las dependencias:

``` bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si falta `requirements.txt`, comprueba que descargaste el repositorio
completo; no instales paquetes al azar.

## 6. Configurar Groq y la URL de FastAPI

Cada persona debe usar **su propia API key de Groq**. No se debe
escribir la clave directamente en el código ni subirla a GitHub.

En la ventana de CMD donde ejecutarás Gradio, configura:

``` bat
set GROQ_API_KEY=PEGA_AQUI_TU_CLAVE
set GROQ_MODEL=PEGA_AQUI_EL_ID_DEL_MODELO
set CHATBOT_API_URL=http://127.0.0.1:8011
```

Reemplaza los valores de ejemplo. El ID del modelo debe ser uno que esté
habilitado en la cuenta de Groq. Estas variables se mantienen solo en
esa ventana de CMD.

Si el programa solicita la clave con `getpass()` cuando no encuentra
`GROQ_API_KEY`, puedes introducirla al iniciar. No compartas capturas
donde aparezca la clave; si la publicaste accidentalmente, revócala y
genera otra.

**Normalmente no necesitas editar `consulta_llm.py` para poner tu
clave.** El programa debe leerla desde la variable de entorno o
solicitarla al arrancar.

## 7. Preparar SQLite

La base de datos local suele llamarse `reservas.db`.

-   Si es una instalación nueva, sigue las instrucciones de creación de
    la base de datos incluidas en la versión del repositorio.
-   Si vas a importar reservas antiguas y el proyecto incluye
    `migrar_reservas.py`, primero haz una copia de seguridad de los
    datos y después ejecuta:

``` bat
python migrar_reservas.py
```

-   Si el proyecto incluye `consultar_sqlite.py`, puedes revisar los
    registros con:

``` bat
python consultar_sqlite.py
```

Ejecuta estos comandos solo si esos archivos existen en la versión
descargada. No borres `reservas.json` ni `reservas.db` hasta verificar
que los datos importantes fueron conservados.

## 8. Iniciar FastAPI

Abre una primera ventana de CMD en la carpeta del proyecto:

``` bat
cd /d "C:\Users\TU_USUARIO\GymBot"
venv\Scripts\activate
set CHATBOT_API_URL=http://127.0.0.1:8011
python -m uvicorn main:app --host 127.0.0.1 --port 8011
```

Deja esa ventana abierta. Comprueba la API aquí:

**http://127.0.0.1:8011/docs**

Si FastAPI no inicia, revisa el error en esa terminal antes de
continuar.

## 9. Iniciar Gradio

Abre una **segunda** ventana de CMD. No cierres la de FastAPI:

``` bat
cd /d "C:\Users\TU_USUARIO\GymBot"
venv\Scripts\activate
set CHATBOT_API_URL=http://127.0.0.1:8011
set GROQ_MODEL=PEGA_AQUI_EL_ID_DEL_MODELO
```

Configura `GROQ_API_KEY` en esta ventana o introdúcela si el programa la
solicita. Después ejecuta:

``` bat
python app_gradio.py
```

Abre **http://127.0.0.1:7860**.

  Ventana   Servicio   Dirección
  --------- ---------- ------------------------------
  CMD 1     FastAPI    `http://127.0.0.1:8011/docs`
  CMD 2     Gradio     `http://127.0.0.1:7860`

Mantén ambas terminales abiertas. Para detener un servicio, vuelve a su
terminal y presiona `Ctrl + C`.

## 10. Pruebas recomendadas

### Prueba A --- Planes y precios

Escribe: `¿Qué planes tiene el gimnasio y cuánto cuestan?`

  Plan         Precio mensual Incluye
  ---------- ---------------- ---------------------------------------------
  Básico         \$60.000 COP Acceso al gimnasio
  Estándar       \$80.000 COP Acceso y clases grupales
  Premium       \$110.000 COP Acceso, clases grupales y valoración física

### Prueba B --- Horario de clase

Escribe: `¿Qué días hay Spinning y a qué hora?`

La configuración de GymBot indica lunes y miércoles a las 18:00, con
duración de una hora.

### Prueba C --- Crear reserva

Usa una fecha futura válida:

`Quiero reservar Spinning el miércoles [AAAA-MM-DD] a las 18:00. Mi nombre es [NOMBRE DE PRUEBA].`

Reemplaza los campos entre corchetes. Confirma solo después de verificar
nombre, servicio, fecha y hora. Guarda el código que devuelva la API.

### Prueba D --- Consultar reserva

Escribe: `Consulta la reserva [CODIGO_DEVUELTO]`.

Usa el código real obtenido en la prueba anterior; no inventes uno.

### Prueba E --- Cruce de horarios

Si existe una valoración de 08:00 a 09:00, una segunda de 08:30 a 09:30
debe rechazarse porque se cruza durante 30 minutos. La API puede
devolver HTTP 409; la interfaz debe mostrar un motivo comprensible.

### Prueba F --- Persistencia

1.  Crea una reserva de prueba y guarda su código.
2.  Detén FastAPI con `Ctrl + C`.
3.  Inicia FastAPI otra vez.
4.  Consulta el mismo código.
5.  Comprueba que la reserva continúa en `reservas.db`.

## 11. Qué debe reemplazar o configurar cada persona

  -----------------------------------------------------------------------
  Archivo/dato            ¿Se modifica?           Qué hacer
  ----------------------- ----------------------- -----------------------
  `GROQ_API_KEY`          Sí                      Poner la clave propia,
                                                  nunca publicarla

  `GROQ_MODEL`            Puede ser necesario     Usar el ID de un modelo
                                                  habilitado

  `CHATBOT_API_URL`       Solo si cambia puerto o Mantenerlo igual al
                          dirección               puerto de FastAPI

  `negocio.json` /        Solo si personaliza el  Actualizar planes,
  archivo de servicios    negocio                 precios, clases y
                                                  horarios

  `main.py`               No para ejecución       Contiene la API
                          normal                  

  `consulta_llm.py`       No para ejecución       Interpreta acciones y
                          normal                  llama a FastAPI

  `chatbot_memoria.py`    No para ejecución       Administra el contexto
                          normal                  conversacional

  `app_gradio.py`         No para ejecución       Presenta la interfaz
                          normal                  

  `requirements.txt`      No normalmente          Lista las dependencias

  `reservas.db`           No editar manualmente   Guarda las reservas
  -----------------------------------------------------------------------

Los nombres pueden variar según la versión del repositorio; comprueba
los archivos que realmente estén incluidos.

## 12. Proteger datos antes de subir a GitHub

Revisa o crea `.gitignore` en la raíz del proyecto. Ejemplo:

``` gitignore
venv/
.venv/
__pycache__/
*.py[cod]
.env
reservas.db
reservas.db-shm
reservas.db-wal
reservas.json
memoria_chatbot.json
```

`reservas.json` y `memoria_chatbot.json` solo deben publicarse si
contienen datos ficticios y no privados. Si se necesitan ejemplos para
una migración, crea copias con nombres y códigos de prueba.

Antes de subir cambios:

1.  Busca claves que empiecen por `gsk_` y contraseñas escritas en el
    código.
2.  Elimina datos reales de clientes e historiales.
3.  Ejecuta `git status` y revisa los archivos que se van a publicar.
4.  No subas `venv/`, archivos `.env` ni bases de datos privadas.

## 13. Solución de problemas

**`uvicorn` no se reconoce**

``` bat
python -m uvicorn main:app --host 127.0.0.1 --port 8011
```

**Falta un módulo**

``` bat
venv\Scripts\activate
python -m pip install -r requirements.txt
```

**Puerto ocupado:** revisa si ya existe una instancia ejecutándose. Si
cambias el puerto, actualiza también `CHATBOT_API_URL`.

**Error de Groq:** comprueba la clave, el ID del modelo, el acceso a
Internet y que el modelo esté habilitado.

**HTTP 409:** suele indicar un conflicto, por ejemplo un cruce con otra
reserva. Si Gradio muestra un texto genérico, revisa el manejo de
`HTTPError` en `consulta_llm.py` y el bloque de excepciones de
`app_gradio.py`.

**No abre el navegador:** verifica que el servidor correspondiente siga
ejecutándose y revisa el error en su terminal.

## 14. Lista final de comprobación

-   [ ] Descargué el repositorio y abrí la carpeta correcta.
-   [ ] Instalé las dependencias.
-   [ ] Configuré mi propia clave de Groq y un modelo habilitado.
-   [ ] FastAPI inicia en el puerto 8011 y `/docs` abre.
-   [ ] Gradio inicia en el puerto 7860.
-   [ ] Puedo consultar planes y horarios.
-   [ ] Puedo crear una reserva y recibir un código.
-   [ ] Puedo consultar una reserva.
-   [ ] Los cruces de horario se rechazan.
-   [ ] Las reservas permanecen después de reiniciar FastAPI.
-   [ ] No publiqué claves ni datos privados.

> **Nota:** esta bitácora describe el flujo esperado. Los comandos de
> migración y nombres de archivos deben comprobarse contra la versión
> exacta del repositorio. Antes de migrar datos que deban conservarse,
> realiza una copia de seguridad y prueba en una copia.
