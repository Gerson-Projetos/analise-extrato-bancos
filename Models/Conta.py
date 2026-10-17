from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from Conn.Database import Base

class Conta(Base):
    __tablename__ = 'contas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    banco = Column(String(100), nullable=False)
    descricao = Column(String(255), nullable=True)
    tbl_extrato = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Conta(banco='{self.banco}', tbl_extrato='{self.tbl_extrato}')>"
