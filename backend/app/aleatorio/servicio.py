"""Servicio de números pseudoaleatorios del modelo.

Concepto de simulación: **fuente de aleatoriedad controlada**. Es la única puerta por la
que el modelo obtiene números aleatorios: cada petición dice para qué es (propósito) y
para quién (id de hormiga), y queda registrada. Si el generador degenera, el evento
`GENERADOR_DEGENERADO` se anota en la bitácora: nunca se re-siembra en silencio.

Hay dos flujos independientes con el mismo tipo de generador (DISENO.md, decisión b):
- MUNDO: genera rocas y fuentes de alimento.
- COMPORTAMIENTO: decisiones de las hormigas y de la reina.
Así el mundo no cambia aunque cambie, por ejemplo, el número de hormigas.
"""

from enum import Enum

from app.aleatorio.base import GeneradorPseudoaleatorio
from app.aleatorio.registro import EntradaRegistro, RegistroAleatorio
from app.eventos.bitacora import SIN_HORMIGA, Bitacora, Evento
from app.eventos.tipos import TipoEvento


class Flujo(str, Enum):
    """Sucesiones independientes de números pseudoaleatorios."""

    MUNDO = "MUNDO"
    COMPORTAMIENTO = "COMPORTAMIENTO"


class Proposito(str, Enum):
    """Para qué se usa cada número (DISENO.md §9)."""

    MUNDO = "MUNDO"
    DIRECCION_SALIDA = "DIRECCION_SALIDA"
    DIRECCION_COLISION = "DIRECCION_COLISION"
    DIRECCION_BORDE = "DIRECCION_BORDE"
    SEGUIR_REINA = "SEGUIR_REINA"
    DIRECCION_FIN_SEGUIMIENTO = "DIRECCION_FIN_SEGUIMIENTO"
    MOVIMIENTO_REINA = "MOVIMIENTO_REINA"


def flujo_de(proposito: Proposito) -> Flujo:
    """Cada propósito pertenece a un flujo: sólo MUNDO usa el flujo del mundo."""
    return Flujo.MUNDO if proposito is Proposito.MUNDO else Flujo.COMPORTAMIENTO


class ServicioAleatorio:
    """Entrega números pseudoaleatorios al modelo y registra cada uno."""

    def __init__(
        self,
        generador_mundo: GeneradorPseudoaleatorio,
        generador_comportamiento: GeneradorPseudoaleatorio,
        registro: RegistroAleatorio | None = None,
        bitacora: Bitacora | None = None,
    ) -> None:
        self._generadores = {
            Flujo.MUNDO: generador_mundo,
            Flujo.COMPORTAMIENTO: generador_comportamiento,
        }
        self.registro = registro if registro is not None else RegistroAleatorio()
        self.bitacora = bitacora if bitacora is not None else Bitacora()
        self._degeneraciones = {flujo: 0 for flujo in Flujo}
        self._tick = 0
        self._tiempo = 0.0

    @property
    def total_generados(self) -> int:
        return self.registro.total

    @property
    def ultimo_indice(self) -> int:
        """Índice global del último número entregado (0 si todavía no hay ninguno)."""
        return self.registro.total

    def degeneraciones(self, flujo: Flujo) -> int:
        """Veces que degeneró (y se re-sembró) el generador de ese flujo."""
        return self._degeneraciones[flujo]

    def generador(self, flujo: Flujo) -> GeneradorPseudoaleatorio:
        return self._generadores[flujo]

    def fijar_tiempo(self, tick: int, tiempo: float) -> None:
        """El reloj de la simulación avisa en qué paso estamos (para el registro)."""
        self._tick = tick
        self._tiempo = tiempo

    def obtener(self, proposito: Proposito, id_hormiga: int = SIN_HORMIGA) -> float:
        """Produce un número u ∈ [0, 1) para `proposito` y lo registra."""
        flujo = flujo_de(proposito)
        generador = self._generadores[flujo]
        u = generador.siguiente()
        entrada = EntradaRegistro(
            indice=self.registro.siguiente_indice,
            flujo=flujo.value,
            generador=generador.nombre,
            proposito=proposito.value,
            id_hormiga=id_hormiga,
            tick=self._tick,
            tiempo=self._tiempo,
            u=u,
            calculo=generador.estado_interno(),
        )
        self.registro.agregar(entrada)
        if generador.degenerado():
            self._registrar_degeneracion(flujo, entrada)
        return u

    def _registrar_degeneracion(self, flujo: Flujo, entrada: EntradaRegistro) -> None:
        self._degeneraciones[flujo] += 1
        self.bitacora.registrar(
            Evento(
                tick=self._tick,
                tiempo=self._tiempo,
                tipo=TipoEvento.GENERADOR_DEGENERADO,
                id_hormiga=entrada.id_hormiga,
                indice_aleatorio=entrada.indice,
                detalle={"flujo": flujo.value, **(entrada.calculo.get("degeneracion") or {})},
            )
        )

    def reiniciar(self) -> None:
        """Repite la corrida desde el principio: generadores, registro y bitácora."""
        for generador in self._generadores.values():
            generador.reiniciar()
        self.registro.limpiar()
        self.bitacora.limpiar()
        self._degeneraciones = {flujo: 0 for flujo in Flujo}
        self._tick = 0
        self._tiempo = 0.0
