"""Parámetros de la simulación.

Concepto de simulación: **entradas del modelo** (parámetros). Todo valor que controla el
comportamiento vive aquí, con su descripción, unidad y rango; no hay "números mágicos"
en el resto del código. La misma validación se aplica a lo que llega desde la interfaz.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.aleatorio.cuadrados_medios import validar_configuracion

# --- Constantes fijas del modelo (no se editan desde la interfaz) -------------------------

DT = 0.1                     # s simulados por paso
ANCHO_MUNDO = 1000.0         # unidades de longitud
ALTO_MUNDO = 700.0
RADIO_NIDO = 25.0
TAMANO_CELDA = 4.0           # lado de la celda de la rejilla espacial
RADIO_ROCA_MIN = 12.0
RADIO_ROCA_MAX = 45.0
RADIO_FUENTE_MIN = 15.0
RADIO_FUENTE_MAX = 30.0
SEPARACION_MINIMA = 8.0      # espacio libre entre dos elementos del mundo
INTENTOS_POR_ELEMENTO = 500  # límite de la aceptación-rechazo al colocar cada elemento
DISTANCIA_REINA_AL_NIDO = 40.0  # posición inicial de la reina, al este del nido


def _campo(defecto: float, minimo: float, maximo: float, unidad: str, descripcion: str):
    return Field(defecto, ge=minimo, le=maximo, description=descripcion,
                 json_schema_extra={"unidad": unidad})


class ParametrosSimulacion(BaseModel):
    """Configuración completa de una corrida (ESPECIFICACION_v2 §6)."""

    model_config = ConfigDict(extra="forbid")

    # Principales
    num_hormigas: int = _campo(2000, 1, 20_000, "hormigas", "Número de hormigas obreras")
    semilla: int = _campo(5735, 1, 99_999_999, "entero de D dígitos",
                          "Semilla del generador (flujo MUNDO); 1 ≤ semilla < 10^D")
    generador: Literal["cuadrados_medios"] = Field(
        "cuadrados_medios", description="Generador de números pseudoaleatorios")
    digitos: Literal[4, 6, 8] = Field(4, description="Dígitos D del método de cuadrados medios",
                                      json_schema_extra={"unidad": "dígitos"})
    pasos_por_segundo: int = _campo(30, 1, 1000, "pasos/s", "Velocidad de simulación")
    num_obstaculos: int = _campo(12, 0, 60, "rocas", "Número de rocas")
    num_fuentes: int = _campo(4, 1, 20, "fuentes", "Número de fuentes de alimento")
    alimento_por_fuente: int = _campo(2000, 1, 100_000, "unidades", "Alimento inicial de cada fuente")
    radio_reina: float = _campo(80.0, 0.0, 300.0, "unidades", "Radio de influencia de la reina")
    p_seguir_reina: float = _campo(0.3, 0.0, 1.0, "probabilidad",
                                   "Probabilidad de seguir a la reina al entrar en su radio")

    # Avanzados
    velocidad_hormiga: float = _campo(20.0, 5.0, 40.0, "unidades/s", "Velocidad de una obrera")
    capacidad_carga: int = _campo(5, 1, 255, "unidades", "Alimento que carga una obrera")
    salidas_por_paso: int = _campo(5, 1, 100, "hormigas/paso", "Hormigas que salen del nido por paso")
    pasos_evasion: int = _campo(5, 1, 100, "pasos", "Duración del estado EVITANDO_OBSTACULO")
    pasos_seguimiento: int = _campo(100, 1, 1000, "pasos", "Duración del seguimiento a la reina")
    energia_max: float = _campo(100.0, 1.0, 1000.0, "energía", "Energía máxima de una obrera")
    consumo_energia: float = _campo(0.1, 0.0, 10.0, "energía/paso", "Consumo fuera del nido")
    umbral_regreso: float = _campo(30.0, 0.0, 1000.0, "energía",
                                   "Bajo este valor la obrera regresa al nido")
    recuperacion_energia: float = _campo(2.0, 0.1, 100.0, "energía/paso", "Recuperación en el nido")
    factor_velocidad_agotada: float = _campo(0.5, 0.1, 1.0, "fracción",
                                             "Velocidad relativa con energía 0")
    distancia_minima_reina: float = _campo(10.0, 0.0, 50.0, "unidades",
                                           "Distancia a la que la seguidora se detiene")
    velocidad_reina: float = _campo(5.0, 0.0, 20.0, "unidades/s", "Velocidad de la reina")
    radio_patrulla: float = _campo(150.0, 50.0, 300.0, "unidades",
                                   "Zona alrededor del nido donde patrulla la reina (sin rocas ni fuentes)")
    pasos_rumbo_reina: int = _campo(50, 1, 1000, "pasos", "Cada cuántos pasos cambia de rumbo la reina")

    @model_validator(mode="after")
    def _validar_relaciones(self) -> "ParametrosSimulacion":
        validar_configuracion(self.semilla, self.digitos)
        if self.umbral_regreso >= self.energia_max:
            raise ValueError("umbral_regreso debe ser menor que energia_max")
        if self.velocidad_hormiga * DT >= RADIO_ROCA_MIN:
            raise ValueError("velocidad_hormiga · dt debe ser menor que el radio mínimo de roca")
        return self

    @property
    def semilla_comportamiento(self) -> int:
        return semilla_comportamiento(self.semilla, self.digitos)


def semilla_comportamiento(semilla: int, digitos: int) -> int:
    """Semilla del flujo COMPORTAMIENTO (DISENO.md, decisión k): (semilla + 10^D/2) mod 10^D."""
    modulo = 10**digitos
    derivada = (semilla + modulo // 2) % modulo
    return derivada if derivada != 0 else 1


# --- Simulación demo ----------------------------------------------------------------------
# Configuración para mostrar en clase, en pocos segundos, todos los fenómenos: muchas
# hormigas, fuentes pequeñas que se agotan, una reina con radio amplio y p = 0.5 (para
# comparar p̂ con p), y D = 4, con el que la degeneración de cuadrados medios aparece pronto.
PARAMETROS_DEMO = ParametrosSimulacion(
    num_hormigas=3000,
    semilla=2468,
    digitos=4,
    pasos_por_segundo=60,
    num_obstaculos=18,
    num_fuentes=6,
    alimento_por_fuente=300,
    radio_reina=120.0,
    p_seguir_reina=0.5,
    salidas_por_paso=10,
)
