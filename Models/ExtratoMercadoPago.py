from sqlalchemy import Column, Integer, String, Numeric, Date, DateTime
from sqlalchemy.sql import func
from Conn.Database import Base

class ExtratoMercadoPago(Base):
    __tablename__ = 'extrato_mercado_pago'

    id = Column(Integer, primary_key=True, autoincrement=True)
    data_lancamento = Column(Date, nullable=False)
    descricao = Column(String(500), nullable=False)
    id_operacao = Column(String(50), nullable=True)
    valor = Column(Numeric(10, 2), nullable=True)
    saldo = Column(Numeric(10, 2), nullable=True)
    arquivo_origem = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    hash_transacao = Column(String(64), unique=True, nullable=True)

    def __repr__(self):
        return f"<ExtratoMercadoPago(data='{self.data_lancamento}', desc='{self.descricao}', valor={self.valor})>"
