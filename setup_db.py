#!/usr/bin/env python3
"""
Script para criar as tabelas do banco de dados uma única vez
Execute apenas uma vez após o deploy inicial
"""

import os
import sys

# Adicionar o diretório do projeto ao path
sys.path.append('/opt/render/project/src' if '/opt/render' in os.getcwd() else '.')

from app import create_database

if __name__ == "__main__":
    try:
        print("Criando tabelas do banco de dados...")
        create_database()
        print("✅ Tabelas criadas com sucesso!")
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        sys.exit(1)