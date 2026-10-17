# 📊 Sistema de Análise Financeira & Dashboard de Extratos Bancários

Sistema em **Python**, **Streamlit**, **Plotly**, **Pandas** e **SQLAlchemy** para consolidação analítica, categorização inteligente e visualização financeira de extratos bancários unificados (**Itaú** e **Mercado Pago**).

O projeto é conectado diretamente à base de dados PostgreSQL populada pelo pipeline de extração (`etl-bancos-extratos`), organizando as informações em uma arquitetura orientada a serviços (**SOA**) e apresentando um painel interativo moderno para acompanhamento de despesas, receitas, fluxo de caixa e taxa de poupança.

---

## 🏗️ Arquitetura do Projeto

```text
analise-extrato-bancos/
│
├── Conn/                           # Camada de Conexão com Banco de Dados
│   ├── __init__.py
│   └── Database.py                 # Singleton de conexão SQLAlchemy e context manager get_db_session
│
├── Models/                         # Modelos ORM (SQLAlchemy) e DTOs
│   ├── __init__.py
│   ├── Conta.py                    # Mapeamento da tabela 'contas'
│   ├── ExtratoItau.py              # Mapeamento ORM da tabela 'extrato_itau'
│   ├── ExtratoMercadoPago.py       # Mapeamento ORM da tabela 'extrato_mercado_pago'
│   ├── Categoria.py                # Mapeamento da tabela 'categorias' (ícone, cor, tipo)
│   ├── RegraCategorizacao.py       # Regras de classificação ('contem', 'regex', 'comeca_com', prioridade)
│   ├── LancamentoCategorizado.py   # Associação persistida entre transação e categoria (manual/auto)
│   └── LancamentoDTO.py            # Dataclass normalizado para transações unificadas de múltiplos bancos
│
├── Repositories/                   # Camada de Acesso a Dados
│   ├── __init__.py
│   ├── ExtratoRepository.py        # Consolidação polimórfica de extratos e conversão para DataFrame
│   └── CategoriaRepository.py      # CRUD de categorias, regras e mapa em memória O(1) de categorizações
│
├── Services/                       # Camada de Regras de Negócio e Cálculos
│   ├── __init__.py
│   ├── CategorizationService.py    # Motor de classificação automática por regras/regex e manual
│   ├── ExpenseAnalysisService.py   # Agregações financeiras (KPIs, categorias, evolução mensal, maiores gastos)
│   └── ReportService.py            # Utilitário para tabelas no terminal (tabulate) e exportador Excel multi-abas
│
├── Util/                           # Utilitários Globais
│   ├── __init__.py
│   └── Formatter.py                # Formatação de moedas (R$), datas, percentuais e barras ASCII
│
├── relatorios/                     # Diretório para saída de planilhas Excel (.xlsx) exportadas
├── main.py                         # Aplicação Principal: Dashboard Web Interativo (Streamlit)
├── requirements.txt                # Lista de dependências do projeto
├── .env.example                    # Modelo com as variáveis de ambiente necessárias
└── .env                            # Configurações de credenciais e host do banco de dados (ignorado no git)
```

---

## ⚡ Funcionalidades Principais

### 1. Unificação Polimórfica de Extratos
- Consolida dados do **Itaú** (`extrato_itau`) e **Mercado Pago** (`extrato_mercado_pago`) sob uma interface unificada (`LancamentoDTO`).
- Normalização de tipos (`RECEITA` e `DESPESA`), valores absolutos e ordenação cronológica.
- Conversão direta em `pandas.DataFrame` otimizado para análises de alto desempenho.

### 2. Motor de Categorização Inteligente
- **Classificação Automática**: Avalia a descrição de cada transação contra regras pré-definidas ordenadas por prioridade.
- **Tipos de Casamento**: Suporte a padrões do tipo `contem`, `regex`, `comeca_com` (`starts_with`) e correspondência exata (`equals`).
- **Categorias Nativas**: Rendimentos & Investimentos, Transferências & Pix Recebidos, Transferências & Pix Enviados, Cartão de Crédito, Alimentação & Supermercado, Moradia & Contas, Compras & Eletrônicos, Transporte & Mobilidade, Serviços & Assinaturas, Saúde & Farmácia, Lazer & Viagens e Outros / Diversos.
- **Precedência Manual**: Classificações realizadas manualmente pelo usuário no painel têm precedência permanente e não são sobrescritas em reprocessamentos automáticos.

### 3. Painel Web Moderno (Streamlit + Plotly)
- **KPI Cards em Tempo Real**: Receitas Totais, Despesas Totais, Saldo Líquido, Taxa de Poupança (%) e Contagem de Operações.
- **Filtros Dinâmicos**: Filtro multi-seleção de bancos e intervalo customizável de datas (date picker).
- **Ações Rápidas na Barra Lateral**:
  - `🔄 Classificar`: Processa apenas lançamentos novos/pendentes de categoria.
  - `⚠️ Reclassificar`: Reprocessa todas as transações aplicando as regras ativas mais recentes (preservando manuais).
  - `📥 Baixar Relatório Excel (.xlsx)`: Gera e faz download imediato da planilha multi-abas consolidada.

### 4. Abas Analíticas do Dashboard
1. **📊 Visão Geral**:
   - Gráfico mensal de fluxo (barras emparelhadas de Receitas e Despesas + linha de Saldo Líquido).
   - Gráfico de rosca (*Donut Chart*) com a distribuição percentual das despesas por categoria.
2. **🏷️ Gastos por Categoria**:
   - Ranking visual em gráfico de barras horizontais com cores personalizadas por categoria.
   - Tabela analítica com Total (R$), Quantidade de transações, Ticket Médio e % sobre despesas.
   - Ferramenta de **Drill-down**: Inspecione todas as transações individuais de qualquer categoria selecionada.
3. **📅 Fluxo & Evolução Temporal**:
   - Curva acumulada de fluxo de caixa e poupança ao longo dos meses.
   - Tabela comparativa mês a mês com taxa de poupança calculada.
4. **🔝 Maiores Gastos**:
   - Slider interativo para selecionar o ranking desejado (Top 5 a Top 50).
   - Visualização gráfica e tabela detalhada das maiores despesas do período.
5. **📑 Extrato Completo & Busca**:
   - Busca textual instantânea na descrição com filtros combinados por tipo (`RECEITA`/`DESPESA`) e categoria.
   - Tabela paginada com ordenação cronológica.
   - Botão para exportação direta do resultado filtrado para **CSV**.
6. **⚙️ Reclassificação Manual**:
   - Seleção interativa de qualquer transação registrada com resumo de data, banco, valor e descrição.
   - Atribuição de nova categoria e campo opcional de observação com salvamento direto no PostgreSQL.

---

## 🗄️ Estrutura do Banco de Dados (PostgreSQL)

O sistema opera no schema configurado (padrão: `financeiro`), utilizando as seguintes tabelas:

| Tabela | Responsabilidade |
| :--- | :--- |
| `contas` | Cadastro das contas bancárias integradas (agência, conta, titular, banco). |
| `extrato_itau` | Transações brutas importadas da conta corrente Itaú. |
| `extrato_mercado_pago` | Transações brutas extraídas da conta digital Mercado Pago. |
| `categorias` | Cadastro de categorias financeiras (nome, cor em hexadecimal, ícone e tipo padrão). |
| `regras_categorizacao` | Padrões de texto/regex associados a categorias com pesos de prioridade. |
| `lancamentos_categorizados` | Registros de relacionamento entre o hash da transação e a categoria atribuída (com flag de manual). |

---

## 🚀 Como Executar

### 1. Pré-requisitos
- **Python 3.10+** (recomendado 3.11 ou 3.12)
- PostgreSQL com as tabelas de extrato já populadas pelo pipeline de ETL.

### 2. Configurar o Ambiente Virtual
No terminal (PowerShell no Windows):

```powershell
# Criar o ambiente virtual (se ainda não existir)
python -m venv venv

# Ativar o ambiente virtual
.\venv\Scripts\Activate.ps1

# Instalar todas as dependências
pip install -r requirements.txt
```

### 3. Configurar o Arquivo `.env`
Crie ou edite o arquivo `.env` na raiz do projeto com os dados do seu banco:

```ini
DB_HOST=192.168.1.150
DB_PORT=5432
DB_DATABASE=sistemas
DB_USERNAME=local
DB_PASSWORD=sua_senha_aqui
DB_SCHEMA=financeiro
```

### 4. Iniciar o Dashboard Web
Execute o comando abaixo no terminal com a venv ativada:

```powershell
streamlit run main.py
```

O Streamlit iniciará o servidor local e abrirá automaticamente no navegador no endereço:
👉 **`http://localhost:8501`**

---

## 📦 Exportação de Relatórios

O sistema oferece duas modalidades de exportação de dados:

1. **Planilha Excel (.xlsx) Multi-Abas**:
   - Pode ser baixada diretamente pela barra lateral do Dashboard.
   - Abas incluídas:
     - `Resumo`: Indicadores gerais (Receitas, Despesas, Saldo Líquido, Poupança).
     - `Categorias`: Tabela agregada por categoria.
     - `Evolução Mensal`: Comparativo mês a mês.
     - `Maiores Gastos`: As 50 maiores saídas financeiras.
     - `Por Banco`: Volume e distribuição por instituição financeira.
     - `Extrato Filtrado`: Base de lançamentos conforme os filtros selecionados.
2. **Exportação CSV**:
   - Disponível na aba **Extrato Completo & Busca** para download instantâneo dos registros filtrados.

---

## 🧩 Extensibilidade

- **Adicionar Novos Bancos**: Crie o modelo ORM correspondente em `Models/` e adicione a leitura unificada no método `get_lancamentos_unificados` em `Repositories/ExtratoRepository.py`.
- **Novas Regras de Categorização**: Novas regras podem ser inseridas via banco de dados na tabela `regras_categorizacao` ou adicionadas na lista base em `CategoriaRepository.inicializar_padroes`.
