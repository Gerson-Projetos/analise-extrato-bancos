# 📊 Sistema de Análise Financeira & Dashboard de Extratos Bancários

Sistema em **Python**, **Streamlit**, **Plotly**, **Pandas** e **SQLAlchemy** para consolidação analítica, categorização inteligente e visualização financeira de extratos bancários unificados (**Itaú** e **Mercado Pago**).

O projeto é conectado diretamente à base de dados PostgreSQL populada pelo pipeline de extração (`etl-bancos-extratos`), organizando as informações em uma arquitetura orientada a serviços (**SOA**) e apresentando um painel interativo moderno para acompanhamento anual de receitas, gastos e saldo, além da evolução diária das despesas de cada mês.

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
```

---

## ⚡ Funcionalidades Principais

### 1. Unificação Polimórfica de Extratos
- Consolida dados do **Itaú** (`extrato_itau`) e **Mercado Pago** (`extrato_mercado_pago`) sob uma interface unificada (`LancamentoDTO`).
- Normalização de tipos (`RECEITA` e `DESPESA`), valores absolutos e ordenação cronológica.
- Conversão direta em `pandas.DataFrame` otimizado para análises de alto desempenho.

### 2. Motor de Categorização Inteligente & Conciliação entre Bancos
- **Conciliação Bidirecional (Itaú <-> Mercado Pago)**: Cruza datas e valores das transferências de mesma titularidade entre os bancos, classificando as duas pontas como `Transferência entre Contas` (tipo `TRANSFERENCIA`) para evitar a duplicação artificial de receitas e despesas operacionais.
- **Identificação Automática de Investimentos (Clear Corretora & Nomad)**: Transferências para a mesma titularidade que não entraram no Mercado Pago são automaticamente identificadas e classificadas na categoria dedicada `Investimentos` (Aportes Clear Corretora ou Nomad).
- **Classificação Automática por Regras**: Avalia a descrição de cada transação contra regras pré-definidas ordenadas por prioridade (`contem`, `regex`, `comeca_com`, `equals`).
- **Categorias Nativas**: Investimentos, Transferência entre Contas, Rendimentos & Investimentos, Transferências & Pix Recebidos, Transferências & Pix Enviados, Cartão de Crédito, Alimentação & Supermercado, Moradia & Contas, Compras & Eletrônicos, Transporte & Mobilidade, Serviços & Assinaturas, Saúde & Farmácia, Lazer & Viagens e Outros / Diversos.
- **Precedência Manual**: Classificações manuais têm precedência permanente e não são sobrescritas em reclassificações automáticas.

### 3. Painel Web Moderno (Streamlit + Plotly)
- **Paleta Visual Unificada**: Verde para receitas, coral para gastos e azul-marinho para saldo, compartilhada entre cartões e gráficos.
- **Filtros Globais na Barra Lateral**:
  - Multi-seleção de **Instituições Bancárias**.
  - Seleção do **Ano** analisado na Visão Geral (padrão: ano mais recente).
- **Ações Rápidas na Barra Lateral**:
  - `🔄 Classificar`: Processa apenas lançamentos novos/pendentes de categoria.
  - `⚠️ Reclassificar`: Reprocessa todas as transações aplicando as regras ativas mais recentes (preservando manuais).
  - `📥 Baixar Relatório {ano} (.xlsx)`: Gera em memória e baixa a planilha multi-abas do ano selecionado.
- **Cache de Dados**: Lançamentos em cache por 5 minutos (`st.cache_data`), invalidado automaticamente após classificações.

### 4. Abas do Dashboard
1. **📊 Visão Geral (métricas anuais)**:
   - **Cartões de KPI**: Receitas, Gastos e Saldo Total do ano, cada um com a **Média Mensal** (calculada apenas sobre os meses com movimentação, evitando distorção em anos parciais).
   - **Grid de gráficos**:
     - *Receitas x Gastos*: barras agrupadas por mês (Jan–Dez).
     - *Saldo Mensal*: barras do saldo de cada mês com linha de referência no zero.
     - *Gastos por Categoria*: ranking em barras horizontais com valor total e quantidade de lançamentos no hover.
2. **📅 Gastos por Dia**:
   - Filtro próprio de **Ano** e **Mês** (padrão: mês mais recente com dados).
   - **Mini-cards**: Total gasto no mês, Média diária, Dias com gasto e Dia de maior gasto.
   - **Gráfico de evolução diária**: barras de gasto por dia (incluindo dias sem gasto), linha de **acumulado no mês** (eixo secundário) e linha tracejada da média diária.
   - **Detalhamento das despesas**: busca textual na descrição e filtro multi-seleção de categorias, com total dos registros filtrados.
   - Exportação das despesas filtradas do mês para **CSV**.
   - **⚙️ Reclassificação manual** (expansível): seleciona um lançamento do mês, atribui nova categoria e observação opcional, salvando direto no PostgreSQL.

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

## 🐳 Execução via Docker

O projeto possui duas configurações prontas para Docker Compose:

### Cenário A: Conectar em Banco Separado / Existente
Utilize quando o PostgreSQL já estiver rodando em outro servidor, container separado ou no próprio host (`192.168.x.x` ou `host.docker.internal`).

1. Configure seu `.env` com os dados do banco externo (exemplo no [.env.docker.example](file:///d:/projetos-local/analise-extrato-bancos/.env.docker.example)).
2. Inicie o container da aplicação:
```powershell
docker compose up -d --build
```
3. Acesse o painel em **`http://localhost:8501`**.

Para parar o container:
```powershell
docker compose down
```

---

### Cenário B: Criando o Container com o Banco Necessário
Utilize quando desejar subir tanto o **PostgreSQL** quanto a **aplicação** de forma totalmente isolada e automática.

1. Inicie a stack completa:
```powershell
docker compose -f docker-compose.with-db.yml up -d --build
```
> O container do PostgreSQL inicializa automaticamente o schema `financeiro` e define persistência em volume Docker (`analise_extrato_postgres_data`). A porta `5432` fica exposta para conexões externas (DBeaver, scripts ETL, etc.).

2. Acesse o painel em **`http://localhost:8501`**.

Para parar os containers mantendo os dados salvos:
```powershell
docker compose -f docker-compose.with-db.yml down
```

---

## 📦 Exportação de Relatórios

O sistema oferece duas modalidades de exportação de dados:

1. **Planilha Excel (.xlsx) Multi-Abas**:
   - Baixada pela barra lateral, considerando o **ano** e os **bancos** selecionados.
   - Abas incluídas:
     - `Resumo`: Ano, bancos, Total de Receitas, Total de Gastos, Saldo Total e meses com movimentação.
     - `Mensal`: Receitas, Gastos e Saldo de Jan a Dez.
     - `Categorias`: Total e quantidade de lançamentos de despesa por categoria.
     - `Extrato`: Todos os lançamentos do ano filtrado.
2. **Exportação CSV**:
   - Disponível na aba **Gastos por Dia** com as despesas do mês conforme busca/categorias aplicadas (separador `;`, codificação UTF-8 com BOM para abrir corretamente no Excel).

---

## 🧩 Extensibilidade

- **Adicionar Novos Bancos**: Crie o modelo ORM correspondente em `Models/` e adicione a leitura unificada no método `get_lancamentos_unificados` em `Repositories/ExtratoRepository.py`.
- **Novas Regras de Categorização**: Novas regras podem ser inseridas via banco de dados na tabela `regras_categorizacao` ou adicionadas na lista base em `CategoriaRepository.inicializar_padroes`.
