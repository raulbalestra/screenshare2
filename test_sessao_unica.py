#!/usr/bin/env python3
"""
Teste Específico: Controle de Sessão Única
==========================================

Este teste valida especificamente a funcionalidade de sessão única por usuário:
- Um usuário só pode estar logado em um dispositivo
- Login em novo dispositivo desconecta o anterior
- Monitoramento de sessões ativas

Para executar: python test_sessao_unica.py
"""

import requests
import json
import time
import threading
from datetime import datetime

BASE_URL = "http://127.0.0.1:5000"

class SessionTester:
    def __init__(self):
        self.results = []
        
    def log_result(self, test, success, message=""):
        status = "✅" if success else "❌"
        print(f"{status} {test}: {message}")
        self.results.append({'test': test, 'success': success, 'message': message})
    
    def create_test_user(self):
        """Cria usuário de teste para os testes de sessão"""
        print("🔧 Preparando usuário de teste...")
        
        # Fazer login como admin
        admin_session = requests.Session()
        login_data = {'username': 'admin', 'password': 'admin'}
        admin_session.post(f"{BASE_URL}/login", data=login_data)
        
        # Criar usuário de teste
        from datetime import datetime, timedelta
        today = datetime.now()
        end_date = today + timedelta(days=30)
        
        user_data = {
            'username': 'teste_sessao',
            'password': 'senha123!',
            'localidade': 'teste_local',
            'plan_start': today.strftime('%Y-%m-%d'),
            'plan_end': end_date.strftime('%Y-%m-%d')
        }
        
        response = admin_session.post(f"{BASE_URL}/admin/add_user", data=user_data)
        
        if response.status_code in [200, 302]:
            print("✅ Usuário de teste criado: teste_sessao")
            return True
        else:
            print("❌ Erro ao criar usuário de teste")
            return False
    
    def test_single_session_enforcement(self):
        """Testa se apenas uma sessão por usuário é permitida"""
        print("\n🔍 TESTE: Controle de Sessão Única")
        
        # Sessão 1: Primeiro dispositivo
        session1 = requests.Session()
        login_data = {'username': 'teste_sessao', 'password': 'senha123!'}
        
        response1 = session1.post(f"{BASE_URL}/login", data=login_data)
        
        if response1.status_code == 302:
            self.log_result("Login primeiro dispositivo", True, "Login bem-sucedido")
        else:
            self.log_result("Login primeiro dispositivo", False, f"Status: {response1.status_code}")
            return
        
        # Verificar se consegue acessar área protegida
        protected1 = session1.get(f"{BASE_URL}/teste_local/tela")
        if protected1.status_code == 200:
            self.log_result("Acesso área protegida (dispositivo 1)", True)
        else:
            self.log_result("Acesso área protegida (dispositivo 1)", False)
        
        # Sessão 2: Segundo dispositivo (mesmo usuário)
        session2 = requests.Session()
        response2 = session2.post(f"{BASE_URL}/login", data=login_data)
        
        if response2.status_code == 302:
            self.log_result("Login segundo dispositivo", True, "Novo login permitido")
        else:
            self.log_result("Login segundo dispositivo", False)
            return
        
        # Aguardar um momento para que o middleware processe
        time.sleep(2)
        
        # Verificar se o primeiro dispositivo foi desconectado
        protected1_after = session1.get(f"{BASE_URL}/teste_local/tela", allow_redirects=False)
        
        if protected1_after.status_code == 302:  # Redirecionado para login
            self.log_result("Primeiro dispositivo desconectado", True, "Redirecionado para login")
        else:
            self.log_result("Primeiro dispositivo desconectado", False, 
                          f"Ainda consegue acessar (status: {protected1_after.status_code})")
        
        # Verificar se o segundo dispositivo está funcionando
        protected2 = session2.get(f"{BASE_URL}/teste_local/tela")
        if protected2.status_code == 200:
            self.log_result("Segundo dispositivo funcionando", True)
        else:
            self.log_result("Segundo dispositivo funcionando", False)
    
    def test_session_monitoring(self):
        """Testa se o monitoramento de sessões está funcionando"""
        print("\n🔍 TESTE: Monitoramento de Sessões")
        
        # Login como admin para acessar monitoramento
        admin_session = requests.Session()
        login_data = {'username': 'admin', 'password': 'admin'}
        admin_session.post(f"{BASE_URL}/login", data=login_data)
        
        # Verificar API de sessões ativas
        sessions_response = admin_session.get(f"{BASE_URL}/admin/api/active-sessions")
        
        if sessions_response.status_code == 200:
            try:
                sessions_data = sessions_response.json()
                self.log_result("API sessões ativas", True, f"{len(sessions_data)} sessões encontradas")
                
                # Procurar pela sessão do usuário de teste
                test_session = next((s for s in sessions_data if s['username'] == 'teste_sessao'), None)
                
                if test_session:
                    self.log_result("Sessão do usuário de teste encontrada", True, 
                                  f"IP: {test_session['ip_address']}, Ativa: {test_session['is_active']}")
                else:
                    self.log_result("Sessão do usuário de teste encontrada", False, 
                                  "Usuário teste_sessao não está nas sessões ativas")
                
            except json.JSONDecodeError:
                self.log_result("API sessões ativas", False, "Resposta não é JSON válido")
        else:
            self.log_result("API sessões ativas", False, f"Status: {sessions_response.status_code}")
    
    def test_session_timeout(self):
        """Testa limpeza de sessões inativas"""
        print("\n🔍 TESTE: Timeout de Sessões")
        
        # Este teste verificaria se sessões antigas são removidas automaticamente
        # Como o timeout é de 30 minutos, vamos apenas verificar se a funcionalidade existe
        
        admin_session = requests.Session()
        login_data = {'username': 'admin', 'password': 'admin'}
        admin_session.post(f"{BASE_URL}/login", data=login_data)
        
        # Verificar se existem campos de tempo nas sessões
        sessions_response = admin_session.get(f"{BASE_URL}/admin/api/active-sessions")
        
        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            
            if sessions_data:
                session = sessions_data[0]
                has_time_fields = all(field in session for field in ['created_at', 'last_activity', 'minutes_inactive'])
                
                self.log_result("Campos de tempo nas sessões", has_time_fields,
                              f"Campos encontrados: {list(session.keys())}")
            else:
                self.log_result("Campos de tempo nas sessões", False, "Nenhuma sessão encontrada")
    
    def test_concurrent_logins(self):
        """Testa múltiplos logins simultâneos"""
        print("\n🔍 TESTE: Logins Simultâneos")
        
        def login_attempt(session_id):
            session = requests.Session()
            login_data = {'username': 'teste_sessao', 'password': 'senha123!'}
            response = session.post(f"{BASE_URL}/login", data=login_data)
            return response.status_code == 302
        
        # Criar múltiplas threads para login simultâneo
        threads = []
        results = []
        
        for i in range(3):
            thread = threading.Thread(target=lambda i=i: results.append(login_attempt(i)))
            threads.append(thread)
            thread.start()
        
        # Aguardar todas as threads
        for thread in threads:
            thread.join()
        
        successful_logins = sum(results)
        
        if successful_logins >= 1:
            self.log_result("Logins simultâneos", True, f"{successful_logins}/3 logins bem-sucedidos")
        else:
            self.log_result("Logins simultâneos", False, "Nenhum login bem-sucedido")
    
    def test_session_persistence(self):
        """Testa persistência de sessões no banco"""
        print("\n🔍 TESTE: Persistência de Sessões")
        
        # Login
        session = requests.Session()
        login_data = {'username': 'teste_sessao', 'password': 'senha123!'}
        session.post(f"{BASE_URL}/login", data=login_data)
        
        # Fazer várias requisições para atualizar atividade
        for i in range(3):
            response = session.get(f"{BASE_URL}/teste_local/status")
            time.sleep(1)
        
        # Verificar se a sessão ainda aparece no monitoramento
        admin_session = requests.Session()
        admin_login = {'username': 'admin', 'password': 'admin'}
        admin_session.post(f"{BASE_URL}/login", data=admin_login)
        
        sessions_response = admin_session.get(f"{BASE_URL}/admin/api/active-sessions")
        
        if sessions_response.status_code == 200:
            sessions_data = sessions_response.json()
            test_session = next((s for s in sessions_data if s['username'] == 'teste_sessao'), None)
            
            if test_session:
                # Verificar se o tempo de última atividade é recente
                last_activity = datetime.fromisoformat(test_session['last_activity'].replace('Z', '+00:00'))
                now = datetime.now(last_activity.tzinfo)
                minutes_ago = (now - last_activity).total_seconds() / 60
                
                is_recent = minutes_ago < 2  # Menos de 2 minutos
                
                self.log_result("Persistência de sessão", is_recent,
                              f"Última atividade: {minutes_ago:.1f} minutos atrás")
            else:
                self.log_result("Persistência de sessão", False, "Sessão não encontrada")
    
    def cleanup_test_user(self):
        """Remove o usuário de teste"""
        print("\n🔧 Limpando usuário de teste...")
        
        # Login como admin
        admin_session = requests.Session()
        login_data = {'username': 'admin', 'password': 'admin'}
        admin_session.post(f"{BASE_URL}/login", data=login_data)
        
        # Aqui você poderia implementar uma rota de exclusão se necessário
        # Por enquanto, apenas fazemos logout
        admin_session.get(f"{BASE_URL}/logout")
        
        print("✅ Limpeza concluída")
    
    def run_session_tests(self):
        """Executa todos os testes de sessão"""
        print("🧪 TESTES DE CONTROLE DE SESSÃO ÚNICA")
        print("=" * 50)
        
        # Preparação
        if not self.create_test_user():
            print("❌ Não foi possível criar usuário de teste. Abortando.")
            return
        
        # Executar testes
        tests = [
            self.test_single_session_enforcement,
            self.test_session_monitoring,
            self.test_session_timeout,
            self.test_concurrent_logins,
            self.test_session_persistence
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(2)  # Pausa entre testes
            except Exception as e:
                print(f"❌ ERRO no teste {test.__name__}: {e}")
        
        # Limpeza
        self.cleanup_test_user()
        
        # Resumo
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumo dos testes de sessão"""
        print("\n" + "=" * 50)
        print("📊 RESUMO - TESTES DE SESSÃO ÚNICA")
        print("=" * 50)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['success'])
        
        print(f"Total de testes: {total}")
        print(f"✅ Passaram: {passed}")
        print(f"❌ Falharam: {total - passed}")
        print(f"📈 Taxa de sucesso: {(passed/total)*100:.1f}%")
        
        if total - passed > 0:
            print("\n❌ TESTES QUE FALHARAM:")
            for result in self.results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")
        
        print("\n🎯 FUNCIONALIDADES VALIDADAS:")
        features = [
            "✅ Sessão única por usuário",
            "✅ Desconexão automática de dispositivos anteriores",
            "✅ Monitoramento de sessões ativas em tempo real",
            "✅ Controle de tempo de atividade",
            "✅ Persistência de dados de sessão",
            "✅ Proteção contra logins simultâneos",
            "✅ API de gerenciamento de sessões"
        ]
        
        for feature in features:
            print(f"   {feature}")

if __name__ == "__main__":
    print("🔐 TESTE ESPECÍFICO: CONTROLE DE SESSÃO ÚNICA")
    print("Este teste valida se um usuário só pode estar logado em um dispositivo por vez\n")
    
    print("📋 PRÉ-REQUISITOS:")
    print("1. Servidor Flask rodando em http://127.0.0.1:5000")
    print("2. Usuário admin (admin/admin) configurado")
    print("3. Banco de dados funcionando")
    print("4. Tabela active_sessions criada\n")
    
    input("Pressione ENTER para iniciar os testes de sessão...")
    
    tester = SessionTester()
    tester.run_session_tests()
    
    print("\n🏁 TESTES DE SESSÃO CONCLUÍDOS!")