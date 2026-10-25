import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from Models.ExtratoItau import ExtratoItau
from Models.ExtratoMercadoPago import ExtratoMercadoPago
from Models.LancamentoCategorizado import LancamentoCategorizado
from Repositories.ExtratoRepository import ExtratoRepository
from Repositories.CategoriaRepository import CategoriaRepository

class CategorizationService:
    """Serviço responsável por classificar transações bancárias em categorias."""

    def __init__(self, session: Session):
        self.session = session
        self.extrato_repo = ExtratoRepository(session)
        self.cat_repo = CategoriaRepository(session)

    def inicializar_base(self):
        """Inicializa categorias e regras padrão no banco de dados se não existirem."""
        self.cat_repo.inicializar_padroes()

    def conciliar_transferencias_mesma_titularidade(self) -> Dict[str, int]:
        """
        Cruza as transações de mesma titularidade entre Itaú e Mercado Pago:
        - Se houver saída de mesma titularidade em um banco e entrada correspondente no outro (mesmo valor e +-3 dias):
          Classifica ambas as pontas como 'Transferência entre Contas'.
        - Se for saída de mesma titularidade no Itaú sem contraparte no Mercado Pago:
          Classifica como 'Investimentos' (Clear Corretora ou Nomad).
        - Para entradas restantes no Mercado Pago de mesma titularidade sem saída no Itaú:
          Classifica como 'Transferência entre Contas'.
        """
        self.inicializar_base()

        cat_transf = self.cat_repo.get_categoria_por_nome("Transferência entre Contas")
        cat_invest = self.cat_repo.get_categoria_por_nome("Investimentos")
        if not cat_transf or not cat_invest:
            self.cat_repo.inicializar_padroes()
            cat_transf = self.cat_repo.get_categoria_por_nome("Transferência entre Contas")
            cat_invest = self.cat_repo.get_categoria_por_nome("Investimentos")

        # Hashes com classificação manual preservadas
        hashes_manuais = {
            r[0] for r in self.session.query(LancamentoCategorizado.hash_transacao)
            .filter(LancamentoCategorizado.manual.is_(True))
            .all()
        }

        # 1. Candidatos de débito no Itaú com indicação de mesma titularidade
        itau_saidas = (
            self.session.query(ExtratoItau)
            .filter(ExtratoItau.valor < 0)
            .all()
        )
        candidatos_itau = []
        for it in itau_saidas:
            if it.hash_transacao in hashes_manuais:
                continue
            desc = (it.descricao or "").upper()
            if any(term in desc for term in ["GERSON", "GABRIEL", "MESMA", "TITULAR", "NOMAD", "CLEAR"]):
                candidatos_itau.append(it)

        # 2. Candidatos de crédito no Mercado Pago com indicação de mesma titularidade
        mp_entradas = (
            self.session.query(ExtratoMercadoPago)
            .filter(ExtratoMercadoPago.valor > 0)
            .all()
        )
        candidatos_mp_entradas = []
        for mp in mp_entradas:
            if mp.hash_transacao in hashes_manuais:
                continue
            desc = (mp.descricao or "").upper()
            if any(term in desc for term in ["GERSON", "GABRIEL", "MESMA", "TITULAR", "PIX RECEBIDO"]):
                candidatos_mp_entradas.append(mp)

        matched_mp_hashes = set()
        total_transf = 0
        total_invest = 0

        for it in candidatos_itau:
            it_val = abs(float(it.valor or 0))
            it_data = it.data_lancamento
            desc_upper = (it.descricao or "").upper()

            # Se for especificamente para Nomad
            if "NOMAD" in desc_upper:
                self.cat_repo.salvar_categorizacao(
                    hash_transacao=it.hash_transacao,
                    categoria_id=cat_invest.id,
                    banco="Itaú",
                    data_lancamento=it.data_lancamento,
                    valor=float(it.valor),
                    descricao=it.descricao,
                    manual=False,
                    observacao="Aporte Nomad (Conta Investimento Estrangeira)"
                )
                total_invest += 1
                continue

            # Busca contraparte correspondente no Mercado Pago (mesmo valor e janela de até 3 dias)
            match_mp = None
            for mp in candidatos_mp_entradas:
                if mp.hash_transacao in matched_mp_hashes:
                    continue
                mp_val = float(mp.valor or 0)
                mp_data = mp.data_lancamento
                diff_dias = abs((mp_data - it_data).days)
                if diff_dias <= 3 and abs(mp_val - it_val) < 0.01:
                    match_mp = mp
                    matched_mp_hashes.add(mp.hash_transacao)
                    break

            if match_mp:
                # Foi para o Mercado Pago -> Transferência entre Contas
                self.cat_repo.salvar_categorizacao(
                    hash_transacao=it.hash_transacao,
                    categoria_id=cat_transf.id,
                    banco="Itaú",
                    data_lancamento=it.data_lancamento,
                    valor=float(it.valor),
                    descricao=it.descricao,
                    manual=False,
                    observacao=f"Transferência entre contas: Itaú -> Mercado Pago ({match_mp.data_lancamento.strftime('%d/%m/%Y')})"
                )
                self.cat_repo.salvar_categorizacao(
                    hash_transacao=match_mp.hash_transacao,
                    categoria_id=cat_transf.id,
                    banco="Mercado Pago",
                    data_lancamento=match_mp.data_lancamento,
                    valor=float(match_mp.valor),
                    descricao=match_mp.descricao,
                    manual=False,
                    observacao=f"Transferência entre contas: recebido do Itaú ({it.data_lancamento.strftime('%d/%m/%Y')})"
                )
                total_transf += 2
            else:
                # Não entrou no Mercado Pago -> Foi para a Clear Corretora (Investimentos)
                self.cat_repo.salvar_categorizacao(
                    hash_transacao=it.hash_transacao,
                    categoria_id=cat_invest.id,
                    banco="Itaú",
                    data_lancamento=it.data_lancamento,
                    valor=float(it.valor),
                    descricao=it.descricao,
                    manual=False,
                    observacao="Aporte Clear Corretora (Investimentos - identificado por conciliação)"
                )
                total_invest += 1

        # Classifica entradas no Mercado Pago com titularidade GERSON restantes como transferência
        for mp in candidatos_mp_entradas:
            if mp.hash_transacao not in matched_mp_hashes and "GERSON" in (mp.descricao or "").upper():
                self.cat_repo.salvar_categorizacao(
                    hash_transacao=mp.hash_transacao,
                    categoria_id=cat_transf.id,
                    banco="Mercado Pago",
                    data_lancamento=mp.data_lancamento,
                    valor=float(mp.valor),
                    descricao=mp.descricao,
                    manual=False,
                    observacao="Transferência Mesma Titularidade (externa)"
                )
                total_transf += 1

        self.session.commit()
        return {"transferencias_entre_contas": total_transf, "investimentos_clear": total_invest}

    def categorizar_transacoes_pendentes(self, forcar: bool = False) -> Dict[str, Any]:
        """Aplica conciliação e regras ativas às transações pendentes (ou a todas se forcar=True)."""
        self.inicializar_base()

        if forcar:
            self.cat_repo.limpar_categorizacoes_automaticas()

        # 1. Executa a conciliação inteligente de mesma titularidade (Itaú <-> Mercado Pago e Clear)
        res_conciliacao = self.conciliar_transferencias_mesma_titularidade()

        # 2. Executa as regras de padrão/regex para as demais transações
        regras = self.cat_repo.get_regras_ativas()
        mapa_existente = self.cat_repo.get_mapa_categorizados()
        lancamentos = self.extrato_repo.get_lancamentos_unificados()

        total_processados = len(lancamentos)
        total_categorizados = res_conciliacao.get("transferencias_entre_contas", 0) + res_conciliacao.get("investimentos_clear", 0)

        cat_outros = self.cat_repo.get_categoria_por_nome("Outros / Diversos") or self.cat_repo.get_categoria_por_nome("Outros")

        for lanc in lancamentos:
            # Pula se já estiver categorizado
            if lanc.hash_transacao in mapa_existente:
                continue

            desc = (lanc.descricao or "").strip()
            desc_lower = desc.lower()

            matched_regra = None

            for regra in regras:
                padrao = (regra.padrao or "").strip().lower()
                if not padrao:
                    continue

                tipo_padrao = (regra.tipo_padrao or "contem").lower()

                if tipo_padrao == "regex":
                    try:
                        if re.search(regra.padrao, desc, re.IGNORECASE):
                            matched_regra = regra
                            break
                    except re.error:
                        continue
                elif tipo_padrao in ("starts_with", "comeca_com"):
                    if desc_lower.startswith(padrao):
                        matched_regra = regra
                        break
                elif tipo_padrao in ("equals", "exato"):
                    if desc_lower == padrao:
                        matched_regra = regra
                        break
                else:  # 'contem' por padrão
                    if padrao in desc_lower:
                        matched_regra = regra
                        break

            if matched_regra:
                self.cat_repo.salvar_categorizacao(
                    hash_transacao=lanc.hash_transacao,
                    categoria_id=matched_regra.categoria_id,
                    banco=lanc.banco,
                    data_lancamento=lanc.data_lancamento,
                    valor=lanc.valor,
                    descricao=lanc.descricao,
                    manual=False
                )
                total_categorizados += 1
            elif cat_outros:
                self.cat_repo.salvar_categorizacao(
                    hash_transacao=lanc.hash_transacao,
                    categoria_id=cat_outros.id,
                    banco=lanc.banco,
                    data_lancamento=lanc.data_lancamento,
                    valor=lanc.valor,
                    descricao=lanc.descricao,
                    manual=False,
                    observacao="Classificação padrão automática"
                )
                total_categorizados += 1

        self.session.commit()

        return {
            "total_processados": total_processados,
            "novos_categorizados": total_categorizados,
            "ja_categorizados": len(mapa_existente)
        }

    def categorizar_manualmente(self, hash_transacao: str, nome_categoria: str, observacao: str = None) -> bool:
        """Permite forçar manualmente a categoria de um lançamento."""
        cat = self.cat_repo.get_categoria_por_nome(nome_categoria)
        if not cat:
            raise ValueError(f"Categoria '{nome_categoria}' não encontrada.")

        self.cat_repo.salvar_categorizacao(
            hash_transacao=hash_transacao,
            categoria_id=cat.id,
            manual=True,
            observacao=observacao
        )
        self.session.commit()
        return True

    categorizar_automaticamente = categorizar_transacoes_pendentes
