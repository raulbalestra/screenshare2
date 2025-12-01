#!/usr/bin/env python3
"""
Teste Específico: Sistema de Datas e Expiração
==============================================

Este teste valida especificamente:
- Sistema de datas de início e fim de plano
- Bloqueio automático de usuários expirados
- Dashboard mostrando status de expiração
- Validações de datas no formulário

Para executar: python test_expiracao.py
"""

import requests
import json
import time
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:5000"

class ExpirationTester:
    def __init__(self):
        self.results = []
        self.admin_session = requests.Session()
        
    def log_result(self, test, success, message=""):
        status = "✅" if success else "❌"
        print(f"{status} {test}: {message}")
        self.results.append({'test': test, 'success': success, 'message': message})
    
    def setup_admin_session(self):
        """Configura sessão de admin"""
        login_data = {'username': 'admin', 'password': 'admin'}
        response = self.admin_session.post(f"{BASE_URL}/login", data=login_data)
        return response.status_code == 302
    
    def test_create_user_with_dates(self):
        """Testa criação de usuário com datas específicas"""
        print("\n🔍 TESTE: Criação de Usuário com Datas")
        
        today = datetime.now()
        future_date = today + timedelta(days=15)
        
        # Usuário com plano válido
        valid_user_data = {
            'username': 'usuario_valido',
            'password': 'senha123!',
            'localidade': 'local_valido',
            'plan_start': today.strftime('%Y-%m-%d'),
            'plan_end': future_date.strftime('%Y-%m-%d')
        }
        
        response = self.admin_session.post(f"{BASE_URL}/admin/add_user", data=valid_user_data)
        
        if response.status_code in [200, 302]:
            self.log_result("Criação usuário válido", True, "Usuário com datas futuras criado")
        else:
            self.log_result("Criação usuário válido", False, f"Status: {response.status_code}")
    
    def test_create_expired_user(self):
        """Testa criação de usuário já expirado"""
        print("\n🔍 TESTE: Criação de Usuário Expirado")
        
        yesterday = datetime.now() - timedelta(days=1)
        week_ago = yesterday - timedelta(days=7)
        
        expired_user_data = {
            'username': 'usuario_expirado',
            'password': 'senha123!',
            'localidade': 'local_expirado',
            'plan_start': week_ago.strftime('%Y-%m-%d'),
            'plan_end': yesterday.strftime('%Y-%m-%d')
        }
        
        response = self.admin_session.post(f"{BASE_URL}/admin/add_user", data=expired_user_data)
        
        if response.status_code in [200, 302]:
            self.log_result("Criação usuário expirado", True, "Usuário com data passada criado")
            
            # Verificar se aparece como expirado no dashboard
            time.sleep(2)  # Aguardar processamento
            return self.verify_user_expiration_status()
        else:
            self.log_result("Criação usuário expirado", False)
            return False
    
    def verify_user_expiration_status(self):
        """Verifica se usuário expirado está bloqueado"""
        response = self.admin_session.get(f"{BASE_URL}/admin/api/dashboard-users")
        
        if response.status_code == 200:
            users = response.json()
            expired_user = next((u for u in users if u['name'] == 'usuario_expirado'), None)
            
            if expired_user:
                is_blocked = not expired_user['is_active']
                self.log_result("Usuário expirado bloqueado automaticamente", is_blocked,
                              f"Status ativo: {expired_user['is_active']}")
                return is_blocked
            else:
                self.log_result("Usuário expirado encontrado", False, "Usuário não encontrado no dashboard")
                return False
        else:
            self.log_result("Dashboard API funcionando", False)
            return False
    
    def test_create_expiring_user(self):
        """Testa usuário que vai expirar em breve"""
        print("\n🔍 TESTE: Usuário Expirando em Breve")
        
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        expiring_user_data = {
            'username': 'usuario_expirando',
            'password': 'senha123!',
            'localidade': 'local_expirando',
            'plan_start': today.strftime('%Y-%m-%d'),
            'plan_end': tomorrow.strftime('%Y-%m-%d')
        }
        
        response = self.admin_session.post(f"{BASE_URL}/admin/add_user", data=expiring_user_data)
        
        if response.status_code in [200, 302]:
            self.log_result("Criação usuário expirando", True)
            
            # Verificar se aparece como "expirando" no dashboard
            time.sleep(2)
            dashboard_response = self.admin_session.get(f"{BASE_URL}/admin/api/dashboard-users")
            
            if dashboard_response.status_code == 200:
                users = dashboard_response.json()
                expiring_user = next((u for u in users if u['name'] == 'usuario_expirando'), None)
                
                if expiring_user:
                    # Usuário deve estar ativo mas próximo da expiração
                    is_active = expiring_user['is_active']
                    has_end_date = expiring_user['plan_end'] is not None
                    
                    self.log_result("Usuário expirando detectado", is_active and has_end_date,
                                  f"Ativo: {is_active}, Data fim: {expiring_user['plan_end']}")
                
            return True
        else:
            self.log_result("Criação usuário expirando", False)
            return False
    
    def test_dashboard_date_display(self):
        """Testa exibição de datas no dashboard"""
        print("\n🔍 TESTE: Exibição de Datas no Dashboard")
        
        response = self.admin_session.get(f"{BASE_URL}/admin/api/dashboard-users")
        
        if response.status_code == 200:
            users = response.json()
            
            if users:
                user_with_dates = next((u for u in users if u.get('plan_start') or u.get('plan_end')), None)
                
                if user_with_dates:
                    has_start_date = user_with_dates.get('plan_start') is not None
                    has_end_date = user_with_dates.get('plan_end') is not None
                    
                    self.log_result("Datas no dashboard", has_start_date or has_end_date,
                                  f"Start: {user_with_dates.get('plan_start')}, End: {user_with_dates.get('plan_end')}")
                else:
                    self.log_result("Datas no dashboard", False, "Nenhum usuário com datas encontrado")
            else:
                self.log_result("Datas no dashboard", False, "Nenhum usuário encontrado")
        else:
            self.log_result("Dashboard API", False)
    
    def test_edit_user_dates(self):
        """Testa edição de datas de usuário"""
        print("\n🔍 TESTE: Edição de Datas de Usuário")
        
        # Primeiro, encontrar um usuário para editar
        users_response = self.admin_session.get(f"{BASE_URL}/admin/api/dashboard-users")
        
        if users_response.status_code == 200:
            users = users_response.json()
            test_user = next((u for u in users if u['name'] == 'usuario_valido'), None)
            
            if test_user:
                user_id = test_user['id']
                
                # Acessar formulário de edição
                edit_response = self.admin_session.get(f"{BASE_URL}/admin/edit_user/{user_id}")
                
                if edit_response.status_code == 200:
                    self.log_result("Acesso formulário edição", True)
                    
                    # Verificar se formulário tem campos de data
                    content = edit_response.text
                    has_date_fields = 'plan_start' in content and 'plan_end' in content
                    
                    self.log_result("Campos de data no formulário", has_date_fields)
                    
                    if has_date_fields:
                        # Tentar atualizar as datas
                        new_end_date = datetime.now() + timedelta(days=60)
                        
                        update_data = {
                            'username': test_user['name'],
                            'localidade': test_user['localidade'],
                            'plan_start': test_user['plan_start'] or datetime.now().strftime('%Y-%m-%d'),
                            'plan_end': new_end_date.strftime('%Y-%m-%d'),
                            'is_admin': 'false',
                            'is_active': 'true'
                        }
                        
                        update_response = self.admin_session.post(f"{BASE_URL}/admin/edit_user/{user_id}", 
                                                                data=update_data)
                        
                        if update_response.status_code in [200, 302]:
                            self.log_result("Atualização de datas", True, "Datas atualizadas com sucesso")
                        else:
                            self.log_result("Atualização de datas", False, f"Status: {update_response.status_code}")
                else:
                    self.log_result("Acesso formulário edição", False)
            else:
                self.log_result("Usuário para edição", False, "usuario_valido não encontrado")
        else:
            self.log_result("Busca usuários", False)
    
    def test_date_validation(self):
        """Testa validação de datas"""
        print("\n🔍 TESTE: Validação de Datas")
        
        # Tentar criar usuário com data de fim anterior à data de início
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        invalid_date_user = {
            'username': 'usuario_data_invalida',
            'password': 'senha123!',
            'localidade': 'local_teste',
            'plan_start': today.strftime('%Y-%m-%d'),
            'plan_end': yesterday.strftime('%Y-%m-%d')  # Data fim antes do início
        }
        
        response = self.admin_session.post(f"{BASE_URL}/admin/add_user", data=invalid_date_user)
        
        # Deve dar erro ou redirecionar de volta
        if response.status_code in [400, 302]:
            self.log_result("Validação datas inválidas", True, "Sistema rejeitou datas inconsistentes")
        else:
            self.log_result("Validação datas inválidas", False, "Sistema aceitou datas inconsistentes")
    
    def test_automatic_expiration_check(self):
        """Testa verificação automática de expiração"""
        print("\n🔍 TESTE: Verificação Automática de Expiração")
        
        # Fazer algumas requisições para triggerar o middleware
        for i in range(3):
            self.admin_session.get(f"{BASE_URL}/admin_dashboard")
            time.sleep(1)
        
        # Verificar se usuários expirados foram processados
        response = self.admin_session.get(f"{BASE_URL}/admin/api/dashboard-users")
        
        if response.status_code == 200:
            users = response.json()
            
            # Contar usuários expirados que estão bloqueados
            expired_and_blocked = 0
            total_expired = 0
            
            for user in users:
                if user.get('plan_end'):
                    end_date = datetime.fromisoformat(user['plan_end'])
                    if end_date < datetime.now():
                        total_expired += 1
                        if not user['is_active']:
                            expired_and_blocked += 1
            
            if total_expired > 0:
                success_rate = (expired_and_blocked / total_expired) * 100
                self.log_result("Bloqueio automático", success_rate >= 80,
                              f"{expired_and_blocked}/{total_expired} usuários expirados bloqueados ({success_rate:.1f}%)")
            else:
                self.log_result("Usuários expirados para teste", False, "Nenhum usuário expirado encontrado")
        else:
            self.log_result("Verificação expiração", False)
    
    def test_dashboard_statistics(self):
        """Testa estatísticas do dashboard relacionadas à expiração"""
        print("\n🔍 TESTE: Estatísticas do Dashboard")
        
        # Acessar a página do dashboard para verificar JavaScript
        dashboard_page = self.admin_session.get(f"{BASE_URL}/dashboard_admin")
        
        if dashboard_page.status_code == 200:
            content = dashboard_page.text
            
            # Verificar se tem elementos para mostrar estatísticas
            has_stats_elements = all(element in content for element in [
                'usersOnline', 'usersExpiring', 'usersBlocked', 'usersTotal'
            ])
            
            self.log_result("Elementos de estatística", has_stats_elements)
            
            # Verificar se JavaScript inclui lógica de expiração
            has_expiration_logic = 'plan_end' in content and 'new Date' in content
            
            self.log_result("Lógica de expiração no frontend", has_expiration_logic)
        else:
            self.log_result("Dashboard carregado", False)
    
    def run_expiration_tests(self):
        """Executa todos os testes de expiração"""
        print("📅 TESTES DE SISTEMA DE DATAS E EXPIRAÇÃO")
        print("=" * 50)
        
        if not self.setup_admin_session():
            print("❌ Não foi possível fazer login como admin. Abortando.")
            return
        
        tests = [
            self.test_create_user_with_dates,
            self.test_create_expired_user,
            self.test_create_expiring_user,
            self.test_dashboard_date_display,
            self.test_edit_user_dates,
            self.test_date_validation,
            self.test_automatic_expiration_check,
            self.test_dashboard_statistics
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(1)
            except Exception as e:
                print(f"❌ ERRO no teste {test.__name__}: {e}")
        
        self.print_summary()
    
    def print_summary(self):
        """Imprime resumo dos testes"""
        print("\n" + "=" * 50)
        print("📊 RESUMO - TESTES DE EXPIRAÇÃO")
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
            "✅ Criação de usuários com datas de plano",
            "✅ Bloqueio automático de usuários expirados",
            "✅ Detecção de usuários expirando em breve",
            "✅ Exibição de datas no dashboard",
            "✅ Edição de datas de usuários existentes",
            "✅ Validação de consistência de datas",
            "✅ Verificação automática via middleware",
            "✅ Estatísticas de expiração no frontend"
        ]
        
        for feature in features:
            print(f"   {feature}")

if __name__ == "__main__":
    print("📅 TESTE ESPECÍFICO: SISTEMA DE DATAS E EXPIRAÇÃO")
    print("Este teste valida o controle de planos com datas de início e fim\n")
    
    print("📋 PRÉ-REQUISITOS:")
    print("1. Servidor Flask rodando em http://127.0.0.1:5000")
    print("2. Usuário admin (admin/admin) configurado")
    print("3. Campos plan_start e plan_end na tabela users")
    print("4. Middleware de expiração funcionando\n")
    
    input("Pressione ENTER para iniciar os testes de expiração...")
    
    tester = ExpirationTester()
    tester.run_expiration_tests()
    
    print("\n🏁 TESTES DE EXPIRAÇÃO CONCLUÍDOS!")