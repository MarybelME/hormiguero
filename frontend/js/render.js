// Dibujo del mundo en el canvas. Sólo dibuja lo que envía el servidor: no calcula nada del modelo.
// El mundo usa y hacia arriba (0° = este, antihorario); el canvas usa y hacia abajo, así que
// se invierte el eje Y al dibujar.

function colores() {
  const estilo = getComputedStyle(document.documentElement);
  const leer = (nombre) => estilo.getPropertyValue(nombre).trim();
  return {
    nido: leer("--mundo-nido"),
    reina: leer("--mundo-reina"),
    patrulla: leer("--mundo-patrulla"),
    roca: leer("--mundo-roca"),
    fuente: leer("--mundo-fuente"),
    texto: leer("--mundo-texto"),
  };
}

function circulo(ctx, x, y, radio) {
  ctx.beginPath();
  ctx.arc(x, y, radio, 0, 2 * Math.PI);
}

// Capa estática: zona de patrulla, nido, reina, rocas y fuentes (con su cantidad).
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

  ctx.strokeStyle = c.reina;
  ctx.lineWidth = 1;
  circulo(ctx, reina.x, yCanvas(reina.y), reina.radio_influencia);
  ctx.stroke();
  ctx.fillStyle = c.reina;
  circulo(ctx, reina.x, yCanvas(reina.y), 6);
  ctx.fill();
}
