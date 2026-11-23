# GymBot — Chatbot de Gimnasio con Telegram y FastAPI

GymBot es un chatbot en español para consultar los planes y servicios de un gimnasio y gestionar reservas de forma segura. El proyecto integra **Groq** para interpretar el lenguaje natural, **Python** para controlar la lógica, **FastAPI** para exponer los endpoints seguros del negocio, **SQLite** para persistir las reservas y una interfaz de **Telegram** para la interacción directa con el usuario.

> Este README explica cómo ejecutar el proyecto en un computador Windows desde un clon limpio del repositorio. Los nombres de variables de entorno y comandos pueden adaptarse a otros sistemas operativos.

## Tabla de contenido

- [Funciones](#funciones)
- [Tecnologías](#tecnologías)
- [Arquitectura y archivos](#arquitectura-y-archivos)
- [Requisitos previos](#requisitos-previos)
- [1. Descargar el proyecto](#1-descargar-el-proyecto)
- [2. Crear y activar el entorno virtual](#2-crear-y-activar-el-entorno-virtual)
- [3. Instalar dependencias](#3-instalar-dependencias)
- [4. Configurar variables de entorno y Groq](#4-configurar-variables-de-entorno-y-groq)
- [5. Preparar la base de datos](#5-preparar-la-base-de-datos)
- [6. Iniciar FastAPI](#6-iniciar-fastapi)
- [7. Iniciar el Bot de Telegram](#7-iniciar-el-bot-de-telegram)
- [8. Probar GymBot en Telegram](#8-probar-gymbot-en-telegram)
- [Reglas de reservas](#reglas-de-reservas)
- [Persistencia y reinicio](#persistencia-y-reinicio)
- [Solución de problemas](#solución-de-problemas)
- [Seguridad antes de publicar en GitHub](#seguridad-antes-de-publicar-en-github)

## Funciones

- Consultar planes, precios, horarios y clases del gimnasio.
- Consultar disponibilidad para una fecha, servicio y hora específica.
- Solicitar la creación de una reserva, validando la capacidad y confirmándola explícitamente.
- Consultar, modificar y cancelar reservas de forma segura asociadas al usuario de Telegram.
- Mantener el contexto de la conversación durante la sesión de chat con el modelo de Groq.
- Guardar las reservas en una base de datos SQLite (`reservas.db`) con soporte para transacciones y control de concurrencia.
- Validar los horarios y rechazar reservas que se crucen cuando no hay capacidad disponible.

## Tecnologías

- Python 3.11 o posterior (recomendado Python 3.12 / 3.13).
- FastAPI y Uvicorn.
- `python-telegram-bot` para la integración con Telegram.
- Pydantic v2 para validación de esquemas.
- SQLite, incluido en la biblioteca estándar de Python.
- API de Groq y modelo de lenguaje compatible.

## Arquitectura y archivos

| Archivo | Responsabilidad |
|---|---|
| `api_telegram.py` | API FastAPI, enrutador protegido por API Key (`X-API-Key`) y validación de identidad por Telegram. |
| `bot_telegram.py` | Lógica del bot de Telegram, manejo de estados, integración con Groq y peticiones al backend. |
| `almacen_sqlite.py` | Persistencia SQLite, reglas de negocio, control de capacidad y operaciones de reservas. |
| `negocio.json` | Catálogo de servicios, duración y horarios permitidos. |
| `requirements.txt` | Dependencias del proyecto. |
| `reservas.db` | Base de datos SQLite local generada automáticamente. No debe subirse al repositorio. |

La arquitectura general es:

```text
Usuario en Telegram
      ↓
Bot de Telegram (bot_telegram.py)
      ↓
Groq: Interpretación de lenguaje natural
      ↓
API FastAPI (api_telegram.py) [Protegida por Token API Key]
      ↓
Almacenamiento SQLite (reservas.db)