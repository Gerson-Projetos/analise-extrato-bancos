from sqlalchemy import Column, Integer, String, Numeric, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from Conn.Database import Base

class LancamentoCategorizado(Base):
    __tablename__ = 'lancamentos_categorizados'

    id = Column(Integer, primary_key=True, autoincrement=True)
    hash_transacao = Column(String(64), unique=True, index=True, nullable=False)
    categoria_id = Column(Integer, ForeignKey('categorias_gastos.id'), nullable=False)
    banco = Column(String(50), nullable=True)
    data_lancamento = Column(Date, nullable=True)
    valor = Column(Numeric(10, 2), nullable=True)
    descricao = Column(String(500), nullable=True)
    manual = Column(Boolean, default=False)
    observacao = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    categoria = relationship('Categoria')

    def __repr__(self):
        return f"<LancamentoCategorizado(hash='{self.hash_transacao[:8]}...', cat_id={self.categoria_id})>"
