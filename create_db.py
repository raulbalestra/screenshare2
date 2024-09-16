import sqlite3

def reset_database():
    # Conecta ao banco de dados (ou cria um novo se não existir)
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # Apaga a tabela existente
    cursor.execute('DROP TABLE IF EXISTS users')

    # Cria a tabela novamente
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            localidade TEXT NOT NULL
        )
    ''')

    # Inserindo os dados iniciais no banco de dados
    cursor.execute('''
        INSERT INTO users (username, password, localidade)
        VALUES
        ('curitiba_user', 'senha_curitiba', 'curitiba'),
        ('sp_user', 'senha_sp', 'sp')
    ''')

    # Salva as mudanças e fecha a conexão
    conn.commit()
    conn.close()

# Execute esta função para resetar o banco de dados e a tabela
reset_database()
