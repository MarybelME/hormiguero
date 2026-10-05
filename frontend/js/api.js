// Cliente REST del simulador. Sólo envía peticiones y devuelve JSON: no calcula nada del modelo.

async function pedir(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });
  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    throw new Error(describirError(respuesta.status, datos));
  }
  return datos;
}

// Convierte los errores de validación de FastAPI (422) en un mensaje legible.
function describirError(estado, datos) {
  if (datos && Array.isArray(datos.detail)) {
    return datos.detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ");
  }
  if (datos && typeof datos.detail === "string") return datos.detail;
  return `Error ${estado} del servidor`;
}

export function obtenerSalud() {
  return pedir("/api/salud");
}

// Crea una simulación nueva con los parámetros dados (los demás toman su valor por defecto).
export function configurarSimulacion(parametros) {
  return pedir("/api/simulacion/configurar", {
    method: "POST",
    body: JSON.stringify(parametros),
  });
}

// solicitud: { generador, semilla, cantidad, digitos, congruencial_a, … }
export function vistaPreviaAleatorios(solicitud) {
  return pedir("/api/aleatorio/vista-previa", {
    method: "POST",
    body: JSON.stringify(solicitud),
  });
}

// solicitud: { generadores: [{ generador, semilla, … }], cantidad, intervalos, alfa }
export function probarGeneradores(solicitud) {
  return pedir("/api/aleatorio/pruebas", {
    method: "POST",
    body: JSON.stringify(solicitud),
  });
}

export function obtenerParametros() {
  return pedir("/api/parametros");
}

export function obtenerEstado() {
  return pedir("/api/simulacion/estado");
}

// Control de la simulación: iniciar, pausar, reiniciar, limpiar.
export function controlar(accion) {
  return pedir(`/api/simulacion/${accion}`, { method: "POST" });
}

export function fijarVelocidad(pasosPorSegundo) {
  return pedir("/api/simulacion/velocidad", {
    method: "PUT",
    body: JSON.stringify({ pasos_por_segundo: pasosPorSegundo }),
  });
}

function consulta(parametros) {
  const datos = new URLSearchParams();
  for (const [clave, valor] of Object.entries(parametros)) {
    if (valor !== "" && valor !== null && valor !== undefined) datos.set(clave, valor);
  }
  return datos.toString();
}

export function obtenerEventos(filtros) {
  return pedir(`/api/eventos?${consulta(filtros)}`);
}

export function obtenerRegistro(filtros) {
  return pedir(`/api/aleatorio/registro?${consulta(filtros)}`);
}

// Descarga un CSV generado por el servidor (GET o POST con cuerpo JSON) y lo guarda con el
// nombre que propone el servidor. Se usa fetch, y no un simple enlace, para mostrar errores.
export async function descargarCsv(ruta, cuerpo) {
  const opciones = cuerpo === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo),
  };
  const respuesta = await fetch(ruta, opciones);
  if (!respuesta.ok) {
    const datos = await respuesta.json().catch(() => null);
    throw new Error(describirError(respuesta.status, datos));
  }
  const disposicion = respuesta.headers.get("Content-Disposition") ?? "";
  const nombre = /filename="?([^"]+)"?/.exec(disposicion)?.[1] ?? "datos.csv";
  const url = URL.createObjectURL(await respuesta.blob());
  const enlace = Object.assign(document.createElement("a"), { href: url, download: nombre });
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return nombre;
}

// --- Lotes de réplicas ---------------------------------------------------------------------

export function iniciarLote(solicitud) {
  return pedir("/api/experimentos", { method: "POST", body: JSON.stringify(solicitud) });
}

export function obtenerLote() {
  return pedir("/api/experimentos");
}

export function cancelarLote() {
  return pedir("/api/experimentos/cancelar", { method: "POST" });
}
