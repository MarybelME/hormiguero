// Punto de entrada del frontend: conecta los formularios con la API y dibuja lo que devuelve.

import { configurarSimulacion, obtenerSalud, vistaPreviaAleatorios } from "./api.js";
import { dibujarCapaEstatica } from "./render.js";
import { mostrarTabla, resumen } from "./tablaAleatorios.js";

const estadoServidor = document.getElementById("estado-servidor");
const formulario = document.getElementById("formulario-generador");
const mensaje = document.getElementById("mensaje-generador");
const tabla = document.getElementById("tabla-aleatorios");
const formularioMundo = document.getElementById("formulario-mundo");
const mensajeMundo = document.getElementById("mensaje-mundo");
const capaEstatica = document.getElementById("capa-estatica");

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

function describirMundo(datos) {
  const g = datos.mundo.generacion;
  return (
    `Semillas: MUNDO = ${datos.semillas.MUNDO}, COMPORTAMIENTO = ${datos.semillas.COMPORTAMIENTO}. ` +
    `Aceptación-rechazo: ${g.candidatos} candidatos, ${g.rechazados} rechazados, ` +
    `${g.numeros_usados} números usados, ${g.resiembras} re-siembras.`
  );
}

async function generarMundo(evento) {
  evento?.preventDefault();
  const parametros = {
    semilla: Number(formularioMundo.semilla.value),
    digitos: Number(formularioMundo.digitos.value),
    num_obstaculos: Number(formularioMundo.num_obstaculos.value),
    num_fuentes: Number(formularioMundo.num_fuentes.value),
  };
  try {
    const datos = await configurarSimulacion(parametros);
    dibujarCapaEstatica(capaEstatica, datos.mundo);
    mensajeMundo.textContent = describirMundo(datos);
    mensajeMundo.className = "mensaje";
  } catch (error) {
    mensajeMundo.textContent = error.message;
    mensajeMundo.className = "mensaje error";
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

formularioMundo.addEventListener("submit", generarMundo);
formulario.addEventListener("submit", generar);
comprobarServidor();
generarMundo();
generar();
