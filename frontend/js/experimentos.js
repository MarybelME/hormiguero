// Panel "Experimentos": réplicas por lote (RF-60).
// El servidor corre el lote en segundo plano con los parámetros del formulario, cambiando sólo
// la semilla; aquí se lanza, se consulta el avance y se muestra el resumen con su IC del 95 %.

import { cancelarLote, descargarCsv, iniciarLote, obtenerLote } from "./api.js";

const INTERVALO_CONSULTA_MS = 500;
const CIFRAS = 4;

function nodo(etiqueta, texto, clase) {
  const elemento = document.createElement(etiqueta);
  if (texto !== undefined) elemento.textContent = texto;
  if (clase) elemento.className = clase;
  return elemento;
}

// Los conteos enteros se muestran completos; los demás, con CIFRAS cifras significativas.
function numero(x) {
  if (x === null || x === undefined) return "—";
  return (Number.isInteger(x) ? x : Number(x.toPrecision(CIFRAS))).toLocaleString("es");
}

function tablaResumen(resultado) {
  const tabla = nodo("table", undefined, "tabla-datos");
  const cabeza = nodo("tr");
  for (const titulo of ["Variable de salida", "Réplicas", "Media", "Desv. estándar", "IC 95 %", "Mín.", "Máx."]) {
    cabeza.append(nodo("th", titulo));
  }
  tabla.createTHead().append(cabeza);
  const cuerpo = tabla.createTBody();
  for (const r of resultado.resumen) {
    const tr = nodo("tr");
    const intervalo = r.ic_inferior === null ? "—" : `[${numero(r.ic_inferior)}, ${numero(r.ic_superior)}]`;
    tr.append(nodo("td", r.descripcion, "izquierda"), nodo("td", r.n), nodo("td", numero(r.media)),
      nodo("td", numero(r.desviacion)), nodo("td", intervalo), nodo("td", numero(r.minimo)),
      nodo("td", numero(r.maximo)));
    cuerpo.append(tr);
  }
  return tabla;
}

function tablaReplicas(resultado) {
  const variables = resultado.resumen.map((r) => r.variable);
  const tabla = nodo("table", undefined, "tabla-datos");
  const cabeza = nodo("tr");
  cabeza.append(nodo("th", "Réplica"), nodo("th", "Semilla"),
    ...resultado.resumen.map((r) => nodo("th", r.descripcion)));
  tabla.createTHead().append(cabeza);
  const cuerpo = tabla.createTBody();
  resultado.replicas.forEach((replica, i) => {
    const tr = nodo("tr");
    tr.append(nodo("td", i + 1), nodo("td", replica.semilla), ...variables.map((v) => nodo("td", numero(replica[v]))));
    cuerpo.append(tr);
  });
  return tabla;
}

function mostrarResultado(contenedor, resultado) {
  const detalle = nodo("details");
  detalle.append(nodo("summary", `Ver las ${resultado.replicas.length} réplicas`),
    nodo("div", undefined, "contenedor-tabla"));
  detalle.lastChild.append(tablaReplicas(resultado));
  const semillas = resultado.semillas;
  contenedor.replaceChildren(
    nodo("p", `${resultado.replicas.length} réplicas de ${resultado.pasos} pasos con las semillas ` +
      `${semillas[0]} … ${semillas[resultado.replicas.length - 1]}; todo lo demás igual.`, "ayuda"),
    tablaResumen(resultado),
    detalle,
  );
}

// leerParametros() devuelve los parámetros del formulario (o null si hay un error).
export function prepararExperimentos({ formulario, mensaje, resultados, botonCancelar, botonCsv, leerParametros }) {
  let consulta = null;

  function avisar(texto, esError = false) {
    mensaje.textContent = texto;
    mensaje.className = esError ? "mensaje error" : "mensaje";
  }

  function mostrarEstado(datos) {
    const corriendo = datos.estado === "corriendo";
    formulario.querySelector("button[type=submit]").disabled = corriendo;
    botonCancelar.disabled = !corriendo;
    botonCsv.disabled = !datos.resultado || datos.resultado.replicas.length === 0;
    if (corriendo) avisar(`Corriendo réplica ${datos.hechas + 1} de ${datos.total}…`);
    else if (datos.estado === "terminado") avisar("Lote terminado.");
    else if (datos.estado === "cancelado") avisar(`Lote cancelado tras ${datos.hechas} réplicas.`);
    else if (datos.estado === "error") avisar(datos.error, true);
    if (datos.resultado && datos.resultado.replicas.length > 0) mostrarResultado(resultados, datos.resultado);
    if (!corriendo && consulta) {
      clearInterval(consulta);
      consulta = null;
    }
  }

  async function consultar() {
    try {
      mostrarEstado(await obtenerLote());
    } catch (error) {
      avisar(error.message, true);
    }
  }

  function seguir() {
    if (!consulta) consulta = setInterval(consultar, INTERVALO_CONSULTA_MS);
  }

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    if (!formulario.reportValidity()) return;
    const parametros = leerParametros();
    if (!parametros) {
      avisar("Revisa el panel de parámetros: hay valores fuera de rango.", true);
      return;
    }
    const semilla = formulario.semilla_inicial.value;
    try {
      mostrarEstado(await iniciarLote({
        parametros,
        replicas: Number(formulario.replicas.value),
        pasos: Number(formulario.pasos.value),
        semilla_inicial: semilla === "" ? null : Number(semilla),
      }));
      resultados.replaceChildren();
      seguir();
    } catch (error) {
      avisar(error.message, true);
    }
  });
  botonCancelar.addEventListener("click", () => cancelarLote().then(mostrarEstado).catch((e) => avisar(e.message, true)));
  botonCsv.addEventListener("click", () => descargarCsv("/api/experimentos/resultado.csv")
    .then((nombre) => avisar(`Descargado ${nombre}.`))
    .catch((e) => avisar(e.message, true)));

  // Si al abrir la página ya hay un lote (es compartido como la simulación), se muestra.
  obtenerLote().then((datos) => {
    mostrarEstado(datos);
    if (datos.estado === "corriendo") seguir();
  }).catch(() => {});
}
