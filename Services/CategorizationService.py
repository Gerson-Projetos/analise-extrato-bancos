import re
from typing import Dict, Any
from sqlalchemy.orm import Session
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

    def categorizar_transacoes_pendentes(self, forcar: bool = False) -> Dict[str, Any]:
        """Aplica regras ativas às transações pendentes (ou a todas se forcar=True)."""
        self.inicializar_base()

        if forcar:
            self.cat_repo.limpar_categorizacoes_automaticas()

        regras = self.cat_repo.get_regras_ativas()
        mapa_existente = self.cat_repo.get_mapa_categorizados()
        lancamentos = self.extrato_repo.get_lancamentos_unificados()

        total_processados = len(lancamentos)
        total_categorizados = 0

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
