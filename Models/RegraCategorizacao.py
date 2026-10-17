from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from Conn.Database import Base

class RegraCategorizacao(Base):
    __tablename__ = 'regras_categorizacao'

    id = Column(Integer, primary_key=True, autoincrement=True)
    categoria_id = Column(Integer, ForeignKey('categorias_gastos.id'), nullable=False)
    padrao = Column(String(255), nullable=False) # Palavra-chave ou padrão regex
    tipo_padrao = Column(String(20), default='contem') # 'contem', 'regex', 'exato'
    prioridade = Column(Integer, default=10) # 1 a 100 (maior prioridade avaliada antes)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    categoria = relationship('Categoria')

    def __repr__(self):
        return f"<RegraCategorizacao(padrao='{self.padrao}', cat_id={self.categoria_id})>"
