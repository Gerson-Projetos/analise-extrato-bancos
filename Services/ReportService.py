import os
import sys
from datetime import datetime
import pandas as pd
from tabulate import tabulate
from Util.Formatter import Formatter

class ReportService:
    @staticmethod
    def exibir_resumo_terminal(resumo: dict):
        """Renderiza o painel executivo consolidado no terminal."""
        p_ini = Formatter.data(resumo.get('periodo_inicio'))
        p_fim = Formatter.data(resumo.get('periodo_fim'))
        bancos_str = ", ".join(resumo.get('bancos', []))

        print("\n" + "=" * 65)
        print("           RESUMO EXECUTIVO FINANCEIRO CONSOLIDADO           ")
        print("=" * 65)
        print(f" Periodo: {p_ini} ate {p_fim}")
        print(f" Bancos Integrados: {bancos_str}")
        print("-" * 65)
        print(f" [+] Total de Receitas:       {Formatter.moeda(resumo.get('total_receitas')):>16}  ({resumo.get('total_receitas_qtd')} entradas)")
        print(f" [-] Total de Despesas:       {Formatter.moeda(resumo.get('total_despesas')):>16}  ({resumo.get('total_despesas_qtd')} saidas)")
        print(" " + "-" * 63)

        saldo = resumo.get('saldo_liquido', 0.0)
        sinal = "+" if saldo >= 0 else ""
        print(f" [=] SALDO LIQUIDO:          {sinal}{Formatter.moeda(saldo):>15}")
        print(f" [*] Taxa de Poupanca:       {Formatter.percentual(resumo.get('taxa_poupanca')):>16}")
        print(f" Total de Transacoes:        {resumo.get('total_transacoes'):>16}")
        print("=" * 65 + "\n")

    @staticmethod
    def exibir_tabela_terminal(df: pd.DataFrame, titulo: str):
        """Exibe DataFrame formatado com tabulate no terminal."""
        print("\n" + "=" * 65)
        print(f"  {titulo.upper()}")
        print("=" * 65)

        if df.empty:
            print("  Nenhum dado encontrado para o periodo/filtro selecionado.")
            print("=" * 65 + "\n")
            return

        df_display = df.copy()

        # Adiciona barra visual se houver coluna % Despesas
        if '% Despesas' in df_display.columns:
            df_display['Visual'] = df_display['% Despesas'].apply(lambda x: Formatter.barra_progresso(x, 12))
            df_display['% Despesas'] = df_display['% Despesas'].apply(Formatter.percentual)

        # Formata colunas de moeda
        for col in df_display.columns:
            if '(R$)' in col:
                df_display[col] = df_display[col].apply(Formatter.moeda)
            elif col == 'Poupança (%)':
                df_display[col] = df_display[col].apply(Formatter.percentual)
            elif col == 'Data':
                df_display[col] = df_display[col].apply(Formatter.data)

        print(tabulate(df_display, headers='keys', tablefmt='simple', showindex=False))
        print("=" * 65 + "\n")

    @staticmethod
    def exportar_relatorio_excel(
        resumo: dict,
        df_categorias: pd.DataFrame,
        df_evolucao: pd.DataFrame,
        df_maiores: pd.DataFrame,
        df_bancos: pd.DataFrame,
        df_extrato_completo: pd.DataFrame,
        caminho_saida: str = None
    ) -> str:
        """Exporta um relatório analítico financeiro completo em formato Excel (.xlsx)."""
        if not caminho_saida:
            os.makedirs("relatorios", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            caminho_saida = os.path.join("relatorios", f"relatorio_financeiro_{timestamp}.xlsx")

        os.makedirs(os.path.dirname(os.path.abspath(caminho_saida)), exist_ok=True)

        resumo_df = pd.DataFrame([
            {"Indicador": "Período Início", "Valor": Formatter.data(resumo.get('periodo_inicio'))},
            {"Indicador": "Período Fim", "Valor": Formatter.data(resumo.get('periodo_fim'))},
            {"Indicador": "Bancos", "Valor": ", ".join(resumo.get('bancos', []))},
            {"Indicador": "Total Receitas (R$)", "Valor": resumo.get('total_receitas')},
            {"Indicador": "Qtd Entradas", "Valor": resumo.get('total_receitas_qtd')},
            {"Indicador": "Total Despesas (R$)", "Valor": resumo.get('total_despesas')},
            {"Indicador": "Qtd Saídas", "Valor": resumo.get('total_despesas_qtd')},
            {"Indicador": "Saldo Líquido (R$)", "Valor": resumo.get('saldo_liquido')},
            {"Indicador": "Taxa de Poupança (%)", "Valor": resumo.get('taxa_poupanca')},
            {"Indicador": "Total Transações", "Valor": resumo.get('total_transacoes')},
        ])

        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            resumo_df.to_excel(writer, sheet_name='Resumo Executivo', index=False)
            df_categorias.to_excel(writer, sheet_name='Gastos por Categoria', index=False)
            df_evolucao.to_excel(writer, sheet_name='Evolução Mensal', index=False)
            df_maiores.to_excel(writer, sheet_name='Maiores Despesas', index=False)
            df_bancos.to_excel(writer, sheet_name='Resumo por Banco', index=False)
            df_extrato_completo.to_excel(writer, sheet_name='Extrato Consolidado', index=False)

        return caminho_saida
