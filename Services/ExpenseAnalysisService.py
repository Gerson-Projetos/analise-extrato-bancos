import pandas as pd
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import date
from Repositories.ExtratoRepository import ExtratoRepository

class ExpenseAnalysisService:
    """Serviço responsável pelos cálculos e agregações analíticas de gastos e receitas."""

    def __init__(self, session: Session):
        self.session = session
        self.repo = ExtratoRepository(session)

    def obter_resumo_financeiro(
        self,
        bancos: Optional[List[str]] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None
    ) -> Dict[str, Any]:
        """Calcula indicadores consolidados de receitas, despesas, saldo e poupança."""
        df = self.repo.get_dataframe(bancos=bancos, data_inicio=data_inicio, data_fim=data_fim)

        if df.empty:
            return {
                "total_receitas": 0.0,
                "total_despesas": 0.0,
                "saldo_liquido": 0.0,
                "taxa_poupanca": 0.0,
                "total_transacoes": 0,
                "total_receitas_qtd": 0,
                "total_despesas_qtd": 0,
                "periodo_inicio": data_inicio,
                "periodo_fim": data_fim,
                "bancos": bancos or ["Todos"]
            }

        receitas_df = df[df['tipo'] == 'RECEITA']
        despesas_df = df[df['tipo'] == 'DESPESA']

        total_receitas = float(receitas_df['valor'].sum())
        total_despesas = float(despesas_df['valor_abs'].sum())
        saldo_liquido = total_receitas - total_despesas

        taxa_poupanca = (saldo_liquido / total_receitas * 100.0) if total_receitas > 0 else 0.0

        p_inicio = df['data'].min() if data_inicio is None else data_inicio
        p_fim = df['data'].max() if data_fim is None else data_fim
        bancos_presentes = sorted(df['banco'].unique().tolist())

        return {
            "total_receitas": round(total_receitas, 2),
            "total_despesas": round(total_despesas, 2),
            "saldo_liquido": round(saldo_liquido, 2),
            "taxa_poupanca": round(taxa_poupanca, 1),
            "total_transacoes": len(df),
            "total_receitas_qtd": len(receitas_df),
            "total_despesas_qtd": len(despesas_df),
            "periodo_inicio": p_inicio,
            "periodo_fim": p_fim,
            "bancos": bancos_presentes
        }

    def obter_gastos_por_categoria(
        self,
        bancos: Optional[List[str]] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None
    ) -> pd.DataFrame:
        """Gera tabela consolidada de despesas agrupadas por Categoria."""
        df = self.repo.get_dataframe(bancos=bancos, data_inicio=data_inicio, data_fim=data_fim)
        despesas = df[df['tipo'] == 'DESPESA'].copy()

        if despesas.empty:
            return pd.DataFrame(columns=["Categoria", "Total (R$)", "Qtd", "% Despesas"])

        agrupado = despesas.groupby('categoria').agg(
            total_gasto=('valor_abs', 'sum'),
            qtd=('id', 'count')
        ).reset_index()

        total_despesas_geral = agrupado['total_gasto'].sum()
        agrupado['perc_total'] = (agrupado['total_gasto'] / total_despesas_geral * 100.0).round(1)
        agrupado = agrupado.sort_values(by='total_gasto', ascending=False)

        agrupado = agrupado.rename(columns={
            'categoria': 'Categoria',
            'total_gasto': 'Total (R$)',
            'qtd': 'Qtd',
            'perc_total': '% Despesas'
        })
        agrupado['Total (R$)'] = agrupado['Total (R$)'].round(2)
        return agrupado

    def obter_evolucao_mensal(
        self,
        bancos: Optional[List[str]] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None
    ) -> pd.DataFrame:
        """Calcula o fluxo mensal (Receitas vs Despesas vs Saldo)."""
        df = self.repo.get_dataframe(bancos=bancos, data_inicio=data_inicio, data_fim=data_fim)
        if df.empty:
            return pd.DataFrame(columns=["Mês", "Receitas (R$)", "Despesas (R$)", "Saldo (R$)", "Poupança (%)"])

        df['data_dt'] = pd.to_datetime(df['data'])
        df['ano_mes'] = df['data_dt'].dt.strftime('%Y-%m')

        rec = df[df['tipo'] == 'RECEITA'].groupby('ano_mes')['valor'].sum()
        desp = df[df['tipo'] == 'DESPESA'].groupby('ano_mes')['valor_abs'].sum()

        evolucao = pd.DataFrame({
            'Receitas (R$)': rec,
            'Despesas (R$)': desp
        }).fillna(0.0)

        evolucao['Saldo (R$)'] = evolucao['Receitas (R$)'] - evolucao['Despesas (R$)']
        evolucao['Poupança (%)'] = (
            (evolucao['Saldo (R$)'] / evolucao['Receitas (R$)']) * 100
        ).fillna(0.0).round(1)

        evolucao = evolucao.reset_index().rename(columns={'ano_mes': 'Mês'})
        evolucao = evolucao.sort_values(by='Mês')

        evolucao['Receitas (R$)'] = evolucao['Receitas (R$)'].round(2)
        evolucao['Despesas (R$)'] = evolucao['Despesas (R$)'].round(2)
        evolucao['Saldo (R$)'] = evolucao['Saldo (R$)'].round(2)

        return evolucao

    def obter_maiores_despesas(
        self,
        top: int = 10,
        bancos: Optional[List[str]] = None,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None
    ) -> pd.DataFrame:
        """Retorna o ranking dos maiores gastos no período selecionado."""
        df = self.repo.get_dataframe(bancos=bancos, data_inicio=data_inicio, data_fim=data_fim)
        despesas = df[df['tipo'] == 'DESPESA'].copy()

        if despesas.empty:
            return pd.DataFrame(columns=["Data", "Banco", "Descrição", "Categoria", "Valor (R$)"])

        top_df = despesas.sort_values(by='valor_abs', ascending=False).head(top)
        top_df = top_df[['data', 'banco', 'descricao', 'categoria', 'valor_abs']].rename(columns={
            'data': 'Data',
            'banco': 'Banco',
            'descricao': 'Descrição',
            'categoria': 'Categoria',
            'valor_abs': 'Valor (R$)'
        })
        top_df['Valor (R$)'] = top_df['Valor (R$)'].round(2)
        return top_df

    def obter_distribuicao_por_banco(self) -> pd.DataFrame:
        """Gera um comparativo de receitas, despesas e transações por instituição bancária."""
        df = self.repo.get_dataframe()
        if df.empty:
            return pd.DataFrame(columns=["Banco", "Receitas (R$)", "Despesas (R$)", "Saldo (R$)", "Transações"])

        rec = df[df['tipo'] == 'RECEITA'].groupby('banco')['valor'].sum()
        desp = df[df['tipo'] == 'DESPESA'].groupby('banco')['valor_abs'].sum()
        qtd = df.groupby('banco')['id'].count()

        bancos_df = pd.DataFrame({
            'Receitas (R$)': rec,
            'Despesas (R$)': desp,
            'Transações': qtd
        }).fillna(0.0)

        bancos_df['Saldo (R$)'] = bancos_df['Receitas (R$)'] - bancos_df['Despesas (R$)']
        bancos_df = bancos_df.reset_index().rename(columns={'banco': 'Banco'})
        bancos_df['Receitas (R$)'] = bancos_df['Receitas (R$)'].round(2)
        bancos_df['Despesas (R$)'] = bancos_df['Despesas (R$)'].round(2)
        bancos_df['Saldo (R$)'] = bancos_df['Saldo (R$)'].round(2)

        return bancos_df
