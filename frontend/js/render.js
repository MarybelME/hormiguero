// Dibujo del mundo en el canvas. Sólo dibuja lo que envía el servidor: no calcula nada del modelo.
// El mundo usa y hacia arriba (0° = este, antihorario); el canvas usa y hacia abajo, así que
// se invierte el eje Y al dibujar.

import { ESTADOS } from "./protocolo.js";

const CODIGO_EN_NIDO = 0;
const TAMANO_HORMIGA = 2;          // unidades del mundo (≈ píxeles a tamaño completo)
const MEDIO_TAMANO_HORMIGA = TAMANO_HORMIGA / 2;
const RADIO_REINA = 6;
const RADIO_SELECCION = 8;
const LARGO_FLECHA = 16;

function leerColores() {
  const estilo = getComputedStyle(document.documentElement);
  const leer = (nombre) => estilo.getPropertyValue(nombre).trim();
  return {
    nido: leer("--mundo-nido"),
    reina: leer("--mundo-reina"),
    patrulla: leer("--mundo-patrulla"),
    roca: leer("--mundo-roca"),
    fuente: leer("--mundo-fuente"),
    texto: leer("--mundo-texto"),
    seleccion: leer("--mundo-seleccion"),
    estados: ESTADOS.map((e) => leer(`--estado-${e.codigo}`)),
  };
}

// Los colores se leen una vez (no en cada cuadro) y se vuelven a leer si cambia el tema.
let coloresGuardados = null;
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => { coloresGuardados = null; });

function colores() {
  coloresGuardados ??= leerColores();
  return coloresGuardados;
}

function circulo(ctx, x, y, radio) {
  ctx.beginPath();
  ctx.arc(x, y, radio, 0, 2 * Math.PI);
}

// Capa estática: zona de patrulla, nido, rocas y fuentes (con su cantidad). La reina se mueve:
// va en la capa dinámica.
export function dibujarCapaEstatica(canvas, mundo) {
  canvas.width = mundo.ancho;
  canvas.height = mundo.alto;
  const ctx = canvas.getContext("2d");
  const c = colores();
  const yCanvas = (y) => mundo.alto - y;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const { nido, reina } = mundo;
  ctx.setLineDash([8, 6]);
  ctx.strokeStyle = c.patrulla;
  ctx.lineWidth = 1.5;
  circulo(ctx, nido.x, yCanvas(nido.y), reina.radio_patrulla);
  ctx.stroke();
  ctx.setLineDash([]);

  for (const roca of mundo.obstaculos) {
    ctx.fillStyle = c.roca;
    circulo(ctx, roca.x, yCanvas(roca.y), roca.radio);
    ctx.fill();
  }

  ctx.font = "bold 13px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  for (const fuente of mundo.fuentes) {
    const proporcion = fuente.cantidad / fuente.cantidad_inicial;
    ctx.globalAlpha = 0.25 + 0.75 * proporcion; // una fuente agotada se ve atenuada
    ctx.fillStyle = c.fuente;
    circulo(ctx, fuente.x, yCanvas(fuente.y), fuente.radio);
    ctx.fill();
    ctx.globalAlpha = 1;
    ctx.fillStyle = c.texto;
    ctx.fillText(String(fuente.cantidad), fuente.x, yCanvas(fuente.y) - fuente.radio - 9);
  }

  ctx.fillStyle = c.nido;
  circulo(ctx, nido.x, yCanvas(nido.y), nido.radio);
  ctx.fill();
}

export function limpiarCanvas(canvas) {
  canvas.getContext("2d").clearRect(0, 0, canvas.width, canvas.height);
}

// Capa dinámica (cada cuadro): hormigas agrupadas por estado (un fillStyle por grupo y
// cuadros de 2×2), la reina en su posición actual y la hormiga seleccionada.
export function dibujarCapaDinamica(canvas, mundo, cuadro, seleccion) {
  const ctx = canvas.getContext("2d");
  const c = colores();
  const alto = mundo.alto;
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const { x, y, estado, n } = cuadro;
  for (let codigo = 0; codigo < c.estados.length; codigo++) {
    if (codigo === CODIGO_EN_NIDO) continue; // dentro del nido no se dibujan: están todas en el centro
    ctx.fillStyle = c.estados[codigo];
    for (let i = 0; i < n; i++) {
      if (estado[i] === codigo) {
        ctx.fillRect(x[i] - MEDIO_TAMANO_HORMIGA, alto - y[i] - MEDIO_TAMANO_HORMIGA, TAMANO_HORMIGA, TAMANO_HORMIGA);
      }
    }
  }

  const { reina } = mundo;
  ctx.strokeStyle = c.reina;
  ctx.lineWidth = 1;
  circulo(ctx, cuadro.reinaX, alto - cuadro.reinaY, reina.radio_influencia);
  ctx.stroke();
  ctx.fillStyle = c.reina;
  circulo(ctx, cuadro.reinaX, alto - cuadro.reinaY, RADIO_REINA);
  ctx.fill();

  if (seleccion !== null && seleccion.id < n) {
    dibujarSeleccion(ctx, c, x[seleccion.id], alto - y[seleccion.id], seleccion.dir);
  }
}

// Anillo alrededor de la hormiga seleccionada y una flecha con su dirección.
function dibujarSeleccion(ctx, c, xs, ys, direccion) {
  ctx.strokeStyle = c.seleccion;
  ctx.lineWidth = 2;
  circulo(ctx, xs, ys, RADIO_SELECCION);
  ctx.stroke();
  if (direccion === null || direccion === undefined) return;
  const radianes = (direccion * Math.PI) / 180;
  ctx.beginPath();
  ctx.moveTo(xs, ys);
  ctx.lineTo(xs + LARGO_FLECHA * Math.cos(radianes), ys - LARGO_FLECHA * Math.sin(radianes));
  ctx.stroke();
}

// Convierte un clic en el canvas (píxeles de pantalla) a coordenadas del mundo.
export function coordenadasMundo(canvas, mundo, evento) {
  const caja = canvas.getBoundingClientRect();
  const x = ((evento.clientX - caja.left) / caja.width) * mundo.ancho;
  const yCanvas = ((evento.clientY - caja.top) / caja.height) * mundo.alto;
  return { x, y: mundo.alto - yCanvas };
}

// Interpreta el clic: la hormiga visible más cercana del último cuadro (no es lógica del modelo).
export function hormigaMasCercana(cuadro, punto, distanciaMaxima) {
  let mejor = -1;
  let mejorDistancia = distanciaMaxima * distanciaMaxima;
  for (let i = 0; i < cuadro.n; i++) {
    if (cuadro.estado[i] === CODIGO_EN_NIDO) continue;
    const dx = cuadro.x[i] - punto.x;
    const dy = cuadro.y[i] - punto.y;
    const d = dx * dx + dy * dy;
    if (d < mejorDistancia) {
      mejorDistancia = d;
      mejor = i;
    }
  }
  return mejor;
}
