"""Exportación a CSV (RF-61): registro de números, bitácora de eventos y series.

Concepto de simulación: **salida de la simulación para análisis**. Los datos se llevan a una
hoja de cálculo para graficarlos y analizarlos fuera del simulador.

Formato (DISENO.md, decisión s): para Excel en español, separador `;`, coma decimal y
UTF-8 con BOM. En Python se lee con `pandas.read_csv(ruta, sep=";", decimal=",")`.

Registro y bitácora completos (decisión p): en memoria sólo hay búferes circulares, así que
se **re-ejecuta la corrida** desde t = 0 hasta el paso pedido en un objeto aparte, escribiendo
cada número y cada evento en el momento en que ocurre. Que el resultado coincida con lo que
se vio en vivo es, en sí mismo, una demostración de la reproducibilidad.
"""

import csv
from collections.abc import Callable, Iterable
from typing import Any, TextIO

from app.aleatorio.registro import EntradaRegistro
from app.config import ParametrosSimulacion
from app.estadisticas.replicas import NIVEL_CONFIANZA, VARIABLES_SALIDA, ResultadoLote
from app.estadisticas.series import COLUMNAS as COLUMNAS_SERIES
from app.eventos.bitacora import SIN_HORMIGA, SIN_NUMERO, Evento
from app.nucleo.simulacion import Simulacion

SEPARADOR = ";"
BOM = "﻿"
CIFRAS_SIGNIFICATIVAS = 12

ENCABEZADOS_REGISTRO = [
    "Índice", "Flujo", "Generador", "Propósito", "Hormiga", "Paso", "Tiempo (s)",
    "Estado previo (x_i)", "Cálculo", "Estado nuevo (x_i+1)", "u",
    "Degeneración", "Longitud del ciclo", "Re-siembra k", "Semilla nueva",
]
ENCABEZADOS_BITACORA = ["Paso", "Tiempo (s)", "Evento", "Hormiga", "Número (índice)", "Detalle"]


def formatear(valor: Any) -> str:
    """Un valor como lo espera Excel en español: coma decimal y vacío para 'no aplica'."""
    if valor is None:
        return ""
    if isinstance(valor, bool):
        return "sí" if valor else "no"
    if isinstance(valor, float):
        return f"{valor:.{CIFRAS_SIGNIFICATIVAS}g}".replace(".", ",")
    return str(valor)


def _escritor(destino: TextIO) -> "csv._writer":
    destino.write(BOM)
    return csv.writer(destino, delimiter=SEPARADOR, lineterminator="\r\n")


def _fila(escritor: "csv._writer", valores: Iterable[Any]) -> None:
    escritor.writerow([formatear(v) for v in valores])


# --- Registro de números ---------------------------------------------------------------------

def describir_calculo(calculo: dict[str, Any]) -> str:
    """El cálculo del número en una línea, según el método."""
    metodo = calculo.get("metodo")
    if metodo == "cuadrados_medios":
        return (f"x² = {calculo['cuadrado']}; relleno {calculo['relleno']}; "
                f"centrales {calculo['centrales']}")
    if metodo in ("congruencial_lineal", "congruencial_multiplicativo"):
        suma = f" + {calculo['c']}" if metodo == "congruencial_lineal" else ""
        return (f"{calculo['a']}·{calculo['previo']}{suma} = {calculo['producto']}; "
                f"mod {calculo['m']} = {calculo['x']}")
    return f"{calculo.get('algoritmo', metodo)} número #{calculo.get('indice')}"


def fila_registro(entrada: EntradaRegistro) -> list[Any]:
    calculo = entrada.calculo
    degeneracion = calculo.get("degeneracion") or {}
    tipo = degeneracion.get("tipo")
    return [
        entrada.indice, entrada.flujo, entrada.generador, entrada.proposito,
        None if entrada.id_hormiga == SIN_HORMIGA else entrada.id_hormiga,
        entrada.tick, entrada.tiempo, calculo.get("previo"), describir_calculo(calculo),
        calculo.get("x"), entrada.u,
        None if tipo is None else getattr(tipo, "value", tipo),
        degeneracion.get("longitud_ciclo"), degeneracion.get("numero_resiembra"),
        degeneracion.get("semilla_nueva"),
    ]


# --- Bitácora -----------------------------------------------------------------------------------

def describir_detalle(detalle: dict[str, Any]) -> str:
    return ", ".join(f"{clave} = {formatear(valor)}" for clave, valor in detalle.items())


def fila_evento(evento: Evento) -> list[Any]:
    return [
        evento.tick, evento.tiempo, evento.tipo.name,
        None if evento.id_hormiga == SIN_HORMIGA else evento.id_hormiga,
        None if evento.indice_aleatorio == SIN_NUMERO else evento.indice_aleatorio,
        describir_detalle(evento.detalle),
    ]


# --- Series -------------------------------------------------------------------------------------

def escribir_series(destino: TextIO, filas: Iterable[dict[str, Any]]) -> int:
    escritor = _escritor(destino)
    _fila(escritor, [encabezado for encabezado, _ in COLUMNAS_SERIES.values()])
    total = 0
    for fila in filas:
        _fila(escritor, [fila[clave] for clave in COLUMNAS_SERIES])
        total += 1
    return total


# --- Re-ejecución de la corrida -----------------------------------------------------------------

QUE_EXPORTAR: dict[str, tuple[list[str], str]] = {
    "registro": (ENCABEZADOS_REGISTRO, "números pseudoaleatorios"),
    "bitacora": (ENCABEZADOS_BITACORA, "eventos"),
}


def exportar_corrida(parametros: ParametrosSimulacion, hasta_tick: int, que: str,
                     destino: TextIO) -> int:
    """Re-ejecuta la corrida desde t = 0 hasta `hasta_tick` y escribe el registro completo
    (`que = "registro"`) o la bitácora completa (`que = "bitacora"`). Devuelve las filas escritas.
    """
    if que not in QUE_EXPORTAR:
        raise ValueError(f"no se puede exportar {que!r}; opciones: {', '.join(QUE_EXPORTAR)}")
    escritor = _escritor(destino)
    _fila(escritor, QUE_EXPORTAR[que][0])
    filas = 0

    def escribir(convertir: Callable[[Any], list[Any]]) -> Callable[[Any], None]:
        def aviso(dato: Any) -> None:
            nonlocal filas
            _fila(escritor, convertir(dato))
            filas += 1
        return aviso

    avisos: dict[str, Any] = (
        {"al_generar_numero": escribir(fila_registro)} if que == "registro"
        else {"al_registrar_evento": escribir(fila_evento)}
    )
    # Búferes mínimos: lo que importa es el aviso por cada número o evento.
    simulacion = Simulacion(parametros, capacidad_registro=1, capacidad_bitacora=1, **avisos)
    simulacion.avanzar(hasta_tick)
    return filas


# --- Lote de réplicas y laboratorio de generadores --------------------------------------------

def escribir_lote(destino: TextIO, resultado: ResultadoLote) -> None:
    """Dos tablas: una fila por réplica y, debajo, el resumen con su intervalo de confianza."""
    escritor = _escritor(destino)
    variables = list(VARIABLES_SALIDA)
    _fila(escritor, ["Réplica", "Semilla", *(VARIABLES_SALIDA[v][0] for v in variables)])
    for numero, replica in enumerate(resultado.replicas, start=1):
        _fila(escritor, [numero, replica["semilla"], *(replica[v] for v in variables)])
    _fila(escritor, [])
    _fila(escritor, [f"Resumen de {len(resultado.replicas)} réplicas de {resultado.pasos} pasos "
                     f"(IC del {NIVEL_CONFIANZA:.0%} con la t de Student)"])
    _fila(escritor, ["Variable", "Réplicas", "Media", "Desviación estándar",
                     "IC inferior", "IC superior", "Mínimo", "Máximo"])
    for r in resultado.resumen:
        _fila(escritor, [r.descripcion, r.n, r.media, r.desviacion, r.ic_inferior, r.ic_superior,
                         r.minimo, r.maximo])


def escribir_laboratorio(destino: TextIO, datos: dict[str, Any]) -> None:
    """Informe comparativo de generadores: una columna por generador."""
    escritor = _escritor(destino)
    resultados = datos["resultados"]
    _fila(escritor, ["", *(r["nombre"] for r in resultados)])
    filas: list[tuple[str, Callable[[dict[str, Any]], Any]]] = [
        ("Semilla", lambda r: r["semilla"]),
        ("Módulo m", lambda r: r["modulo"]),
        ("Números (n)", lambda r: r["muestra"]["n"]),
        ("Re-siembras (degeneraciones)", lambda r: r["resiembras"]),
        ("Números distintos", lambda r: r["muestra"]["distintos"]),
        ("Media (esperada 0,5)", lambda r: r["muestra"]["media"]),
        ("Varianza (esperada 1/12)", lambda r: r["muestra"]["varianza"]),
    ]
    for titulo, obtener in filas:
        _fila(escritor, [titulo, *(obtener(r) for r in resultados)])
    for i, prueba in enumerate(resultados[0]["pruebas"]):
        nombre = prueba["prueba"]
        _fila(escritor, [f"{nombre}: estadístico", *(r["pruebas"][i]["estadistico"] for r in resultados)])
        _fila(escritor, [f"{nombre}: valor crítico", *(r["pruebas"][i]["valor_critico"] for r in resultados)])
        _fila(escritor, [f"{nombre}: valor p", *(r["pruebas"][i]["p_valor"] for r in resultados)])
        _fila(escritor, [f"{nombre}: ¿se rechaza H0 con α = {formatear(datos['alfa'])}?",
                         *(r["pruebas"][i]["rechaza"] for r in resultados)])
    intervalos = len(resultados[0]["muestra"]["histograma"])
    for j in range(intervalos):
        _fila(escritor, [f"Frecuencia en [{formatear(j / intervalos)}; {formatear((j + 1) / intervalos)})",
                         *(r["muestra"]["histograma"][j] for r in resultados)])
