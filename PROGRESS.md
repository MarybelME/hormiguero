# PROGRESS.md — Cómo clonar y ejecutar el simulador en otra PC

Guía rápida para tener el proyecto funcionando en una computadora nueva y saber en qué punto
va. La bitácora detallada de cada etapa está en [docs/PROGRESO.md](docs/PROGRESO.md).

---

## 1. Estado actual

| Etapa | Estado |
|---|---|
| E0 Análisis y diseño | Terminada |
| E1 Base y generadores | Terminada |
| E2 Modelo y motor | Terminada |
| E3 Tiempo real, interfaz y modo didáctico | Terminada (pendiente de revisión) |
| E4 Experimentación, feromonas y pulido | Pendiente |

Qué se puede hacer hoy: generar el mundo con una semilla, correr la simulación en tiempo real
(iniciar, pausar, reiniciar, limpiar, cambiar la velocidad), ver las estadísticas en vivo,
seleccionar una hormiga con un clic para ver el número pseudoaleatorio que usó y su cálculo,
consultar la bitácora de eventos y el registro de números, y lanzar una **simulación demo**.

> **Importante:** un clon sólo trae lo que está subido a GitHub. Si la etapa E3 todavía no
> tiene commit y push, el clon tendrá la versión de la etapa E2 (sin tiempo real). Comprueba
> con `git log --oneline -1` que el último commit sea el de la etapa 3.

---

## 2. Requisitos

- **Git** — <https://git-scm.com/downloads>
- **Python 3.11 o superior** (se desarrolló con 3.13) — <https://www.python.org/downloads/>.
  En Windows, marca "Add python.exe to PATH" al instalar.
- Un navegador moderno (Edge, Chrome o Firefox).

Comprueba en una terminal:

```powershell
git --version
python --version
```

---

## 3. Clonar e instalar (una sola vez)

En PowerShell (Windows):

```powershell
git clone https://github.com/MarybelME/hormiguero.git
cd hormiguero
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
```

En Linux o macOS, cambia la activación por `source .venv/bin/activate` (y usa `python3` si
`python` no existe).

Si PowerShell no deja activar el entorno ("la ejecución de scripts está deshabilitada"), ejecuta
una vez:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

o bien no lo actives y antepone `.venv\Scripts\python -m` a cada comando
(por ejemplo `.venv\Scripts\python -m uvicorn ...`).

---

## 4. Comprobar que todo funciona

Desde la carpeta del proyecto, con el entorno activado:

```powershell
pytest backend/tests -q
```

Deben pasar todas las pruebas (216 al cerrar la etapa E3). El aviso de Starlette sobre `httpx2`
es normal y no afecta.

Opcional, para medir el rendimiento del núcleo sin servidor:

```powershell
python backend/scripts/benchmark.py
```

---

## 5. Ejecutar el simulador

```powershell
uvicorn app.main:app --reload --app-dir backend
```

Abre <http://127.0.0.1:8000>. La documentación interactiva de la API está en
<http://127.0.0.1:8000/docs>. Para detener el servidor: `Ctrl+C` en la terminal.

Prueba rápida:

1. Pulsa **★ Simulación demo**: se cargan 3 000 hormigas y la simulación arranca sola.
2. Pulsa **Pausar** y haz clic sobre una hormiga: el panel muestra su último número
   pseudoaleatorio, su cálculo paso a paso y el siguiente evento previsto.
3. **Reiniciar** vuelve a t = 0: al iniciar de nuevo se repite exactamente la misma corrida.

---

## 6. Si algo no funciona

| Síntoma | Solución |
|---|---|
| Los botones no hacen nada o el encabezado dice "La interfaz no terminó de cargar" | Recarga con **Ctrl+F5** (el navegador guardó archivos JS de una versión anterior). |
| `python` no se reconoce | Reinstala Python marcando "Add to PATH", o usa `py` en lugar de `python`. |
| `uvicorn` o `pytest` no se reconocen | El entorno no está activado: `.venv\Scripts\activate`. |
| "Address already in use" / puerto 8000 ocupado | Hay otro servidor abierto. Ciérralo o usa otro puerto: `uvicorn app.main:app --reload --app-dir backend --port 8001`. |
| El encabezado dice "tiempo real desconectado" | El servidor se detuvo o se está reiniciando; la página se reconecta sola en unos segundos. |
| Con `--reload` el servidor no toma los cambios | Detén con `Ctrl+C` y vuelve a ejecutarlo (en Windows, `--reload` necesita correr en una terminal visible). |

---

## 7. Continuar el desarrollo en la otra PC

- Antes de trabajar: `git pull` para traer lo último.
- Al terminar: `git add -A`, `git commit -m "…"` y `git push`, para tenerlo en las dos PCs.
- Si trabajas con Claude Code, la guía permanente es [CLAUDE.md](CLAUDE.md); cada etapa empieza
  leyendo [docs/DISENO.md](docs/DISENO.md) y [docs/PROGRESO.md](docs/PROGRESO.md).
- Siguiente paso del plan: revisar E3 y, cuando se apruebe, empezar la etapa **E4**
  (réplicas por lote, CSV, pruebas estadísticas, otros generadores, feromonas y guía docente).
