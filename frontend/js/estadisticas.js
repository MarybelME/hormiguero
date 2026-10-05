// Estadísticas en vivo (RF-40): variables de estado del sistema y contadores de eventos.
// Las filas se crean una sola vez; en cada mensaje sólo se cambia su texto.

const FORMATO = new Intl.NumberFormat("es-MX");

// [clave, etiqueta, cómo obtener el valor a partir del mensaje]
const FILAS = [
  ["tiempo", "Tiempo de simulación", (d) => `${d.tiempo.toFixed(1)} s (paso ${FORMATO.format(d.tick)})`],
  ["velocidad", "Velocidad (pedida / real)", (d) => `${d.pasos_por_segundo_pedidos} / ${d.pasos_por_segundo_reales} pasos/s`],
  ["total", "Total de hormigas", (d) => FORMATO.format(d.total_hormigas)],
  ["en_nido", "En el nido", (d) => FORMATO.format(d.conteo_estados.EN_NIDO)],
  ["buscando", "Buscando comida", (d) => FORMATO.format(d.conteo_estados.BUSCANDO_COMIDA)],
  ["con_comida", "Regresando con comida", (d) => FORMATO.format(d.conteo_estados.TRANSPORTANDO_COMIDA)],
  ["sin_comida", "Regresando sin comida", (d) => FORMATO.format(d.conteo_estados.REGRESANDO_AL_NIDO)],
  ["siguiendo", "Siguiendo a la reina", (d) => FORMATO.format(d.conteo_estados.SIGUIENDO_REINA)],
  ["evitando", "Evitando obstáculo", (d) => FORMATO.format(d.conteo_estados.EVITANDO_OBSTACULO)],
  ["recolectado", "Alimento recolectado", (d) => FORMATO.format(d.alimento_recolectado)],
  ["fuentes", "Alimento en cada fuente", (d) => d.alimento_por_fuente.map((c) => FORMATO.format(c)).join(" · ")],
  ["colisiones", "Colisiones (rocas / borde)", (d) => `${FORMATO.format(d.colisiones)} / ${FORMATO.format(d.colisiones_borde)}`],
  ["cambios", "Cambios de dirección", (d) => FORMATO.format(d.cambios_direccion)],
  ["seguir", "Decisión de seguir a la reina", describirDecisiones],
  ["numeros", "Números pseudoaleatorios generados", (d) => FORMATO.format(d.numeros_generados)],
  ["resiembras", "Re-siembras (mundo / comportamiento)", (d) => `${d.resiembras.MUNDO} / ${d.resiembras.COMPORTAMIENTO}`],
];

// Frecuencia observada frente a la probabilidad del parámetro: p̂ debería acercarse a p.
function describirDecisiones(d) {
  if (d.decisiones_seguir === 0) return `sin decisiones aún (p = ${d.p_seguir_reina})`;
  const frecuencia = d.seguimientos / d.decisiones_seguir;
  return `${d.seguimientos} de ${d.decisiones_seguir} (p̂ = ${frecuencia.toFixed(3)}, p = ${d.p_seguir_reina})`;
}

const valores = new Map();

export function prepararEstadisticas(contenedor) {
  for (const [clave, etiqueta] of FILAS) {
    const dt = document.createElement("dt");
    dt.textContent = etiqueta;
    const dd = document.createElement("dd");
    dd.textContent = "—";
    contenedor.append(dt, dd);
    valores.set(clave, dd);
  }
}

export function mostrarEstadisticas(datos) {
  for (const [clave, , obtener] of FILAS) {
    valores.get(clave).textContent = obtener(datos);
  }
}

export function vaciarEstadisticas() {
  for (const dd of valores.values()) dd.textContent = "—";
}
