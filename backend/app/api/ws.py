"""WebSocket `/ws/simulacion`: flujo de cuadros y mensajes en tiempo real (DISENO.md §12.2).

Servidor → cliente: cuadros binarios (`protocolo.py`) y mensajes JSON `control`, `mundo`,
`estadisticas`, `seleccion` y `error`.
Cliente → servidor (JSON): `{"tipo": "seleccionar", "id": 123}` y `{"tipo": "deseleccionar"}`.
Los comandos de control (iniciar, pausar…) van por REST.
"""

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.servicio.controlador import AccionInvalida, ControladorSimulacion, Suscripcion

router = APIRouter()


async def _enviar(websocket: WebSocket, suscripcion: Suscripcion) -> None:
    while True:
        for mensaje in await suscripcion.siguiente():
            if isinstance(mensaje, bytes):
                await websocket.send_bytes(mensaje)
            else:
                await websocket.send_json(mensaje)


async def _recibir(websocket: WebSocket, controlador: ControladorSimulacion,
                   suscripcion: Suscripcion) -> None:
    while True:
        texto = await websocket.receive_text()
        try:
            mensaje = json.loads(texto)
        except json.JSONDecodeError:
            mensaje = None
        tipo = mensaje.get("tipo") if isinstance(mensaje, dict) else None
        try:
            if tipo == "seleccionar":
                id_hormiga = mensaje.get("id")
                if not isinstance(id_hormiga, int) or isinstance(id_hormiga, bool):
                    raise AccionInvalida("El id de la hormiga debe ser un entero")
                controlador.seleccionar(suscripcion, id_hormiga)
            elif tipo == "deseleccionar":
                controlador.deseleccionar(suscripcion)
            else:
                raise AccionInvalida(f"Mensaje desconocido: {tipo!r}")
        except AccionInvalida as error:
            suscripcion.enviar_mensaje({"tipo": "error", "mensaje": str(error)})


@router.websocket("/ws/simulacion")
async def ws_simulacion(websocket: WebSocket) -> None:
    await websocket.accept()
    controlador: ControladorSimulacion = websocket.app.state.controlador
    suscripcion = controlador.suscribir()
    tareas = [
        asyncio.create_task(_enviar(websocket, suscripcion)),
        asyncio.create_task(_recibir(websocket, controlador, suscripcion)),
    ]
    try:
        hechas, _ = await asyncio.wait(tareas, return_when=asyncio.FIRST_COMPLETED)
        for tarea in hechas:
            error = tarea.exception()
            if error is not None and not isinstance(error, WebSocketDisconnect):
                raise error
    finally:
        for tarea in tareas:
            tarea.cancel()
        controlador.desuscribir(suscripcion)
