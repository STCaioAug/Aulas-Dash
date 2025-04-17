"""
Migração para adicionar a coluna lesson_type à tabela Lesson.

Este script adiciona a coluna lesson_type à tabela lesson existente.
Ele deve ser executado uma única vez para atualizar o banco de dados.
"""

import sys
import os
import sqlite3
from datetime import datetime

# Adiciona o diretório raiz ao path para importar o app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def add_lesson_type_column():
    """
    Adiciona a coluna lesson_type à tabela lesson com valor padrão 'fixed'.
    
    Returns:
        bool: True se a migração foi bem-sucedida, False caso contrário.
    """
    try:
        # Caminho para o banco de dados SQLite
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'tutoring.db')
        
        # Verifica se o banco de dados existe
        if not os.path.exists(db_path):
            print(f"Banco de dados não encontrado em {db_path}")
            return False
            
        # Conecta ao banco de dados
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se a coluna já existe
        cursor.execute("PRAGMA table_info(lesson)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'lesson_type' not in column_names:
            # Adiciona a coluna lesson_type com valor padrão 'fixed'
            cursor.execute("ALTER TABLE lesson ADD COLUMN lesson_type VARCHAR(20) DEFAULT 'fixed'")
            
            # Commit das alterações
            conn.commit()
            print("Coluna 'lesson_type' adicionada com sucesso à tabela 'lesson'")
        else:
            print("A coluna 'lesson_type' já existe na tabela 'lesson'")
            
        # Fecha a conexão
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro durante a migração: {str(e)}")
        return False

if __name__ == "__main__":
    print("Iniciando migração para adicionar coluna lesson_type...")
    success = add_lesson_type_column()
    
    if success:
        print("Migração concluída com sucesso!")
    else:
        print("Erro durante a migração. Verifique os logs para mais detalhes.")