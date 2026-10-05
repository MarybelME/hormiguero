"""Ejecución de lotes de réplicas desde la interfaz (DISENO.md, decisión q).

El lote corre en un hilo aparte (`asyncio.to_thread`) para no congelar el servidor: la
simulación en vivo sigue, aunque más lenta, mientras el lote avanza. Hay a lo sumo un lote
a la vez; se puede consultar su avance y cancelarlo.
"""

import asyncio
import threading
from dataclasses import asdict
from enum import Enum
from typing import Any

from app.config import ParametrosSimulacion
from app.estadisticas.replicas import ResultadoLote, ejecutar_lote
from app.servicio.controlador import AccionInvalida

# Límite de trabajo de un lote lanzado desde la interfaz: réplicas × pasos × hormigas.
# Con ~3 millones de hormiga-pasos por segundo (benchmark) son unos 100 s como máximo.
PRESUPUESTO_LOTE = 300_000_000


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", " ")


class EstadoExperimento(str, Enum):
    INACTIVO = "inactivo"
    CORRIENDO = "corriendo"
    TERMINADO = "terminado"
    CANCELADO = "cancelado"
    ERROR = "error"


class ControladorExperimento:
    """Un lote de réplicas a la vez, con avance y cancelación."""

    def __init__(self) -> None:
        self.estado = EstadoExperimento.INACTIVO
        self.hechas = 0
        self.total = 0
        self.resultado: ResultadoLote | None = None
        self.error: str | None = None
        self._cancelar = threading.Event()
        self._tarea: asyncio.Task[None] | None = None

    def iniciar(self, parametros: ParametrosSimulacion, replicas: int, pasos: int,
                semilla_inicial: int | None = None) -> None:
        if self.estado is EstadoExperimento.CORRIENDO:
            raise AccionInvalida("Ya hay un lote en curso: espera a que termine o cancélalo")
        trabajo = replicas * pasos * parametros.num_hormigas
        if trabajo > PRESUPUESTO_LOTE:
            raise ValueError(
                f"El lote es demasiado grande para la interfaz ({_miles(trabajo)} hormiga-pasos; "
                f"máximo {_miles(PRESUPUESTO_LOTE)}). Usa menos réplicas, pasos u hormigas, o el "
                "script backend/scripts/experimento_lote.py")
        self.estado = EstadoExperimento.CORRIENDO
        self.hechas, self.total = 0, replicas
        self.resultado, self.error = None, None
        self._cancelar.clear()
        self._tarea = asyncio.get_running_loop().create_task(
            self._correr(parametros, replicas, pasos, semilla_inicial))

    async def _correr(self, parametros: ParametrosSimulacion, replicas: int, pasos: int,
                      semilla_inicial: int | None) -> None:
        try:
            self.resultado = await asyncio.to_thread(
                ejecutar_lote, parametros, replicas, pasos, semilla_inicial,
                al_terminar_replica=self._avance, cancelado=self._cancelar.is_set,
            )
            self.estado = (EstadoExperimento.CANCELADO if self._cancelar.is_set()
                           else EstadoExperimento.TERMINADO)
        except Exception as error:  # noqa: BLE001 — se informa en la interfaz
            self.error = str(error)
            self.estado = EstadoExperimento.ERROR

    def _avance(self, hechas: int, total: int) -> None:
        self.hechas, self.total = hechas, total

    def cancelar(self) -> None:
        if self.estado is not EstadoExperimento.CORRIENDO:
            raise AccionInvalida("No hay un lote en curso")
        self._cancelar.set()

    async def esperar(self) -> None:
        """Espera a que termine el lote en curso (pruebas y cierre del servidor)."""
        if self._tarea is not None:
            await self._tarea

    async def detener(self) -> None:
        self._cancelar.set()
        await self.esperar()

    def estado_actual(self) -> dict[str, Any]:
        return {
            "estado": self.estado.value,
            "hechas": self.hechas,
            "total": self.total,
            "error": self.error,
            "resultado": None if self.resultado is None else asdict(self.resultado),
        }
