// Presentación del cálculo de los números pseudoaleatorios, para cada método.
// El servidor calcula todo y envía el detalle de cada número (`calculo`, con su `metodo`);
// aquí sólo se decide cómo mostrarlo: en la tabla paso a paso, en el registro de la corrida
// y en el panel de la hormiga seleccionada. Se marca la degeneración y la re-siembra.

const DECIMALES_ANGULO = 3;
const DECIMALES_U = 6; // para métodos cuyo u no tiene un número fijo de dígitos

export function celda(texto, clase) {
  const td = document.createElement("td");
  td.textContent = texto;
  if (clase) td.className = clase;
  return td;
}

function nodo(etiqueta, texto, clase) {
  const elemento = document.createElement(etiqueta);
  if (texto !== undefined) elemento.textContent = texto;
  if (clase) elemento.className = clase;
  return elemento;
}

// Relleno con los dígitos centrales resaltados: "32" + "8902" (resaltado) + "25".
function partesRelleno(relleno, digitos) {
  const inicio = digitos / 2;
  return [relleno.slice(0, inicio), nodo("span", relleno.slice(inicio, inicio + digitos), "centrales"),
    relleno.slice(inicio + digitos)];
}

export function celdaRelleno(relleno, digitos) {
  const td = celda("", "relleno");
  td.append(...partesRelleno(relleno, digitos));
  return td;
}

export function rellenarCeros(valor, digitos) {
  return String(valor).padStart(digitos, "0");
}

const miles = (n) => Number(n).toLocaleString("es");

// --- Cada método: cómo se escribe un estado, u y el cálculo ------------------------------

const CUADRADOS_MEDIOS = {
  estado: (x, c) => rellenarCeros(x, c.digitos),
  u: (u, c) => u.toFixed(c.digitos),
  modulo: (c) => `10^${c.digitos}`,
  // Celda "Cálculo" del registro: xᵢ² y el relleno con los centrales resaltados.
  celdaCalculo(c) {
    const td = celda(`${miles(c.cuadrado)} → `, "relleno");
    td.append(...partesRelleno(c.relleno, c.digitos));
    return td;
  },
  pasos: (c, u) => [
    `Semilla / estado previo: xᵢ = ${rellenarCeros(c.previo, c.digitos)}`,
    `Cuadrado: xᵢ² = ${miles(c.cuadrado)}`,
    ["Relleno a 2D dígitos: "], // arreglo = paso con el relleno resaltado (ver listaCalculo)
    `Dígitos centrales: ${c.centrales}`,
    `u = ${c.centrales} / 10^${c.digitos} = ${u.toFixed(c.digitos)}`,
  ],
  columnas: ["xᵢ (semilla)", "xᵢ²", "Relleno a 2D dígitos", "Centrales"],
  celdas: (f) => [celda(rellenarCeros(f.previo, f.digitos)), celda(miles(f.cuadrado)),
    celdaRelleno(f.relleno, f.digitos), celda(f.centrales, "centrales")],
  explicacion: "Se eleva al cuadrado el número, se completa con ceros a la izquierda hasta 2D " +
    "dígitos y se toman los D dígitos del centro: ese es el nuevo número, y u = x / 10^D.",
};

function congruencial(conIncremento) {
  const formula = (c) => conIncremento ? `${miles(c.a)} · ${miles(c.previo)} + ${miles(c.c)}`
    : `${miles(c.a)} · ${miles(c.previo)}`;
  return {
    estado: (x) => String(x),
    u: (u) => String(Number(u.toFixed(10))),
    modulo: (c) => miles(c.m),
    celdaCalculo: (c) => celda(`${formula(c)} = ${miles(c.producto)}; mod ${miles(c.m)}`),
    pasos: (c, u) => [
      `Estado previo: xᵢ = ${miles(c.previo)}`,
      `${conIncremento ? "a · xᵢ + c" : "a · xᵢ"} = ${formula(c)} = ${miles(c.producto)}`,
      `xᵢ₊₁ = ${miles(c.producto)} mod ${miles(c.m)} = ${miles(c.x)}`,
      `u = xᵢ₊₁ / m = ${miles(c.x)} / ${miles(c.m)} = ${String(Number(u.toFixed(10)))}`,
    ],
    columnas: ["xᵢ", conIncremento ? "a · xᵢ + c" : "a · xᵢ", "xᵢ₊₁ = (…) mod m"],
    celdas: (f) => [celda(miles(f.previo)), celda(miles(f.producto)), celda(miles(f.x), "centrales")],
    explicacion: conIncremento
      ? "xᵢ₊₁ = (a · xᵢ + c) mod m y u = xᵢ₊₁ / m. Con buenos a, c y m (Hull-Dobell) el periodo es m; " +
        "al completarlo la sucesión se repetiría: se registra y se re-siembra."
      : "xᵢ₊₁ = (a · xᵢ) mod m y u = xᵢ₊₁ / m (congruencial sin incremento). Con m primo y a raíz " +
        "primitiva el periodo es m − 1.",
  };
}

const NUMPY = {
  estado: (x) => String(x),
  u: (u) => u.toFixed(DECIMALES_U),
  modulo: () => "2^32",
  celdaCalculo: (c) => celda(`${c.algoritmo}: número #${c.indice} (caja negra)`),
  pasos: (c, u) => [
    `Generador de referencia ${c.algoritmo} de NumPy, número #${c.indice} de su sucesión.`,
    "Su estado interno es de 128 bits: no se muestra el cálculo, sólo el resultado.",
    `u = ${u.toFixed(DECIMALES_U)}`,
  ],
  columnas: ["Número de la sucesión"],
  celdas: (f) => [celda(`#${f.indice}`)],
  explicacion: "Generador moderno de NumPy (PCG64, periodo 2^128), usado como referencia para " +
    "comparar los métodos clásicos. No degenera en la práctica.",
};

const METODOS = {
  cuadrados_medios: CUADRADOS_MEDIOS,
  congruencial_lineal: congruencial(true),
  congruencial_multiplicativo: congruencial(false),
  numpy: NUMPY,
};

const metodo = (calculo) => METODOS[calculo.metodo] ?? NUMPY;

export function formatearU(u, calculo) {
  return metodo(calculo).u(u, calculo);
}

export function explicacionMetodo(nombreMetodo) {
  return METODOS[nombreMetodo]?.explicacion ?? "";
}

// Lista <ol> con el cálculo paso a paso (panel de la hormiga seleccionada).
export function listaCalculo(calculo, u) {
  const lista = nodo("ol", undefined, "pasos-calculo");
  for (const paso of metodo(calculo).pasos(calculo, u)) {
    if (typeof paso === "string") {
      lista.append(nodo("li", paso));
    } else { // relleno de cuadrados medios con los centrales resaltados
      const li = nodo("li", paso[0]);
      const relleno = nodo("span", undefined, "relleno");
      relleno.append(...partesRelleno(calculo.relleno, calculo.digitos));
      li.append(relleno);
      lista.append(li);
    }
  }
  return lista;
}

// Celdas xᵢ · cálculo · xᵢ₊₁ · u del registro de la corrida.
export function celdasRegistro(calculo, u) {
  const m = metodo(calculo);
  if (m === NUMPY) {
    return [celda("—"), m.celdaCalculo(calculo), celda("—"), celda(m.u(u, calculo))];
  }
  const siguiente = calculo.metodo === "cuadrados_medios" ? calculo.centrales : m.estado(calculo.x, calculo);
  return [celda(m.estado(calculo.previo, calculo)), m.celdaCalculo(calculo),
    celda(siguiente, "centrales"), celda(m.u(u, calculo))];
}

export function describirDegeneracion(deg, calculo) {
  const estado = metodo(calculo).estado(deg.estado, calculo);
  if (deg.tipo === "CERO") {
    return `Degeneró: el generador cayó en ${estado} (desde ahí sólo produciría ceros).`;
  }
  if (calculo.metodo === "cuadrados_medios") {
    return `Degeneró: el estado ${estado} ya había aparecido; ciclo de longitud ${deg.longitud_ciclo}.`;
  }
  return `Completó su periodo: el estado volvió a ${estado} después de ${miles(deg.longitud_ciclo)} números; ` +
    "desde aquí la sucesión se repetiría.";
}

export function describirResiembra(deg, calculo, semillaOriginal, pasoResiembra = 7919) {
  const m = metodo(calculo);
  const semilla = semillaOriginal === undefined ? "semilla" : semillaOriginal;
  return `Re-siembra #${deg.numero_resiembra}: nueva semilla = (${semilla} + ${deg.numero_resiembra} · ` +
    `${pasoResiembra}) mod ${m.modulo(calculo)} = ${m.estado(deg.semilla_nueva, calculo)}`;
}

// --- Tabla paso a paso (vista previa) ----------------------------------------------------

function encabezado(tabla, columnas) {
  const tr = document.createElement("tr");
  for (const texto of ["i", ...columnas, "uᵢ", "Dirección = u·360°"]) tr.append(nodo("th", texto));
  tabla.tHead.replaceChildren(tr);
  return columnas.length + 3;
}

function filaNumero(fila) {
  const m = metodo(fila);
  const tr = document.createElement("tr");
  tr.append(celda(fila.indice), ...m.celdas(fila), celda(m.u(fila.u, fila)),
    celda(`${fila.angulo.toFixed(DECIMALES_ANGULO)}°`));
  if (fila.degeneracion) {
    tr.className = "degenerado";
    tr.title = describirDegeneracion(fila.degeneracion, fila);
  }
  return tr;
}

function filaResiembra(fila, datos, columnas) {
  const tr = document.createElement("tr");
  tr.className = "resiembra";
  const td = celda(`${describirDegeneracion(fila.degeneracion, fila)} ` +
    describirResiembra(fila.degeneracion, fila, datos.semilla, datos.paso_resiembra));
  td.colSpan = columnas;
  tr.append(td);
  return tr;
}

// Dibuja la respuesta de /api/aleatorio/vista-previa (encabezado y filas según el método).
export function mostrarTabla(tabla, datos) {
  const columnas = encabezado(tabla, METODOS[datos.metodo].columnas);
  const filas = document.createDocumentFragment();
  for (const fila of datos.filas) {
    filas.append(filaNumero(fila));
    if (fila.degeneracion) filas.append(filaResiembra(fila, datos, columnas));
  }
  tabla.tBodies[0].replaceChildren(filas);
}

export function resumen(datos) {
  const n = datos.filas.length;
  if (datos.resiembras === 0) {
    return `${n} números generados con ${datos.generador}; sin degeneración.`;
  }
  return `${n} números generados con ${datos.generador}; el generador degeneró y se re-sembró ` +
    `${datos.resiembras} ${datos.resiembras === 1 ? "vez" : "veces"}.`;
}
