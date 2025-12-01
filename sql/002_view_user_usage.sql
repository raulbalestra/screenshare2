-- Script para criar VIEW de monitoramento de usuários
-- Consolida dados reais de uso sem mocks

CREATE OR REPLACE VIEW v_user_usage AS
SELECT
    u.id,
    u.username,
    u.localidade,
    u.is_admin,
    u.is_active,
    MAX(e.created_at) AS last_activity_at,
    COUNT(*) FILTER (
        WHERE e.created_at >= NOW() - INTERVAL '30 days'
    ) AS access_last_30d,
    CASE
        WHEN MAX(e.created_at) >= NOW() - INTERVAL '5 minutes'
        THEN TRUE
        ELSE FALSE
    END AS using_now,
    COUNT(DISTINCT DATE(e.created_at)) FILTER (
        WHERE e.created_at >= NOW() - INTERVAL '30 days'
    ) AS days_active_last_30d
FROM users u
LEFT JOIN usage_events e ON e.user_id = u.id
GROUP BY u.id, u.username, u.localidade, u.is_admin, u.is_active
ORDER BY using_now DESC, last_activity_at DESC NULLS LAST;

-- Confirma criação da VIEW
SELECT 'VIEW v_user_usage criada com sucesso!' AS resultado;