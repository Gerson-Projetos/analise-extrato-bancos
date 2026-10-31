-- ==============================================================================
-- Script de Inicialização do PostgreSQL para o Sistema de Análise de Extratos
-- ==============================================================================

-- Criação do schema financeiro
CREATE SCHEMA IF NOT EXISTS financeiro;

-- Define o search_path padrão para o banco e usuário
SET search_path TO financeiro, public;
ALTER DATABASE sistemas SET search_path TO financeiro, public;

-- Habilita extensões úteis se necessário
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Log de confirmação
DO $$
BEGIN
    RAISE NOTICE 'Schema "financeiro" inicializado com sucesso.';
END $$;
