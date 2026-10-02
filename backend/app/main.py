"""Punto de entrada de la aplicación web.

Crea la aplicación FastAPI, registra las rutas de la API y sirve el frontend estático en `/`.
Ejecutar desde la raíz del proyecto:

    uvicorn app.main:app --reload --app-dir backend
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.rutas_rest import router as router_rest

CARPETA_FRONTEND = Path(__file__).resolve().parents[2] / "frontend"

app = FastAPI(
    title="Simulador educativo de hormiguero",
    description="Instrumento didáctico para la materia Simulación.",
    version=__version__,
)
app.include_router(router_rest)
# Se monta al final para que las rutas /api tengan prioridad sobre los archivos estáticos.
app.mount("/", StaticFiles(directory=CARPETA_FRONTEND, html=True), name="frontend")
