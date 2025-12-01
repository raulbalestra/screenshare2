#!/usr/bin/env python3
"""
TESTE DE ESTRESSE - Sistema de Screen Share
Simula múltiplos usuários fazendo login, upload de frames e streaming HLS
"""

import asyncio
import aiohttp
import time
import random
import threading
import psutil
import psycopg2
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

class StressTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.users = [
            {"username": "curitiba_user", "password": "senha_curitiba", "localidade": "curitiba"},
            {"username": "sp_user", "password": "senha_sp", "localidade": "sp"},
            {"username": "admin", "password": "admin", "localidade": "admin"}
        ]
        self.sessions = []
        self.results = {
            "login_times": [],
            "frame_upload_times": [],
            "hls_times": [],
            "dashboard_times": [],
            "errors": [],
            "total_requests": 0,
            "successful_requests": 0
        }
        
    async def login_user(self, session, user):
        """Faz login com um usuário"""
        try:
            start_time = time.time()
            
            # GET na página de login
            async with session.get(f"{self.base_url}/") as response:
                if response.status != 200:
                    raise Exception(f"GET login page failed: {response.status}")
            
            # POST para login
            login_data = {
                "username": user["username"],
                "password": user["password"]
            }
            
            async with session.post(f"{self.base_url}/login", data=login_data) as response:
                if response.status not in [200, 302]:
                    raise Exception(f"Login failed: {response.status}")
                    
            end_time = time.time()
            login_time = end_time - start_time
            self.results["login_times"].append(login_time)
            self.results["successful_requests"] += 1
            
            return True
            
        except Exception as e:
            self.results["errors"].append(f"Login error for {user['username']}: {str(e)}")
            return False
        finally:
            self.results["total_requests"] += 1

    async def upload_fake_frame(self, session, localidade):
        """Simula upload de frame (PNG fake)"""
        try:
            start_time = time.time()
            
            # Criar dados fake de imagem PNG (1x1 pixel)
            fake_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x12IDATx\x9cc```bPPP\x00\x02\xd2\x00\x05\xe0\xa9\x1a\x00\x00\x00\x00IEND\xaeB`\x82'
            
            data = aiohttp.FormData()
            data.add_field('frame', fake_png, filename='frame.png', content_type='image/png')
            
            async with session.post(f"{self.base_url}/{localidade}/upload_frame", data=data) as response:
                if response.status not in [200, 204]:
                    raise Exception(f"Frame upload failed: {response.status}")
                    
            end_time = time.time()
            frame_time = end_time - start_time
            self.results["frame_upload_times"].append(frame_time)
            self.results["successful_requests"] += 1
            
            return True
            
        except Exception as e:
            self.results["errors"].append(f"Frame upload error for {localidade}: {str(e)}")
            return False
        finally:
            self.results["total_requests"] += 1

    async def send_hls_chunk(self, session, localidade):
        """Simula envio de chunk HLS (WebM fake)"""
        try:
            start_time = time.time()
            
            # Dados fake de WebM (header mínimo)
            fake_webm = b'\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04webm\x42\x87\x81\x02\x42\x85\x81\x02'
            
            async with session.post(f"{self.base_url}/{localidade}/hls_ingest", 
                                  data=fake_webm, 
                                  headers={'Content-Type': 'video/webm'}) as response:
                if response.status not in [200, 204]:
                    raise Exception(f"HLS chunk failed: {response.status}")
                    
            end_time = time.time()
            hls_time = end_time - start_time
            self.results["hls_times"].append(hls_time)
            self.results["successful_requests"] += 1
            
            return True
            
        except Exception as e:
            self.results["errors"].append(f"HLS chunk error for {localidade}: {str(e)}")
            return False
        finally:
            self.results["total_requests"] += 1

    async def test_dashboard(self, session):
        """Testa acesso ao dashboard e API"""
        try:
            start_time = time.time()
            
            # Testar página do dashboard
            async with session.get(f"{self.base_url}/dashboard_admin") as response:
                if response.status not in [200, 302]:
                    raise Exception(f"Dashboard failed: {response.status}")
            
            # Testar API do dashboard
            async with session.get(f"{self.base_url}/admin/api/dashboard-users") as response:
                if response.status not in [200, 403]:  # 403 se não for admin
                    raise Exception(f"Dashboard API failed: {response.status}")
                    
            end_time = time.time()
            dashboard_time = end_time - start_time
            self.results["dashboard_times"].append(dashboard_time)
            self.results["successful_requests"] += 1
            
            return True
            
        except Exception as e:
            self.results["errors"].append(f"Dashboard error: {str(e)}")
            return False
        finally:
            self.results["total_requests"] += 1

    async def simulate_user_session(self, user, duration_seconds=60):
        """Simula uma sessão completa de usuário"""
        connector = aiohttp.TCPConnector(limit=100)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Fazer login
            if not await self.login_user(session, user):
                return
            
            print(f"👤 Usuário {user['username']} logado, iniciando atividade por {duration_seconds}s...")
            
            start_time = time.time()
            while (time.time() - start_time) < duration_seconds:
                # Simular atividades aleatórias
                activity = random.choice(['frame', 'hls', 'dashboard'])
                
                if activity == 'frame':
                    await self.upload_fake_frame(session, user['localidade'])
                elif activity == 'hls':
                    await self.send_hls_chunk(session, user['localidade'])
                elif activity == 'dashboard':
                    await self.test_dashboard(session)
                
                # Intervalo entre atividades (simula uso real)
                await asyncio.sleep(random.uniform(0.5, 3.0))

    def monitor_system_resources(self, duration_seconds):
        """Monitora recursos do sistema durante o teste"""
        print("🔍 Iniciando monitoramento de recursos...")
        
        cpu_usage = []
        memory_usage = []
        
        start_time = time.time()
        while (time.time() - start_time) < duration_seconds:
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            
            cpu_usage.append(cpu)
            memory_usage.append(memory)
            
            print(f"💻 CPU: {cpu:.1f}% | RAM: {memory:.1f}% | Requests: {self.results['total_requests']}")
        
        return {
            "avg_cpu": sum(cpu_usage) / len(cpu_usage),
            "max_cpu": max(cpu_usage),
            "avg_memory": sum(memory_usage) / len(memory_usage),
            "max_memory": max(memory_usage)
        }

    def check_database_performance(self):
        """Verifica performance do banco de dados"""
        try:
            conn = psycopg2.connect(
                host='localhost',
                database='screenshare',
                user='postgres',
                password='101410'
            )
            cursor = conn.cursor()
            
            # Verificar eventos criados durante o teste
            cursor.execute("SELECT COUNT(*) FROM usage_events WHERE created_at >= NOW() - INTERVAL '5 minutes'")
            recent_events = cursor.fetchone()[0]
            
            # Verificar conexões ativas
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            active_connections = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                "recent_events": recent_events,
                "active_connections": active_connections
            }
            
        except Exception as e:
            return {"error": str(e)}

    async def run_stress_test(self, concurrent_users=5, duration_minutes=2):
        """Executa teste de estresse principal"""
        duration_seconds = duration_minutes * 60
        
        print(f"🚀 INICIANDO TESTE DE ESTRESSE")
        print(f"👥 Usuários simultâneos: {concurrent_users}")
        print(f"⏰ Duração: {duration_minutes} minutos")
        print(f"🎯 URL: {self.base_url}")
        print("=" * 50)
        
        # Iniciar monitoramento em thread separada
        monitor_thread = threading.Thread(
            target=lambda: setattr(self, 'system_stats', 
                                  self.monitor_system_resources(duration_seconds))
        )
        monitor_thread.start()
        
        # Criar múltiplas sessões de usuário
        tasks = []
        for i in range(concurrent_users):
            user = self.users[i % len(self.users)]  # Rotaciona entre usuários
            task = asyncio.create_task(self.simulate_user_session(user, duration_seconds))
            tasks.append(task)
        
        # Executar todos os testes simultaneamente
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aguardar monitoramento terminar
        monitor_thread.join()
        
        # Gerar relatório
        self.generate_report()

    def generate_report(self):
        """Gera relatório do teste de estresse"""
        print("\n" + "=" * 50)
        print("📊 RELATÓRIO DO TESTE DE ESTRESSE")
        print("=" * 50)
        
        # Estatísticas de requisições
        total = self.results['total_requests']
        success = self.results['successful_requests']
        error_rate = ((total - success) / total * 100) if total > 0 else 0
        
        print(f"📈 REQUISIÇÕES:")
        print(f"  Total: {total}")
        print(f"  Sucessos: {success}")
        print(f"  Erros: {total - success}")
        print(f"  Taxa de erro: {error_rate:.2f}%")
        
        # Tempos de resposta
        if self.results['login_times']:
            avg_login = sum(self.results['login_times']) / len(self.results['login_times'])
            print(f"\n⏱️  TEMPOS MÉDIOS:")
            print(f"  Login: {avg_login:.3f}s")
        
        if self.results['frame_upload_times']:
            avg_frame = sum(self.results['frame_upload_times']) / len(self.results['frame_upload_times'])
            print(f"  Upload frame: {avg_frame:.3f}s")
        
        if self.results['hls_times']:
            avg_hls = sum(self.results['hls_times']) / len(self.results['hls_times'])
            print(f"  HLS chunk: {avg_hls:.3f}s")
        
        if self.results['dashboard_times']:
            avg_dashboard = sum(self.results['dashboard_times']) / len(self.results['dashboard_times'])
            print(f"  Dashboard: {avg_dashboard:.3f}s")
        
        # Recursos do sistema
        if hasattr(self, 'system_stats'):
            stats = self.system_stats
            print(f"\n💻 RECURSOS DO SISTEMA:")
            print(f"  CPU média: {stats['avg_cpu']:.1f}%")
            print(f"  CPU máxima: {stats['max_cpu']:.1f}%")
            print(f"  RAM média: {stats['avg_memory']:.1f}%")
            print(f"  RAM máxima: {stats['max_memory']:.1f}%")
        
        # Banco de dados
        db_stats = self.check_database_performance()
        if 'error' not in db_stats:
            print(f"\n🗄️  BANCO DE DADOS:")
            print(f"  Eventos criados: {db_stats['recent_events']}")
            print(f"  Conexões ativas: {db_stats['active_connections']}")
        
        # Erros
        if self.results['errors']:
            print(f"\n❌ ERROS ENCONTRADOS ({len(self.results['errors'])}):")
            for error in self.results['errors'][:10]:  # Primeiros 10 erros
                print(f"  • {error}")
            if len(self.results['errors']) > 10:
                print(f"  ... e mais {len(self.results['errors']) - 10} erros")
        
        print("\n" + "=" * 50)
        
        # Recomendações
        if error_rate > 10:
            print("⚠️  ALTA TAXA DE ERRO - Verifique configuração do servidor")
        if hasattr(self, 'system_stats') and self.system_stats['max_cpu'] > 90:
            print("⚠️  CPU SATURADA - Considere otimizar ou escalar")
        if hasattr(self, 'system_stats') and self.system_stats['max_memory'] > 90:
            print("⚠️  MEMÓRIA SATURADA - Considere aumentar RAM")
        if error_rate < 5:
            print("✅ SISTEMA ESTÁVEL - Performance adequada")

async def main():
    # Configurações do teste
    test = StressTest()
    
    print("Escolha o tipo de teste:")
    print("1. Teste leve (3 usuários, 1 minuto)")
    print("2. Teste médio (10 usuários, 3 minutos)")
    print("3. Teste pesado (20 usuários, 5 minutos)")
    print("4. Teste extremo (50 usuários, 10 minutos)")
    print("5. Personalizado")
    
    choice = input("\nDigite sua escolha (1-5): ").strip()
    
    if choice == "1":
        await test.run_stress_test(concurrent_users=3, duration_minutes=1)
    elif choice == "2":
        await test.run_stress_test(concurrent_users=10, duration_minutes=3)
    elif choice == "3":
        await test.run_stress_test(concurrent_users=20, duration_minutes=5)
    elif choice == "4":
        await test.run_stress_test(concurrent_users=50, duration_minutes=10)
    elif choice == "5":
        users = int(input("Número de usuários simultâneos: "))
        minutes = int(input("Duração em minutos: "))
        await test.run_stress_test(concurrent_users=users, duration_minutes=minutes)
    else:
        print("Opção inválida, executando teste leve...")
        await test.run_stress_test(concurrent_users=3, duration_minutes=1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Teste interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro durante o teste: {e}")