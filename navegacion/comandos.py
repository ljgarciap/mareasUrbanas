"""Patrón Command: solicitudes encapsuladas con historial y deshacer."""
from __future__ import annotations
from abc import ABC, abstractmethod

from .navegador import Navegador
from .ruta import ResultadoBusqueda
from .trafico import SensorTrafico


class Comando(ABC):
    @abstractmethod
    def ejecutar(self): ...

    @abstractmethod
    def deshacer(self) -> None: ...


class CalcularRutaComando(Comando):
    def __init__(self, nav: Navegador, origen: int, destino: int):
        self.nav, self.o, self.d = nav, origen, destino
        self.resultado: ResultadoBusqueda | None = None

    def ejecutar(self) -> ResultadoBusqueda:
        self.resultado = self.nav.calcular(self.o, self.d)
        return self.resultado

    def deshacer(self) -> None:      # consulta sin efectos: sólo descarta el resultado
        self.resultado = None


class ReportarIncidenteComando(Comando):
    def __init__(self, sensor: SensorTrafico, a: int, b: int, factor: float):
        self.sensor, self.a, self.b, self.factor = sensor, a, b, factor
        self._previo: float | None = None

    def ejecutar(self):
        self._previo = self.sensor.grafo.arista(self.a, self.b).congestion
        return self.sensor.reportar(self.a, self.b, self.factor)

    def deshacer(self) -> None:      # restaura y vuelve a notificar a los observadores
        if self._previo is not None:
            self.sensor.reportar(self.a, self.b, self._previo)


class Invocador:
    def __init__(self):
        self.historial: list[Comando] = []

    def ejecutar(self, c: Comando):
        r = c.ejecutar()
        self.historial.append(c)
        return r

    def deshacer_ultimo(self) -> bool:
        if not self.historial:
            return False
        self.historial.pop().deshacer()
        return True
