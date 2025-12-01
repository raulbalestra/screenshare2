-- Script para criar tabela de eventos de uso REAL
-- Execute este script no PostgreSQL para habilitar monitoramento real

CREATE TABLE IF NOT EXISTS usage_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    localidade VARCHAR(100) NOT NULL,
    event_type TEXT NOT NULL,         -- 'login', 'frame', 'hls_chunk'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices para performance nas consultas de monitoramento
CREATE INDEX IF NOT EXISTS idx_usage_events_user_created_at
    ON usage_events (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_events_localidade_created_at
    ON usage_events (localidade, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_usage_events_event_type_created_at
    ON usage_events (event_type, created_at DESC);

-- Confirma criação
SELECT 'Tabela usage_events criada com sucesso!' AS resultado;