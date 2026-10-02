"""Pruebas del servicio y del registro de números pseudoaleatorios (RF-12, RF-14, RF-15)."""

from app.aleatorio.cuadrados_medios import GeneradorCuadradosMedios
from app.aleatorio.registro import EntradaRegistro, RegistroAleatorio
from app.aleatorio.servicio import Flujo, Proposito, ServicioAleatorio
from app.eventos.tipos import TipoEvento


def crear_servicio(semilla_mundo: int = 5735, semilla_comportamiento: int = 735) -> ServicioAleatorio:
    return ServicioAleatorio(
        GeneradorCuadradosMedios(semilla_mundo),
        GeneradorCuadradosMedios(semilla_comportamiento),
    )


def test_registra_proposito_hormiga_e_indice() -> None:
    servicio = crear_servicio()
    servicio.fijar_tiempo(tick=3, tiempo=0.3)
    u = servicio.obtener(Proposito.DIRECCION_SALIDA, id_hormiga=42)
    (entrada,) = servicio.registro.pagina(desde=1, limite=10)
    assert entrada.indice == 1
    assert entrada.u == u
    assert entrada.proposito == "DIRECCION_SALIDA"
    assert entrada.flujo == "COMPORTAMIENTO"
    assert entrada.id_hormiga == 42
    assert entrada.generador == "Cuadrados medios"
    assert (entrada.tick, entrada.tiempo) == (3, 0.3)
    assert entrada.calculo["previo"] == 735
    assert servicio.total_generados == 1


def test_proposito_mundo_usa_el_flujo_mundo() -> None:
    servicio = crear_servicio()
    assert servicio.obtener(Proposito.MUNDO) == 0.8902  # primer número de la semilla 5735
    assert servicio.registro.pagina(1, 1)[0].flujo == "MUNDO"


def test_flujos_independientes() -> None:
    """Pedir números de COMPORTAMIENTO no altera la sucesión del MUNDO (RF-15)."""
    solo_mundo = crear_servicio()
    esperado = [solo_mundo.obtener(Proposito.MUNDO) for _ in range(50)]

    mezclado = crear_servicio()
    obtenido = []
    for i in range(50):
        for _ in range(i % 7):
            mezclado.obtener(Proposito.SEGUIR_REINA, id_hormiga=i)
        obtenido.append(mezclado.obtener(Proposito.MUNDO))
    assert obtenido == esperado


def test_degeneracion_genera_evento_en_bitacora() -> None:
    servicio = crear_servicio(semilla_comportamiento=1)  # 1 → 0 en el primer número
    servicio.fijar_tiempo(tick=7, tiempo=0.7)
    servicio.obtener(Proposito.DIRECCION_SALIDA, id_hormiga=5)
    (evento,) = servicio.bitacora.ultimos(10)
    assert evento.tipo is TipoEvento.GENERADOR_DEGENERADO
    assert evento.tick == 7
    assert evento.id_hormiga == 5
    assert evento.indice_aleatorio == 1
    assert evento.detalle["flujo"] == "COMPORTAMIENTO"
    assert evento.detalle["tipo"] == "CERO"
    assert evento.detalle["semilla_nueva"] == 7920
    assert servicio.degeneraciones(Flujo.COMPORTAMIENTO) == 1
    assert servicio.degeneraciones(Flujo.MUNDO) == 0


def test_cada_degeneracion_queda_en_bitacora_y_registro() -> None:
    servicio = crear_servicio()
    for _ in range(500):
        servicio.obtener(Proposito.DIRECCION_COLISION)
    eventos = servicio.bitacora.ultimos(1000)
    assert len(eventos) == servicio.degeneraciones(Flujo.COMPORTAMIENTO) > 0
    for evento in eventos:
        entrada = servicio.registro.pagina(evento.indice_aleatorio, 1)[0]
        assert entrada.calculo["degeneracion"]["semilla_nueva"] == evento.detalle["semilla_nueva"]


def test_reiniciar_repite_la_corrida() -> None:
    servicio = crear_servicio()
    primera = [servicio.obtener(Proposito.DIRECCION_SALIDA) for _ in range(300)]
    servicio.reiniciar()
    assert servicio.total_generados == 0
    assert servicio.bitacora.total == 0
    assert [servicio.obtener(Proposito.DIRECCION_SALIDA) for _ in range(300)] == primera


def _entrada(indice: int) -> EntradaRegistro:
    return EntradaRegistro(indice, "MUNDO", "prueba", "MUNDO", -1, 0, 0.0, 0.5)


def test_registro_circular_descarta_los_mas_viejos() -> None:
    registro = RegistroAleatorio(capacidad=5)
    for i in range(1, 13):
        registro.agregar(_entrada(i))
    assert registro.total == 12
    assert registro.primer_indice_disponible == 8
    assert [e.indice for e in registro.pagina(desde=1, limite=100)] == [8, 9, 10, 11, 12]
    assert [e.indice for e in registro.pagina(desde=10, limite=2)] == [10, 11]
    assert registro.pagina(desde=13, limite=5) == []
