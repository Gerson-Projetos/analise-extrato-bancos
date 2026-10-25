import sys
import os
import io
import calendar
from datetime import datetime
import pandas as pd
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

# Paleta de cores compartilhada entre cartões e gráficos
COR_RECEITA = "#22a06b"        # verde (barras)
COR_RECEITA_BG = "#e3f6ec"     # verde claro (cartão)
COR_RECEITA_TXT = "#14532d"
COR_GASTO = "#f0645c"          # vermelho/coral (barras)
COR_GASTO_BG = "#fde6e3"       # coral claro (cartão)
COR_GASTO_TXT = "#7f1d1d"
COR_SALDO = "#1f2a44"          # azul marinho (cartão + barras de saldo)
COR_SALDO_TXT = "#f8fafc"

MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
MESES_NOME = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]

# Estilização CSS personalizada
st.markdown(f"""
<style>
    .kpi-card {{
        border-radius: 16px;
        padding: 20px 24px;
        box-shadow: 0 4px 14px -4px rgba(15, 23, 42, 0.12);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        min-height: 132px;
    }}
    .kpi-card:hover {{
        transform: translateY(-3px);
        box-shadow: 0 12px 24px -8px rgba(15, 23, 42, 0.22);
    }}
    .kpi-title {{
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        opacity: 0.85;
        margin-bottom: 6px;
    }}
    .kpi-value {{
        font-size: 2.1rem;
        font-weight: 800;
        line-height: 1.15;
        margin-bottom: 8px;
    }}
    .kpi-sub {{
        font-size: 0.85rem;
        opacity: 0.8;
    }}
    .kpi-sub b {{ font-weight: 700; }}
    .kpi-receita {{ background: {COR_RECEITA_BG}; color: {COR_RECEITA_TXT}; border: 1px solid #b7e4cb; }}
    .kpi-gasto   {{ background: {COR_GASTO_BG};   color: {COR_GASTO_TXT};   border: 1px solid #f8c4bd; }}
    .kpi-saldo   {{ background: linear-gradient(135deg, {COR_SALDO} 0%, #2c3b5e 100%); color: {COR_SALDO_TXT}; border: 1px solid {COR_SALDO}; }}

    .mini-card {{
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 12px 16px;
    }}
    .mini-title {{
        font-size: 0.75rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .mini-value {{
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a;
    }}
    .mini-sub {{ font-size: 0.75rem; color: #94a3b8; }}
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
@st.cache_data(ttl=300, show_spinner="Carregando lançamentos...")
def carregar_dados():
    with get_db_session() as session:
        repo = ExtratoRepository(session)
        df = repo.get_dataframe()
        cat_repo = CategoriaRepository(session)
        categorias = [c.nome for c in cat_repo.get_todas_categorias()]
    return df, categorias


def recarregar():
    """Limpa o cache de dados e reexecuta o app (após alterações no banco)."""
    carregar_dados.clear()
    st.rerun()


def kpi_card(classe: str, titulo: str, valor: float, media: float, meses: int) -> str:
    return f"""
    <div class="kpi-card {classe}">
        <div class="kpi-title">{titulo}</div>
        <div class="kpi-value">{Formatter.moeda(valor)}</div>
        <div class="kpi-sub">Média Mensal: <b>{Formatter.moeda(media)}</b> · {meses} {'mês' if meses == 1 else 'meses'}</div>
    </div>
    """


def mini_card(titulo: str, valor: str, sub: str = "") -> str:
    return f"""
    <div class="mini-card">
        <div class="mini-title">{titulo}</div>
        <div class="mini-value">{valor}</div>
        <div class="mini-sub">{sub}</div>
    </div>
    """


def layout_base(fig: go.Figure, altura: int) -> go.Figure:
    fig.update_layout(
        height=altura,
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        separators=",.",
        font=dict(family="Inter, sans-serif"),
    )
    fig.update_yaxes(tickprefix="R$ ", gridcolor="#eef2f7")
    return fig


df_raw, lista_categorias = carregar_dados()

if df_raw.empty:
    st.warning("⚠️ Nenhuma transação encontrada no banco de dados. Execute o ETL ou verifique a conexão.")
    st.stop()

# ==============================================================================
# Barra Lateral (Filtros Globais e Ações)
# ==============================================================================
st.sidebar.markdown("### 🏦 **Filtros**")

bancos_disponiveis = sorted(df_raw['banco'].unique().tolist())
bancos_selecionados = st.sidebar.multiselect(
    "Instituições Bancárias:",
    options=bancos_disponiveis,
    default=bancos_disponiveis
)

anos_disponiveis = sorted(df_raw['ano'].unique().tolist(), reverse=True)
ano_selecionado = st.sidebar.selectbox("Ano (Visão Geral):", options=anos_disponiveis, index=0)

df_bancos = df_raw[df_raw['banco'].isin(bancos_selecionados)].copy()
df_ano = df_bancos[df_bancos['ano'] == ano_selecionado].copy()

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚡ **Ações Rápidas**")

col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    if st.button("🔄 Classificar", width="stretch", help="Categoriza transações pendentes"):
        with get_db_session() as session:
            res = CategorizationService(session).categorizar_transacoes_pendentes(forcar=False)
        st.toast(f"Classificados: {res['novos_categorizados']}")
        recarregar()

with col_b2:
    if st.button("⚠️ Reclassificar", width="stretch", help="Reclassifica todas as transações com novas regras"):
        with get_db_session() as session:
            res = CategorizationService(session).categorizar_transacoes_pendentes(forcar=True)
        st.toast(f"Reclassificados: {res['novos_categorizados']}")
        recarregar()

# ------------------------------------------------------------------------------
# Agregações do ano selecionado (usadas na Visão Geral e no Excel)
# ------------------------------------------------------------------------------
receitas_ano = df_ano[df_ano['tipo'] == 'RECEITA']
despesas_ano = df_ano[df_ano['tipo'] == 'DESPESA']

rec_mes = receitas_ano.groupby('mes')['valor'].sum()
desp_mes = despesas_ano.groupby('mes')['valor_abs'].sum()

df_mensal = pd.DataFrame({'mes': range(1, 13)})
df_mensal['Receitas'] = df_mensal['mes'].map(rec_mes).fillna(0.0)
df_mensal['Gastos'] = df_mensal['mes'].map(desp_mes).fillna(0.0)
df_mensal['Saldo'] = df_mensal['Receitas'] - df_mensal['Gastos']
df_mensal['Mês'] = df_mensal['mes'].apply(lambda m: MESES_ABREV[m - 1])

total_receitas = float(df_mensal['Receitas'].sum())
total_gastos = float(df_mensal['Gastos'].sum())
saldo_total = total_receitas - total_gastos

# Média mensal considera apenas os meses com movimentação (evita distorção em anos parciais)
meses_com_dados = max(int(df_ano['mes'].nunique()), 1)

df_cat_ano = (
    despesas_ano.groupby('categoria')
    .agg(total=('valor_abs', 'sum'), qtd=('id', 'count'))
    .reset_index()
    .sort_values(by='total', ascending=False)
)

# Exportação Excel (gerada em memória a partir dos dados já filtrados)
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
    pd.DataFrame([
        {"Indicador": "Ano", "Valor": ano_selecionado},
        {"Indicador": "Bancos", "Valor": ", ".join(bancos_selecionados)},
        {"Indicador": "Total Receitas (R$)", "Valor": round(total_receitas, 2)},
        {"Indicador": "Total Gastos (R$)", "Valor": round(total_gastos, 2)},
        {"Indicador": "Saldo Total (R$)", "Valor": round(saldo_total, 2)},
        {"Indicador": "Meses com movimentação", "Valor": meses_com_dados},
    ]).to_excel(writer, sheet_name='Resumo', index=False)
    df_mensal[['Mês', 'Receitas', 'Gastos', 'Saldo']].to_excel(writer, sheet_name='Mensal', index=False)
    df_cat_ano.rename(columns={'categoria': 'Categoria', 'total': 'Total (R$)', 'qtd': 'Qtd'}) \
        .to_excel(writer, sheet_name='Categorias', index=False)
    df_ano.drop(columns=['ano_mes'], errors='ignore').to_excel(writer, sheet_name='Extrato', index=False)

st.sidebar.markdown("---")
st.sidebar.download_button(
    label=f"📥 Baixar Relatório {ano_selecionado} (.xlsx)",
    data=excel_buffer.getvalue(),
    file_name=f"relatorio_financeiro_{ano_selecionado}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    width="stretch"
)
st.sidebar.caption("💡 Base conectada ao PostgreSQL: **financeiro**")

# ==============================================================================
# Cabeçalho
# ==============================================================================
st.title("💳 Painel Financeiro")

tab_visao, tab_diario = st.tabs(["📊 Visão Geral", "📅 Gastos por Dia"])

# ------------------------------------------------------------------------------
# ABA 1: VISÃO GERAL (métricas anuais)
# ------------------------------------------------------------------------------
with tab_visao:
    st.caption(
        f"Ano de **{ano_selecionado}** · Bancos: `{'`, `'.join(bancos_selecionados) or 'nenhum'}`"
    )

    # Cartões de KPI
    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(kpi_card("kpi-receita", "💵 Receitas", total_receitas,
                             total_receitas / meses_com_dados, meses_com_dados), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi_card("kpi-gasto", "💸 Gastos", total_gastos,
                             total_gastos / meses_com_dados, meses_com_dados), unsafe_allow_html=True)
    with k3:
        st.markdown(kpi_card("kpi-saldo", "⚖️ Saldo Total", saldo_total,
                             saldo_total / meses_com_dados, meses_com_dados), unsafe_allow_html=True)

    st.markdown("<div style='height: 18px'></div>", unsafe_allow_html=True)

    if df_ano.empty:
        st.info("Sem movimentações para o ano e bancos selecionados.")
    else:
        col_esq, col_dir = st.columns([6, 4])

        with col_esq:
            # Gráfico 1: Receitas x Gastos
            with st.container(border=True):
                st.markdown("##### Receitas x Gastos")
                fig_rg = go.Figure()
                fig_rg.add_trace(go.Bar(
                    x=df_mensal['Mês'], y=df_mensal['Receitas'], name='Receitas',
                    marker_color=COR_RECEITA, marker_cornerradius=4,
                    hovertemplate='%{x}<br>Receitas: R$ %{y:,.2f}<extra></extra>'
                ))
                fig_rg.add_trace(go.Bar(
                    x=df_mensal['Mês'], y=df_mensal['Gastos'], name='Gastos',
                    marker_color=COR_GASTO, marker_cornerradius=4,
                    hovertemplate='%{x}<br>Gastos: R$ %{y:,.2f}<extra></extra>'
                ))
                fig_rg.update_layout(barmode='group', bargap=0.25, bargroupgap=0.08)
                fig_rg.update_xaxes(categoryorder='array', categoryarray=MESES_ABREV)
                st.plotly_chart(layout_base(fig_rg, 320), width="stretch")

            # Gráfico 2: Saldo Mensal
            with st.container(border=True):
                st.markdown("##### Saldo Mensal")
                fig_saldo = go.Figure(go.Bar(
                    x=df_mensal['Mês'], y=df_mensal['Saldo'], name='Saldo',
                    marker_color=COR_SALDO, marker_cornerradius=4,
                    hovertemplate='%{x}<br>Saldo: R$ %{y:,.2f}<extra></extra>'
                ))
                fig_saldo.add_hline(y=0, line_width=1, line_color="#94a3b8")
                fig_saldo.update_layout(showlegend=False, bargap=0.35)
                fig_saldo.update_xaxes(categoryorder='array', categoryarray=MESES_ABREV)
                st.plotly_chart(layout_base(fig_saldo, 280), width="stretch")

        with col_dir:
            # Gráfico 3: Gastos por Categoria
            with st.container(border=True):
                st.markdown("##### Gastos por Categoria")
                if df_cat_ano.empty:
                    st.info("Nenhum gasto no período.")
                else:
                    df_cat_plot = df_cat_ano.sort_values(by='total', ascending=True)  # maior no topo
                    fig_cat = go.Figure(go.Bar(
                        x=df_cat_plot['total'], y=df_cat_plot['categoria'], orientation='h',
                        marker_color=COR_GASTO, marker_cornerradius=4,
                        text=df_cat_plot['total'].apply(Formatter.moeda),
                        textposition='auto', insidetextanchor='end',
                        customdata=df_cat_plot['qtd'],
                        hovertemplate='<b>%{y}</b><br>Total: R$ %{x:,.2f}<br>%{customdata} lançamentos<extra></extra>'
                    ))
                    fig_cat.update_layout(showlegend=False, bargap=0.3)
                    layout_base(fig_cat, 676)
                    fig_cat.update_yaxes(tickprefix="")
                    fig_cat.update_xaxes(tickprefix="R$ ", gridcolor="#eef2f7")
                    st.plotly_chart(fig_cat, width="stretch")

# ------------------------------------------------------------------------------
# ABA 2: GASTOS POR DIA
# ------------------------------------------------------------------------------
with tab_diario:
    f1, f2, _ = st.columns([1, 1, 3])
    with f1:
        idx_ano = anos_disponiveis.index(ano_selecionado) if ano_selecionado in anos_disponiveis else 0
        ano_dia = st.selectbox("Ano:", options=anos_disponiveis, index=idx_ano, key="ano_dia")

    meses_disponiveis = sorted(df_bancos[df_bancos['ano'] == ano_dia]['mes'].unique().tolist())
    if not meses_disponiveis:
        meses_disponiveis = list(range(1, 13))
    with f2:
        mes_dia = st.selectbox(
            "Mês:",
            options=meses_disponiveis,
            index=len(meses_disponiveis) - 1,  # mês mais recente com dados
            format_func=lambda m: MESES_NOME[m - 1],
            key="mes_dia"
        )

    df_mes = df_bancos[(df_bancos['ano'] == ano_dia) & (df_bancos['mes'] == mes_dia)].copy()
    desp_mes_df = df_mes[df_mes['tipo'] == 'DESPESA'].copy()

    # Série diária com todos os dias do mês (dias sem gasto = 0)
    dias_no_mes = calendar.monthrange(int(ano_dia), int(mes_dia))[1]
    gasto_dia = desp_mes_df.groupby(desp_mes_df['data'].dt.day)['valor_abs'].sum()
    df_dia = pd.DataFrame({'dia': range(1, dias_no_mes + 1)})
    df_dia['Gastos'] = df_dia['dia'].map(gasto_dia).fillna(0.0)
    df_dia['data'] = pd.Timestamp(year=int(ano_dia), month=int(mes_dia), day=1) + \
        pd.to_timedelta(df_dia['dia'] - 1, unit='D')

    total_mes = float(df_dia['Gastos'].sum())
    dias_com_gasto = int((df_dia['Gastos'] > 0).sum())
    media_diaria = total_mes / dias_no_mes
    dia_pico = df_dia.loc[df_dia['Gastos'].idxmax()] if total_mes > 0 else None

    m1, m2, m3, m4 = st.columns(4)
    m1.markdown(mini_card("Total gasto no mês", Formatter.moeda(total_mes),
                          f"{len(desp_mes_df)} lançamentos"), unsafe_allow_html=True)
    m2.markdown(mini_card("Média diária", Formatter.moeda(media_diaria),
                          f"{dias_no_mes} dias corridos"), unsafe_allow_html=True)
    m3.markdown(mini_card("Dias com gasto", f"{dias_com_gasto}",
                          f"de {dias_no_mes} dias"), unsafe_allow_html=True)
    m4.markdown(mini_card(
        "Dia de maior gasto",
        Formatter.moeda(dia_pico['Gastos']) if dia_pico is not None else "-",
        Formatter.data(dia_pico['data']) if dia_pico is not None else "sem gastos"
    ), unsafe_allow_html=True)

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    # Gráfico de evolução diária
    with st.container(border=True):
        st.markdown(f"##### Gastos diários · {MESES_NOME[mes_dia - 1]} de {ano_dia}")
        fig_dia = go.Figure()
        fig_dia.add_trace(go.Bar(
            x=df_dia['data'], y=df_dia['Gastos'], name='Gasto do dia',
            marker_color=COR_GASTO, marker_cornerradius=3,
            hovertemplate='%{x|%d/%m/%Y}<br>Gastos: R$ %{y:,.2f}<extra></extra>'
        ))
        fig_dia.add_trace(go.Scatter(
            x=df_dia['data'], y=df_dia['Gastos'].cumsum(), name='Acumulado no mês',
            mode='lines', line=dict(color=COR_SALDO, width=2), yaxis='y2',
            hovertemplate='%{x|%d/%m/%Y}<br>Acumulado: R$ %{y:,.2f}<extra></extra>'
        ))
        if total_mes > 0:
            fig_dia.add_hline(
                y=media_diaria, line_dash="dash", line_color="#94a3b8",
                annotation_text=f"Média {Formatter.moeda(media_diaria)}", annotation_position="top left"
            )
        layout_base(fig_dia, 380)
        fig_dia.update_layout(
            hovermode="x unified",
            yaxis2=dict(overlaying='y', side='right', showgrid=False, tickprefix="R$ ", rangemode='tozero'),
        )
        fig_dia.update_xaxes(tickformat="%d", dtick=86400000.0)
        st.plotly_chart(fig_dia, width="stretch")

    # Detalhamento das despesas
    st.markdown("##### 📑 Despesas do período")
    d1, d2 = st.columns([2, 2])
    with d1:
        busca = st.text_input("🔍 Buscar na descrição:", placeholder="Ex: Pix, Mercado, Uber...", key="busca_dia")
    with d2:
        cats_mes = sorted(desp_mes_df['categoria'].unique().tolist())
        cats_sel = st.multiselect("Categorias:", options=cats_mes, default=[], placeholder="Todas", key="cats_dia")

    df_tabela = desp_mes_df
    if busca:
        df_tabela = df_tabela[df_tabela['descricao'].str.contains(busca, case=False, na=False, regex=False)]
    if cats_sel:
        df_tabela = df_tabela[df_tabela['categoria'].isin(cats_sel)]

    colunas = ['data', 'banco', 'descricao', 'categoria', 'valor_abs', 'observacao']
    df_tabela = df_tabela[[c for c in colunas if c in df_tabela.columns]].sort_values(by='data', ascending=False)

    st.dataframe(
        df_tabela,
        hide_index=True,
        width="stretch",
        height=420,
        column_config={
            'data': st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            'banco': st.column_config.TextColumn("Banco"),
            'descricao': st.column_config.TextColumn("Descrição", width="large"),
            'categoria': st.column_config.TextColumn("Categoria"),
            'valor_abs': st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f"),
            'observacao': st.column_config.TextColumn("Observação"),
        }
    )
    st.caption(f"{len(df_tabela)} registros · Total: **{Formatter.moeda(df_tabela['valor_abs'].sum())}**")

    st.download_button(
        "📥 Baixar despesas do mês (CSV)",
        data=df_tabela.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name=f"despesas_{ano_dia}_{mes_dia:02d}.csv",
        mime="text/csv",
        key="csv_dia"
    )

    # Reclassificação manual (restrita aos lançamentos do mês selecionado)
    with st.expander("⚙️ Reclassificar manualmente um lançamento deste mês"):
        st.caption("Classificações manuais têm precedência e não são sobrescritas pelas regras automáticas.")
        opcoes = df_mes.sort_values(by='data', ascending=False)
        if opcoes.empty:
            st.info("Nenhum lançamento neste mês.")
        else:
            labels = {
                r.hash_transacao: f"[{Formatter.data(r.data)}] ({r.banco}) {str(r.descricao)[:40]} | "
                                  f"{Formatter.moeda(r.valor)} [Atual: {r.categoria}]"
                for r in opcoes.itertuples()
            }
            r1, r2 = st.columns([3, 2])
            with r1:
                item_sel = st.selectbox("Lançamento:", options=list(labels.keys()),
                                        format_func=lambda h: labels[h], key="reclass_item")
            with r2:
                nova_cat = st.selectbox("Nova categoria:", options=lista_categorias, key="reclass_cat")
            obs_manual = st.text_input("Observação (opcional):", placeholder="Motivo da classificação manual",
                                       key="reclass_obs")

            if st.button("💾 Salvar nova categoria", type="primary", key="reclass_btn"):
                with get_db_session() as session:
                    sucesso = CategorizationService(session).categorizar_manualmente(
                        hash_transacao=item_sel,
                        nome_categoria=nova_cat,
                        observacao=obs_manual or "Reclassificação manual via dashboard"
                    )
                if sucesso:
                    st.toast(f"Lançamento atualizado para '{nova_cat}'.")
                    recarregar()
                else:
                    st.error("Erro ao atualizar lançamento.")
