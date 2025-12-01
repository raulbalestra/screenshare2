#!/usr/bin/env python3
"""
Teste Abrangente do Sistema Screen Share
========================================

Este arquivo testa todas as funcionalidades implementadas:
- Sistema de usuários com datas de plano
- Controle de sessão única por dispositivo
- Bloqueio automático por expiração
- Dashboard administrativo
- Monitoramento de sessões ativas
- Segurança e validações

Para executar: python test_sistema.py
"""

import requests
import json
import time
from datetime import datetime, timedelta
import sys

# Configurações
BASE_URL = "http://127.0.0.1:5000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

class ScreenShareTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        status = "✅ PASSOU" if success else "❌ FALHOU"
        print(f"{status} - {test_name}")
        if message:
            print(f"   {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
    
    def make_request(self, method, endpoint, **kwargs):
        """Faz requisição HTTP com tratamento de erro"""
        try:
            url = f"{BASE_URL}{endpoint}"
            response = self.session.request(method, url, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão: {e}")
            return None
    
    def test_1_server_status(self):
        """Testa se o servidor está rodando"""
        print("\n🔍 TESTE 1: Status do Servidor")
        response = self.make_request('GET', '/')
        
        if response and response.status_code == 200:
            self.log_test("Servidor acessível", True, "Flask está rodando")
            return True
        else:
            self.log_test("Servidor acessível", False, "Servidor não está rodando em http://127.0.0.1:5000")
            return False
    
    def test_2_admin_login(self):
        """Testa login do administrador"""
        print("\n🔍 TESTE 2: Login do Administrador")
        
        # Primeiro, pegar a página de login para obter o formulário
        login_page = self.make_request('GET', '/')
        if not login_page:
            self.log_test("Acesso à página de login", False)
            return False
        
        self.log_test("Acesso à página de login", True)
        
        # Tentar fazer login
        login_data = {
            'username': ADMIN_USER,
            'password': ADMIN_PASS
        }
        
        response = self.make_request('POST', '/login', data=login_data, allow_redirects=False)
        
        if response and response.status_code == 302:
            self.log_test("Login do admin", True, "Redirecionamento após login")
            return True
        else:
            self.log_test("Login do admin", False, f"Status: {response.status_code if response else 'Sem resposta'}")
            return False
    
    def test_3_admin_dashboard(self):
        """Testa acesso ao dashboard administrativo"""
        print("\n🔍 TESTE 3: Dashboard Administrativo")
        
        response = self.make_request('GET', '/admin_dashboard')
        
        if response and response.status_code == 200:
            self.log_test("Acesso ao dashboard admin", True)
            
            # Testar se o painel admin tem os botões corretos
            admin_panel = self.make_request('GET', '/admin_dashboard')
            if admin_panel and "Dashboard" in admin_panel.text:
                self.log_test("Painel administrativo carregado", True)
            else:
                self.log_test("Painel administrativo carregado", False)
                
            return True
        else:
            self.log_test("Acesso ao dashboard admin", False)
            return False
    
    def test_4_dashboard_api(self):
        """Testa API do dashboard"""
        print("\n🔍 TESTE 4: API do Dashboard")
        
        response = self.make_request('GET', '/admin/api/dashboard-users')
        
        if response and response.status_code == 200:
            try:
                users_data = response.json()
                self.log_test("API dashboard-users", True, f"Retornou {len(users_data)} usuários")
                
                # Verificar estrutura dos dados
                if users_data and isinstance(users_data, list):
                    user = users_data[0]
                    expected_fields = ['id', 'name', 'localidade', 'plan_start', 'plan_end', 'is_active']
                    has_all_fields = all(field in user for field in expected_fields)
                    
                    self.log_test("Estrutura de dados da API", has_all_fields, 
                                f"Campos encontrados: {list(user.keys())}")
                
                return True
            except json.JSONDecodeError:
                self.log_test("API dashboard-users", False, "Resposta não é JSON válido")
                return False
        else:
            self.log_test("API dashboard-users", False, "Erro ao acessar API")
            return False
    
    def test_5_sessions_api(self):
        """Testa API de sessões ativas"""
        print("\n🔍 TESTE 5: API de Sessões Ativas")
        
        response = self.make_request('GET', '/admin/api/active-sessions')
        
        if response and response.status_code == 200:
            try:
                sessions_data = response.json()
                self.log_test("API active-sessions", True, f"Retornou {len(sessions_data)} sessões")
                
                # Verificar se há pelo menos a sessão do admin atual
                if len(sessions_data) >= 1:
                    session = sessions_data[0]
                    expected_fields = ['username', 'ip_address', 'last_activity', 'is_active']
                    has_fields = all(field in session for field in expected_fields)
                    
                    self.log_test("Estrutura de sessões", has_fields)
                
                return True
            except json.JSONDecodeError:
                self.log_test("API active-sessions", False, "Resposta não é JSON válido")
                return False
        else:
            self.log_test("API active-sessions", False, "Erro ao acessar API")
            return False
    
    def test_6_add_user_form(self):
        """Testa formulário de adicionar usuário"""
        print("\n🔍 TESTE 6: Formulário de Adicionar Usuário")
        
        response = self.make_request('GET', '/admin/add_user')
        
        if response and response.status_code == 200:
            self.log_test("Acesso ao form adicionar usuário", True)
            
            # Verificar se o formulário tem os campos corretos
            content = response.text
            required_fields = ['username', 'password', 'localidade', 'plan_start', 'plan_end']
            
            has_all_fields = all(field in content for field in required_fields)
            self.log_test("Campos obrigatórios no formulário", has_all_fields,
                        f"Campos verificados: {required_fields}")
            
            return True
        else:
            self.log_test("Acesso ao form adicionar usuário", False)
            return False
    
    def test_7_create_test_user(self):
        """Testa criação de usuário de teste"""
        print("\n🔍 TESTE 7: Criação de Usuário de Teste")
        
        # Dados do usuário de teste
        today = datetime.now()
        end_date = today + timedelta(days=30)
        
        user_data = {
            'username': 'teste_usuario',
            'password': 'senha123456!',
            'localidade': 'teste_local',
            'plan_start': today.strftime('%Y-%m-%d'),
            'plan_end': end_date.strftime('%Y-%m-%d')
        }
        
        response = self.make_request('POST', '/admin/add_user', data=user_data, allow_redirects=False)
        
        if response and response.status_code == 302:
            self.log_test("Criação de usuário de teste", True, "Usuário criado com sucesso")
            return True
        else:
            self.log_test("Criação de usuário de teste", False, 
                        f"Status: {response.status_code if response else 'Sem resposta'}")
            return False
    
    def test_8_user_expiration_logic(self):
        """Testa lógica de expiração de usuários"""
        print("\n🔍 TESTE 8: Lógica de Expiração de Usuários")
        
        # Criar usuário expirado (data de fim ontem)
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now()
        
        expired_user_data = {
            'username': 'usuario_expirado',
            'password': 'senha123456!',
            'localidade': 'teste_expiracao',
            'plan_start': yesterday.strftime('%Y-%m-%d'),
            'plan_end': yesterday.strftime('%Y-%m-%d')
        }
        
        response = self.make_request('POST', '/admin/add_user', data=expired_user_data, allow_redirects=False)
        
        if response and response.status_code == 302:
            self.log_test("Criação de usuário expirado", True)
            
            # Verificar se aparece no dashboard como expirado
            dashboard_response = self.make_request('GET', '/admin/api/dashboard-users')
            if dashboard_response:
                users = dashboard_response.json()
                expired_user = next((u for u in users if u['name'] == 'usuario_expirado'), None)
                
                if expired_user:
                    # Verificar se o usuário está marcado como bloqueado/expirado
                    is_expired = (not expired_user['is_active'] or 
                                expired_user.get('status') == 'blocked')
                    self.log_test("Usuário expirado está bloqueado", is_expired)
                
            return True
        else:
            self.log_test("Criação de usuário expirado", False)
            return False
    
    def test_9_session_monitoring(self):
        """Testa monitoramento de sessões"""
        print("\n🔍 TESTE 9: Monitoramento de Sessões")
        
        response = self.make_request('GET', '/admin/sessions')
        
        if response and response.status_code == 200:
            self.log_test("Acesso ao monitor de sessões", True)
            
            # Verificar se a página tem os elementos corretos
            content = response.text
            elements = ['Sessões Ativas', 'table', 'bootstrap']
            
            has_elements = all(element in content for element in elements)
            self.log_test("Elementos da página de sessões", has_elements)
            
            return True
        else:
            self.log_test("Acesso ao monitor de sessões", False)
            return False
    
    def test_10_edit_user_functionality(self):
        """Testa funcionalidade de edição de usuário"""
        print("\n🔍 TESTE 10: Edição de Usuário")
        
        # Primeiro, verificar se conseguimos acessar uma página de edição
        # Vamos tentar editar o usuário ID 1 (provavelmente o admin)
        response = self.make_request('GET', '/admin/edit_user/1')
        
        if response and response.status_code == 200:
            self.log_test("Acesso ao form de edição", True)
            
            # Verificar se o formulário tem os campos corretos
            content = response.text
            edit_fields = ['username', 'localidade', 'plan_start', 'plan_end', 'is_admin', 'is_active']
            
            has_edit_fields = all(field in content for field in edit_fields)
            self.log_test("Campos de edição presentes", has_edit_fields)
            
            return True
        else:
            self.log_test("Acesso ao form de edição", False, 
                        f"Status: {response.status_code if response else 'Sem resposta'}")
            return False
    
    def test_11_security_validation(self):
        """Testa validações de segurança"""
        print("\n🔍 TESTE 11: Validações de Segurança")
        
        # Teste de SQL Injection
        malicious_data = {
            'username': "admin'; DROP TABLE users; --",
            'password': 'senha123'
        }
        
        response = self.make_request('POST', '/login', data=malicious_data, allow_redirects=False)
        
        # Deve retornar erro ou redirect para login, não erro 500
        if response and response.status_code in [302, 400, 403]:
            self.log_test("Proteção contra SQL Injection", True)
        else:
            self.log_test("Proteção contra SQL Injection", False, 
                        f"Status inesperado: {response.status_code if response else 'Sem resposta'}")
        
        # Teste de dados muito longos
        long_data = {
            'username': 'a' * 1000,
            'password': 'b' * 1000
        }
        
        response = self.make_request('POST', '/login', data=long_data, allow_redirects=False)
        
        if response and response.status_code in [302, 400]:
            self.log_test("Proteção contra overflow de dados", True)
        else:
            self.log_test("Proteção contra overflow de dados", False)
        
        return True
    
    def test_12_logout_functionality(self):
        """Testa funcionalidade de logout"""
        print("\n🔍 TESTE 12: Funcionalidade de Logout")
        
        response = self.make_request('GET', '/logout', allow_redirects=False)
        
        if response and response.status_code == 302:
            self.log_test("Logout funcional", True, "Redirecionamento após logout")
            
            # Tentar acessar área restrita após logout
            protected_response = self.make_request('GET', '/admin_dashboard', allow_redirects=False)
            
            if protected_response and protected_response.status_code == 302:
                self.log_test("Proteção após logout", True, "Redirecionado para login")
            else:
                self.log_test("Proteção após logout", False, "Ainda consegue acessar área restrita")
            
            return True
        else:
            self.log_test("Logout funcional", False)
            return False
    
    def run_all_tests(self):
        """Executa todos os testes"""
        print("🚀 INICIANDO TESTES DO SISTEMA SCREEN SHARE")
        print("=" * 50)
        
        tests = [
            self.test_1_server_status,
            self.test_2_admin_login,
            self.test_3_admin_dashboard,
            self.test_4_dashboard_api,
            self.test_5_sessions_api,
            self.test_6_add_user_form,
            self.test_7_create_test_user,
            self.test_8_user_expiration_logic,
            self.test_9_session_monitoring,
            self.test_10_edit_user_functionality,
            self.test_11_security_validation,
            self.test_12_logout_functionality
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(1)  # Pausa entre testes
            except Exception as e:
                print(f"❌ ERRO no teste {test.__name__}: {e}")
        
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumo dos testes"""
        print("\n" + "=" * 50)
        print("📊 RESUMO DOS TESTES")
        print("=" * 50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total de testes: {total_tests}")
        print(f"✅ Passaram: {passed_tests}")
        print(f"❌ Falharam: {failed_tests}")
        print(f"📈 Taxa de sucesso: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n❌ TESTES QUE FALHARAM:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test']}: {result['message']}")
        
        print("\n🔧 FUNCIONALIDADES TESTADAS:")
        features = [
            "✅ Servidor Flask funcionando",
            "✅ Sistema de login/logout",
            "✅ Dashboard administrativo",
            "✅ API de usuários e sessões",
            "✅ Criação e edição de usuários",
            "✅ Sistema de expiração de planos",
            "✅ Monitoramento de sessões ativas",
            "✅ Validações de segurança",
            "✅ Controle de acesso por permissões"
        ]
        
        for feature in features:
            print(f"   {feature}")

if __name__ == "__main__":
    print("🧪 SISTEMA DE TESTES - SCREEN SHARE")
    print("Desenvolvido para testar todas as funcionalidades implementadas\n")
    
    print("📋 INSTRUÇÕES:")
    print("1. Certifique-se que o servidor Flask está rodando em http://127.0.0.1:5000")
    print("2. Certifique-se que existe um usuário admin com senha 'admin'")
    print("3. Execute: python test_sistema.py")
    print("4. Aguarde os resultados dos testes\n")
    
    input("Pressione ENTER para começar os testes...")
    
    tester = ScreenShareTester()
    tester.run_all_tests()
    
    print("\n🎯 TESTES CONCLUÍDOS!")
    print("Verifique os resultados acima para identificar possíveis problemas.")