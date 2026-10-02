"""RNF-04: el núcleo de la simulación no depende de la capa web."""

import ast
from pathlib import Path

import pytest

CARPETA_APP = Path(__file__).resolve().parents[1] / "app"
CAPA_WEB = {"api", "servicio"}  # además de main.py
MODULOS_WEB = {"fastapi", "starlette", "uvicorn"}


def archivos_del_nucleo() -> list[Path]:
    return [
        ruta for ruta in CARPETA_APP.rglob("*.py")
        if ruta.name != "main.py" and ruta.relative_to(CARPETA_APP).parts[0] not in CAPA_WEB
    ]


def modulos_importados(ruta: Path) -> set[str]:
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            nombres.update(alias.name.split(".")[0] for alias in nodo.names)
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            nombres.add(nodo.module.split(".")[0])
    return nombres


def test_hay_archivos_del_nucleo() -> None:
    assert archivos_del_nucleo()


@pytest.mark.parametrize("ruta", archivos_del_nucleo(), ids=lambda r: r.relative_to(CARPETA_APP).as_posix())
def test_el_nucleo_no_importa_la_web(ruta: Path) -> None:
    assert not modulos_importados(ruta) & MODULOS_WEB


@pytest.mark.parametrize("ruta", archivos_del_nucleo(), ids=lambda r: r.relative_to(CARPETA_APP).as_posix())
def test_el_nucleo_no_usa_generadores_del_lenguaje(ruta: Path) -> None:
    """Todo número aleatorio sale de un generador configurado (CLAUDE.md §6)."""
    importados = modulos_importados(ruta)
    assert "random" not in importados
    assert "numpy.random" not in ruta.read_text(encoding="utf-8")
