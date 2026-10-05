// Controles de la simulación: botones, velocidad y panel de parámetros.
// El formulario se construye con el esquema que envía el servidor (descripción, unidad y
// rango de cada parámetro); el navegador valida los rangos, pero el servidor vuelve a validar.

import { fijarVelocidad } from "./api.js";

// Parámetros que se muestran sin desplegar "Avanzados".
const PRINCIPALES = new Set([
  "num_hormigas", "semilla", "generador", "digitos", "num_obstaculos", "num_fuentes",
  "alimento_por_fuente", "radio_reina", "p_seguir_reina", "feromonas_activas",
]);
// La velocidad no es un parámetro de la corrida: se controla en vivo desde la barra.
const CAMPO_VELOCIDAD = "pasos_por_segundo";
// Lo que define al generador (sin la semilla): lo reusan la tabla paso a paso y el laboratorio.
const CONSTANTES_GENERADOR = [
  "digitos", "congruencial_a", "congruencial_c", "congruencial_m", "multiplicativo_a", "multiplicativo_m",
];

// Qué botones tienen sentido en cada estado del controlador.
const BOTONES_ACTIVOS = {
  vacio: ["iniciar"],
  listo: ["iniciar", "reiniciar", "limpiar"],
  corriendo: ["pausar", "reiniciar", "limpiar"],
  pausado: ["iniciar", "reiniciar", "limpiar"],
};
const TEXTO_ESTADO = {
  vacio: "Sin mundo",
  listo: "Listo (t = 0)",
  corriendo: "Corriendo",
  pausado: "En pausa",
};

const botones = {
  iniciar: document.getElementById("boton-iniciar"),
  pausar: document.getElementById("boton-pausar"),
  reiniciar: document.getElementById("boton-reiniciar"),
  limpiar: document.getElementById("boton-limpiar"),
};
const rangoVelocidad = document.getElementById("rango-velocidad");
const campoVelocidad = document.getElementById("campo-velocidad");
const estadoControlador = document.getElementById("estado-controlador");

// --- Formulario de parámetros ----------------------------------------------------------

function crearCampo(nombre, propiedad, etiquetas) {
  const etiqueta = document.createElement("label");
  etiqueta.title = `${nombre}: ${propiedad.description}`;
  const texto = document.createElement("span");
  texto.textContent = propiedad.description;
  const codigo = document.createElement("code");
  codigo.textContent = nombre;

  let entrada;
  if (propiedad.type === "boolean") {
    entrada = document.createElement("select");
    entrada.append(new Option("no", "false"), new Option("sí", "true"));
  } else if (propiedad.enum || propiedad.const !== undefined) {
    entrada = document.createElement("select");
    for (const opcion of propiedad.enum ?? [propiedad.const]) {
      entrada.append(new Option(etiquetas[opcion] ?? String(opcion), String(opcion)));
    }
  } else {
    entrada = document.createElement("input");
    entrada.type = "number";
    entrada.required = true;
    entrada.min = propiedad.minimum;
    entrada.max = propiedad.maximum;
    entrada.step = propiedad.type === "integer" ? "1" : "any";
  }
  entrada.name = nombre;
  entrada.dataset.tipo = propiedad.type;
  if (propiedad.solo_generador) entrada.dataset.soloGenerador = propiedad.solo_generador;

  const rango = document.createElement("small");
  const unidad = propiedad.unidad ? ` ${propiedad.unidad}` : "";
  rango.textContent = propiedad.minimum !== undefined
    ? `${propiedad.minimum} – ${propiedad.maximum}${unidad}`
    : unidad.trim();

  etiqueta.append(texto, codigo, entrada, rango);
  return etiqueta;
}

// etiquetas: nombres legibles de las opciones (p. ej. de cada generador).
export function construirFormulario(formulario, esquema, valores, etiquetas = {}) {
  const principales = formulario.querySelector("#parametros-principales");
  const avanzados = formulario.querySelector("#parametros-avanzados");
  for (const [nombre, propiedad] of Object.entries(esquema.properties)) {
    if (nombre === CAMPO_VELOCIDAD) continue;
    (PRINCIPALES.has(nombre) ? principales : avanzados).append(crearCampo(nombre, propiedad, etiquetas));
  }
  formulario.elements.generador.addEventListener("change", () => marcarCamposDelGenerador(formulario));
  fijarValores(formulario, valores);
}

// Las constantes de un generador sólo se pueden editar cuando ese generador está elegido.
function marcarCamposDelGenerador(formulario) {
  const generador = formulario.elements.generador.value;
  for (const entrada of formulario.querySelectorAll("[data-solo-generador]")) {
    const activo = entrada.dataset.soloGenerador === generador;
    entrada.disabled = !activo;
    entrada.closest("label").classList.toggle("inactivo", !activo);
  }
}

export function fijarValores(formulario, valores) {
  for (const [nombre, valor] of Object.entries(valores)) {
    const entrada = formulario.elements.namedItem(nombre);
    if (entrada) entrada.value = String(valor);
  }
  if (formulario.elements.generador) marcarCamposDelGenerador(formulario);
}

// Constantes del generador tal como están en el formulario (aunque no estén aplicadas).
export function leerConstantesGenerador(formulario) {
  return Object.fromEntries(
    CONSTANTES_GENERADOR.map((nombre) => [nombre, Number(formulario.elements[nombre].value)]));
}

// Lee el formulario; devuelve null (y marca el campo) si algún valor está fuera de rango.
export function leerParametros(formulario) {
  if (!formulario.reportValidity()) return null;
  const parametros = {};
  for (const entrada of formulario.querySelectorAll("input, select")) {
    const tipo = entrada.dataset.tipo;
    if (tipo === "boolean") parametros[entrada.name] = entrada.value === "true";
    else parametros[entrada.name] = tipo === "integer" || tipo === "number" ? Number(entrada.value) : entrada.value;
  }
  parametros[CAMPO_VELOCIDAD] = Number(campoVelocidad.value);
  return parametros;
}

// --- Botones y velocidad ---------------------------------------------------------------

export function mostrarEstadoControlador(estado, pasosPorSegundo) {
  const activos = BOTONES_ACTIVOS[estado] ?? [];
  for (const [nombre, boton] of Object.entries(botones)) {
    boton.disabled = !activos.includes(nombre);
  }
  estadoControlador.textContent = TEXTO_ESTADO[estado] ?? estado;
  estadoControlador.dataset.estado = estado;
  if (document.activeElement !== campoVelocidad && document.activeElement !== rangoVelocidad) {
    fijarVelocidadVisible(pasosPorSegundo);
  }
}

// Sólo cambia lo que se ve; la velocidad se envía con la corrida o al mover el control.
export function fijarVelocidadVisible(pasosPorSegundo) {
  rangoVelocidad.value = campoVelocidad.value = pasosPorSegundo;
}

// alAccion(accion) se llama al pulsar un botón; debe devolver una promesa.
export function prepararBotones(alAccion, alError) {
  for (const [accion, boton] of Object.entries(botones)) {
    boton.addEventListener("click", () => alAccion(accion).catch(alError));
  }
}

export function prepararVelocidad(alError) {
  let espera = null;
  const enviar = (valor) => {
    clearTimeout(espera); // no se envía una petición por cada píxel que se arrastra
    espera = setTimeout(() => fijarVelocidad(valor).catch(alError), 150);
  };
  rangoVelocidad.addEventListener("input", () => {
    campoVelocidad.value = rangoVelocidad.value;
    enviar(Number(rangoVelocidad.value));
  });
  campoVelocidad.addEventListener("change", () => {
    if (!campoVelocidad.reportValidity()) return;
    rangoVelocidad.value = campoVelocidad.value;
    enviar(Number(campoVelocidad.value));
  });
}
