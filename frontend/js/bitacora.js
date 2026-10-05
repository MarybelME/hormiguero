// Bitácora de eventos filtrable (RF-52) y registro de números pseudoaleatorios de la corrida.
// Ambas tablas se piden por REST: el servidor filtra y pagina; aquí sólo se muestran.

import { obtenerEventos, obtenerRegistro } from "./api.js";
import { celda, celdaRelleno, rellenarCeros } from "./tablaAleatorios.js";

const INTERVALO_AUTOMATICO_MS = 1000;
const SIN_VALOR = -1; // id de hormiga o índice de número ausente

function formatearDetalle(detalle) {
  return Object.entries(detalle)
    .map(([clave, valor]) => `${clave} = ${typeof valor === "number" && !Number.isInteger(valor) ? valor.toFixed(4) : valor}`)
    .join(", ");
}

function filaEvento(evento) {
  const tr = document.createElement("tr");
  tr.append(
    celda(evento.tick),
    celda(evento.tiempo.toFixed(1)),
    celda(evento.tipo),
    celda(evento.id_hormiga === SIN_VALOR ? "—" : evento.id_hormiga),
    celda(evento.indice_aleatorio === SIN_VALOR ? "—" : `#${evento.indice_aleatorio}`),
    celda(formatearDetalle(evento.detalle), "izquierda"),
  );
  if (evento.tipo === "GENERADOR_DEGENERADO") tr.className = "degenerado";
  return tr;
}

function filaRegistro(entrada) {
  const c = entrada.calculo;
  const tr = document.createElement("tr");
  tr.append(
    celda(entrada.indice),
    celda(entrada.flujo),
    celda(entrada.proposito, "izquierda"),
    celda(entrada.id_hormiga === SIN_VALOR ? "—" : entrada.id_hormiga),
    celda(entrada.tick),
    celda(rellenarCeros(c.previo, c.digitos)),
    celda(c.cuadrado.toLocaleString("es")),
    celdaRelleno(c.relleno, c.digitos),
    celda(c.centrales, "centrales"),
    celda(entrada.u.toFixed(c.digitos)),
  );
  if (c.degeneracion) {
    tr.className = "degenerado";
    tr.title = `Degeneró (${c.degeneracion.tipo}); re-siembra con semilla ${c.degeneracion.semilla_nueva}`;
  }
  return tr;
}

// Une un formulario de filtros, una tabla y un mensaje, con actualización automática opcional.
function prepararTabla({ formulario, tabla, mensaje, pedir, fila, describir, alRecibir }) {
  let hayMundo = false;

  async function actualizar() {
    if (!hayMundo) return;
    const filtros = Object.fromEntries(new FormData(formulario));
    delete filtros.automatico;
    try {
      const datos = await pedir(filtros);
      alRecibir?.(datos);
      const filas = document.createDocumentFragment();
      for (const elemento of describir(datos).filas) filas.append(fila(elemento));
      tabla.tBodies[0].replaceChildren(filas);
      mensaje.textContent = describir(datos).resumen;
      mensaje.className = "mensaje";
    } catch (error) {
      mensaje.textContent = error.message;
      mensaje.className = "mensaje error";
    }
  }

  formulario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    if (formulario.reportValidity()) actualizar();
  });
  setInterval(() => {
    if (formulario.elements.automatico.checked && !document.hidden) actualizar();
  }, INTERVALO_AUTOMATICO_MS);

  return {
    actualizar,
    fijarHayMundo(valor) {
      hayMundo = valor;
      if (!valor) {
        tabla.tBodies[0].replaceChildren();
        mensaje.textContent = "";
      }
    },
  };
}

export function prepararBitacora(formulario, tabla, mensaje) {
  const selectorTipo = formulario.elements.tipo;
  const controlador = prepararTabla({
    formulario, tabla, mensaje,
    pedir: obtenerEventos,
    fila: filaEvento,
    describir: (datos) => ({
      filas: datos.eventos,
      resumen: `${datos.eventos.length} eventos mostrados de ${datos.total} registrados en la corrida.`,
    }),
    // El catálogo de tipos lo envía el servidor; se carga una sola vez en el selector.
    alRecibir: (datos) => {
      if (selectorTipo.options.length > 1) return;
      for (const tipo of datos.tipos) selectorTipo.append(new Option(tipo, tipo));
    },
  });
  return {
    ...controlador,
    filtrarPorHormiga(id) {
      formulario.elements.id_hormiga.value = id;
      controlador.actualizar();
      formulario.scrollIntoView({ behavior: "smooth", block: "start" });
    },
  };
}

export function prepararRegistro(formulario, tabla, mensaje) {
  return prepararTabla({
    formulario, tabla, mensaje,
    pedir: obtenerRegistro,
    fila: filaRegistro,
    describir: (datos) => ({
      filas: datos.entradas,
      resumen: `${datos.total} números generados en la corrida; en memoria desde el #${datos.primer_indice_disponible}.`,
    }),
  });
}
