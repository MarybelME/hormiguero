// Vista de tabla paso a paso del generador de cuadrados medios.
// Muestra semilla → cuadrado → relleno → dígitos centrales → u, y marca la degeneración
// y la re-siembra que calculó el servidor (aquí no se calcula ningún número).

const DECIMALES_ANGULO = 3;

export function celda(texto, clase) {
  const td = document.createElement("td");
  td.textContent = texto;
  if (clase) td.className = clase;
  return td;
}

// Relleno con los dígitos centrales resaltados: "32" + "8902" (resaltado) + "25".
export function celdaRelleno(relleno, digitos) {
  const td = celda("", "relleno");
  const inicio = digitos / 2;
  const centrales = document.createElement("span");
  centrales.className = "centrales";
  centrales.textContent = relleno.slice(inicio, inicio + digitos);
  td.append(relleno.slice(0, inicio), centrales, relleno.slice(inicio + digitos));
  return td;
}

export function rellenarCeros(valor, digitos) {
  return String(valor).padStart(digitos, "0");
}

export function describirDegeneracion(deg, digitos) {
  const estado = rellenarCeros(deg.estado, digitos);
  if (deg.tipo === "CERO") {
    return `Degeneró: el generador cayó en ${estado} (desde ahí sólo produciría ceros).`;
  }
  return `Degeneró: el estado ${estado} ya había aparecido; ciclo de longitud ${deg.longitud_ciclo}.`;
}

function describirResiembra(deg, datos) {
  const modulo = `10^${datos.digitos}`;
  return (
    `Re-siembra #${deg.numero_resiembra}: nueva semilla = ` +
    `(${datos.semilla} + ${deg.numero_resiembra} · ${datos.paso_resiembra}) mod ${modulo} = ` +
    `${rellenarCeros(deg.semilla_nueva, datos.digitos)}`
  );
}

function filaNumero(fila, digitos) {
  const tr = document.createElement("tr");
  tr.append(
    celda(fila.indice),
    celda(rellenarCeros(fila.previo, digitos)),
    celda(fila.cuadrado.toLocaleString("es")),
    celdaRelleno(fila.relleno, digitos),
    celda(fila.centrales, "centrales"),
    celda(fila.u.toFixed(digitos)),
    celda(`${fila.angulo.toFixed(DECIMALES_ANGULO)}°`),
  );
  if (fila.degeneracion) {
    tr.className = "degenerado";
    tr.title = describirDegeneracion(fila.degeneracion, digitos);
  }
  return tr;
}

function filaResiembra(fila, datos) {
  const tr = document.createElement("tr");
  tr.className = "resiembra";
  const td = celda(
    `${describirDegeneracion(fila.degeneracion, datos.digitos)} ${describirResiembra(fila.degeneracion, datos)}`,
  );
  td.colSpan = 7;
  tr.append(td);
  return tr;
}

// Dibuja la respuesta de /api/aleatorio/vista-previa en el <tbody> de la tabla.
export function mostrarTabla(tabla, datos) {
  const filas = document.createDocumentFragment();
  for (const fila of datos.filas) {
    filas.append(filaNumero(fila, datos.digitos));
    if (fila.degeneracion) filas.append(filaResiembra(fila, datos));
  }
  tabla.tBodies[0].replaceChildren(filas);
}

export function resumen(datos) {
  const n = datos.filas.length;
  if (datos.resiembras === 0) {
    return `${n} números generados con ${datos.generador}; sin degeneración.`;
  }
  return `${n} números generados con ${datos.generador}; el generador degeneró y se re-sembró ${datos.resiembras} ${datos.resiembras === 1 ? "vez" : "veces"}.`;
}
