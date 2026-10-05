// Punto de entrada del frontend: une controles, WebSocket, dibujo y paneles.
// El servidor es la única fuente de verdad: aquí sólo se envían comandos y se dibuja lo recibido.

import {
  configurarSimulacion, controlar, obtenerEstado, obtenerParametros, obtenerSalud, vistaPreviaAleatorios,
} from "./api.js";
import { prepararBitacora, prepararRegistro } from "./bitacora.js";
import {
  construirFormulario, fijarValores, fijarVelocidadVisible, leerParametros, mostrarEstadoControlador, prepararBotones,
  prepararVelocidad,
} from "./controles.js";
import { mostrarEstadisticas, prepararEstadisticas, vaciarEstadisticas } from "./estadisticas.js";
import { mostrarHormiga, vaciarPanel } from "./panelDidactico.js";
import { ESTADOS } from "./protocolo.js";
import {
  coordenadasMundo, dibujarCapaDinamica, dibujarCapaEstatica, hormigaMasCercana, limpiarCanvas,
} from "./render.js";
import { mostrarTabla, resumen } from "./tablaAleatorios.js";
import { conectar, enviar } from "./ws.js";

const DISTANCIA_CLIC = 12; // unidades del mundo alrededor del clic para elegir una hormiga

const $ = (id) => document.getElementById(id);
const estadoServidor = $("estado-servidor");
const capaEstatica = $("capa-estatica");
const capaDinamica = $("capa-dinamica");
const mensajeSimulacion = $("mensaje-simulacion");
const formularioParametros = $("formulario-parametros");
const mensajeParametros = $("mensaje-parametros");
const panelDidactico = $("panel-didactico");

// Estado de la vista (no del modelo): lo último recibido del servidor.
const vista = {
  mundo: null,
  cuadro: null,
  cuadroPendiente: false,
  estadoControlador: "vacio",
  seleccion: null,       // { id, dir } de la hormiga seleccionada en esta pestaña
  pSeguir: null,
  valoresDefecto: {},
  valoresDemo: null,
};

const bitacora = prepararBitacora($("filtros-bitacora"), $("tabla-bitacora"), $("mensaje-bitacora"));
const registro = prepararRegistro($("filtros-registro"), $("tabla-registro"), $("mensaje-registro"));

function avisar(elemento, texto, esError = false) {
  elemento.textContent = texto;
  elemento.className = esError ? "mensaje error" : "mensaje";
}

// --- Mensajes del servidor ---------------------------------------------------------------

function alRecibirMundo(datos) {
  vista.mundo = datos.mundo;
  capaDinamica.width = datos.mundo.ancho;
  capaDinamica.height = datos.mundo.alto; // cambiar el tamaño borra el canvas: se redibuja
  vista.cuadroPendiente = true;
  dibujarCapaEstatica(capaEstatica, datos.mundo);
  const g = datos.mundo.generacion;
  avisar(mensajeSimulacion,
    `Semillas: MUNDO = ${datos.semillas.MUNDO}, COMPORTAMIENTO = ${datos.semillas.COMPORTAMIENTO}. ` +
    `Aceptación-rechazo: ${g.candidatos} candidatos, ${g.rechazados} rechazados, ` +
    `${g.numeros_usados} números usados, ${g.resiembras} re-siembras.`);
  bitacora.fijarHayMundo(true);
  registro.fijarHayMundo(true);
}

function alRecibirControl(datos) {
  vista.estadoControlador = datos.estado_controlador;
  mostrarEstadoControlador(datos.estado_controlador, datos.pasos_por_segundo);
  if (datos.estado_controlador === "vacio") {
    vista.mundo = null;
    vista.cuadro = null;
    deseleccionar();
    limpiarCanvas(capaEstatica);
    limpiarCanvas(capaDinamica);
    vaciarEstadisticas();
    bitacora.fijarHayMundo(false);
    registro.fijarHayMundo(false);
    avisar(mensajeSimulacion, "Sin mundo: pulsa Iniciar o Aplicar para crear una corrida con los parámetros del formulario.");
  }
}

function alRecibirMensaje(mensaje) {
  switch (mensaje.tipo) {
    case "control": alRecibirControl(mensaje); break;
    case "mundo": alRecibirMundo(mensaje); break;
    case "estadisticas":
      vista.pSeguir = mensaje.p_seguir_reina;
      mostrarEstadisticas(mensaje);
      break;
    case "seleccion":
      if (vista.seleccion?.id !== mensaje.hormiga.id) return; // llegó tarde, ya se cambió
      vista.seleccion.dir = mensaje.hormiga.dir;
      mostrarHormiga(panelDidactico, mensaje.hormiga, vista.pSeguir, {
        deseleccionar, verEventos: (id) => bitacora.filtrarPorHormiga(id),
      });
      vista.cuadroPendiente = true;
      break;
    case "deseleccion": // el servidor la borró (corrida nueva)
      vista.seleccion = null;
      vista.cuadroPendiente = true;
      vaciarPanel(panelDidactico);
      break;
    case "error": avisar(mensajeSimulacion, mensaje.mensaje, true); break;
  }
}

function alRecibirCuadro(cuadro) {
  vista.cuadro = cuadro;
  vista.cuadroPendiente = true;
}

// Se dibuja a lo sumo una vez por refresco de pantalla y sólo el último cuadro recibido.
function dibujar() {
  if (vista.cuadroPendiente && vista.mundo && vista.cuadro) {
    dibujarCapaDinamica(capaDinamica, vista.mundo, vista.cuadro, vista.seleccion);
    vista.cuadroPendiente = false;
  }
  requestAnimationFrame(dibujar);
}

// --- Selección de hormiga ----------------------------------------------------------------

function seleccionar(id) {
  vista.seleccion = { id, dir: null };
  enviar({ tipo: "seleccionar", id });
}

function deseleccionar() {
  if (vista.seleccion) enviar({ tipo: "deseleccionar" });
  vista.seleccion = null;
  vista.cuadroPendiente = true;
  vaciarPanel(panelDidactico);
}

capaDinamica.addEventListener("click", (evento) => {
  if (!vista.mundo || !vista.cuadro) return;
  const punto = coordenadasMundo(capaDinamica, vista.mundo, evento);
  const id = hormigaMasCercana(vista.cuadro, punto, DISTANCIA_CLIC);
  if (id >= 0) seleccionar(id);
  else deseleccionar();
});

// --- Controles ---------------------------------------------------------------------------

async function aplicarParametros() {
  const parametros = leerParametros(formularioParametros);
  if (!parametros) throw new Error("Revisa los parámetros marcados: están fuera de rango.");
  deseleccionar();
  await configurarSimulacion(parametros);
  avisar(mensajeParametros, "Corrida nueva creada en t = 0.");
}

const TEXTO_ACCION = {
  iniciar: "Simulación en marcha.",
  pausar: "Simulación en pausa.",
  reiniciar: "De vuelta en t = 0 con la misma configuración: pulsa Iniciar para repetir la corrida.",
  limpiar: "Se borró la corrida.",
};

async function alAccion(accion) {
  avisar(mensajeParametros, "");
  let estado;
  if (accion === "iniciar") {
    // El servidor pudo perder la corrida (p. ej. si se reinició): se consulta antes de iniciar.
    if ((await obtenerEstado()).estado_controlador === "vacio") await aplicarParametros();
    estado = await controlar("iniciar");
  } else {
    estado = await controlar(accion);
  }
  // La respuesta REST actualiza los botones de inmediato, aunque el WebSocket tarde.
  alRecibirControl(estado);
  if (accion !== "limpiar") avisar(mensajeSimulacion, TEXTO_ACCION[accion]);
}

// Llena el formulario con los parámetros de demostración, crea la corrida y la inicia.
async function cargarDemo() {
  if (!vista.valoresDemo) throw new Error("Todavía no se cargan los parámetros del servidor.");
  fijarValores(formularioParametros, vista.valoresDemo);
  fijarVelocidadVisible(vista.valoresDemo.pasos_por_segundo);
  await aplicarParametros();
  alRecibirControl(await controlar("iniciar"));
  avisar(mensajeParametros, "Simulación demo: 3 000 hormigas, fuentes pequeñas que se agotan y p = 0.5. Haz clic en una hormiga para seguirla.");
}

function alError(error) {
  avisar(mensajeSimulacion, error.message, true);
}

formularioParametros.addEventListener("submit", (evento) => {
  evento.preventDefault();
  aplicarParametros().catch((error) => avisar(mensajeParametros, error.message, true));
});
$("boton-valores-defecto").addEventListener("click", () => fijarValores(formularioParametros, vista.valoresDefecto));
$("boton-demo").addEventListener("click", () => cargarDemo().catch(alError));

function prepararLeyendaEstados() {
  const leyenda = $("leyenda-estados");
  for (const estado of ESTADOS) {
    if (estado.codigo === 0) continue; // en el nido no se dibujan
    const li = document.createElement("li");
    const muestra = document.createElement("span");
    muestra.className = "muestra cuadrada";
    muestra.style.background = `var(--estado-${estado.codigo})`;
    li.append(muestra, `${estado.texto} (${estado.codigo})`);
    leyenda.append(li);
  }
}

// --- Vista previa del generador (etapa E1) -----------------------------------------------

const formularioGenerador = $("formulario-generador");

async function generarTabla(evento) {
  evento?.preventDefault();
  const solicitud = {
    semilla: Number(formularioGenerador.semilla.value),
    digitos: Number(formularioGenerador.digitos.value),
    cantidad: Number(formularioGenerador.cantidad.value),
  };
  try {
    const datos = await vistaPreviaAleatorios(solicitud);
    mostrarTabla($("tabla-aleatorios"), datos);
    avisar($("mensaje-generador"), resumen(datos));
  } catch (error) {
    avisar($("mensaje-generador"), error.message, true);
  }
}

formularioGenerador.addEventListener("submit", generarTabla);

// --- Arranque ----------------------------------------------------------------------------

let textoServidor = "Servidor";

async function iniciarPagina() {
  prepararEstadisticas($("estadisticas"));
  prepararLeyendaEstados();
  prepararBotones(alAccion, alError);
  prepararVelocidad(alError);
  mostrarEstadoControlador("vacio", 30);
  generarTabla();

  try {
    const salud = await obtenerSalud();
    textoServidor = `Servidor en línea · v${salud.version}`;
    estadoServidor.textContent = textoServidor;
    estadoServidor.className = "estado-servidor ok";
    const { valores, demo, esquema } = await obtenerParametros();
    vista.valoresDefecto = valores;
    vista.valoresDemo = demo;
    construirFormulario(formularioParametros, esquema, valores);
    // La simulación es compartida: si ya existe una corrida, no se reemplaza al abrir la página.
    const estado = await obtenerEstado();
    if (estado.estado_controlador === "vacio") await aplicarParametros();
  } catch (error) {
    estadoServidor.textContent = "Sin conexión con el servidor";
    estadoServidor.className = "estado-servidor error";
    alError(error);
  }

  conectar({
    cuadro: alRecibirCuadro,
    mensaje: alRecibirMensaje,
    conexion: (conectado) => {
      estadoServidor.textContent = conectado ? textoServidor : `${textoServidor} · tiempo real desconectado (reintentando)`;
      estadoServidor.className = conectado ? "estado-servidor ok" : "estado-servidor error";
      if (conectado && vista.seleccion) enviar({ tipo: "seleccionar", id: vista.seleccion.id });
    },
  });
  requestAnimationFrame(dibujar);
  document.body.dataset.lista = "si";
}

iniciarPagina();
