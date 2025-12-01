#!/usr/bin/env python3
"""
TESTE DE COMPONENTES ESPECÍFICOS
Testes individuais para cada parte do sistema
"""

import requests
import time
import threading
import psutil
import concurrent.futures
from datetime import datetime

class ComponentTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def login_admin(self):
        """Faz login como admin"""
        try:
            response = self.session.post(f"{self.base_url}/login", data={
                "username": "admin",
                "password": "admin"
            })
            return response.status_code in [200, 302]
        except Exception as e:
            print(f"❌ Erro no login: {e}")
            return False
    
    def test_dashboard_api_performance(self, requests_count=100):
        """Testa performance da API do dashboard"""
        print(f"🔄 Testando API dashboard com {requests_count} requisições...")
        
        if not self.login_admin():
            print("❌ Falha no login admin")
            return
        
        times = []
        errors = 0
        
        def make_request():
            try:
                start = time.time()
                response = self.session.get(f"{self.base_url}/admin/api/dashboard-users")
                end = time.time()
                
                if response.status_code == 200:
                    return end - start
                else:
                    return None
            except:
                return None
        
        # Executa requisições em paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(requests_count)]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    times.append(result)
                else:
                    errors += 1
        
        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"📊 RESULTADOS API DASHBOARD:")
            print(f"  Sucesso: {len(times)}/{requests_count}")
            print(f"  Erros: {errors}")
            print(f"  Tempo médio: {avg_time:.3f}s")
            print(f"  Tempo mínimo: {min_time:.3f}s")
            print(f"  Tempo máximo: {max_time:.3f}s")
            print(f"  RPS: {len(times)/sum(times):.1f} req/s")
        
    def test_frame_upload_flood(self, uploads_count=50):
        """Testa flood de uploads de frame"""
        print(f"📤 Testando {uploads_count} uploads simultâneos...")
        
        # Login como usuário normal
        self.session.post(f"{self.base_url}/login", data={
            "username": "curitiba_user",
            "password": "senha_curitiba"
        })
        
        # Criar imagem fake PNG mínima
        fake_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x12IDATx\x9cc```bPPP\x00\x02\xd2\x00\x05\xe0\xa9\x1a\x00\x00\x00\x00IEND\xaeB`\x82'
        
        times = []
        errors = 0
        
        def upload_frame():
            try:
                start = time.time()
                files = {'frame': ('frame.png', fake_png, 'image/png')}
                response = self.session.post(f"{self.base_url}/curitiba/upload_frame", files=files)
                end = time.time()
                
                if response.status_code in [200, 204]:
                    return end - start
                else:
                    return None
            except:
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(upload_frame) for _ in range(uploads_count)]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    times.append(result)
                else:
                    errors += 1
        
        if times:
            print(f"📊 RESULTADOS UPLOAD FRAMES:")
            print(f"  Sucesso: {len(times)}/{uploads_count}")
            print(f"  Erros: {errors}")
            print(f"  Tempo médio: {sum(times)/len(times):.3f}s")
            print(f"  Upload rate: {len(times)/sum(times):.1f} frames/s")
    
    def test_hls_chunk_flood(self, chunks_count=100):
        """Testa flood de chunks HLS"""
        print(f"🎥 Testando {chunks_count} chunks HLS...")
        
        # Login como usuário normal
        self.session.post(f"{self.base_url}/login", data={
            "username": "curitiba_user",
            "password": "senha_curitiba"
        })
        
        # WebM header fake mínimo
        fake_webm = b'\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01\x42\xf2\x81\x04webm\x42\x87\x81\x02\x42\x85\x81\x02'
        
        times = []
        errors = 0
        
        def send_chunk():
            try:
                start = time.time()
                response = self.session.post(
                    f"{self.base_url}/curitiba/hls_ingest",
                    data=fake_webm,
                    headers={'Content-Type': 'video/webm'}
                )
                end = time.time()
                
                if response.status_code in [200, 204]:
                    return end - start
                else:
                    return None
            except:
                return None
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(send_chunk) for _ in range(chunks_count)]
            
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    times.append(result)
                else:
                    errors += 1
        
        if times:
            print(f"📊 RESULTADOS HLS CHUNKS:")
            print(f"  Sucesso: {len(times)}/{chunks_count}")
            print(f"  Erros: {errors}")
            print(f"  Tempo médio: {sum(times)/len(times):.3f}s")
            print(f"  Chunk rate: {len(times)/sum(times):.1f} chunks/s")
    
    def monitor_ffmpeg_processes(self, duration_seconds=30):
        """Monitora processos FFmpeg durante teste"""
        print(f"🎬 Monitorando FFmpeg por {duration_seconds}s...")
        
        start_time = time.time()
        ffmpeg_count = []
        cpu_usage = []
        
        while (time.time() - start_time) < duration_seconds:
            # Contar processos FFmpeg
            ffmpeg_procs = 0
            total_cpu = 0
            
            for proc in psutil.process_iter(['name', 'cpu_percent']):
                try:
                    if 'ffmpeg' in proc.info['name'].lower():
                        ffmpeg_procs += 1
                        total_cpu += proc.info['cpu_percent'] or 0
                except:
                    continue
            
            ffmpeg_count.append(ffmpeg_procs)
            cpu_usage.append(total_cpu)
            
            print(f"🎬 FFmpeg: {ffmpeg_procs} processos, CPU: {total_cpu:.1f}%")
            time.sleep(2)
        
        if ffmpeg_count:
            print(f"📊 MONITORAMENTO FFMPEG:")
            print(f"  Processos máximo: {max(ffmpeg_count)}")
            print(f"  CPU máximo: {max(cpu_usage):.1f}%")
            print(f"  CPU médio: {sum(cpu_usage)/len(cpu_usage):.1f}%")

def main():
    print("🧪 TESTE DE COMPONENTES ESPECÍFICOS")
    print("=" * 40)
    
    test = ComponentTest()
    
    print("Escolha o teste:")
    print("1. API Dashboard (100 requisições)")
    print("2. Upload de Frames (50 uploads)")
    print("3. Chunks HLS (100 chunks)")
    print("4. Monitorar FFmpeg (30s)")
    print("5. Teste completo (todos)")
    
    choice = input("\nDigite sua escolha (1-5): ").strip()
    
    if choice == "1":
        test.test_dashboard_api_performance()
    elif choice == "2":
        test.test_frame_upload_flood()
    elif choice == "3":
        test.test_hls_chunk_flood()
    elif choice == "4":
        test.monitor_ffmpeg_processes()
    elif choice == "5":
        print("🚀 Executando teste completo...")
        test.test_dashboard_api_performance(50)
        print()
        test.test_frame_upload_flood(30)
        print()
        test.test_hls_chunk_flood(50)
        print()
        test.monitor_ffmpeg_processes(20)
    else:
        print("Opção inválida!")

if __name__ == "__main__":
    main()