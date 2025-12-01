#!/usr/bin/env python3
"""
MONITOR EM TEMPO REAL
Monitora recursos do sistema, banco de dados e Flask em tempo real
"""

import psutil
import psycopg2
import requests
import time
import os
from datetime import datetime
import threading

class SystemMonitor:
    def __init__(self, flask_url="http://localhost:5000"):
        self.flask_url = flask_url
        self.running = True
        
    def get_db_stats(self):
        """Obtém estatísticas do banco de dados"""
        try:
            conn = psycopg2.connect(
                host='localhost',
                database='screenshare',
                user='postgres',
                password='101410'
            )
            cursor = conn.cursor()
            
            # Eventos recentes
            cursor.execute("SELECT COUNT(*) FROM usage_events WHERE created_at >= NOW() - INTERVAL '1 minute'")
            events_last_min = cursor.fetchone()[0]
            
            # Total de usuários
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
            
            # Usuários online agora
            cursor.execute("SELECT COUNT(*) FROM v_user_usage WHERE using_now = true")
            users_online = cursor.fetchone()[0]
            
            # Conexões ativas no PostgreSQL
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            active_connections = cursor.fetchone()[0]
            
            # Tamanho da tabela de eventos
            cursor.execute("SELECT COUNT(*) FROM usage_events")
            total_events = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            return {
                "events_last_min": events_last_min,
                "total_users": total_users,
                "users_online": users_online,
                "active_connections": active_connections,
                "total_events": total_events
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_flask_stats(self):
        """Testa responsividade do Flask"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.flask_url}/", timeout=5)
            response_time = time.time() - start_time
            
            return {
                "status_code": response.status_code,
                "response_time": response_time,
                "flask_responsive": response.status_code == 200
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "flask_responsive": False,
                "response_time": None
            }
    
    def get_ffmpeg_stats(self):
        """Monitora processos FFmpeg"""
        ffmpeg_processes = []
        total_cpu = 0
        total_memory = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if 'ffmpeg' in proc.info['name'].lower():
                    ffmpeg_processes.append({
                        'pid': proc.info['pid'],
                        'cpu': proc.info['cpu_percent'] or 0,
                        'memory': proc.info['memory_percent'] or 0
                    })
                    total_cpu += proc.info['cpu_percent'] or 0
                    total_memory += proc.info['memory_percent'] or 0
            except:
                continue
        
        return {
            "process_count": len(ffmpeg_processes),
            "total_cpu": total_cpu,
            "total_memory": total_memory,
            "processes": ffmpeg_processes
        }
    
    def print_status(self):
        """Imprime status atual do sistema"""
        os.system('cls' if os.name == 'nt' else 'clear')  # Limpa tela
        
        print("🖥️  MONITOR EM TEMPO REAL - SCREEN SHARE SYSTEM")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Pressione Ctrl+C para sair")
        print("=" * 60)
        
        # Sistema
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:').percent
        
        print(f"💻 SISTEMA:")
        print(f"   CPU: {cpu:5.1f}% | RAM: {memory:5.1f}% | Disk: {disk:5.1f}%")
        
        # Flask
        flask_stats = self.get_flask_stats()
        if flask_stats.get('flask_responsive'):
            flask_status = f"✅ Online ({flask_stats['response_time']:.3f}s)"
        else:
            flask_status = f"❌ Offline ({flask_stats.get('error', 'N/A')})"
        
        print(f"🌐 FLASK: {flask_status}")
        
        # FFmpeg
        ffmpeg_stats = self.get_ffmpeg_stats()
        print(f"🎬 FFMPEG: {ffmpeg_stats['process_count']} processos | CPU: {ffmpeg_stats['total_cpu']:.1f}% | RAM: {ffmpeg_stats['total_memory']:.1f}%")
        
        # Banco de dados
        db_stats = self.get_db_stats()
        if 'error' not in db_stats:
            print(f"🗄️  DATABASE:")
            print(f"   Eventos (1min): {db_stats['events_last_min']} | Total: {db_stats['total_events']}")
            print(f"   Usuários online: {db_stats['users_online']}/{db_stats['total_users']} | Conexões: {db_stats['active_connections']}")
        else:
            print(f"🗄️  DATABASE: ❌ Erro - {db_stats['error']}")
        
        # Detalhes FFmpeg
        if ffmpeg_stats['processes']:
            print(f"\n📋 PROCESSOS FFMPEG:")
            for proc in ffmpeg_stats['processes'][:5]:  # Máximo 5 processos
                print(f"   PID {proc['pid']}: CPU {proc['cpu']:5.1f}% | RAM {proc['memory']:5.1f}%")
        
        print("\n" + "=" * 60)
        
        # Alertas
        alerts = []
        if cpu > 80:
            alerts.append("⚠️  CPU alta (>80%)")
        if memory > 85:
            alerts.append("⚠️  Memória alta (>85%)")
        if ffmpeg_stats['process_count'] > 10:
            alerts.append("⚠️  Muitos processos FFmpeg")
        if not flask_stats.get('flask_responsive'):
            alerts.append("🚨 Flask não responsivo")
        if 'error' in db_stats:
            alerts.append("🚨 Erro no banco de dados")
        
        if alerts:
            print("🚨 ALERTAS:")
            for alert in alerts:
                print(f"   {alert}")
        else:
            print("✅ Sistema funcionando normalmente")
    
    def run_monitor(self, interval=2):
        """Executa monitor em loop"""
        try:
            while self.running:
                self.print_status()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n👋 Monitor encerrado pelo usuário")
            self.running = False

def run_load_simulation():
    """Simula carga no sistema enquanto monitora"""
    import requests
    import threading
    
    def simulate_requests():
        session = requests.Session()
        
        # Login
        session.post("http://localhost:5000/login", data={
            "username": "curitiba_user",
            "password": "senha_curitiba"
        })
        
        while True:
            try:
                # Simula upload de frame
                fake_data = b'fake_image_data' * 100
                files = {'frame': ('frame.png', fake_data, 'image/png')}
                session.post("http://localhost:5000/curitiba/upload_frame", files=files, timeout=5)
                time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except:
                pass
    
    # Inicia algumas threads de simulação
    for i in range(3):
        thread = threading.Thread(target=simulate_requests, daemon=True)
        thread.start()

def main():
    print("Escolha o tipo de monitoramento:")
    print("1. Monitor simples (apenas visualizar)")
    print("2. Monitor com simulação de carga")
    
    choice = input("\nDigite sua escolha (1-2): ").strip()
    
    monitor = SystemMonitor()
    
    if choice == "2":
        print("🔥 Iniciando simulação de carga...")
        run_load_simulation()
        time.sleep(2)
    
    print("🖥️  Iniciando monitor em tempo real...")
    time.sleep(1)
    
    monitor.run_monitor()

if __name__ == "__main__":
    main()