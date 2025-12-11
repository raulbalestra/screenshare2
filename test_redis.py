#!/usr/bin/env python3
"""
Script de Teste - Redis Implementation
Valida a implementação do Redis no sistema ScreenShare

Testes realizados:
1. Conexão Redis
2. Save/Get frames
3. Fila FIFO
4. Estatísticas
5. Performance comparison
"""

import sys
import time
import os

# Adicionar diretório ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from redis_manager import init_redis_manager

def print_section(title):
    """Imprime título de seção formatado."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")

def test_redis_connection():
    """Teste 1: Conexão com Redis."""
    print_section("TESTE 1: Conexão com Redis")
    
    manager = init_redis_manager()
    
    if manager.is_available():
        print("✅ Redis conectado com sucesso!")
        print(f"   Host: {os.getenv('REDIS_HOST', 'localhost')}")
        print(f"   Port: {os.getenv('REDIS_PORT', '6379')}")
        print(f"   TTL: {manager.frame_ttl} segundos")
        print(f"   Max Queue Size: {manager.queue_max_size}")
        return manager
    else:
        print("❌ Redis não disponível")
        print("   Sistema operará em modo fallback (disco)")
        return None

def test_save_and_get_frame(manager):
    """Teste 2: Salvar e recuperar frame."""
    if not manager or not manager.is_available():
        print("\n⚠️  Teste 2 pulado - Redis não disponível")
        return False
    
    print_section("TESTE 2: Salvar e Recuperar Frame")
    
    # Criar dados de teste
    test_localidade = "teste_localidade"
    test_frame_data = b"PNG_DATA_TESTE" * 1000  # Simular frame PNG
    
    print(f"Salvando frame de teste ({len(test_frame_data)} bytes)...")
    success = manager.save_frame(test_localidade, test_frame_data, "test_user")
    
    if success:
        print("✅ Frame salvo no Redis")
    else:
        print("❌ Erro ao salvar frame")
        return False
    
    # Tentar recuperar
    print("\nRecuperando frame...")
    retrieved_data = manager.get_frame(test_localidade)
    
    if retrieved_data:
        print(f"✅ Frame recuperado ({len(retrieved_data)} bytes)")
        
        if retrieved_data == test_frame_data:
            print("✅ Dados íntegros (match perfeito)")
            return True
        else:
            print("❌ Dados corrompidos (não coincidem)")
            return False
    else:
        print("❌ Frame não encontrado")
        return False

def test_queue_operations(manager):
    """Teste 3: Operações de fila."""
    if not manager or not manager.is_available():
        print("\n⚠️  Teste 3 pulado - Redis não disponível")
        return False
    
    print_section("TESTE 3: Sistema de Fila FIFO")
    
    test_localidade = "teste_fila"
    
    # Limpar fila antes do teste
    manager.clear_queue(test_localidade)
    print(f"Fila de {test_localidade} limpa")
    
    # Adicionar 10 frames à fila
    print("\nAdicionando 10 frames à fila...")
    for i in range(10):
        frame_data = f"FRAME_{i}".encode() * 100
        success = manager.push_to_queue(test_localidade, frame_data)
        if success:
            print(f"  ✓ Frame {i+1} adicionado")
    
    # Verificar tamanho da fila
    queue_size = manager.get_queue_size(test_localidade)
    print(f"\n✅ Tamanho da fila: {queue_size} frames")
    
    if queue_size != 10:
        print(f"❌ Esperado 10 frames, encontrado {queue_size}")
        return False
    
    # Remover 3 frames (FIFO - os mais antigos)
    print("\nRemovendo 3 frames mais antigos (FIFO)...")
    for i in range(3):
        frame = manager.pop_from_queue(test_localidade)
        if frame:
            print(f"  ✓ Frame {i+1} removido")
    
    # Verificar novo tamanho
    queue_size = manager.get_queue_size(test_localidade)
    print(f"\n✅ Novo tamanho da fila: {queue_size} frames")
    
    if queue_size != 7:
        print(f"❌ Esperado 7 frames, encontrado {queue_size}")
        return False
    
    # Limpar fila
    manager.clear_queue(test_localidade)
    queue_size = manager.get_queue_size(test_localidade)
    print(f"\n✅ Fila limpa: {queue_size} frames restantes")
    
    return queue_size == 0

def test_statistics(manager):
    """Teste 4: Estatísticas."""
    if not manager or not manager.is_available():
        print("\n⚠️  Teste 4 pulado - Redis não disponível")
        return False
    
    print_section("TESTE 4: Estatísticas Redis")
    
    stats = manager.get_stats()
    
    print("Estatísticas do Redis Manager:")
    print(f"  Cache Hits: {stats['cache_hits']}")
    print(f"  Cache Misses: {stats['cache_misses']}")
    print(f"  Cache Hit Rate: {stats['cache_hit_rate']}%")
    print(f"  Frames Salvos: {stats['frames_saved']}")
    print(f"  Frames na Fila: {stats['frames_queued']}")
    print(f"  Erros: {stats['errors']}")
    print(f"  Redis Disponível: {stats['redis_available']}")
    
    if stats['redis_available']:
        print("\n✅ Estatísticas coletadas com sucesso")
        return True
    else:
        print("\n❌ Redis não disponível nas estatísticas")
        return False

def test_performance(manager):
    """Teste 5: Performance comparison (Redis vs simulação disco)."""
    if not manager or not manager.is_available():
        print("\n⚠️  Teste 5 pulado - Redis não disponível")
        return False
    
    print_section("TESTE 5: Performance Comparison")
    
    test_localidade = "teste_performance"
    test_frame_data = b"PNG_FRAME_DATA" * 5000  # ~70KB frame
    
    # Salvar frame
    manager.save_frame(test_localidade, test_frame_data)
    
    # Teste 1: Recuperar do Redis (100 vezes)
    print(f"Recuperando frame do Redis (100 iterações)...")
    redis_times = []
    
    for _ in range(100):
        start = time.time()
        frame = manager.get_frame(test_localidade)
        elapsed = time.time() - start
        redis_times.append(elapsed * 1000)  # Converter para ms
    
    redis_avg = sum(redis_times) / len(redis_times)
    redis_min = min(redis_times)
    redis_max = max(redis_times)
    
    print(f"  Média: {redis_avg:.2f}ms")
    print(f"  Min: {redis_min:.2f}ms")
    print(f"  Max: {redis_max:.2f}ms")
    
    # Teste 2: Simular leitura de disco
    import tempfile
    print(f"\nSimulando leitura de disco (100 iterações)...")
    
    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(test_frame_data)
        tmp_path = tmp.name
    
    disk_times = []
    
    for _ in range(100):
        start = time.time()
        with open(tmp_path, 'rb') as f:
            _ = f.read()
        elapsed = time.time() - start
        disk_times.append(elapsed * 1000)
    
    # Limpar arquivo temporário
    os.unlink(tmp_path)
    
    disk_avg = sum(disk_times) / len(disk_times)
    disk_min = min(disk_times)
    disk_max = max(disk_times)
    
    print(f"  Média: {disk_avg:.2f}ms")
    print(f"  Min: {disk_min:.2f}ms")
    print(f"  Max: {disk_max:.2f}ms")
    
    # Comparação
    print("\n" + "=" * 60)
    print("RESULTADO:")
    print(f"  Redis: {redis_avg:.2f}ms")
    print(f"  Disco: {disk_avg:.2f}ms")
    
    speedup = disk_avg / redis_avg
    print(f"  🚀 Speedup: {speedup:.2f}x mais rápido com Redis")
    print("=" * 60)
    
    return True

def test_metadata(manager):
    """Teste 6: Metadados do frame."""
    if not manager or not manager.is_available():
        print("\n⚠️  Teste 6 pulado - Redis não disponível")
        return False
    
    print_section("TESTE 6: Metadados do Frame")
    
    test_localidade = "teste_metadata"
    test_frame_data = b"TESTE_METADATA" * 100
    
    # Salvar com metadados
    print("Salvando frame com metadados...")
    manager.save_frame(test_localidade, test_frame_data, "usuario_teste")
    
    # Recuperar metadados
    print("\nRecuperando metadados...")
    metadata = manager.get_frame_metadata(test_localidade)
    
    if metadata:
        print("✅ Metadados recuperados:")
        print(f"  Timestamp: {metadata.get('timestamp')}")
        print(f"  Tamanho: {metadata.get('size')} bytes")
        print(f"  Usuário: {metadata.get('username')}")
        return True
    else:
        print("❌ Metadados não encontrados")
        return False

def main():
    """Executa todos os testes."""
    print("\n" + "=" * 60)
    print("  REDIS IMPLEMENTATION - TEST SUITE")
    print("  ScreenShare System")
    print("=" * 60)
    
    results = {}
    
    # Teste 1: Conexão
    manager = test_redis_connection()
    results['connection'] = manager is not None and manager.is_available()
    
    if not results['connection']:
        print("\n❌ Testes abortados - Redis não disponível")
        print("   Verifique se Redis está rodando:")
        print("   sudo service redis-server start")
        return 1
    
    # Teste 2: Save/Get
    results['save_get'] = test_save_and_get_frame(manager)
    
    # Teste 3: Fila
    results['queue'] = test_queue_operations(manager)
    
    # Teste 4: Estatísticas
    results['stats'] = test_statistics(manager)
    
    # Teste 5: Performance
    results['performance'] = test_performance(manager)
    
    # Teste 6: Metadados
    results['metadata'] = test_metadata(manager)
    
    # Resumo final
    print_section("RESUMO DOS TESTES")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"  {test_name.upper()}: {status}")
    
    print(f"\n{'=' * 60}")
    print(f"  RESULTADO FINAL: {passed}/{total} testes passaram")
    print(f"{'=' * 60}\n")
    
    if passed == total:
        print("🎉 SUCESSO! Todos os testes passaram!")
        print("   Sistema Redis está funcionando perfeitamente.")
        return 0
    else:
        print("⚠️  Alguns testes falharam.")
        print("   Verifique os logs acima para mais detalhes.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Testes interrompidos pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
