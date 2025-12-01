-- Criação da tabela usage_events para monitoramento de uso
CREATE TABLE IF NOT EXISTS usage_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    localidade VARCHAR(100) NOT NULL,
    event_type TEXT NOT NULL,         -- 'login', 'frame', 'hls_chunk'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para performance nas consultas
CREATE INDEX IF NOT EXISTS idx_usage_events_user_created_at
    ON usage_events (user_id, created_at DESC);

-- Índice adicional para consultas por localidade
CREATE INDEX IF NOT EXISTS idx_usage_events_localidade_created_at
    ON usage_events (localidade, created_at DESC);