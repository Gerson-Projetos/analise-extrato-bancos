from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from Models.Categoria import Categoria
from Models.RegraCategorizacao import RegraCategorizacao
from Models.LancamentoCategorizado import LancamentoCategorizado

class CategoriaRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_todas_categorias(self) -> List[Categoria]:
        return self.session.query(Categoria).order_by(Categoria.nome).all()

    def get_categoria_por_nome(self, nome: str) -> Optional[Categoria]:
        cat = self.session.query(Categoria).filter(Categoria.nome.ilike(nome.strip())).first()
        if not cat and "outros" in nome.lower():
            cat = self.session.query(Categoria).filter(Categoria.nome.ilike("%outros%")).first()
        return cat

    def get_regras_ativas(self) -> List[RegraCategorizacao]:
        return (
            self.session.query(RegraCategorizacao)
            .filter(RegraCategorizacao.ativo.is_(True))
            .order_by(RegraCategorizacao.prioridade.desc())
            .all()
        )

    def get_mapa_categorizados(self) -> Dict[str, Categoria]:
        """Retorna dicionário {hash_transacao: Categoria} para acesso rápido O(1)."""
        resultados = (
            self.session.query(LancamentoCategorizado.hash_transacao, Categoria)
            .join(Categoria, LancamentoCategorizado.categoria_id == Categoria.id)
            .all()
        )
        return {r[0]: r[1] for r in resultados}

    def get_mapa_lancamentos(self) -> Dict[str, LancamentoCategorizado]:
        """Retorna dicionário {hash_transacao: LancamentoCategorizado} com Categoria carregada."""
        from sqlalchemy.orm import joinedload
        registros = (
            self.session.query(LancamentoCategorizado)
            .options(joinedload(LancamentoCategorizado.categoria))
            .all()
        )
        return {r.hash_transacao: r for r in registros}

    def limpar_categorizacoes_automaticas(self):
        """Remove classificações que não foram manuais para permitir reclassificação total."""
        self.session.query(LancamentoCategorizado).filter(LancamentoCategorizado.manual.is_(False)).delete()
        self.session.commit()

    def salvar_categorizacao(
        self,
        hash_transacao: str,
        categoria_id: int,
        banco: str = None,
        data_lancamento = None,
        valor: float = None,
        descricao: str = None,
        manual: bool = False,
        observacao: str = None
    ) -> LancamentoCategorizado:
        registro = (
            self.session.query(LancamentoCategorizado)
            .filter_by(hash_transacao=hash_transacao)
            .first()
        )
        if registro:
            registro.categoria_id = categoria_id
            registro.manual = manual
            if observacao:
                registro.observacao = observacao
            if banco:
                registro.banco = banco
            if data_lancamento:
                registro.data_lancamento = data_lancamento
            if valor is not None:
                registro.valor = valor
            if descricao:
                registro.descricao = descricao
        else:
            registro = LancamentoCategorizado(
                hash_transacao=hash_transacao,
                categoria_id=categoria_id,
                banco=banco,
                data_lancamento=data_lancamento,
                valor=valor,
                descricao=descricao,
                manual=manual,
                observacao=observacao
            )
            self.session.add(registro)
        return registro

    def inicializar_padroes(self):
        """Cadastra categorias e regras padrão no banco de dados se não existirem."""
        categorias_base = [
            ("Rendimentos & Investimentos", "Rendimentos automáticos, CDB, poupança, dividendos", "#2ECC71", "📈", "RECEITA"),
            ("Transferências & Pix Recebidos", "TEDs, DOCs e Pix recebidos de terceiros", "#3498DB", "📥", "RECEITA"),
            ("Transferências & Pix Enviados", "Pix e transferências enviadas a pessoas ou empresas", "#95A5A6", "📤", "DESPESA"),
            ("Cartão de Crédito", "Pagamento de fatura de cartão de crédito", "#8E44AD", "💳", "DESPESA"),
            ("Compras & Eletrônicos", "Mercado Livre, compras online, informática e utilidades", "#E67E22", "🛍️", "DESPESA"),
            ("Alimentação & Supermercado", "Supermercados, padarias, restaurantes, delivery e atacados", "#E74C3C", "🍔", "DESPESA"),
            ("Moradia & Contas", "Água, luz, condomínio, aluguel, gás e pagamentos de contas", "#9B59B6", "🏠", "DESPESA"),
            ("Transporte & Mobilidade", "Combustível, Uber, 99, estacionamento e pedágio", "#F1C40F", "🚗", "DESPESA"),
            ("Serviços & Assinaturas", "Streaming, software, assinaturas e planos de telefonia", "#1ABC9C", "💻", "DESPESA"),
            ("Saúde & Farmácia", "Farmácias, remédios, planos de saúde e consultas", "#E84393", "💊", "DESPESA"),
            ("Lazer & Viagens", "Cinemas, hotéis, viagens e passeios", "#00CEC9", "✈️", "DESPESA"),
            ("Investimentos", "Aportes e transferências para corretoras e contas de investimentos (Clear Corretora, Nomad, etc.)", "#16A085", "📈", "DESPESA"),
            ("Transferência entre Contas", "Transferências entre contas bancárias da mesma titularidade (Itaú <-> Mercado Pago)", "#95A5A6", "🔄", "TRANSFERENCIA"),
            ("Outros / Diversos", "Gastos gerais não classificados em outras categorias", "#7F8C8D", "🏷️", "DESPESA"),
        ]

        cat_objs = {}
        for nome, desc, cor, icone, tipo in categorias_base:
            cat = self.session.query(Categoria).filter_by(nome=nome).first()
            if not cat:
                cat = Categoria(
                    nome=nome,
                    descricao=desc,
                    cor_hex=cor,
                    icone=icone,
                    tipo_padrao=tipo
                )
                self.session.add(cat)
                self.session.flush()
            cat_objs[nome] = cat

        regras_base = [
            # Investimentos
            ("Investimentos", "NOMAD", "contem", 45),
            ("Investimentos", "CLEAR", "contem", 45),

            # Rendimentos
            ("Rendimentos & Investimentos", "Rendimento", "contem", 50),
            ("Rendimentos & Investimentos", "CDB", "contem", 50),
            ("Rendimentos & Investimentos", "Rendimentos", "contem", 50),
            ("Rendimentos & Investimentos", "Aplicacao", "contem", 40),

            # Transferências Recebidas
            ("Transferências & Pix Recebidos", "Pix recebido", "contem", 45),
            ("Transferências & Pix Recebidos", "TED recebida", "contem", 45),
            ("Transferências & Pix Recebidos", "DOC recebido", "contem", 45),
            ("Transferências & Pix Recebidos", "TED 001.4260", "contem", 45),

            # Cartão de Crédito
            ("Cartão de Crédito", "FATURA PAGA", "contem", 45),
            ("Cartão de Crédito", "Pagamento Cartão", "contem", 45),
            ("Cartão de Crédito", "Pagamento Cartao", "contem", 45),
            ("Cartão de Crédito", "Fatura Cartao", "contem", 45),

            # Transferências Enviadas / Pix
            ("Transferências & Pix Enviados", "Pix enviado", "contem", 40),
            ("Transferências & Pix Enviados", "PIX TRANSF", "contem", 40),
            ("Transferências & Pix Enviados", "QR Pix", "contem", 40),
            ("Transferências & Pix Enviados", "TED enviada", "contem", 40),

            # Compras
            ("Compras & Eletrônicos", "Mercado Livre", "contem", 35),
            ("Compras & Eletrônicos", "MercadoPago", "contem", 30),
            ("Compras & Eletrônicos", "Amazon", "contem", 35),
            ("Compras & Eletrônicos", "Shopee", "contem", 35),
            ("Compras & Eletrônicos", "Magalu", "contem", 35),

            # Alimentação
            ("Alimentação & Supermercado", "ASSAI", "contem", 35),
            ("Alimentação & Supermercado", "ATACADAO", "contem", 35),
            ("Alimentação & Supermercado", "RSHOP", "contem", 25),
            ("Alimentação & Supermercado", "Ifood", "contem", 35),
            ("Alimentação & Supermercado", "McDonalds", "contem", 35),
            ("Alimentação & Supermercado", "Burger", "contem", 35),
            ("Alimentação & Supermercado", "Restaurante", "contem", 30),
            ("Alimentação & Supermercado", "Supermercado", "contem", 35),
            ("Alimentação & Supermercado", "Padaria", "contem", 30),

            # Moradia & Contas
            ("Moradia & Contas", "Pagamento de conta", "contem", 30),
            ("Moradia & Contas", "EBANX", "contem", 30),
            ("Moradia & Contas", "Enel", "contem", 35),
            ("Moradia & Contas", "Sabesp", "contem", 35),
            ("Moradia & Contas", "Condominio", "contem", 35),

            # Transporte
            ("Transporte & Mobilidade", "Uber", "contem", 35),
            ("Transporte & Mobilidade", "99App", "contem", 35),
            ("Transporte & Mobilidade", "Posto", "contem", 30),
            ("Transporte & Mobilidade", "Gasolina", "contem", 30),

            # Serviços / Assinaturas
            ("Serviços & Assinaturas", "Netflix", "contem", 35),
            ("Serviços & Assinaturas", "Spotify", "contem", 35),
            ("Serviços & Assinaturas", "Google", "contem", 25),
            ("Serviços & Assinaturas", "Apple", "contem", 25),

            # Saúde
            ("Saúde & Farmácia", "Drogaria", "contem", 35),
            ("Saúde & Farmácia", "Farmacia", "contem", 35),
            ("Saúde & Farmácia", "Raia", "contem", 35),
            ("Saúde & Farmácia", "Drogasil", "contem", 35),
        ]

        for cat_nome, padrao, tipo, prio in regras_base:
            if cat_nome in cat_objs:
                regra_existente = self.session.query(RegraCategorizacao).filter_by(
                    categoria_id=cat_objs[cat_nome].id,
                    padrao=padrao
                ).first()
                if not regra_existente:
                    r = RegraCategorizacao(
                        categoria_id=cat_objs[cat_nome].id,
                        padrao=padrao,
                        tipo_padrao=tipo,
                        prioridade=prio
                    )
                    self.session.add(r)

        self.session.commit()

    # Aliases
    inicializar_categorias_padrao = inicializar_padroes
    get_mapa_categorizacoes_existentes = get_mapa_categorizados
