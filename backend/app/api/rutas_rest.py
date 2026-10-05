"""Rutas REST (JSON) del simulador.

La capa web sólo traduce peticiones HTTP a llamadas del núcleo y valida la entrada con
Pydantic; no contiene lógica de simulación.
"""

import io
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.responses import Response
from pydantic import BaseModel, Field

from app import __version__
from app.config import PARAMETROS_DEMO, ParametrosGenerador, ParametrosSimulacion
from app.aleatorio.base import PASO_RESIEMBRA
from app.aleatorio.fabrica import GENERADORES, crear_generador
from app.aleatorio.laboratorio import evaluar_generador
from app.aleatorio.pruebas_estadisticas import ALFA_POR_DEFECTO
from app.aleatorio.variables import angulo
from app.estadisticas.exportar import escribir_laboratorio
from app.eventos.bitacora import Evento
from app.eventos.tipos import TipoEvento
from app.modelo.generacion_mundo import ErrorGeneracionMundo
from app.nucleo.simulacion import Simulacion
from app.servicio.controlador import AccionInvalida, ControladorSimulacion

CANTIDAD_POR_DEFECTO = 20
CANTIDAD_MAXIMA_VISTA_PREVIA = 1000  # filas que la tabla didáctica puede mostrar a la vez
CANTIDAD_MINIMA_PRUEBAS = 10
CANTIDAD_MAXIMA_PRUEBAS = 100_000    # números por generador en el laboratorio
INTERVALOS_MAXIMOS = 100
GENERADORES_MAXIMOS = len(GENERADORES)

router = APIRouter(prefix="/api")


class RespuestaSalud(BaseModel):
    estado: Literal["ok"]
    version: str


class SolicitudVistaPrevia(ParametrosGenerador):
    """Generador para calcular una tabla paso a paso (cualquier método)."""

    cantidad: int = Field(
        CANTIDAD_POR_DEFECTO, ge=1, le=CANTIDAD_MAXIMA_VISTA_PREVIA,
        description="Cuántos números generar",
    )


class SolicitudPruebas(BaseModel):
    """Laboratorio: varios generadores, cada uno con su semilla, y las mismas pruebas."""

    generadores: list[ParametrosGenerador] = Field(min_length=1, max_length=GENERADORES_MAXIMOS)
    cantidad: int = Field(1000, ge=CANTIDAD_MINIMA_PRUEBAS, le=CANTIDAD_MAXIMA_PRUEBAS,
                          description="Números por generador")
    intervalos: int = Field(10, ge=2, le=INTERVALOS_MAXIMOS, description="Intervalos k de la prueba χ²")
    alfa: Literal[0.01, 0.05, 0.1] = Field(ALFA_POR_DEFECTO, description="Nivel de significancia")


@router.get("/salud", response_model=RespuestaSalud)
def salud() -> RespuestaSalud:
    """Comprueba que el servidor responde."""
    return RespuestaSalud(estado="ok", version=__version__)


@router.post("/aleatorio/vista-previa")
def vista_previa(solicitud: SolicitudVistaPrevia) -> dict[str, Any]:
    """Tabla paso a paso del generador. Usa un generador temporal: no toca la simulación.

    Cada fila es el cálculo completo del número (`estado_interno` del generador, que indica
    su `metodo`) más la dirección u · 360° que tomaría una hormiga.
    """
    generador = crear_generador(solicitud.configuracion_generador, solicitud.semilla)
    filas = []
    for _ in range(solicitud.cantidad):
        u = generador.siguiente()
        filas.append({**generador.estado_interno(), "u": u, "angulo": angulo(u)})
    return {
        "generador": generador.nombre,
        "metodo": solicitud.generador,
        "semilla": solicitud.semilla,
        "digitos": solicitud.digitos,
        "modulo": generador.modulo,
        "paso_resiembra": PASO_RESIEMBRA,
        "filas": filas,
        "resiembras": generador.resiembras,
    }


@router.post("/aleatorio/pruebas")
def pruebas(solicitud: SolicitudPruebas) -> dict[str, Any]:
    """Pruebas de uniformidad (χ², K-S) e independencia (corridas) para comparar generadores."""
    resultados = [
        evaluar_generador(g.configuracion_generador, g.semilla, solicitud.cantidad,
                          solicitud.intervalos, solicitud.alfa)
        for g in solicitud.generadores
    ]
    return {"cantidad": solicitud.cantidad, "intervalos": solicitud.intervalos,
            "alfa": solicitud.alfa, "resultados": resultados}


@router.post("/aleatorio/pruebas.csv")
def pruebas_csv(solicitud: SolicitudPruebas) -> Response:
    """El mismo informe comparativo de generadores, como CSV para una hoja de cálculo."""
    destino = io.StringIO()
    escribir_laboratorio(destino, pruebas(solicitud))
    return Response(destino.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="comparacion_generadores.csv"'})


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
        "generadores": {nombre: tipo.nombre for nombre, tipo in GENERADORES.items()},
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
