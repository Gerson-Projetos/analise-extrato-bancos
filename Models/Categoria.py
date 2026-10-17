from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from Conn.Database import Base

class Categoria(Base):
    __tablename__ = 'categorias_gastos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String(100), unique=True, nullable=False)
    descricao = Column(String(255), nullable=True)
    cor_hex = Column(String(7), default='#808080')
    icone = Column(String(50), default='🏷️')
    tipo_padrao = Column(String(20), default='DESPESA') # 'DESPESA' ou 'RECEITA'
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Categoria(id={self.id}, nome='{self.nome}', icone='{self.icone}')>"
