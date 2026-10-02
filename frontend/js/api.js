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
  return `Error ${estado} del servidor`;
}

export function obtenerSalud() {
  return pedir("/api/salud");
}

export function vistaPreviaAleatorios({ semilla, digitos, cantidad }) {
  return pedir("/api/aleatorio/vista-previa", {
    method: "POST",
    body: JSON.stringify({ generador: "cuadrados_medios", semilla, digitos, cantidad }),
  });
}
