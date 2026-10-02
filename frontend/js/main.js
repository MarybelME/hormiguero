// Punto de entrada del frontend: conecta el formulario del generador con la API.

import { obtenerSalud, vistaPreviaAleatorios } from "./api.js";
import { mostrarTabla, resumen } from "./tablaAleatorios.js";

const estadoServidor = document.getElementById("estado-servidor");
const formulario = document.getElementById("formulario-generador");
const mensaje = document.getElementById("mensaje-generador");
const tabla = document.getElementById("tabla-aleatorios");

async function comprobarServidor() {
  try {
    const salud = await obtenerSalud();
    estadoServidor.textContent = `Servidor en línea · v${salud.version}`;
    estadoServidor.className = "estado-servidor ok";
  } catch {
    estadoServidor.textContent = "Sin conexión con el servidor";
    estadoServidor.className = "estado-servidor error";
  }
}

async function generar(evento) {
  evento?.preventDefault();
  const solicitud = {
    semilla: Number(formulario.semilla.value),
    digitos: Number(formulario.digitos.value),
    cantidad: Number(formulario.cantidad.value),
  };
  try {
    const datos = await vistaPreviaAleatorios(solicitud);
    mostrarTabla(tabla, datos);
    mensaje.textContent = resumen(datos);
    mensaje.className = "mensaje";
  } catch (error) {
    mensaje.textContent = error.message;
    mensaje.className = "mensaje error";
  }
}

formulario.addEventListener("submit", generar);
comprobarServidor();
generar();
