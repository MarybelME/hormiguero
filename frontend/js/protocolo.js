// Lectura del cuadro binario que envía el servidor (DISENO.md §12.2, versión 1, little-endian).
// Sólo interpreta bytes: no calcula nada del modelo.
//
//   desplazamiento  tamaño  tipo        campo
//   0               1       uint8       version = 1
//   1               1       uint8       tipo_mensaje = 1 (CUADRO)
//   2               2       uint16      reservado
//   4               4       uint32      tick
//   8               4       uint32      n
//   12              4       float32     tiempo simulado (s)
//   16              4       float32     reina_x
//   20              4       float32     reina_y
//   24              4·n     float32[n]  x
//   24 + 4n         4·n     float32[n]  y
//   24 + 8n         n       uint8[n]    estado

export const VERSION_PROTOCOLO = 1;
export const TIPO_CUADRO = 1;
export const TIPO_FEROMONAS = 2;
export const TAMANO_ENCABEZADO = 24;
export const TAMANO_ENCABEZADO_FEROMONAS = 20;

// Códigos de EstadoHormiga: deben coincidir con backend/app/modelo/estados.py.
export const ESTADOS = [
  { codigo: 0, nombre: "EN_NIDO", texto: "En el nido" },
  { codigo: 1, nombre: "BUSCANDO_COMIDA", texto: "Buscando comida" },
  { codigo: 2, nombre: "SIGUIENDO_REINA", texto: "Siguiendo a la reina" },
  { codigo: 3, nombre: "EVITANDO_OBSTACULO", texto: "Evitando obstáculo" },
  { codigo: 4, nombre: "TRANSPORTANDO_COMIDA", texto: "Transportando comida" },
  { codigo: 5, nombre: "REGRESANDO_AL_NIDO", texto: "Regresando al nido (sin comida)" },
];

// Tipo de mensaje binario (byte 1): CUADRO o FEROMONAS.
export function tipoMensaje(buffer) {
  return new DataView(buffer).getUint8(1);
}

// Mensaje tipo 2 (DISENO.md §12.2): campo de feromonas cuantizado a 0–255.
//   0 uint8 version · 1 uint8 tipo = 2 · 2 uint16 columnas · 4 uint32 tick · 8 uint16 filas
//   10 uint16 reservado · 12 float32 tamano_celda · 16 float32 concentracion_maxima
//   20 uint8[filas·columnas] fila por fila; fila 0 = parte baja del mundo (y pequeña)
export function decodificarFeromonas(buffer) {
  const vista = new DataView(buffer);
  const columnas = vista.getUint16(2, true);
  const filas = vista.getUint16(8, true);
  if (buffer.byteLength !== TAMANO_ENCABEZADO_FEROMONAS + filas * columnas) {
    throw new Error(`El mensaje de feromonas mide ${buffer.byteLength} bytes`);
  }
  return {
    tick: vista.getUint32(4, true),
    columnas,
    filas,
    tamanoCelda: vista.getFloat32(12, true),
    maxima: vista.getFloat32(16, true),
    valores: new Uint8Array(buffer, TAMANO_ENCABEZADO_FEROMONAS, filas * columnas),
  };
}

export function decodificarCuadro(buffer) {
  const vista = new DataView(buffer);
  const version = vista.getUint8(0);
  const tipo = vista.getUint8(1);
  if (version !== VERSION_PROTOCOLO || tipo !== TIPO_CUADRO) {
    throw new Error(`Cuadro con versión ${version} y tipo ${tipo} no soportado`);
  }
  const n = vista.getUint32(8, true);
  if (buffer.byteLength !== TAMANO_ENCABEZADO + 9 * n) {
    throw new Error(`El cuadro mide ${buffer.byteLength} bytes; se esperaban ${TAMANO_ENCABEZADO + 9 * n}`);
  }
  return {
    tick: vista.getUint32(4, true),
    n,
    tiempo: vista.getFloat32(12, true),
    reinaX: vista.getFloat32(16, true),
    reinaY: vista.getFloat32(20, true),
    // Vistas sobre el mismo buffer, sin copiar (el encabezado mide 24 bytes, múltiplo de 4).
    x: new Float32Array(buffer, TAMANO_ENCABEZADO, n),
    y: new Float32Array(buffer, TAMANO_ENCABEZADO + 4 * n, n),
    estado: new Uint8Array(buffer, TAMANO_ENCABEZADO + 8 * n, n),
  };
}
