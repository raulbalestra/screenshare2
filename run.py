from multiprocessing import Process
import os

def run_app():
    """Executa o código principal (Flask)."""
    os.system("python3 app.py")  # Altere para "python app.py" no Windows

def run_diagnostic():
    """Executa o script de diagnóstico."""
    os.system("python3 diagnostic.py")  # Altere para "python diagnostic.py" no Windows

if __name__ == "__main__":
    # Cria processos para o app e o diagnóstico
    app_process = Process(target=run_app)
    diagnostic_process = Process(target=run_diagnostic)

    # Inicia os processos
    app_process.start()
    diagnostic_process.start()

    # Aguarda os dois processos finalizarem
    app_process.join()
    diagnostic_process.join()
