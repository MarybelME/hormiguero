"""Punto de entrada de la aplicación web.

Crea la aplicación FastAPI, registra las rutas de la API y sirve el frontend estático en `/`.
Ejecutar desde la raíz del proyecto:

    uvicorn app.main:app --reload --app-dir backend
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from app import __version__
from app.api.rutas_rest import router as router_rest
from app.api.ws import router as router_ws
from app.servicio.controlador import ControladorSimulacion

CARPETA_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"


class FrontendSinCache(StaticFiles):
    """Archivos del frontend con `Cache-Control: no-cache`.

    El navegador guarda los módulos JS; sin esta cabecera puede reusar uno de una versión
    anterior junto a otro nuevo y la interfaz deja de funcionar. Con `no-cache` revalida
    cada archivo (si no cambió, el servidor responde 304 sin reenviarlo).
    """

    async def get_response(self, path: str, scope) -> Response:
        respuesta = await super().get_response(path, scope)
        respuesta.headers["Cache-Control"] = "no-cache"
        return respuesta


@asynccontextmanager
async def ciclo_de_vida(aplicacion: FastAPI) -> AsyncIterator[None]:
    yield
    await aplicacion.state.controlador.detener()  # al apagar, se detiene el bucle


app = FastAPI(
    title="Simulador educativo de hormiguero",
    description="Instrumento didáctico para la materia Simulación.",
    version=__version__,
    lifespan=ciclo_de_vida,
)
# Una sola simulación compartida por todos los clientes (DISENO.md, decisión m).
app.state.controlador = ControladorSimulacion()
app.include_router(router_rest)
app.include_router(router_ws)
# Se monta al final para que las rutas /api tengan prioridad sobre los archivos estáticos.
app.mount("/", FrontendSinCache(directory=CARPETA_FRONTEND, html=True), name="frontend")
