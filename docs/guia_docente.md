# Guía docente — Simulador educativo de hormiguero

Esta guía es para el docente de **Simulación** que quiera usar el simulador en clase. Propone
un recorrido de cinco sesiones, cada una ligada a conceptos del programa de la materia, con
demostraciones de pocos minutos y ejercicios para los estudiantes. Todos los valores numéricos
que se citan son reproducibles: con la misma semilla y los mismos parámetros, el simulador da
exactamente lo mismo en cualquier computadora.

---

## 1. Antes de la clase

1. Instalar y arrancar (detalle en [PROGRESS.md](../PROGRESS.md)):
   ```powershell
   .venv\Scripts\activate
   uvicorn app.main:app --app-dir backend
   ```
   y abrir <http://127.0.0.1:8000>. Si la página se ve rara tras actualizar, Ctrl+F5.
2. **Una simulación compartida**: todas las pestañas (y todos los estudiantes conectados al mismo
   servidor) ven y controlan la misma corrida. En el proyector conviene que sólo el docente la
   controle; cada pestaña sí tiene su propia hormiga seleccionada.
3. El botón **★ Simulación demo** prepara en un clic una corrida que muestra casi todo:
   3 000 hormigas, fuentes pequeñas que se agotan, la reina con p = 0.5 y feromonas.

## 2. La pantalla y los conceptos que muestra

| Lo que se ve | Concepto de simulación |
|---|---|
| El rectángulo del mundo y su borde | Sistema y su frontera |
| Hormigas (puntos de color) | Entidades temporales y móviles; el color es su **estado** |
| Reina (círculo morado) y su radio | Entidad permanente; zona donde se decide una Bernoulli |
| Nido | Parte del sistema / punto de servicio (recibe depósitos, recupera energía) |
| Fuentes verdes con su cantidad | Recursos consumibles y finitos |
| Rocas grises | Restricciones |
| Rastro rosa | Campo del entorno (feromonas): variable de estado repartida en el espacio |
| Estadísticas en vivo | Variables de estado del sistema y contadores de eventos |
| Panel "Hormiga seleccionada" | Atributos de una entidad, el número pseudoaleatorio que usó y el próximo evento |
| Bitácora de eventos | Registro de eventos con tiempo, entidad y número usado |
| Registro de números | Trazabilidad: semilla → cálculo → u → para qué se usó |
| Parámetros (con rango y unidad) | Entradas del modelo |
| Tabla paso a paso y laboratorio | Generación y validación de números pseudoaleatorios |
| Experimentos | Réplicas, variables de salida e intervalos de confianza |

Una frase útil para toda la materia, que el simulador hace visible: **lo continuo cambia en
cada paso (posición, energía); lo discreto cambia por eventos (estado, carga, dirección)**.

Aclaración de modelado para los estudiantes: es un modelo de **tiempo discreto** (paso fijo
`dt = 0.1 s`) con **bitácora de eventos**; los eventos se detectan dentro de cada paso. No es un
simulador de eventos discretos puro. El "siguiente evento" del panel es una **predicción** que
no consume números ni altera nada.

---

## 3. Recorrido sugerido

### Sesión 1 — Números pseudoaleatorios y su generación (≈ 50 min)

**Conceptos**: generador pseudoaleatorio, semilla, periodo, degeneración, cuadrados medios,
congruencial lineal y multiplicativo.

1. **Cuadrados medios a mano** (sección "Tabla paso a paso", método Cuadrados medios,
   semilla 5735, D = 4). Que los estudiantes calculen los dos primeros números en el cuaderno y
   los comparen: 5735² = 32 890 225 → relleno `32890225` → centrales `8902` → u = 0.8902; luego
   8902² = 79 245 604 → `2456` → u = 0.2456. Siguen 0.0319, 0.1017, 0.0342, 0.1169.
2. **Degeneración**: semilla 1 (cae en 0), 2500 (2500² = 6 250 000 → `06250000` → `2500`: ciclo de
   longitud 1), 6100 (ciclo de longitud 4). La fila roja y la fila azul muestran la
   **re-siembra visible**: `nueva = (semilla + k · 7919) mod 10^D`. Mensaje clave: la
   degeneración no se oculta; se detecta, se registra y se corrige con una regla que cualquiera
   puede repetir.
3. **Congruencial lineal**: en Parámetros → Avanzados poner `a = 5`, `c = 3`, `m = 16` y en la
   tabla elegir "Congruencial lineal", semilla 7. Se recorren los 16 estados y en el número 16
   vuelve a la semilla: **periodo completo** (cumple Hull-Dobell: c impar, a − 1 múltiplo de 4,
   m potencia de 2). Cambiar a `c = 2` (semilla 1): el periodo cae a 8.
4. **Multiplicativo**: `a = 3`, `m = 7`, semilla 1 → 3, 2, 6, 4, 5, 1: periodo m − 1 = 6 porque 3 es
   raíz primitiva de 7. Con `a = 3`, `m = 11` el periodo es 5; con `a = 2`, `m = 11`, 10.
5. Volver a los valores clásicos (botón "Valores por defecto" del panel de parámetros):
   ANSI C (`a = 1103515245`, `c = 12345`, `m = 2^31`) y Park-Miller (`a = 16807`, `m = 2^31 − 1`).

### Sesión 2 — Validar un generador: pruebas estadísticas (≈ 50 min)

**Conceptos**: prueba de hipótesis, uniformidad (χ², Kolmogórov-Smirnov), independencia
(corridas arriba y abajo), nivel de significancia, valor p.

1. Laboratorio con los cuatro generadores, semilla 5735, n = 1000, k = 10, α = 0.05
   (con las constantes por defecto). Resultado reproducible:
   - **Cuadrados medios (D = 4)**: 25 re-siembras, sólo 424 números distintos de 1000, y
     **rechaza las tres pruebas**. El histograma lo muestra a simple vista.
   - Los dos congruenciales clásicos y NumPy: no se rechaza ninguna.
2. Repetir cuadrados medios con D = 6 (pasa χ² y K-S, **falla corridas**: los números tienen
   la distribución correcta pero no son independientes) y con D = 8 (pasa las tres).
   Excelente para distinguir **uniformidad** de **independencia**.
3. Congruencial `a = 5`, `c = 3`, `m = 16`, semilla 7: periodo completo y aun así rechaza las tres.
   Con m = 16 sólo existen 16 valores posibles: el periodo completo no basta si m es chico.
4. **Pasar las pruebas no prueba que el generador sea bueno**: el multiplicativo RANDU
   (`a = 65539`, `m = 2^31`, semilla 1, n = 5000) pasa las tres pruebas, y sin embargo es famoso
   porque sus ternas consecutivas caen en sólo 15 planos del cubo unitario. Las pruebas pueden
   rechazar un generador, nunca certificarlo.
5. "Descargar informe (CSV)" deja la comparación lista para una hoja de cálculo.

### Sesión 3 — El sistema: entidades, atributos, eventos y variables aleatorias (≈ 50 min)

**Conceptos**: sistema, entidad, atributo, variable de estado, evento, variable aleatoria
(uniforme continua y Bernoulli), reloj de simulación.

1. **★ Simulación demo**. Señalar los estados por color y el conteo por estado en las
   estadísticas (suman siempre el total de hormigas).
2. **Pausar** y hacer clic en una hormiga. El panel muestra sus atributos y **el último número
   que usó** con su cálculo completo. Si fue una dirección: `dirección = u · 360°`; si fue la
   decisión de seguir a la reina: `Bernoulli: u < p`.
3. "Ver sus eventos": la bitácora filtrada por esa hormiga. Cada cambio de dirección trae el
   índice del número que lo produjo; buscarlo en el registro ("Desde el índice") cierra el
   ciclo **semilla → cálculo → u → decisión → evento**.
4. **Variable aleatoria Bernoulli**: la fila "Decisión de seguir a la reina" compara la
   frecuencia observada p̂ con p. En la demo (p = 0.5) p̂ ronda 0.54. Preguntar: ¿por qué no da
   exactamente 0.5? (muestra finita y, con D = 4, un generador degradado).
5. **Reloj de simulación frente a reloj real**: subir la velocidad a 300 pasos/s. El tiempo
   simulado avanza 10 veces más rápido, pero el resultado tras N pasos es el mismo.

### Sesión 4 — Reproducibilidad y experimentación (≈ 50 min)

**Conceptos**: semilla, reproducibilidad, réplicas independientes, variable de salida,
media muestral, intervalo de confianza, números aleatorios comunes.

1. **Reproducibilidad**: correr la demo, pausar, anotar paso y alimento recolectado.
   **Reiniciar** e iniciar de nuevo hasta el mismo paso: todo coincide. Además, "Descargar
   registro completo" re-ejecuta la corrida desde t = 0 en otro objeto y obtiene los mismos
   números que se vieron en vivo.
2. **Una corrida no basta**: en "Experimentos", 10 réplicas de 1 000 pasos. La tabla da media,
   desviación e IC del 95 % (`media ± t · s/√n`) de cada variable de salida. Discutir el ancho
   del intervalo y qué pasa con 20 o 30 réplicas.
3. **Comparar escenarios**: repetir el lote con `p_seguir_reina = 0.1` y luego `0.9`, o con
   feromonas sí/no. ¿Se traslapan los intervalos? ¿Qué se puede concluir?
4. Dos flujos de números (MUNDO y COMPORTAMIENTO): cambiar el número de hormigas **no** cambia
   las rocas ni las fuentes. Es la base de la técnica de **números aleatorios comunes**. Nota:
   en un lote cada réplica cambia la semilla y, con ella, también el mundo.
5. Para lotes grandes, la terminal:
   ```powershell
   python backend/scripts/experimento_lote.py --replicas 30 --pasos 3000 --csv lote.csv
   python backend/scripts/experimento_lote.py --replicas 20 --parametro feromonas_activas=true
   ```

### Sesión 5 — Comportamiento emergente: feromonas (≈ 30 min)

**Conceptos**: campo del entorno (variable de estado espacial), proceso de decaimiento,
regla local y comportamiento emergente.

1. Activar "Feromonas" (o usar la demo) y correr. Las hormigas con comida dejan rastro y las
   que buscan lo siguen con tres sensores (izquierda, frente, derecha). Nadie "planea" la ruta:
   **emerge** de reglas locales.
2. Seleccionar una hormiga que busca: el panel muestra sus tres lecturas, el umbral y qué decide.
   La regla es **determinista**: no consume números pseudoaleatorios.
3. **Evaporación**: cada paso `c ← c · (1 − ρ)`. Sin depósitos, tras k pasos queda `c₀ (1 − ρ)^k`.
   Con ρ = 0.01, el rastro pierde la mitad en ln 2 / 0.01 ≈ 69 pasos (6.9 s simulados). Cuando
   una fuente se agota, su ruta se desvanece.
4. Experimento: mismas semillas, feromonas no/sí. Con la semilla 5735, 3 000 hormigas y
   `salidas_por_paso = 10`, en 1 000 pasos se recolectan 2 060 unidades sin feromonas y 3 850
   con ellas. Confirmarlo con réplicas.

---

## 4. Ejercicios sugeridos

1. **Cuadrados medios a mano.** Calcula los primeros 8 números con semilla 6100 y D = 4.
   ¿Dónde degenera y cuál es la longitud del ciclo? Verifícalo en la tabla paso a paso.
   *(Respuesta: ciclo de longitud 4 al cuarto número.)*
2. **Periodo de un congruencial.** Sin el simulador, predice el periodo de
   `x_{i+1} = (5x_i + 3) mod 16`, de `(5x_i + 2) mod 16` y de `(3x_i) mod 7`. Comprueba con la tabla.
   *(16, 8 y 6.)*
3. **Hull-Dobell.** Encuentra valores de `a` y `c` con `m = 64` que den periodo completo y otros
   que no. Explica cada caso con las tres condiciones del teorema.
4. **¿Cuántos dígitos hacen falta?** En el laboratorio, compara cuadrados medios con D = 4, 6 y 8
   (semilla 5735, n = 1000). Reporta re-siembras, números distintos y qué pruebas rechazan.
5. **Uniforme no es independiente.** Construye un argumento de por qué un generador puede pasar
   χ² y K-S y fallar corridas. Usa el caso D = 6.
6. **RANDU.** Investiga por qué RANDU es malo si pasa las tres pruebas del laboratorio.
7. **Rastrear una decisión.** Selecciona una hormiga, encuentra en la bitácora su último
   `ENTRADA_RADIO_REINA` y, en el registro, el número usado. Explica con ese `u` y con `p` por qué
   la siguió o no.
8. **Frecuencia frente a probabilidad.** Con p = 0.3, 0.5 y 0.8, deja correr 2 000 pasos y anota p̂.
   ¿Qué tan cerca queda de p? Repite con D = 8. ¿Qué cambia y por qué?
9. **Réplicas e IC.** Estima el alimento recolectado a los 1 000 pasos con 5, 10 y 30 réplicas.
   ¿Cómo cambia el ancho del intervalo? ¿Se cumple aproximadamente que se reduce como 1/√n?
10. **Diseño de experimento.** ¿Las feromonas aumentan el alimento recolectado a los 1 500
    pasos? Plantea hipótesis, corre dos lotes (sí/no) y concluye con los intervalos.
11. **Recurso finito.** Con fuentes pequeñas, observa en las series (CSV) el "Alimento en las
    fuentes" a lo largo del tiempo. Grafica e identifica cuándo se agota cada fuente.
12. **Régimen transitorio.** En las series de una corrida larga, grafica las hormigas
    "Buscando comida". ¿Cuándo se estabiliza? ¿Qué implica para elegir la duración de las réplicas?
13. **Evaporación.** Con ρ = 0.01, 0.05 y 0.2, observa qué tan largas y persistentes son las rutas.
    Relaciónalo con la vida media `ln 2 / ρ`.

---

## 5. Limitaciones del modelo (para discutir con honestidad)

- Las hormigas no mueren ni se reproducen: la energía sólo las hace volver al nido.
- La reina patrulla cerca del nido; no hay rocas ni fuentes en su zona de patrulla.
- Cuadrados medios con D = 4 degenera en cada corrida: la re-siembra mantiene la simulación
  usable, pero los números ya no son de buena calidad. Es intencional, para discutirlo.
- Los sensores de feromona sólo existen en el estado "Buscando comida"; las que regresan van
  directo al nido.
- El "siguiente evento" es una predicción en línea recta: puede no ocurrir (por ejemplo, si
  una feromona la desvía o la reina se mueve).
- Las réplicas de un lote cambian la semilla y, con ella, también el mundo (rocas y fuentes).

## 6. Referencia rápida

| Quiero mostrar… | Dónde |
|---|---|
| Cálculo de un número | Tabla paso a paso; panel de la hormiga seleccionada |
| Degeneración y re-siembra | Semillas 1, 2500, 6100 (D = 4); bitácora `GENERADOR_DEGENERADO` |
| Comparar generadores | Laboratorio (y su CSV) |
| Bernoulli | Estadísticas: "Decisión de seguir a la reina" (p̂ frente a p) |
| Reproducibilidad | Reiniciar; descargar el registro completo |
| Intervalos de confianza | Experimentos; `scripts/experimento_lote.py` |
| Series de tiempo | "Descargar series (CSV)" |
| Comportamiento emergente | Feromonas activas |

Los CSV usan `;` como separador y coma decimal (Excel en español). En Python:
`pandas.read_csv("archivo.csv", sep=";", decimal=",")`.
