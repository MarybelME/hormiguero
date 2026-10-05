// Laboratorio de generadores (RF-62): compara métodos con las mismas pruebas estadísticas.
// El servidor genera las muestras y calcula los estadísticos; aquí sólo se arma la solicitud
// y se presenta la tabla comparativa con un histograma por generador.

import { descargarCsv, probarGeneradores } from "./api.js";

const DECIMALES = 4;

function nodo(etiqueta, texto, clase) {
  const elemento = document.createElement(etiqueta);
  if (texto !== undefined) elemento.textContent = texto;
  if (clase) elemento.className = clase;
  return elemento;
}

const numero = (x) => Number(x).toFixed(DECIMALES);

// Barras de frecuencia por intervalo, con una línea en la frecuencia esperada n/k.
function histograma(frecuencias, n) {
  const contenedor = nodo("div", undefined, "histograma");
  const esperada = n / frecuencias.length;
  const maximo = Math.max(...frecuencias, esperada);
  const linea = nodo("div", undefined, "esperada");
  linea.style.bottom = `${(esperada / maximo) * 100}%`;
  linea.title = `Frecuencia esperada n/k = ${esperada.toFixed(1)}`;
  contenedor.append(linea);
  frecuencias.forEach((f, j) => {
    const barra = nodo("div", undefined, "barra");
    barra.style.height = `${(f / maximo) * 100}%`;
    barra.title = `[${(j / frecuencias.length).toFixed(2)}, ${((j + 1) / frecuencias.length).toFixed(2)}): ${f}`;
    contenedor.append(barra);
  });
  return contenedor;
}

function decision(prueba) {
  const celda = nodo("td", undefined, prueba.rechaza ? "rechaza" : "no-rechaza");
  celda.append(
    nodo("div", `estadístico ${numero(prueba.estadistico)} · crítico ${numero(prueba.valor_critico)}`),
    nodo("div", `p = ${numero(prueba.p_valor)}`),
    nodo("strong", prueba.rechaza ? "Se rechaza H₀" : "No se rechaza H₀"),
  );
  if (prueba.detalle.advertencia) celda.append(nodo("div", `⚠ ${prueba.detalle.advertencia}`, "ayuda"));
  return celda;
}

function fila(titulo, celdas) {
  const tr = nodo("tr");
  tr.append(nodo("th", titulo), ...celdas);
  return tr;
}

function tablaComparativa(datos) {
  const resultados = datos.resultados;
  const tabla = nodo("table", undefined, "tabla-datos tabla-laboratorio");
  const cabeza = nodo("tr");
  cabeza.append(nodo("th", ""), ...resultados.map((r) => nodo("th", r.nombre)));
  tabla.createTHead().append(cabeza);
  const cuerpo = tabla.createTBody();
  const celdas = (f) => resultados.map((r) => {
    const td = nodo("td");
    const contenido = f(r);
    if (typeof contenido === "string") td.textContent = contenido;
    else td.append(contenido);
    return td;
  });
  cuerpo.append(
    fila("Semilla · módulo m", celdas((r) => `${r.semilla} · ${Number(r.modulo).toLocaleString("es")}`)),
    fila("Re-siembras (degeneraciones)", celdas((r) => String(r.resiembras))),
    fila("Números distintos", celdas((r) => `${r.muestra.distintos} de ${r.muestra.n}`)),
    fila("Media (esperada 0.5)", celdas((r) => numero(r.muestra.media))),
    fila("Varianza (esperada 1/12 ≈ 0.0833)", celdas((r) => numero(r.muestra.varianza))),
    fila("Histograma (k intervalos)", celdas((r) => histograma(r.muestra.histograma, r.muestra.n))),
    fila("Primeros números", celdas((r) => r.primeros.slice(0, 5).map((u) => u.toFixed(DECIMALES)).join(", "))),
  );
  resultados[0].pruebas.forEach((prueba, i) => {
    const tr = fila(`${prueba.prueba} — H₀: ${prueba.hipotesis_nula}`, []);
    tr.append(...resultados.map((r) => decision(r.pruebas[i])));
    cuerpo.append(tr);
  });
  return tabla;
}

// leerConstantes() devuelve { digitos, congruencial_a, … } del panel de parámetros.
export function prepararLaboratorio({ formulario, casillas, resultados, mensaje, botonCsv, nombres, leerConstantes }) {
  for (const [metodo, nombre] of Object.entries(nombres)) {
    const etiqueta = nodo("label", undefined, "casilla");
    const casilla = nodo("input");
    casilla.type = "checkbox";
    casilla.name = "generador";
    casilla.value = metodo;
    casilla.checked = true;
    etiqueta.append(casilla, ` ${nombre}`);
    casillas.append(etiqueta);
  }

  function avisarError(texto) {
    mensaje.textContent = texto;
    mensaje.className = "mensaje error";
  }

  // La solicitud con los generadores elegidos, o null si el formulario no es válido.
  function armarSolicitud() {
    if (!formulario.reportValidity()) return null;
    const elegidos = [...formulario.querySelectorAll("input[name=generador]:checked")].map((c) => c.value);
    if (elegidos.length === 0) {
      avisarError("Elige al menos un generador.");
      return null;
    }
    const semilla = Number(formulario.semilla.value);
    const constantes = leerConstantes();
    return {
      generadores: elegidos.map((generador) => ({ generador, semilla, ...constantes })),
      cantidad: Number(formulario.cantidad.value),
      intervalos: Number(formulario.intervalos.value),
      alfa: Number(formulario.alfa.value),
    };
  }

  botonCsv.addEventListener("click", () => {
    const solicitud = armarSolicitud();
    if (!solicitud) return;
    descargarCsv("/api/aleatorio/pruebas.csv", solicitud)
      .then((nombre) => { mensaje.textContent = `Descargado ${nombre}.`; mensaje.className = "mensaje"; })
      .catch((error) => avisarError(error.message));
  });

  formulario.addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const solicitud = armarSolicitud();
    if (!solicitud) return;
    mensaje.textContent = "Generando y probando…";
    mensaje.className = "mensaje";
    try {
      const datos = await probarGeneradores(solicitud);
      resultados.replaceChildren(tablaComparativa(datos));
      mensaje.textContent = `${datos.cantidad} números por generador, k = ${datos.intervalos}, α = ${datos.alfa}.`;
    } catch (error) {
      avisarError(error.message);
    }
  });
}
