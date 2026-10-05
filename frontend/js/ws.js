// Conexión WebSocket con el servidor: recibe cuadros binarios y mensajes JSON, y envía la
// selección de hormiga. Si la conexión se cae, reintenta cada pocos segundos.

import { TIPO_FEROMONAS, decodificarCuadro, decodificarFeromonas, tipoMensaje } from "./protocolo.js";

const ESPERA_RECONEXION_MS = 2000;

let socket = null;

// manejadores: { cuadro(cuadro), feromonas(campo), mensaje(json), conexion(conectado) }
export function conectar(manejadores) {
  const protocolo = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocolo}://${location.host}/ws/simulacion`);
  socket.binaryType = "arraybuffer";

  socket.addEventListener("open", () => manejadores.conexion(true));
  socket.addEventListener("message", (evento) => {
    if (evento.data instanceof ArrayBuffer) {
      if (tipoMensaje(evento.data) === TIPO_FEROMONAS) manejadores.feromonas(decodificarFeromonas(evento.data));
      else manejadores.cuadro(decodificarCuadro(evento.data));
    } else {
      manejadores.mensaje(JSON.parse(evento.data));
    }
  });
  socket.addEventListener("close", () => {
    manejadores.conexion(false);
    setTimeout(() => conectar(manejadores), ESPERA_RECONEXION_MS);
  });
}

export function enviar(mensaje) {
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(mensaje));
  }
}
