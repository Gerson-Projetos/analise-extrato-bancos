import sys
import os
import io
from datetime import datetime, date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import dotenv

# Garante o diretório do projeto no sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Carrega configurações de ambiente
dotenv.load_dotenv(os.path.join(project_root, ".env"))

from Conn.Database import Database, get_db_session
from Repositories.ExtratoRepository import ExtratoRepository
from Repositories.CategoriaRepository import CategoriaRepository
from Services.CategorizationService import CategorizationService
from Services.ExpenseAnalysisService import ExpenseAnalysisService
from Services.ReportService import ReportService
from Util.Formatter import Formatter

# ==============================================================================
# Configuração da Página
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Financeiro | Análise de Extratos",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada
st.markdown("""
<style>
    .metric-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        font-size: 1.75rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #94a3b8;
    }
    .positive-val { color: #10b981; }
    .negative-val { color: #ef4444; }
    .neutral-val { color: #3b82f6; }
</style>
""", unsafe_allow_html=True)

# Assegura que tabelas necessárias existam
@st.cache_resource
def init_db():
    db = Database()
    db.create_tables()
    return True

init_db()

# ==============================================================================
# Funções de Carga de Dados (com cache do Streamlit)
# ==============================================================================
def carregar_dados():
    with get_db_session() as session:
        repo = ExtratoRepository(session)
        df = repo.get_dataframe()
        cat_repo = CategoriaRepository(session)
        categorias = [c.nome for c in cat_repo.get_todas_categorias()]
    return df, categorias

df_raw, lista_categorias = carregar_dados()

if df_raw.empty:
    st.warning("⚠️ Nenhuma transação encontrada no banco de dados. Execute o ETL ou verifique a conexão.")
    st.stop()

# ==============================================================================
# Barra Lateral (Filtros e Controles)
# ==============================================================================
st.sidebar.markdown("### 🏦 **Filtros Analíticos**")
st.sidebar.markdown("---")

# 1. Filtro de Banco
bancos_disponiveis = sorted(df_raw['banco'].unique().tolist())
bancos_selecionados = st.sidebar.multiselect(
    "Instituições Bancárias:",
    options=bancos_disponiveis,
    default=bancos_disponiveis
)

# 2. Filtro de Data
min_date = df_raw['data'].min().date()
max_date = df_raw['data'].max().date()

data_range = st.sidebar.date_input(
    "Período de Análise:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    format="DD/MM/YYYY"
)

# Validação do período
if isinstance(data_range, (list, tuple)) and len(data_range) == 2:
    start_date, end_date = data_range
else:
    start_date, end_date = min_date, max_date

# Aplica filtros
df_filtrado = df_raw[
    (df_raw['banco'].isin(bancos_selecionados)) &
    (df_raw['data'].dt.date >= start_date) &
    (df_raw['data'].dt.date <= end_date)
].copy()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ **Ações Rápidas**")

col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    if st.button("🔄 Classificar", use_container_width=True, help="Categoriza transações pendentes"):
        with get_db_session() as session:
            cat_service = CategorizationService(session)
            res = cat_service.categorizar_transacoes_pendentes(forcar=False)
            st.sidebar.success(f"Classificados: {res['novos_categorizados']}")
            st.rerun()

with col_b2:
    if st.button("⚠️ Reclassificar", use_container_width=True, help="Reclassifica todas as transações com novas regras"):
        with get_db_session() as session:
            cat_service = CategorizationService(session)
            res = cat_service.categorizar_transacoes_pendentes(forcar=True)
            st.sidebar.warning(f"Reclassificados: {res['novos_categorizados']}")
            st.rerun()

# Botão para exportar Excel
st.sidebar.markdown("---")
with get_db_session() as session:
    service = ExpenseAnalysisService(session)
    resumo_dict = service.obter_resumo_financeiro(
        bancos=bancos_selecionados,
        data_inicio=start_date,
        data_fim=end_date
    )
    df_cat_full = service.obter_gastos_por_categoria(bancos=bancos_selecionados, data_inicio=start_date, data_fim=end_date)
    df_evo_full = service.obter_evolucao_mensal(bancos=bancos_selecionados, data_inicio=start_date, data_fim=end_date)
    df_mai_full = service.obter_maiores_despesas(top=50, bancos=bancos_selecionados, data_inicio=start_date, data_fim=end_date)
    df_ban_full = service.obter_distribuicao_por_banco()

excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
    pd.DataFrame([
        {"Indicador": "Período", "Valor": f"{Formatter.data(start_date)} até {Formatter.data(end_date)}"},
        {"Indicador": "Total Receitas (R$)", "Valor": resumo_dict.get('total_receitas')},
        {"Indicador": "Total Despesas (R$)", "Valor": resumo_dict.get('total_despesas')},
        {"Indicador": "Saldo Líquido (R$)", "Valor": resumo_dict.get('saldo_liquido')},
        {"Indicador": "Taxa de Poupança (%)", "Valor": resumo_dict.get('taxa_poupanca')},
        {"Indicador": "Total Transações", "Valor": resumo_dict.get('total_transacoes')},
    ]).to_excel(writer, sheet_name='Resumo', index=False)
    df_cat_full.to_excel(writer, sheet_name='Categorias', index=False)
    df_evo_full.to_excel(writer, sheet_name='Evolução Mensal', index=False)
    df_mai_full.to_excel(writer, sheet_name='Maiores Gastos', index=False)
    df_ban_full.to_excel(writer, sheet_name='Por Banco', index=False)
    df_filtrado.to_excel(writer, sheet_name='Extrato Filtrado', index=False)

excel_data = excel_buffer.getvalue()

st.sidebar.download_button(
    label="📥 Baixar Relatório Excel (.xlsx)",
    data=excel_data,
    file_name=f"relatorio_financeiro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

st.sidebar.caption("💡 Base conectada ao PostgreSQL: **financeiro**")

# ==============================================================================
# Cabeçalho Principal e KPIs
# ==============================================================================
st.title("💳 Painel Analítico de Extratos Bancários")
st.markdown(
    f"Visualizando dados consolidados de **{Formatter.data(start_date)}** até **{Formatter.data(end_date)}** "
    f"para os bancos: `{'`, `'.join(bancos_selecionados)}`."
)

# Cálculos de Métricas
receitas_df = df_filtrado[df_filtrado['tipo'] == 'RECEITA']
despesas_df = df_filtrado[df_filtrado['tipo'] == 'DESPESA']

total_receitas = float(receitas_df['valor'].sum()) if not receitas_df.empty else 0.0
total_despesas = float(despesas_df['valor_abs'].sum()) if not despesas_df.empty else 0.0
saldo_liquido = total_receitas - total_despesas
taxa_poupanca = (saldo_liquido / total_receitas * 100.0) if total_receitas > 0 else 0.0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">💵 Receitas Totais</div>
        <div class="metric-value positive-val">{Formatter.moeda(total_receitas)}</div>
        <div class="metric-sub">{len(receitas_df)} transações recebidas</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">💸 Despesas Totais</div>
        <div class="metric-value negative-val">{Formatter.moeda(total_despesas)}</div>
        <div class="metric-sub">{len(despesas_df)} saídas registradas</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    saldo_class = "positive-val" if saldo_liquido >= 0 else "negative-val"
    sinal = "+" if saldo_liquido > 0 else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">⚖️ Saldo Líquido</div>
        <div class="metric-value {saldo_class}">{sinal}{Formatter.moeda(saldo_liquido)}</div>
        <div class="metric-sub">Receitas menos Despesas</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    poup_class = "positive-val" if taxa_poupanca >= 0 else "negative-val"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">📈 Taxa de Poupança</div>
        <div class="metric-value {poup_class}">{Formatter.percentual(taxa_poupanca)}</div>
        <div class="metric-sub">Proporção economizada</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">🔢 Total Transações</div>
        <div class="metric-value neutral-val">{len(df_filtrado)}</div>
        <div class="metric-sub">Operações no período</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# Abas de Navegação Analítica
# ==============================================================================
tab_visao, tab_categorias, tab_tempo, tab_maiores, tab_extrato, tab_gestao = st.tabs([
    "📊 Visão Geral",
    "🏷️ Gastos por Categoria",
    "📅 Fluxo & Evolução Temporal",
    "🔝 Maiores Gastos",
    "📑 Extrato Completo & Busca",
    "⚙️ Reclassificação Manual"
])

# ------------------------------------------------------------------------------
# ABA 1: VISÃO GERAL
# ------------------------------------------------------------------------------
with tab_visao:
    col_chart_left, col_chart_right = st.columns([3, 2])

    with col_chart_left:
        st.subheader("📈 Evolução Mensal: Receitas vs Despesas vs Saldo")
        if not df_filtrado.empty:
            df_filtrado['ano_mes'] = df_filtrado['data'].dt.strftime('%Y-%m')
            rec_m = df_filtrado[df_filtrado['tipo'] == 'RECEITA'].groupby('ano_mes')['valor'].sum()
            desp_m = df_filtrado[df_filtrado['tipo'] == 'DESPESA'].groupby('ano_mes')['valor_abs'].sum()

            df_fluxo = pd.DataFrame({'Receitas': rec_m, 'Despesas': desp_m}).fillna(0.0).reset_index()
            df_fluxo['Saldo'] = df_fluxo['Receitas'] - df_fluxo['Despesas']

            fig_fluxo = go.Figure()
            fig_fluxo.add_trace(go.Bar(
                x=df_fluxo['ano_mes'],
                y=df_fluxo['Receitas'],
                name='Receitas',
                marker_color='#10b981',
                hovertemplate='%{x}<br>Receitas: R$ %{y:,.2f}<extra></extra>'
            ))
            fig_fluxo.add_trace(go.Bar(
                x=df_fluxo['ano_mes'],
                y=df_fluxo['Despesas'],
                name='Despesas',
                marker_color='#ef4444',
                hovertemplate='%{x}<br>Despesas: R$ %{y:,.2f}<extra></extra>'
            ))
            fig_fluxo.add_trace(go.Scatter(
                x=df_fluxo['ano_mes'],
                y=df_fluxo['Saldo'],
                name='Saldo Líquido',
                mode='lines+markers',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8),
                hovertemplate='%{x}<br>Saldo: R$ %{y:,.2f}<extra></extra>'
            ))
            fig_fluxo.update_layout(
                barmode='group',
                margin=dict(l=20, r=20, t=30, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Mês",
                yaxis_title="Valor (R$)",
                hovermode="x unified",
                template="plotly_white"
            )
            st.plotly_chart(fig_fluxo, use_container_width=True)
        else:
            st.info("Sem dados para o gráfico.")

    with col_chart_right:
        st.subheader("🍩 Distribuição de Gastos por Categoria")
        if not despesas_df.empty:
            cat_summary = despesas_df.groupby('categoria')['valor_abs'].sum().reset_index()
            cat_summary = cat_summary.sort_values(by='valor_abs', ascending=False)

            fig_donut = px.pie(
                cat_summary,
                values='valor_abs',
                names='categoria',
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Prism
            )
            fig_donut.update_traces(
                textposition='inside',
                textinfo='percent+label',
                hovertemplate='<b>%{label}</b><br>Total: R$ %{value:,.2f}<br>% do Total: %{percent}<extra></extra>'
            )
            fig_donut.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                showlegend=False,
                template="plotly_white"
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        else:
            st.info("Nenhuma despesa para exibir.")

    st.markdown("---")
    st.subheader("🏦 Comparativo de Contas & Instituições")
    if not df_filtrado.empty:
        rec_banco = df_filtrado[df_filtrado['tipo'] == 'RECEITA'].groupby('banco')['valor'].sum()
        desp_banco = df_filtrado[df_filtrado['tipo'] == 'DESPESA'].groupby('banco')['valor_abs'].sum()
        qtd_banco = df_filtrado.groupby('banco')['id'].count()

        df_bancos_comp = pd.DataFrame({
            'Receitas': rec_banco,
            'Despesas': desp_banco,
            'Transações': qtd_banco
        }).fillna(0.0)
        df_bancos_comp['Saldo'] = df_bancos_comp['Receitas'] - df_bancos_comp['Despesas']
        df_bancos_comp = df_bancos_comp.reset_index()

        col_b_chart, col_b_table = st.columns([3, 2])
        with col_b_chart:
            fig_bancos = px.bar(
                df_bancos_comp,
                x='banco',
                y=['Receitas', 'Despesas', 'Saldo'],
                barmode='group',
                color_discrete_map={'Receitas': '#10b981', 'Despesas': '#ef4444', 'Saldo': '#3b82f6'},
                labels={'value': 'Valor (R$)', 'banco': 'Banco', 'variable': 'Indicador'}
            )
            fig_bancos.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_bancos, use_container_width=True)

        with col_b_table:
            df_b_table = df_bancos_comp.copy()
            df_b_table['Receitas'] = df_b_table['Receitas'].apply(Formatter.moeda)
            df_b_table['Despesas'] = df_b_table['Despesas'].apply(Formatter.moeda)
            df_b_table['Saldo'] = df_b_table['Saldo'].apply(Formatter.moeda)
            st.dataframe(df_b_table, hide_index=True, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 2: GASTOS POR CATEGORIA
# ------------------------------------------------------------------------------
with tab_categorias:
    st.subheader("🏷️ Análise Detalhada de Despesas por Categoria")

    if not despesas_df.empty:
        cat_agg = despesas_df.groupby('categoria').agg(
            total=('valor_abs', 'sum'),
            qtd=('id', 'count')
        ).reset_index()

        total_desp_geral = cat_agg['total'].sum()
        cat_agg['perc'] = (cat_agg['total'] / total_desp_geral * 100.0).round(1)
        cat_agg = cat_agg.sort_values(by='total', ascending=True) # Ascendente para barra horizontal

        col_cat_grafico, col_cat_tabela = st.columns([3, 2])

        with col_cat_grafico:
            fig_cat = px.bar(
                cat_agg,
                y='categoria',
                x='total',
                orientation='h',
                text=cat_agg['total'].apply(Formatter.moeda),
                labels={'total': 'Total Gasto (R$)', 'categoria': 'Categoria'},
                color='total',
                color_continuous_scale='Reds'
            )
            fig_cat.update_traces(
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>Total: R$ %{x:,.2f}<extra></extra>'
            )
            fig_cat.update_layout(
                coloraxis_showscale=False,
                margin=dict(l=20, r=50, t=20, b=20),
                template="plotly_white"
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        with col_cat_tabela:
            cat_table = cat_agg.sort_values(by='total', ascending=False).copy()
            cat_table['Total'] = cat_table['total'].apply(Formatter.moeda)
            cat_table['% Despesas'] = cat_table['perc'].apply(Formatter.percentual)
            cat_table = cat_table[['categoria', 'Total', 'qtd', '% Despesas']].rename(columns={
                'categoria': 'Categoria',
                'qtd': 'Transações'
            })
            st.dataframe(cat_table, hide_index=True, use_container_width=True)

        # Drill-down por Categoria Selecionada
        st.markdown("---")
        st.subheader("🔍 Inspecionar Transações da Categoria")
        cat_escolhida = st.selectbox("Selecione uma Categoria para Detalhes:", options=cat_table['Categoria'].tolist())

        df_cat_filtrada = despesas_df[despesas_df['categoria'] == cat_escolhida].copy()
        df_cat_filtrada = df_cat_filtrada[['data', 'banco', 'descricao', 'valor_abs']].rename(columns={
            'data': 'Data',
            'banco': 'Banco',
            'descricao': 'Descrição',
            'valor_abs': 'Valor (R$)'
        }).sort_values(by='Data', ascending=False)

        col_sub_m1, col_sub_m2 = st.columns(2)
        col_sub_m1.metric("Total na Categoria", Formatter.moeda(df_cat_filtrada['Valor (R$)'].sum()))
        col_sub_m2.metric("Qtd Transações", len(df_cat_filtrada))

        df_cat_filtrada['Data'] = df_cat_filtrada['Data'].apply(Formatter.data)
        df_cat_filtrada['Valor (R$)'] = df_cat_filtrada['Valor (R$)'].apply(Formatter.moeda)
        st.dataframe(df_cat_filtrada, hide_index=True, use_container_width=True)
    else:
        st.info("Nenhuma despesa para exibir.")

# ------------------------------------------------------------------------------
# ABA 3: FLUXO & EVOLUÇÃO TEMPORAL
# ------------------------------------------------------------------------------
with tab_tempo:
    st.subheader("📅 Demonstrativo Mensal Consolidado")

    if not df_filtrado.empty:
        df_tempo = df_filtrado.copy()
        df_tempo['ano_mes'] = df_tempo['data'].dt.strftime('%Y-%m')

        rec_series = df_tempo[df_tempo['tipo'] == 'RECEITA'].groupby('ano_mes')['valor'].sum()
        desp_series = df_tempo[df_tempo['tipo'] == 'DESPESA'].groupby('ano_mes')['valor_abs'].sum()

        tab_mensal = pd.DataFrame({
            'Receitas (R$)': rec_series,
            'Despesas (R$)': desp_series
        }).fillna(0.0)

        tab_mensal['Saldo (R$)'] = tab_mensal['Receitas (R$)'] - tab_mensal['Despesas (R$)']
        tab_mensal['Taxa Poupança (%)'] = (
            (tab_mensal['Saldo (R$)'] / tab_mensal['Receitas (R$)']) * 100.0
        ).fillna(0.0).round(1)

        tab_mensal = tab_mensal.reset_index().rename(columns={'ano_mes': 'Mês'})
        tab_mensal = tab_mensal.sort_values(by='Mês')

        # Gráfico de Área Empilhada / Linha
        fig_evolucao_area = go.Figure()
        fig_evolucao_area.add_trace(go.Scatter(
            x=tab_mensal['Mês'], y=tab_mensal['Receitas (R$)'],
            fill='tozeroy', name='Receitas', line=dict(color='#10b981', width=2)
        ))
        fig_evolucao_area.add_trace(go.Scatter(
            x=tab_mensal['Mês'], y=tab_mensal['Despesas (R$)'],
            fill='tozeroy', name='Despesas', line=dict(color='#ef4444', width=2)
        ))
        fig_evolucao_area.update_layout(
            title="Receitas vs Despesas (Área Acumulada)",
            xaxis_title="Mês",
            yaxis_title="Total (R$)",
            template="plotly_white",
            hovermode="x unified"
        )
        st.plotly_chart(fig_evolucao_area, use_container_width=True)

        # Tabela formatada
        tab_mensal_fmt = tab_mensal.copy()
        tab_mensal_fmt['Receitas (R$)'] = tab_mensal_fmt['Receitas (R$)'].apply(Formatter.moeda)
        tab_mensal_fmt['Despesas (R$)'] = tab_mensal_fmt['Despesas (R$)'].apply(Formatter.moeda)
        tab_mensal_fmt['Saldo (R$)'] = tab_mensal_fmt['Saldo (R$)'].apply(Formatter.moeda)
        tab_mensal_fmt['Taxa Poupança (%)'] = tab_mensal_fmt['Taxa Poupança (%)'].apply(Formatter.percentual)

        st.dataframe(tab_mensal_fmt, hide_index=True, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 4: MAIORES GASTOS
# ------------------------------------------------------------------------------
with tab_maiores:
    st.subheader("🔝 Ranking dos Maiores Gastos")
    col_top_sel, _ = st.columns([1, 3])
    with col_top_sel:
        top_qtd = st.slider("Quantidade de itens no ranking:", min_value=5, max_value=50, value=15, step=5)

    if not despesas_df.empty:
        top_despesas = despesas_df.sort_values(by='valor_abs', ascending=False).head(top_qtd)

        fig_top = px.bar(
            top_despesas,
            x='valor_abs',
            y='descricao',
            orientation='h',
            color='categoria',
            labels={'valor_abs': 'Valor (R$)', 'descricao': 'Descrição', 'categoria': 'Categoria'},
            text=top_despesas['valor_abs'].apply(Formatter.moeda)
        )
        fig_top.update_layout(
            yaxis={'categoryorder': 'total ascending'},
            margin=dict(l=20, r=50, t=20, b=20),
            template="plotly_white"
        )
        st.plotly_chart(fig_top, use_container_width=True)

        tabela_top = top_despesas[['data', 'banco', 'descricao', 'categoria', 'valor_abs']].copy()
        tabela_top['Data'] = tabela_top['data'].apply(Formatter.data)
        tabela_top['Valor (R$)'] = tabela_top['valor_abs'].apply(Formatter.moeda)
        tabela_top = tabela_top[['Data', 'banco', 'descricao', 'categoria', 'Valor (R$)']].rename(columns={
            'banco': 'Banco',
            'descricao': 'Descrição',
            'categoria': 'Categoria'
        })
        st.dataframe(tabela_top, hide_index=True, use_container_width=True)

# ------------------------------------------------------------------------------
# ABA 5: EXTRATO COMPLETO & BUSCA
# ------------------------------------------------------------------------------
with tab_extrato:
    st.subheader("📑 Extrato Consolidado Interativo")

    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    with col_f1:
        busca_texto = st.text_input("🔍 Buscar na descrição da transação:", placeholder="Ex: Pix, Assai, Mercado...")
    with col_f2:
        tipo_filtro = st.selectbox("Tipo:", options=["Todos", "RECEITA", "DESPESA"])
    with col_f3:
        cat_filtro = st.selectbox("Categoria:", options=["Todas"] + lista_categorias)

    df_busca = df_filtrado.copy()

    if busca_texto:
        df_busca = df_busca[df_busca['descricao'].str.contains(busca_texto, case=False, na=False)]
    if tipo_filtro != "Todos":
        df_busca = df_busca[df_busca['tipo'] == tipo_filtro]
    if cat_filtro != "Todas":
        df_busca = df_busca[df_busca['categoria'] == cat_filtro]

    st.write(f"Mostrando **{len(df_busca)}** registros encontrados:")

    df_tabela_view = df_busca[['data', 'banco', 'descricao', 'categoria', 'tipo', 'valor']].copy()
    df_tabela_view = df_tabela_view.sort_values(by='data', ascending=False)
    df_tabela_view['Data'] = df_tabela_view['data'].apply(Formatter.data)
    df_tabela_view['Valor (R$)'] = df_tabela_view['valor'].apply(Formatter.moeda)
    df_tabela_view = df_tabela_view[['Data', 'banco', 'descricao', 'categoria', 'tipo', 'Valor (R$)']].rename(columns={
        'banco': 'Banco',
        'descricao': 'Descrição',
        'categoria': 'Categoria',
        'tipo': 'Tipo'
    })

    st.dataframe(df_tabela_view, hide_index=True, use_container_width=True, height=450)

    # Exportar CSV da busca atual
    csv_data = df_busca.to_csv(index=False, sep=";").encode("utf-8")
    st.download_button(
        "📥 Baixar Registros Filtrados (CSV)",
        data=csv_data,
        file_name="extrato_filtrado.csv",
        mime="text/csv"
    )

# ------------------------------------------------------------------------------
# ABA 6: RECLASSIFICAÇÃO MANUAL
# ------------------------------------------------------------------------------
with tab_gestao:
    st.subheader("⚙️ Gestão e Reclassificação Manual de Gastos")
    st.markdown("""
    Permite atribuir manualmente uma nova categoria a qualquer transação existente.
    Classificações manuais têm precedência e não são sobrescritas pelas regras automáticas.
    """)

    # Transações candidatas (ordenadas pelas mais recentes)
    transacoes_opcoes = df_filtrado[['hash_transacao', 'data', 'descricao', 'banco', 'valor', 'categoria']].copy()
    transacoes_opcoes = transacoes_opcoes.sort_values(by='data', ascending=False)

    transacoes_opcoes['label'] = transacoes_opcoes.apply(
        lambda r: f"[{Formatter.data(r['data'])}] ({r['banco']}) {r['descricao'][:40]} | {Formatter.moeda(r['valor'])} [Atual: {r['categoria']}]",
        axis=1
    )

    col_m1, col_m2 = st.columns([3, 2])
    with col_m1:
        item_selecionado = st.selectbox(
            "Selecione a Transação:",
            options=transacoes_opcoes['hash_transacao'].tolist(),
            format_func=lambda h: transacoes_opcoes[transacoes_opcoes['hash_transacao'] == h]['label'].values[0]
        )

    with col_m2:
        nova_categoria = st.selectbox("Nova Categoria Desejada:", options=lista_categorias)

    obs_manual = st.text_input("Observação (opcional):", placeholder="Motivo da classificação manual")

    if st.button("💾 Salvar Nova Categoria", type="primary"):
        with get_db_session() as session:
            cat_service = CategorizationService(session)
            sucesso = cat_service.categorizar_manualmente(
                hash_transacao=item_selecionado,
                nome_categoria=nova_categoria,
                observacao=obs_manual or "Reclassificação manual via dashboard"
            )
            if sucesso:
                st.success(f"Transação atualizada para a categoria '{nova_categoria}' com sucesso!")
                st.rerun()
            else:
                st.error("Erro ao atualizar transação.")
