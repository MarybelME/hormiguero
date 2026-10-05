"""Rutas REST (JSON) del simulador.

La capa web sólo traduce peticiones HTTP a llamadas del núcleo y valida la entrada con
Pydantic; no contiene lógica de simulación.
"""

from collections.abc import Callable
from dataclasses import asdict
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator

from app import __version__
from app.config import PARAMETROS_DEMO, ParametrosSimulacion
from app.aleatorio.cuadrados_medios import (
    DIGITOS_POR_DEFECTO,
    PASO_RESIEMBRA,
    GeneradorCuadradosMedios,
    PasoCuadradosMedios,
    TipoDegeneracion,
    validar_configuracion,
)
from app.aleatorio.variables import angulo
from app.eventos.bitacora import Evento
from app.eventos.tipos import TipoEvento
from app.modelo.generacion_mundo import ErrorGeneracionMundo
from app.nucleo.simulacion import Simulacion
from app.servicio.controlador import AccionInvalida, ControladorSimulacion

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


# --- Simulación: configuración, control y consultas ---------------------------------------
# Las rutas son `async` para ejecutarse en el mismo hilo que el bucle del controlador: así
# una consulta nunca ve la simulación a medio paso.

LIMITE_EVENTOS_MAX = 1000
LIMITE_REGISTRO_MAX = 1000


class SolicitudVelocidad(BaseModel):
    pasos_por_segundo: int = ParametrosSimulacion.model_fields["pasos_por_segundo"]


def _controlador(request: Request) -> ControladorSimulacion:
    return request.app.state.controlador


def _simulacion_actual(request: Request) -> Simulacion:
    simulacion = _controlador(request).simulacion
    if simulacion is None:
        raise HTTPException(status_code=404, detail="Todavía no hay un mundo configurado")
    return simulacion


def _ejecutar(accion: Callable[[], None], controlador: ControladorSimulacion) -> dict[str, Any]:
    try:
        accion()
    except AccionInvalida as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return controlador.estado_actual()


def _respuesta_mundo(simulacion: Simulacion) -> dict[str, Any]:
    p = simulacion.parametros
    return {
        "mundo": simulacion.mundo.capa_estatica(),
        "semillas": {"MUNDO": p.semilla, "COMPORTAMIENTO": p.semilla_comportamiento},
    }


@router.get("/parametros")
def parametros() -> dict[str, Any]:
    """Valores por defecto, valores de la simulación demo y esquema (descripción, unidad y rango)."""
    return {
        "valores": ParametrosSimulacion().model_dump(),
        "demo": PARAMETROS_DEMO.model_dump(),
        "esquema": ParametrosSimulacion.model_json_schema(),
    }


@router.post("/simulacion/configurar")
async def configurar(parametros: ParametrosSimulacion, request: Request) -> dict[str, Any]:
    """Crea una corrida nueva en t = 0 (genera el mundo con la semilla) y devuelve la capa estática."""
    try:
        simulacion = _controlador(request).configurar(parametros)
    except ErrorGeneracionMundo as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _respuesta_mundo(simulacion)


@router.get("/mundo")
async def mundo(request: Request) -> dict[str, Any]:
    """Capa estática del mundo actual: dimensiones, nido, reina, rocas y fuentes."""
    return _respuesta_mundo(_simulacion_actual(request))


@router.post("/simulacion/iniciar")
async def iniciar(request: Request) -> dict[str, Any]:
    controlador = _controlador(request)
    return _ejecutar(controlador.iniciar, controlador)


@router.post("/simulacion/pausar")
async def pausar(request: Request) -> dict[str, Any]:
    controlador = _controlador(request)
    return _ejecutar(controlador.pausar, controlador)


@router.post("/simulacion/reiniciar")
async def reiniciar(request: Request) -> dict[str, Any]:
    """Vuelve a t = 0 con la misma configuración (la corrida se repetirá idéntica)."""
    controlador = _controlador(request)
    return _ejecutar(controlador.reiniciar, controlador)


@router.post("/simulacion/limpiar")
async def limpiar(request: Request) -> dict[str, Any]:
    """Borra mundo, hormigas, registros y estadísticas."""
    controlador = _controlador(request)
    return _ejecutar(controlador.limpiar, controlador)


@router.put("/simulacion/velocidad")
async def velocidad(solicitud: SolicitudVelocidad, request: Request) -> dict[str, Any]:
    """Cambia los pasos por segundo en vivo, sin reiniciar."""
    controlador = _controlador(request)
    controlador.fijar_velocidad(solicitud.pasos_por_segundo)
    return {"pasos_por_segundo": controlador.pasos_por_segundo}


@router.get("/simulacion/estado")
async def estado(request: Request) -> dict[str, Any]:
    """Estado del controlador y, si hay mundo, las estadísticas actuales."""
    controlador = _controlador(request)
    datos = controlador.estado_actual()
    datos["estadisticas"] = None if controlador.simulacion is None else controlador.estadisticas()
    return datos


@router.get("/hormigas/{id_hormiga}")
async def hormiga(id_hormiga: int, request: Request) -> dict[str, Any]:
    """Vista didáctica: atributos, último número con su cálculo, último y siguiente evento."""
    simulacion = _simulacion_actual(request)
    if not 0 <= id_hormiga < simulacion.mundo.hormigas.n:
        raise HTTPException(status_code=404, detail=f"No existe la hormiga {id_hormiga}")
    return simulacion.vista_hormiga(id_hormiga)


def _evento_json(evento: Evento) -> dict[str, Any]:
    datos = asdict(evento)
    datos["tipo"] = evento.tipo.name
    return datos


@router.get("/eventos")
async def eventos(
    request: Request,
    id_hormiga: int | None = None,
    tipo: str | None = None,
    limite: int = Query(100, ge=1, le=LIMITE_EVENTOS_MAX),
) -> dict[str, Any]:
    """Últimos eventos de la bitácora, filtrables por hormiga y por tipo."""
    simulacion = _simulacion_actual(request)
    tipo_evento = None
    if tipo:
        if tipo not in TipoEvento.__members__:
            raise HTTPException(status_code=422, detail=f"Tipo de evento desconocido: {tipo}")
        tipo_evento = TipoEvento[tipo]
    encontrados = simulacion.bitacora.filtrar(limite, id_hormiga, tipo_evento)
    return {
        "total": simulacion.bitacora.total,
        "tipos": [tipo.name for tipo in TipoEvento if tipo is not TipoEvento.NINGUNO],
        "eventos": [_evento_json(e) for e in encontrados],
    }


@router.get("/aleatorio/registro")
async def registro(
    request: Request,
    desde: int | None = Query(None, ge=1),
    limite: int = Query(50, ge=1, le=LIMITE_REGISTRO_MAX),
) -> dict[str, Any]:
    """Página del registro de números pseudoaleatorios (por defecto, los más recientes)."""
    registro = _simulacion_actual(request).aleatorio.registro
    if desde is None:
        desde = max(1, registro.total - limite + 1)
    return {
        "total": registro.total,
        "primer_indice_disponible": registro.primer_indice_disponible,
        "entradas": [asdict(e) for e in registro.pagina(desde, limite)],
    }
