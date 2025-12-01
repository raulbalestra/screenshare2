-- Script de teste para verificar se o monitoramento está funcionando
-- Execute após criar as tabelas e fazer alguns logins

-- 1. Verificar se a tabela usage_events foi criada
SELECT 'Verificando tabela usage_events...' AS etapa;
SELECT 
    COUNT(*) as total_eventos,
    COUNT(DISTINCT user_id) as usuarios_com_eventos,
    COUNT(DISTINCT event_type) as tipos_de_evento
FROM usage_events;

-- 2. Verificar últimos eventos registrados
SELECT 'Últimos 10 eventos registrados:' AS etapa;
SELECT 
    u.username,
    ue.localidade,
    ue.event_type,
    ue.created_at
FROM usage_events ue
JOIN users u ON u.id = ue.user_id
ORDER BY ue.created_at DESC
LIMIT 10;

-- 3. Verificar a VIEW v_user_usage
SELECT 'Dados da VIEW v_user_usage:' AS etapa;
SELECT 
    username,
    localidade,
    is_active,
    last_activity_at,
    access_last_30d,
    using_now,
    days_active_last_30d
FROM v_user_usage;

-- 4. Verificar usuários que estão "usando agora"
SELECT 'Usuários usando AGORA (últimos 5 minutos):' AS etapa;
SELECT 
    username,
    localidade,
    last_activity_at
FROM v_user_usage 
WHERE using_now = true;

-- Resultado do teste
SELECT 
    CASE 
        WHEN EXISTS (SELECT 1 FROM usage_events) 
        THEN '✅ SUCESSO: Sistema de monitoramento funcionando!'
        ELSE '❌ AVISO: Nenhum evento registrado ainda. Faça login para testar.'
    END AS resultado_final;