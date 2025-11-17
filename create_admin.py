"""
Script para criar usuário administrador
Usage:
    python create_admin.py
"""
import os
import sys

# ensure project dir is on path
project_root = os.path.dirname(__file__)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.models import UserManager


def main():
    try:
        print("Criando usuário administrador...")
        
        # Criar admin
        username = "admin"
        email = "admin@raizen.com"
        password = "admin123"
        localidade = "São Paulo"
        
        success = UserManager.create_user(username, email, password, localidade, is_admin=True)
        
        if success:
            print(f"✅ Usuário admin criado com sucesso!")
            print(f"   Username: {username}")
            print(f"   Email: {email}")
            print(f"   Senha: {password}")
            print(f"   Localidade: {localidade}")
        else:
            print("⚠️  Usuário já existe ou erro ao criar")
            
    except Exception as e:
        print(f"❌ Erro ao criar admin: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
