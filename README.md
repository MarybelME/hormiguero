# Simulador educativo de hormiguero

Simulación web de un hormiguero para la materia **Simulación** (Ingeniería en Sistemas).
Es un instrumento didáctico: hace visibles entidades, atributos, eventos, recursos, variables
aleatorias y la generación de números pseudoaleatorios.

- Especificación: [docs/ESPECIFICACION_v2.md](docs/ESPECIFICACION_v2.md)
- Diseño: [docs/DISENO.md](docs/DISENO.md)
- Avance por etapa: [docs/PROGRESO.md](docs/PROGRESO.md)
- Guía para usarlo en clase: [docs/guia_docente.md](docs/guia_docente.md)
- Clonar y ejecutar en otra PC: [PROGRESS.md](PROGRESS.md)

## Requisitos

Python 3.11 o superior y un navegador moderno.

## Instalación

```powershell
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r backend/requirements.txt
```

## Ejecutar

Desde la raíz del proyecto:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

Abrir <http://127.0.0.1:8000>. La documentación interactiva de la API está en
<http://127.0.0.1:8000/docs>.

## Pruebas

```powershell
pytest backend/tests -q
```

## Scripts sin servidor

```powershell
python backend/scripts/benchmark.py                 # pasos por segundo (añadir --feromonas)
python backend/scripts/experimento_lote.py --replicas 10 --pasos 1000 --csv lote.csv
```
