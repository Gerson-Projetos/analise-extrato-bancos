from datetime import date, datetime
from typing import Optional, Union

class Formatter:
    @staticmethod
    def moeda(valor: Optional[Union[float, int]]) -> str:
        """Formata valor float para formato monetário brasileiro: R$ 1.250,50"""
        if valor is None:
            return "R$ 0,00"
        s = f"{valor:,.2f}"
        s = s.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"

    @staticmethod
    def percentual(valor: Optional[Union[float, int]]) -> str:
        """Formata percentual: 25.5 -> 25,5%"""
        if valor is None:
            return "0,0%"
        return f"{valor:.1f}%".replace(".", ",")

    @staticmethod
    def data(d: Optional[Union[date, datetime, str]]) -> str:
        """Formata data para dd/mm/aaaa."""
        if not d:
            return "-"
        if isinstance(d, (date, datetime)):
            return d.strftime("%d/%m/%Y")
        return str(d)

    @staticmethod
    def barra_progresso(percentual: float, tamanho: int = 15) -> str:
        """Gera barra de progresso em texto simples (ASCII seguro para qualquer terminal)."""
        if percentual < 0:
            percentual = 0
        if percentual > 100:
            percentual = 100
        preenchidos = int((percentual / 100) * tamanho)
        vazios = tamanho - preenchidos
        return f"[{'#' * preenchidos}{'-' * vazios}]"
