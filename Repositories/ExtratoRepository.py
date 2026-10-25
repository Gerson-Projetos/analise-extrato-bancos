from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
from datetime import date
from sqlalchemy import text

from Models.Conta import Conta
from Models.ExtratoItau import ExtratoItau
from Models.ExtratoMercadoPago import ExtratoMercadoPago
from Models.LancamentoDTO import LancamentoDTO
from Repositories.CategoriaRepository import CategoriaRepository

class ExtratoRepository:
    def __init__(self, session: Session):
        self.session = session
        self.cat_repo = CategoriaRepository(session)

    def get_contas_configuradas(self) -> List[Conta]:
        return self.session.query(Conta).all()

    def get_lancamentos_unificados(
        self,
        bancos: Optional[List[str]] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        tipo: Optional[str] = None, # 'RECEITA' ou 'DESPESA'
        busca: Optional[str] = None
    ) -> List[LancamentoDTO]:
        """Busca e consolida lançamentos de todas as tabelas de extrato ativas."""
        mapa_lanc = self.cat_repo.get_mapa_lancamentos()
        lancamentos: List[LancamentoDTO] = []

        bancos_norm = [b.lower() for b in bancos] if bancos else None

        # 1. Extrato Itaú
        if not bancos_norm or 'itau' in bancos_norm:
            q_itau = self.session.query(ExtratoItau)
            if data_inicio:
                q_itau = q_itau.filter(ExtratoItau.data_lancamento >= data_inicio)
            if data_fim:
                q_itau = q_itau.filter(ExtratoItau.data_lancamento <= data_fim)
            if busca:
                q_itau = q_itau.filter(ExtratoItau.descricao.ilike(f"%{busca}%"))

            for row in q_itau.order_by(ExtratoItau.data_lancamento.desc()).all():
                val = float(row.valor) if row.valor is not None else 0.0

                lanc_cat = mapa_lanc.get(row.hash_transacao)
                cat_obj = lanc_cat.categoria if lanc_cat else None
                cat_nome = cat_obj.nome if cat_obj else "Não categorizado"
                cat_cor = cat_obj.cor_hex if cat_obj else "#808080"
                cat_icone = cat_obj.icone if cat_obj else "🏷️"
                obs = lanc_cat.observacao if lanc_cat else None

                if cat_obj and cat_obj.tipo_padrao == "TRANSFERENCIA":
                    tipo_transacao = "TRANSFERENCIA"
                else:
                    tipo_transacao = "RECEITA" if val >= 0 else "DESPESA"

                if tipo and tipo.upper() != tipo_transacao:
                    continue

                lancamentos.append(LancamentoDTO(
                    id=row.id,
                    banco="Itaú",
                    tabela_origem="extrato_itau",
                    data_lancamento=row.data_lancamento,
                    descricao=row.descricao,
                    valor=val,
                    tipo=tipo_transacao,
                    saldo=float(row.saldo) if row.saldo is not None else None,
                    hash_transacao=row.hash_transacao,
                    categoria=cat_nome,
                    categoria_cor=cat_cor,
                    categoria_icone=cat_icone,
                    arquivo_origem=row.arquivo_origem,
                    observacao=obs
                ))

        # 2. Extrato Mercado Pago
        if not bancos_norm or 'mercado_pago' in bancos_norm or 'mercado pago' in bancos_norm:
            q_mp = self.session.query(ExtratoMercadoPago)
            if data_inicio:
                q_mp = q_mp.filter(ExtratoMercadoPago.data_lancamento >= data_inicio)
            if data_fim:
                q_mp = q_mp.filter(ExtratoMercadoPago.data_lancamento <= data_fim)
            if busca:
                q_mp = q_mp.filter(ExtratoMercadoPago.descricao.ilike(f"%{busca}%"))

            for row in q_mp.order_by(ExtratoMercadoPago.data_lancamento.desc()).all():
                val = float(row.valor) if row.valor is not None else 0.0

                lanc_cat = mapa_lanc.get(row.hash_transacao)
                cat_obj = lanc_cat.categoria if lanc_cat else None
                cat_nome = cat_obj.nome if cat_obj else "Não categorizado"
                cat_cor = cat_obj.cor_hex if cat_obj else "#808080"
                cat_icone = cat_obj.icone if cat_obj else "🏷️"
                obs = lanc_cat.observacao if lanc_cat else None

                if cat_obj and cat_obj.tipo_padrao == "TRANSFERENCIA":
                    tipo_transacao = "TRANSFERENCIA"
                else:
                    tipo_transacao = "RECEITA" if val >= 0 else "DESPESA"

                if tipo and tipo.upper() != tipo_transacao:
                    continue

                lancamentos.append(LancamentoDTO(
                    id=row.id,
                    banco="Mercado Pago",
                    tabela_origem="extrato_mercado_pago",
                    data_lancamento=row.data_lancamento,
                    descricao=row.descricao,
                    valor=val,
                    tipo=tipo_transacao,
                    saldo=float(row.saldo) if row.saldo is not None else None,
                    hash_transacao=row.hash_transacao,
                    categoria=cat_nome,
                    categoria_cor=cat_cor,
                    categoria_icone=cat_icone,
                    arquivo_origem=row.arquivo_origem,
                    observacao=obs
                ))

        # Ordena todos cronologicamente descrescente
        lancamentos.sort(key=lambda x: x.data_lancamento, reverse=True)
        return lancamentos

    def get_dataframe(self, **kwargs) -> pd.DataFrame:
        """Retorna os lançamentos unificados como pandas.DataFrame para análise analítica."""
        dados = self.get_lancamentos_unificados(**kwargs)
        if not dados:
            return pd.DataFrame(columns=[
                "id", "banco", "data", "ano", "mes", "ano_mes",
                "descricao", "valor", "valor_abs", "tipo",
                "saldo", "categoria", "hash_transacao", "observacao"
            ])

        linhas = []
        for d in dados:
            linhas.append({
                "id": d.id,
                "banco": d.banco,
                "data": d.data_lancamento,
                "ano": d.data_lancamento.year,
                "mes": d.data_lancamento.month,
                "ano_mes": d.data_lancamento.strftime("%Y-%m"),
                "descricao": d.descricao,
                "valor": d.valor,
                "valor_abs": abs(d.valor),
                "tipo": d.tipo,
                "saldo": d.saldo,
                "categoria": d.categoria,
                "hash_transacao": d.hash_transacao,
                "arquivo_origem": d.arquivo_origem,
                "observacao": d.observacao
            })

        df = pd.DataFrame(linhas)
        df['data'] = pd.to_datetime(df['data'])
        return df

    # Alias de conveniência
    get_todos_lancamentos = get_lancamentos_unificados
