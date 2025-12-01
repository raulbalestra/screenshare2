#!/usr/bin/env python3
# Script para verificar os eventos registrados
import psycopg2
import os
from datetime import datetime

def verificar_eventos():
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'screenshare'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '101410'),
            port=os.getenv('DB_PORT', '5432')
        )
        cursor = conn.cursor()
        
        print("=" * 50)
        print("🔍 VERIFICAÇÃO DE EVENTOS DE MONITORAMENTO")
        print("=" * 50)
        
        # Total de eventos
        cursor.execute("SELECT COUNT(*) FROM usage_events")
        total = cursor.fetchone()[0]
        print(f"📊 Total de eventos registrados: {total}")
        
        if total > 0:
            # Últimos eventos
            print("\n📝 ÚLTIMOS 10 EVENTOS:")
            cursor.execute("""
                SELECT u.username, ue.localidade, ue.event_type, ue.created_at
                FROM usage_events ue
                JOIN users u ON u.id = ue.user_id
                ORDER BY ue.created_at DESC
                LIMIT 10
            """)
            eventos = cursor.fetchall()
            
            for evento in eventos:
                time_str = evento[3].strftime("%d/%m/%Y %H:%M:%S")
                print(f"  • {evento[0]} ({evento[1]}) → {evento[2]} em {time_str}")
            
            # Dados da VIEW
            print("\n👥 DADOS DA VIEW v_user_usage:")
            cursor.execute("""
                SELECT username, localidade, last_activity_at, access_last_30d, using_now
                FROM v_user_usage
                ORDER BY using_now DESC, last_activity_at DESC NULLS LAST
            """)
            users = cursor.fetchall()
            
            for user in users:
                status = "🟢 ONLINE" if user[4] else "🔴 OFFLINE"
                last_activity = user[2].strftime("%d/%m/%Y %H:%M:%S") if user[2] else "Nunca"
                print(f"  • {user[0]} ({user[1]}) - {status}")
                print(f"    └─ Última atividade: {last_activity}")
                print(f"    └─ Eventos (30d): {user[3]}")
                
        else:
            print("\n⚠️  Nenhum evento registrado ainda.")
            print("📋 PRÓXIMOS PASSOS:")
            print("1. Faça login no sistema")
            print("2. Use o compartilhamento de tela")  
            print("3. Execute este script novamente")
        
        print("\n" + "=" * 50)
        print("✅ VERIFICAÇÃO CONCLUÍDA")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    verificar_eventos()