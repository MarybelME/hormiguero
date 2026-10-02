"""Rutas REST (JSON) del simulador.

La capa web sólo traduce peticiones HTTP a llamadas del núcleo y valida la entrada con
Pydantic; no contiene lógica de simulación.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from app import __version__
from app.aleatorio.cuadrados_medios import (
    DIGITOS_POR_DEFECTO,
    PASO_RESIEMBRA,
    GeneradorCuadradosMedios,
    PasoCuadradosMedios,
    TipoDegeneracion,
    validar_configuracion,
)
from app.aleatorio.variables import angulo

CANTIDAD_POR_DEFECTO = 20
CANTIDAD_MAXIMA_VISTA_PREVIA = 1000  # filas que la tabla didáctica puede mostrar a la vez

router = APIRouter(prefix="/api")


class RespuestaSalud(BaseModel):
    estado: Literal["ok"]
    version: str


class SolicitudVistaPrevia(BaseModel):
    """Configuración del generador para calcular una tabla paso a paso."""

    generador: Literal["cuadrados_medios"] = "cuadrados_medios"
    semilla: int = Field(description="Semilla inicial, 1 ≤ semilla < 10^digitos")
    digitos: Literal[4, 6, 8] = Field(DIGITOS_POR_DEFECTO, description="Dígitos D del método")
    cantidad: int = Field(
        CANTIDAD_POR_DEFECTO, ge=1, le=CANTIDAD_MAXIMA_VISTA_PREVIA,
        description="Cuántos números generar",
    )

    @model_validator(mode="after")
    def _validar_semilla(self) -> "SolicitudVistaPrevia":
        validar_configuracion(self.semilla, self.digitos)
        return self


class DegeneracionVista(BaseModel):
    tipo: TipoDegeneracion
    estado: int
    longitud_ciclo: int | None
    numero_resiembra: int
    semilla_nueva: int


class FilaVistaPrevia(BaseModel):
    """Una fila de la tabla: semilla → cuadrado → relleno → centrales → u."""

    indice: int
    previo: int
    cuadrado: int
    relleno: str
    centrales: str
    u: float
    angulo: float
    degeneracion: DegeneracionVista | None


class RespuestaVistaPrevia(BaseModel):
    generador: str
    semilla: int
    digitos: int
    paso_resiembra: int
    filas: list[FilaVistaPrevia]
    resiembras: int


def _fila(paso: PasoCuadradosMedios) -> FilaVistaPrevia:
    degeneracion = paso.degeneracion
    return FilaVistaPrevia(
        indice=paso.indice,
        previo=paso.previo,
        cuadrado=paso.cuadrado,
        relleno=paso.relleno,
        centrales=paso.centrales,
        u=paso.u,
        angulo=angulo(paso.u),
        degeneracion=None if degeneracion is None else DegeneracionVista(
            tipo=degeneracion.tipo,
            estado=degeneracion.estado,
            longitud_ciclo=degeneracion.longitud_ciclo,
            numero_resiembra=degeneracion.numero_resiembra,
            semilla_nueva=degeneracion.semilla_nueva,
        ),
    )


@router.get("/salud", response_model=RespuestaSalud)
def salud() -> RespuestaSalud:
    """Comprueba que el servidor responde."""
    return RespuestaSalud(estado="ok", version=__version__)


@router.post("/aleatorio/vista-previa", response_model=RespuestaVistaPrevia)
def vista_previa(solicitud: SolicitudVistaPrevia) -> RespuestaVistaPrevia:
    """Tabla paso a paso del generador. Usa un generador temporal: no toca la simulación."""
    generador = GeneradorCuadradosMedios(solicitud.semilla, solicitud.digitos)
    filas = [_fila(generador.siguiente_paso()) for _ in range(solicitud.cantidad)]
    return RespuestaVistaPrevia(
        generador=generador.nombre,
        semilla=solicitud.semilla,
        digitos=solicitud.digitos,
        paso_resiembra=PASO_RESIEMBRA,
        filas=filas,
        resiembras=generador.resiembras,
    )
