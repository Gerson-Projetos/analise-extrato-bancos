from dataclasses import dataclass
from datetime import date
from typing import Optional

@dataclass
class LancamentoDTO:
    id: int
    banco: str
    tabela_origem: str
    data_lancamento: date
    descricao: str
    valor: float
    tipo: str # 'RECEITA' ou 'DESPESA'
    saldo: Optional[float]
    hash_transacao: str
    categoria: str = 'Não categorizado'
    categoria_cor: str = '#808080'
    categoria_icone: str = '🏷️'
    arquivo_origem: Optional[str] = None
    observacao: Optional[str] = None
