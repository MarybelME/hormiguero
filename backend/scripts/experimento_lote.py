"""Réplicas por lote sin servidor (RF-60).

Corre varias réplicas de la misma configuración cambiando sólo la semilla y resume cada
variable de salida con su media, desviación estándar e intervalo de confianza del 95 %.

Uso (desde la raíz del proyecto):

    python backend/scripts/experimento_lote.py --replicas 10 --pasos 2000
    python backend/scripts/experimento_lote.py --replicas 20 --pasos 1000 --hormigas 1000 \\
        --generador congruencial_lineal --csv lote.csv
    python backend/scripts/experimento_lote.py --parametro p_seguir_reina=0.8 --parametro radio_reina=150

Cualquier parámetro de `config.ParametrosSimulacion` se puede fijar con `--parametro nombre=valor`.
Con las mismas opciones, el lote se repite idéntico.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import ParametrosSimulacion  # noqa: E402
from app.estadisticas.exportar import escribir_lote  # noqa: E402
from app.estadisticas.replicas import ResultadoLote, ejecutar_lote  # noqa: E402


def leer_parametros(opciones: argparse.Namespace) -> ParametrosSimulacion:
    valores: dict[str, str] = {}
    for asignacion in opciones.parametro:
        nombre, separador, valor = asignacion.partition("=")
        if not separador:
            raise SystemExit(f"--parametro espera nombre=valor; se recibió {asignacion!r}")
        valores[nombre.strip()] = valor.strip()
    if opciones.hormigas is not None:
        valores["num_hormigas"] = str(opciones.hormigas)
    if opciones.generador is not None:
        valores["generador"] = opciones.generador
    if opciones.semilla is not None:
        valores["semilla"] = str(opciones.semilla)
    return ParametrosSimulacion(**valores)  # Pydantic convierte y valida los textos


def formatear(valor: float | None) -> str:
    return "—" if valor is None else f"{valor:,.4g}".replace(",", " ")


def imprimir(resultado: ResultadoLote, segundos: float) -> None:
    print(f"\n{len(resultado.replicas)} réplicas de {resultado.pasos} pasos "
          f"(semillas {resultado.semillas[0]} … {resultado.semillas[-1]}) en {segundos:.1f} s\n")
    print(f"{'Variable de salida':<46}{'Media':>12}{'Desv. est.':>12}{'IC 95 %':>26}")
    for r in resultado.resumen:
        intervalo = "—" if r.ic_inferior is None else f"[{formatear(r.ic_inferior)}, {formatear(r.ic_superior)}]"
        print(f"{r.descripcion:<46}{formatear(r.media):>12}{formatear(r.desviacion):>12}{intervalo:>26}")


def main() -> None:
    lector = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    lector.add_argument("--replicas", type=int, default=10, help="número de réplicas (≥ 2)")
    lector.add_argument("--pasos", type=int, default=1000, help="pasos de cada réplica")
    lector.add_argument("--semilla", type=int, help="semilla de la primera réplica")
    lector.add_argument("--hormigas", type=int, help="número de hormigas")
    lector.add_argument("--generador", help="cuadrados_medios, congruencial_lineal, …")
    lector.add_argument("--parametro", action="append", default=[], metavar="NOMBRE=VALOR",
                        help="cualquier otro parámetro de la simulación (se puede repetir)")
    lector.add_argument("--csv", type=Path, help="archivo CSV donde guardar réplicas y resumen")
    opciones = lector.parse_args()
    if opciones.replicas < 2:
        raise SystemExit("se necesitan al menos 2 réplicas")

    parametros = leer_parametros(opciones)
    inicio = time.perf_counter()
    resultado = ejecutar_lote(
        parametros, opciones.replicas, opciones.pasos,
        al_terminar_replica=lambda hechas, total: print(f"  réplica {hechas}/{total}", end="\r"),
    )
    imprimir(resultado, time.perf_counter() - inicio)
    if opciones.csv:
        with opciones.csv.open("w", encoding="utf-8", newline="") as archivo:
            escribir_lote(archivo, resultado)
        print(f"\nCSV guardado en {opciones.csv}")


if __name__ == "__main__":
    main()
