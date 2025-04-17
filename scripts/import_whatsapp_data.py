"""
Script para importar dados de WhatsApp dos responsáveis.
Este script deve ser executado depois que os responsáveis já estão cadastrados no sistema.
"""
import sys
import os

# Adicionar diretório raiz ao path para importar os módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Guardian

# Dados de contato de WhatsApp dos responsáveis
whatsapp_data = [
    ("Daniella Risola", "+55 19 98224-4747", "https://wa.me/5519982244747"),
    ("Marcela", "+55 19 98911-3534", "https://wa.me/5519989113534"),
    ("Maysa", "+55 19 99891-6701", "https://wa.me/5519998916701"),
    ("Karin", "+55 11 97626-9474", "https://wa.me/5511976269474"),
    ("Giovanela", "+55 19 98186-7873", "https://wa.me/5519981867873"),
    ("Mariana", "+55 19 99130-8899", "https://wa.me/5519991308899"),
    ("Silvia", "+55 19 99602-8813", "https://wa.me/5519996028813"),
    ("Gisele", "+55 19 99928-4241", "https://wa.me/5519999284241"),
    ("Márcia", "+55 19 99603-7665", "https://wa.me/5519996037665"),
    ("Jacqueline Polisel", "+55 19 97402-9787", "https://wa.me/5519974029787"),
    ("Leandro", "+55 11 97679-6336", "https://wa.me/5511976796336")
]

def import_whatsapp_data():
    """
    Importa os dados de WhatsApp para os responsáveis existentes.
    
    Returns:
        int: Número de responsáveis atualizados
    """
    updated_count = 0
    
    with app.app_context():
        for name, phone, whatsapp_link in whatsapp_data:
            # Buscar guardião pelo nome (usando like para correspondência parcial)
            guardian = Guardian.query.filter(Guardian.name.like(f"%{name}%")).first()
            
            if guardian:
                guardian.phone = phone if not guardian.phone else guardian.phone
                guardian.whatsapp = whatsapp_link
                updated_count += 1
                print(f"Atualizado: {guardian.name} - WhatsApp: {whatsapp_link}")
            else:
                print(f"Responsável não encontrado: {name}")
        
        # Commit das alterações
        if updated_count > 0:
            db.session.commit()
    
    return updated_count

if __name__ == "__main__":
    print("Importando dados de WhatsApp dos responsáveis...")
    updated = import_whatsapp_data()
    print(f"Importação concluída! {updated} responsáveis atualizados.")