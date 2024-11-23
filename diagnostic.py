import time
import psutil
import requests
import os

# Configurações
BASE_URL = "https://screenshare2-v2.onrender.com"  # Altere para a URL de produção, se necessário
ENDPOINTS = [
    "/",
    "/Bria/tela",
    "/Bjeq/tela",
    "/Bbr/tela",
    "/Baur/tela",
    "/Bmad/tela",
    "/Bubp/tela",
    "/Bjeq/tela",
    "/Bron/tela",
    "/curitiba/tela",
     "/sp/tela",
    "/healthz",
]
THRESHOLD_MEMORY_MB = 500  # Limite de memória em MB
THRESHOLD_CPU_PERCENT = 80  # Limite de uso de CPU

def monitor_resources():
    """Monitora uso de memória e CPU do servidor."""
    memory = psutil.virtual_memory().used / 1024 ** 2  # Memória usada (em MB)
    cpu = psutil.cpu_percent(interval=1)  # Uso de CPU (em %)
    print(f"Uso de memória: {memory:.2f} MB | Uso de CPU: {cpu:.2f}%")
    return memory, cpu

def check_endpoints():
    """Verifica os endpoints do sistema."""
    print("\nVerificando endpoints:")
    for endpoint in ENDPOINTS:
        url = f"{BASE_URL}{endpoint}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ {endpoint} - OK")
            else:
                print(f"⚠️ {endpoint} - Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint} - Error: {str(e)}")

def clean_cache():
    """Remove arquivos de cache desnecessários."""
    cache_dir = os.path.join(os.getcwd(), "static/images")
    if not os.path.exists(cache_dir):
        print("📁 Diretório de cache não encontrado.")
        return
    print("🧹 Limpando arquivos de cache...")
    for root, _, files in os.walk(cache_dir):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                os.remove(file_path)
                print(f"🗑️ Arquivo removido: {file_path}")
            except Exception as e:
                print(f"Erro ao remover {file_path}: {str(e)}")

def diagnostic():
    """Executa o diagnóstico completo."""
    print("\n🔍 Iniciando diagnóstico...")
    memory, cpu = monitor_resources()
    check_endpoints()

    # Se os limites forem excedidos, executa limpeza
    if memory > THRESHOLD_MEMORY_MB or cpu > THRESHOLD_CPU_PERCENT:
        print("\n⚠️ Limite de recursos excedido. Executando ações corretivas...")
        clean_cache()

if __name__ == "__main__":
    while True:
        diagnostic()
        time.sleep(300)  # Executa o diagnóstico a cada 5 minutos
