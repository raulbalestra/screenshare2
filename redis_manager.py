"""
Redis Frame Manager - Gerenciamento de frames e fila com Redis
Autor: ScreenShare System
Data: 11/12/2025

Este módulo gerencia frames de screen sharing usando Redis para:
- Cache de frames (muito mais rápido que disco)
- Sistema de fila FIFO para processamento
- TTL automático para limpeza de frames antigos
- Monitoramento de performance
"""

import redis
import os
import logging
from typing import Optional, List, Dict
from datetime import datetime

logger = logging.getLogger('redis_manager')


class RedisFrameManager:
    """
    Gerenciador de frames usando Redis para cache e sistema de fila.
    
    Recursos:
    - Salvar/recuperar frames binários com TTL
    - Sistema de fila FIFO com limite de tamanho
    - Estatísticas de cache hit/miss
    - Fallback para disco em caso de erro
    """
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 6379,
                 password: Optional[str] = None,
                 db: int = 0,
                 frame_ttl: int = 30,
                 queue_max_size: int = 100,
                 enabled: bool = True):
        """
        Inicializa conexão com Redis.
        
        Args:
            host: Host do Redis
            port: Porta do Redis
            password: Senha (opcional)
            db: Número do database
            frame_ttl: Tempo de vida dos frames em segundos
            queue_max_size: Tamanho máximo da fila
            enabled: Se False, opera em modo fallback (sem Redis)
        """
        self.enabled = enabled
        self.frame_ttl = frame_ttl
        self.queue_max_size = queue_max_size
        self.redis_client = None
        
        # Estatísticas
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'frames_saved': 0,
            'frames_queued': 0,
            'errors': 0
        }
        
        if not self.enabled:
            logger.info("Redis desabilitado - operando em modo fallback (disco)")
            return
        
        try:
            # Tentar conectar ao Redis
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                password=password if password else None,
                db=db,
                decode_responses=False,  # Importante para dados binários
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Testar conexão
            self.redis_client.ping()
            logger.info(f"✓ Conectado ao Redis em {host}:{port} (DB {db})")
            logger.info(f"  TTL de frames: {frame_ttl}s | Tamanho máximo da fila: {queue_max_size}")
            
        except redis.ConnectionError as e:
            logger.error(f"✗ Erro ao conectar ao Redis: {e}")
            logger.warning("Sistema operará em modo fallback (disco)")
            self.enabled = False
            self.redis_client = None
        except Exception as e:
            logger.error(f"✗ Erro inesperado ao inicializar Redis: {e}")
            self.enabled = False
            self.redis_client = None
    
    def is_available(self) -> bool:
        """Verifica se Redis está disponível."""
        if not self.enabled or not self.redis_client:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    def _get_frame_key(self, localidade: str) -> str:
        """Gera chave Redis para frame de uma localidade."""
        return f"frame:{localidade.lower()}:current"
    
    def _get_queue_key(self, localidade: str) -> str:
        """Gera chave Redis para fila de frames de uma localidade."""
        return f"queue:{localidade.lower()}:frames"
    
    def _get_metadata_key(self, localidade: str) -> str:
        """Gera chave Redis para metadados do frame."""
        return f"frame:{localidade.lower()}:metadata"
    
    def save_frame(self, localidade: str, frame_data: bytes, username: str = None) -> bool:
        """
        Salva frame no Redis com TTL.
        
        Args:
            localidade: Nome da localidade
            frame_data: Dados binários do frame (PNG)
            username: Nome do usuário que enviou (opcional)
        
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        if not self.is_available():
            logger.debug(f"Redis indisponível - frame de {localidade} não salvo no cache")
            return False
        
        try:
            frame_key = self._get_frame_key(localidade)
            metadata_key = self._get_metadata_key(localidade)
            
            # Salvar frame com TTL
            self.redis_client.setex(frame_key, self.frame_ttl, frame_data)
            
            # Salvar metadados
            metadata = {
                'timestamp': datetime.now().isoformat(),
                'size': len(frame_data),
                'username': username or 'unknown'
            }
            self.redis_client.hmset(metadata_key, metadata)
            self.redis_client.expire(metadata_key, self.frame_ttl)
            
            self.stats['frames_saved'] += 1
            logger.debug(f"✓ Frame de {localidade} salvo no Redis ({len(frame_data)} bytes, TTL: {self.frame_ttl}s)")
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"✗ Erro ao salvar frame de {localidade} no Redis: {e}")
            return False
    
    def get_frame(self, localidade: str) -> Optional[bytes]:
        """
        Recupera frame do Redis.
        
        Args:
            localidade: Nome da localidade
        
        Returns:
            Dados binários do frame ou None se não encontrado
        """
        if not self.is_available():
            return None
        
        try:
            frame_key = self._get_frame_key(localidade)
            frame_data = self.redis_client.get(frame_key)
            
            if frame_data:
                self.stats['cache_hits'] += 1
                logger.debug(f"✓ Cache HIT para {localidade} ({len(frame_data)} bytes)")
                return frame_data
            else:
                self.stats['cache_misses'] += 1
                logger.debug(f"✗ Cache MISS para {localidade}")
                return None
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"✗ Erro ao recuperar frame de {localidade}: {e}")
            return None
    
    def push_to_queue(self, localidade: str, frame_data: bytes, metadata: dict = None) -> bool:
        """
        Adiciona frame à fila FIFO (Left Push).
        
        Args:
            localidade: Nome da localidade
            frame_data: Dados binários do frame
            metadata: Metadados adicionais (opcional)
        
        Returns:
            True se adicionou com sucesso
        """
        if not self.is_available():
            return False
        
        try:
            queue_key = self._get_queue_key(localidade)
            
            # Verificar tamanho da fila
            queue_size = self.redis_client.llen(queue_key)
            
            # Se fila está cheia, remover o mais antigo (Right Pop)
            if queue_size >= self.queue_max_size:
                removed = self.redis_client.rpop(queue_key)
                logger.debug(f"Fila de {localidade} cheia ({queue_size}), removido frame mais antigo")
            
            # Adicionar novo frame no início da fila (Left Push)
            self.redis_client.lpush(queue_key, frame_data)
            
            # Definir TTL na fila (expira se não houver novos frames)
            self.redis_client.expire(queue_key, self.frame_ttl * 2)
            
            self.stats['frames_queued'] += 1
            logger.debug(f"✓ Frame de {localidade} adicionado à fila (tamanho: {queue_size + 1})")
            return True
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"✗ Erro ao adicionar frame à fila de {localidade}: {e}")
            return False
    
    def pop_from_queue(self, localidade: str) -> Optional[bytes]:
        """
        Remove e retorna frame mais antigo da fila (Right Pop - FIFO).
        
        Args:
            localidade: Nome da localidade
        
        Returns:
            Dados binários do frame ou None se fila vazia
        """
        if not self.is_available():
            return None
        
        try:
            queue_key = self._get_queue_key(localidade)
            frame_data = self.redis_client.rpop(queue_key)
            
            if frame_data:
                logger.debug(f"✓ Frame removido da fila de {localidade}")
            
            return frame_data
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"✗ Erro ao remover frame da fila de {localidade}: {e}")
            return None
    
    def get_queue_size(self, localidade: str) -> int:
        """Retorna tamanho atual da fila."""
        if not self.is_available():
            return 0
        
        try:
            queue_key = self._get_queue_key(localidade)
            return self.redis_client.llen(queue_key)
        except:
            return 0
    
    def clear_queue(self, localidade: str) -> bool:
        """Limpa toda a fila de uma localidade."""
        if not self.is_available():
            return False
        
        try:
            queue_key = self._get_queue_key(localidade)
            self.redis_client.delete(queue_key)
            logger.info(f"✓ Fila de {localidade} limpa")
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao limpar fila de {localidade}: {e}")
            return False
    
    def delete_frame(self, localidade: str) -> bool:
        """Remove frame do cache Redis."""
        if not self.is_available():
            return False
        
        try:
            frame_key = self._get_frame_key(localidade)
            metadata_key = self._get_metadata_key(localidade)
            
            self.redis_client.delete(frame_key, metadata_key)
            logger.debug(f"✓ Frame de {localidade} removido do Redis")
            return True
        except Exception as e:
            logger.error(f"✗ Erro ao remover frame de {localidade}: {e}")
            return False
    
    def get_frame_metadata(self, localidade: str) -> Optional[Dict]:
        """Recupera metadados do frame."""
        if not self.is_available():
            return None
        
        try:
            metadata_key = self._get_metadata_key(localidade)
            metadata = self.redis_client.hgetall(metadata_key)
            
            if metadata:
                # Converter bytes para strings
                return {k.decode('utf-8'): v.decode('utf-8') for k, v in metadata.items()}
            return None
            
        except Exception as e:
            logger.error(f"✗ Erro ao recuperar metadados de {localidade}: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas de uso."""
        stats = self.stats.copy()
        
        # Calcular taxa de acerto do cache
        total_requests = stats['cache_hits'] + stats['cache_misses']
        if total_requests > 0:
            stats['cache_hit_rate'] = round((stats['cache_hits'] / total_requests) * 100, 2)
        else:
            stats['cache_hit_rate'] = 0
        
        stats['redis_available'] = self.is_available()
        return stats
    
    def reset_stats(self):
        """Reseta estatísticas."""
        self.stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'frames_saved': 0,
            'frames_queued': 0,
            'errors': 0
        }
        logger.info("Estatísticas resetadas")
    
    def close(self):
        """Fecha conexão com Redis."""
        if self.redis_client:
            try:
                self.redis_client.close()
                logger.info("Conexão com Redis fechada")
            except:
                pass


# Instância global (será inicializada no app.py)
redis_manager: Optional[RedisFrameManager] = None


def init_redis_manager(app_config: dict = None) -> RedisFrameManager:
    """
    Inicializa o gerenciador Redis com configurações.
    
    Args:
        app_config: Dicionário com configurações (ou None para usar variáveis de ambiente)
    
    Returns:
        Instância de RedisFrameManager
    """
    global redis_manager
    
    # Obter configurações
    if app_config:
        config = app_config
    else:
        config = {
            'REDIS_ENABLED': os.getenv('REDIS_ENABLED', 'True').lower() == 'true',
            'REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
            'REDIS_PORT': int(os.getenv('REDIS_PORT', '6379')),
            'REDIS_PASSWORD': os.getenv('REDIS_PASSWORD', ''),
            'REDIS_DB': int(os.getenv('REDIS_DB', '0')),
            'REDIS_FRAME_TTL': int(os.getenv('REDIS_FRAME_TTL', '30')),
            'REDIS_QUEUE_MAX_SIZE': int(os.getenv('REDIS_QUEUE_MAX_SIZE', '100'))
        }
    
    redis_manager = RedisFrameManager(
        host=config['REDIS_HOST'],
        port=config['REDIS_PORT'],
        password=config['REDIS_PASSWORD'] if config['REDIS_PASSWORD'] else None,
        db=config['REDIS_DB'],
        frame_ttl=config['REDIS_FRAME_TTL'],
        queue_max_size=config['REDIS_QUEUE_MAX_SIZE'],
        enabled=config['REDIS_ENABLED']
    )
    
    return redis_manager


def get_redis_manager() -> Optional[RedisFrameManager]:
    """Retorna instância global do gerenciador Redis."""
    return redis_manager
