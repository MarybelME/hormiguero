"""Rutas de experimentación: exportar a CSV (RF-61) y lotes de réplicas (RF-60).

Igual que el resto de la capa web, sólo traduce peticiones a llamadas del núcleo. Lo que
tarda (re-ejecutar una corrida, correr un lote) se hace en un hilo aparte para no detener
la simulación en vivo.
"""

import asyncio
import io
import os
import tempfile
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.background import BackgroundTask
from starlette.responses import FileResponse, Response

from app.config import SEMILLA_MAXIMA, ParametrosSimulacion
from app.estadisticas.exportar import escribir_lote, escribir_series, exportar_corrida
from app.servicio.controlador import AccionInvalida, ControladorSimulacion
from app.servicio.experimentos import ControladorExperimento

TIPO_CSV = "text/csv; charset=utf-8"
REPLICAS_MAXIMAS = 30
PASOS_MAXIMOS_LOTE = 5000

router = APIRouter(prefix="/api")


def _controlador(request: Request) -> ControladorSimulacion:
    return request.app.state.controlador


def _experimento(request: Request) -> ControladorExperimento:
    return request.app.state.experimento


def _cabecera_descarga(nombre: str) -> dict[str, str]:
    return {"Content-Disposition": f'attachment; filename="{nombre}"'}


def respuesta_csv(texto: str, nombre: str) -> Response:
    return Response(texto, media_type=TIPO_CSV, headers=_cabecera_descarga(nombre))


# --- Exportar la corrida actual -------------------------------------------------------------

def _exportar_a_archivo(parametros: ParametrosSimulacion, hasta_tick: int, que: str) -> str:
    """Re-ejecuta la corrida y deja el CSV en un archivo temporal (puede pesar varios MB)."""
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", suffix=".csv",
                                     delete=False) as archivo:
        exportar_corrida(parametros, hasta_tick, que, archivo)
        return archivo.name


@router.get("/exportar/{que}.csv")
async def exportar(que: Literal["registro", "bitacora", "series"], request: Request) -> Response:
    """CSV completo de la corrida actual hasta el paso en que va.

    `registro` y `bitacora` re-ejecutan la corrida desde t = 0 (DISENO.md, decisión p);
    `series` sale de memoria.
    """
    simulacion = _controlador(request).simulacion
    if simulacion is None:
        raise HTTPException(status_code=404, detail="Todavía no hay una corrida que exportar")
    # Se leen aquí, en el hilo del bucle, para no ver la simulación a medio paso.
    parametros, tick = simulacion.parametros, simulacion.tick
    nombre = f"{que}_semilla{parametros.semilla}_paso{tick}.csv"
    if que == "series":
        destino = io.StringIO()
        escribir_series(destino, simulacion.series.filas)
        return respuesta_csv(destino.getvalue(), nombre)
    ruta = await asyncio.to_thread(_exportar_a_archivo, parametros, tick, que)
    return FileResponse(ruta, media_type=TIPO_CSV, filename=nombre,
                        background=BackgroundTask(os.remove, ruta))


# --- Lotes de réplicas ------------------------------------------------------------------------

class SolicitudLote(BaseModel):
    parametros: ParametrosSimulacion
    replicas: int = Field(10, ge=2, le=REPLICAS_MAXIMAS, description="Número de réplicas")
    pasos: int = Field(1000, ge=10, le=PASOS_MAXIMOS_LOTE, description="Pasos de cada réplica")
    semilla_inicial: int | None = Field(
        None, ge=1, le=SEMILLA_MAXIMA,
        description="Semilla de la primera réplica (por defecto, la de los parámetros)")


@router.post("/experimentos")
async def iniciar_lote(solicitud: SolicitudLote, request: Request) -> dict[str, Any]:
    """Lanza un lote de réplicas en segundo plano; el avance se consulta con GET."""
    experimento = _experimento(request)
    try:
        experimento.iniciar(solicitud.parametros, solicitud.replicas, solicitud.pasos,
                            solicitud.semilla_inicial)
    except AccionInvalida as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return experimento.estado_actual()


@router.get("/experimentos")
async def estado_lote(request: Request) -> dict[str, Any]:
    return _experimento(request).estado_actual()


@router.post("/experimentos/cancelar")
async def cancelar_lote(request: Request) -> dict[str, Any]:
    experimento = _experimento(request)
    try:
        experimento.cancelar()
    except AccionInvalida as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return experimento.estado_actual()


@router.get("/experimentos/resultado.csv")
async def resultado_lote_csv(request: Request) -> Response:
    resultado = _experimento(request).resultado
    if resultado is None or not resultado.replicas:
        raise HTTPException(status_code=404, detail="Todavía no hay resultados de un lote")
    destino = io.StringIO()
    escribir_lote(destino, resultado)
    return respuesta_csv(destino.getvalue(), f"lote_{len(resultado.replicas)}replicas_{resultado.pasos}pasos.csv")
