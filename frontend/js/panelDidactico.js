// Panel didáctico de la hormiga seleccionada (RF-50, RF-51).
// Muestra sus atributos, el último número pseudoaleatorio que usó con su cálculo paso a paso,
// su último evento y el siguiente evento previsto. Todo lo calcula el servidor; aquí sólo se
// presenta (el ángulo u · 360° se muestra para explicar cómo se obtuvo la dirección).

import { ESTADOS } from "./protocolo.js";
import { celdaRelleno, describirDegeneracion, rellenarCeros } from "./tablaAleatorios.js";

const TEXTO_ESTADO = Object.fromEntries(ESTADOS.map((e) => [e.nombre, e.texto]));
const GRADOS_POR_VUELTA = 360;

function elemento(etiqueta, texto, clase) {
  const nodo = document.createElement(etiqueta);
  if (texto !== undefined) nodo.textContent = texto;
  if (clase) nodo.className = clase;
  return nodo;
}

function listaAtributos(pares) {
  const dl = elemento("dl", undefined, "atributos");
  for (const [nombre, valor] of pares) {
    dl.append(elemento("dt", nombre), elemento("dd", valor));
  }
  return dl;
}

function atributos(h) {
  return listaAtributos([
    ["Estado", `${TEXTO_ESTADO[h.estado]} (${h.estado})`],
    ["Estado previo", h.estado_previo],
    ["Posición (x, y)", `(${h.x.toFixed(1)}, ${h.y.toFixed(1)})`],
    ["Dirección", `${h.dir.toFixed(1)}°`],
    ["Velocidad", `${h.vel.toFixed(1)} unidades/s`],
    ["Energía", h.energia.toFixed(1)],
    ["Carga", `${h.carga} unidades`],
    ["Pasos restantes", h.pasos_restantes],
    ["Dentro del radio de la reina", h.en_radio_reina ? "sí" : "no"],
  ]);
}

// Qué significó el número para la hormiga, según su propósito.
function interpretacion(numero, pSeguir) {
  if (numero.proposito.startsWith("DIRECCION")) {
    return `dirección = u · 360° = ${(numero.u * GRADOS_POR_VUELTA).toFixed(2)}°`;
  }
  if (numero.proposito === "SEGUIR_REINA" && pSeguir !== null) {
    const sigue = numero.u < pSeguir;
    return `Bernoulli: u ${sigue ? "<" : "≥"} p = ${pSeguir} ⇒ ${sigue ? "la sigue" : "no la sigue"}`;
  }
  return "";
}

// Cálculo paso a paso: xᵢ → xᵢ² → relleno (centrales resaltados) → centrales → u.
function calculo(numero, pSeguir) {
  const c = numero.calculo;
  const d = c.digitos;
  const pasos = elemento("ol", undefined, "pasos-calculo");
  const relleno = elemento("span", undefined, "relleno");
  relleno.append(...celdaRelleno(c.relleno, d).childNodes);
  const filaRelleno = elemento("li", "Relleno a 2D dígitos: ");
  filaRelleno.append(relleno);
  pasos.append(
    elemento("li", `Semilla / estado previo: xᵢ = ${rellenarCeros(c.previo, d)}`),
    elemento("li", `Cuadrado: xᵢ² = ${c.cuadrado.toLocaleString("es")}`),
    filaRelleno,
    elemento("li", `Dígitos centrales: ${c.centrales}`),
    elemento("li", `u = ${c.centrales} / 10^${d} = ${numero.u.toFixed(d)}`),
  );
  const texto = interpretacion(numero, pSeguir);
  if (texto) pasos.append(elemento("li", texto, "resultado"));
  return pasos;
}

function ultimoNumero(h, pSeguir) {
  const bloque = elemento("div", undefined, "bloque");
  bloque.append(elemento("h4", "Último número pseudoaleatorio usado"));
  if (h.ultimo_numero_fuera_de_bufer) {
    bloque.append(elemento("p", `Número #${h.ultimo_indice_u} (u = ${h.ultimo_u.toFixed(4)}); su cálculo ya salió del búfer del registro.`, "ayuda"));
    return bloque;
  }
  const numero = h.ultimo_numero;
  if (!numero) {
    bloque.append(elemento("p", "Todavía no ha usado ningún número.", "ayuda"));
    return bloque;
  }
  bloque.append(
    elemento("p", `Número #${numero.indice} · flujo ${numero.flujo} · propósito ${numero.proposito} · ` +
      `método: ${numero.generador} · paso ${numero.tick}`),
    calculo(numero, pSeguir),
  );
  if (numero.calculo.degeneracion) {
    const deg = numero.calculo.degeneracion;
    bloque.append(elemento("p", `${describirDegeneracion(deg, numero.calculo.digitos)} ` +
      `Re-siembra #${deg.numero_resiembra}: semilla nueva ${rellenarCeros(deg.semilla_nueva, numero.calculo.digitos)}.`, "aviso"));
  }
  return bloque;
}

function eventos(h) {
  const bloque = elemento("div", undefined, "bloque");
  bloque.append(elemento("h4", "Eventos"));
  const ultimo = h.ultimo_evento === "NINGUNO" ? "ninguno todavía" : `${h.ultimo_evento} (paso ${h.tick_ultimo_evento})`;
  const siguiente = h.siguiente_evento;
  const pares = [
    ["Último evento", ultimo],
    ["Siguiente evento (predicción)", siguiente.descripcion],
  ];
  bloque.append(listaAtributos(pares));
  if (siguiente.aleatorio) {
    bloque.append(elemento("p", "Ese evento usará un número pseudoaleatorio o depende del azar: es una posibilidad, no una certeza.", "ayuda"));
  }
  bloque.append(elemento("p", "La predicción no consume números ni modifica la simulación.", "ayuda"));
  return bloque;
}

// acciones: { deseleccionar(), verEventos(id) }
export function mostrarHormiga(contenedor, h, pSeguir, acciones) {
  const encabezado = elemento("div", undefined, "encabezado-seleccion");
  encabezado.append(elemento("strong", `Hormiga #${h.id}`), elemento("span", ` paso ${h.tick}`, "ayuda"));
  const verEventos = elemento("button", "Ver sus eventos", "secundario");
  verEventos.type = "button";
  verEventos.addEventListener("click", () => acciones.verEventos(h.id));
  const quitar = elemento("button", "Deseleccionar", "secundario");
  quitar.type = "button";
  quitar.addEventListener("click", acciones.deseleccionar);
  encabezado.append(verEventos, quitar);

  contenedor.replaceChildren(encabezado, atributos(h), ultimoNumero(h, pSeguir), eventos(h));
}

export function vaciarPanel(contenedor) {
  contenedor.replaceChildren(elemento("p", "Ninguna hormiga seleccionada.", "ayuda"));
}
