"""
Script para importar dados de aulas fixas, aulas extras, feriados e observações.

Este script importa os dados fornecidos sobre aulas fixas de 2025, 
aulas extras, feriados e observações para o banco de dados.
"""

import sys
import os
import re
from datetime import datetime, date, time, timedelta

# Adiciona o diretório pai ao path para importar os módulos do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Student, Guardian, Lesson, Holiday

def parse_time_range(time_str):
    """Converte uma string de intervalo de tempo (ex: '15:00-16:30') em objetos time."""
    # Trata diferentes formatos de hora: 15:00-16:30 ou 15h00-16h30
    clean_str = time_str.replace('h', ':')
    if '-' not in clean_str:
        return None, None
    
    start_str, end_str = clean_str.split('-')
    
    # Converter para objetos time
    try:
        start_parts = start_str.strip().split(':')
        if len(start_parts) == 1:
            start_parts.append('00')
        start_hour, start_minute = map(int, start_parts)
        
        end_parts = end_str.strip().split(':')
        if len(end_parts) == 1:
            end_parts.append('00')
        end_hour, end_minute = map(int, end_parts)
        
        start_time = time(start_hour, start_minute)
        end_time = time(end_hour, end_minute)
        
        return start_time, end_time
    except (ValueError, TypeError):
        print(f"Erro ao converter horário: {time_str}")
        return None, None

def parse_date(date_str):
    """Converte uma string de data (ex: '01/04') em objeto date."""
    if not date_str or date_str == "(sem data)":
        return None
    
    try:
        # Assumindo formato DD/MM
        day, month = map(int, date_str.split('/'))
        year = 2025  # Ano fixo conforme especificado nos dados
        return date(year, month, day)
    except (ValueError, TypeError):
        print(f"Erro ao converter data: {date_str}")
        return None

def find_or_create_student(name):
    """Busca um aluno pelo nome ou cria novo se não existir."""
    # Extrai o primeiro nome para busca
    first_name = name.split()[0]
    
    # Busca por alunos com o mesmo primeiro nome
    students = Student.query.filter(Student.name.ilike(f"%{first_name}%")).all()
    
    if students:
        # Se encontrar exatamente um aluno, retorna
        if len(students) == 1:
            return students[0]
        
        # Se encontrar múltiplos, tenta encontrar o melhor match
        for student in students:
            # Correspondência exata
            if student.name.lower() == name.lower():
                return student
            
            # Correspondência parcial (nome é parte do nome completo do aluno)
            student_parts = student.name.lower().split()
            name_parts = name.lower().split()
            
            if all(part in student_parts for part in name_parts):
                return student
    
    # Se não encontrar, cria novo estudante
    print(f"Criando novo aluno: {name}")
    new_student = Student(name=name)
    db.session.add(new_student)
    db.session.commit()
    return new_student

def extract_location(info):
    """Extrai informações de localização de uma string."""
    location = None
    
    # Procura por padrões de localização após o símbolo | ou após um espaço
    location_patterns = [
        r'\|\s*(.*)',                  # Texto após |
        r'Apto\s+\d+\s+Torre\s+\d+',   # Apto seguido de número e torre
        r'Apto\s+\d+',                 # Apenas apartamento
    ]
    
    for pattern in location_patterns:
        match = re.search(pattern, info)
        if match:
            location = match.group(1) if '|' in pattern else match.group(0)
            location = location.strip()
            break
    
    return location

def extract_guardian_name(info):
    """Extrai nome do responsável entre parênteses."""
    guardian_match = re.search(r'\((.*?)\)', info)
    return guardian_match.group(1) if guardian_match else None

def import_fixed_lessons():
    """Importa as aulas fixas do ano de 2025."""
    print("Importando aulas fixas de 2025...")
    
    # Mapeamento de dia da semana para número (0=segunda, 6=domingo)
    weekday_map = {
        'segunda': 0,
        'terça': 1,
        'quarta': 2,
        'quinta': 3,
        'sexta': 4,
        'sábado': 5,
        'domingo': 6
    }
    
    # Dados das aulas fixas
    fixed_lessons = {
        'segunda': [
            "Maria (Giovanella) | 15:00-16:30 | Apto 111 Torre 1",
            "João (Apto 91 Torre 2) | 16:40-17:40"
        ],
        'terça': [
            "Lourenço (Maysa) | 15:30-17:00",
            "Gabi Selencio (Silvia) | 17:00-18:00"
        ],
        'quarta': [
            "Lorenzo (Márcia Maciel) | 14:30-15:30",
            "Otávio (Filho da Gisele) | 15:30-17:00",
            "Pietro (Marcela) | 17:30-19:00"
        ],
        'quinta': [
            "Pedro (Dani) | 15:00-16:00",
            "Carol (Dani) | 16:00-17:00"
        ],
        'sexta': [
            "Lourenço (Maysa) | 14:30-16:00",
            "Gui/Pedrão (Karin) | 16:00-17:30"
        ],
        'sábado': [
            "João Paulo | 08:30-09:30 | Aula de Inglês"
        ]
    }
    
    # Limpar aulas fixas existentes para 2025 para evitar duplicação
    start_date = date(2025, 1, 1)
    end_date = date(2025, 12, 31)
    Lesson.query.filter(
        Lesson.date >= start_date,
        Lesson.date <= end_date,
        Lesson.lesson_type == 'fixed'
    ).delete()
    db.session.commit()
    
    # Gerar todas as datas de 2025
    current_date = date(2025, 1, 1)
    end_of_year = date(2025, 12, 31)
    
    lessons_added = 0
    
    while current_date <= end_of_year:
        weekday = current_date.weekday()
        
        # Converter número do dia da semana para nome
        weekday_name = list(weekday_map.keys())[list(weekday_map.values()).index(weekday)]
        
        # Se houver aulas para este dia da semana
        if weekday_name in fixed_lessons:
            for lesson_info in fixed_lessons[weekday_name]:
                # Extrair informações da aula
                if '|' in lesson_info:
                    parts = lesson_info.split('|')
                    student_info = parts[0].strip()
                    time_info = parts[1].strip() if len(parts) > 1 else None
                    location = parts[2].strip() if len(parts) > 2 else None
                    
                    # Se o terceiro campo contém "Aula de", é o assunto
                    subject = None
                    if location and "Aula de" in location:
                        subject = location
                        location = None
                else:
                    student_info = lesson_info
                    time_info = None
                    location = None
                
                # Extrair informações do aluno
                if '(' in student_info:
                    student_name = student_info.split('(')[0].strip()
                    guardian_name = extract_guardian_name(student_info)
                else:
                    student_name = student_info.strip()
                    guardian_name = None
                
                # Se contiver '/', são múltiplos alunos na mesma aula
                student_names = [name.strip() for name in student_name.split('/')]
                
                # Extrair horário
                start_time, end_time = None, None
                if time_info:
                    start_time, end_time = parse_time_range(time_info)
                
                # Para cada aluno na lista, criar aula
                for name in student_names:
                    student = find_or_create_student(name)
                    
                    # Se não tiver assunto específico, usar matéria genérica
                    if not subject:
                        subject = "Matéria Escolar"
                    
                    # Criar nova aula
                    new_lesson = Lesson(
                        student_id=student.id,
                        date=current_date,
                        start_time=start_time,
                        end_time=end_time,
                        subject=subject,
                        status='scheduled',
                        lesson_type='fixed',
                        notes=f"Aula fixa de {weekday_name}. {f'Local: {location}' if location else ''} {f'Responsável: {guardian_name}' if guardian_name else ''}"
                    )
                    
                    db.session.add(new_lesson)
                    lessons_added += 1
        
        # Avançar para o próximo dia
        current_date += timedelta(days=1)
    
    db.session.commit()
    print(f"Aulas fixas importadas: {lessons_added}")

def import_extra_lessons():
    """Importa as aulas extras agendadas."""
    print("Importando aulas extras agendadas...")
    
    # Dados das aulas extras
    extra_lessons = [
        "Felipe | 01/04 | 19:30-21:00",
        "Felipe | 16/04 | 18:30-20:30",
        "Felipe | 22/04 | 18:30",
        "Felipe | 28/03 | 18:00 | Física",
        "Felipe | 03/04 | 18:30 | Matemática",
        "Felipe | 07/03 | (sem horário) | Revisão Matemática",
        "Felipe | 24/04 | (sem horário) | Química",
        "Pietro | 04/04 | 18:00-19:30 | Álgebra",
        "Pietro | 09/04 | (sem horário) | Geometria",
        "Pietro | 14/04 | (sem horário) | Química",
        "Pietro | 23/04 | (sem horário) | Física",
        "João (Filho da Mariana) | 23/04 | 16:00 | Estudo para prova dia 29/04 | STATUS: PENDENTE DE CONFIRMAÇÃO",
        "Maria | (sem data) | (terça-feira) | Aula extra a confirmar"
    ]
    
    lessons_added = 0
    
    for lesson_info in extra_lessons:
        parts = [part.strip() for part in lesson_info.split('|')]
        
        # Extrair informações básicas
        student_info = parts[0]
        
        # Extrair nome do aluno e responsável
        if '(' in student_info:
            student_name = student_info.split('(')[0].strip()
            guardian_name = extract_guardian_name(student_info)
        else:
            student_name = student_info
            guardian_name = None
        
        # Extrair data
        lesson_date = None
        if len(parts) > 1:
            date_str = parts[1]
            
            # Verificar se contém um dia da semana
            weekday_pattern = r'\(([^)]*dia|segunda|terça|quarta|quinta|sexta|sábado|domingo)[^)]*\)'
            weekday_match = re.search(weekday_pattern, date_str, re.IGNORECASE)
            
            if weekday_match:
                # Caso especial para data por dia da semana
                weekday_info = weekday_match.group(1).lower()
                # Aqui usaríamos essa informação para encontrar a próxima data deste dia da semana
                # Por simplicidade, deixaremos como None e adicionaremos isso nas observações
                lesson_date = None
            elif "sem data" not in date_str.lower():
                lesson_date = parse_date(date_str)
        
        # Extrair horário
        start_time, end_time = None, None
        if len(parts) > 2:
            time_str = parts[2]
            if "sem horário" not in time_str.lower():
                start_time, end_time = parse_time_range(time_str)
                
                # Se só temos horário de início, assumir 1h de duração
                if start_time and not end_time:
                    hour = (start_time.hour + 1) % 24
                    end_time = time(hour, start_time.minute)
        
        # Extrair assunto/matéria
        subject = "Aula Extra"
        if len(parts) > 3:
            subject = parts[3]
        
        # Extrair status ou outras observações
        status = 'scheduled'
        notes = ""
        if len(parts) > 4:
            status_info = parts[4]
            if "PENDENTE" in status_info:
                status = 'pending'
                notes = status_info
        
        # Encontrar ou criar aluno
        student = find_or_create_student(student_name)
        
        # Criar notas combinando informações
        if guardian_name:
            notes += f" Responsável: {guardian_name}."
            
        if not lesson_date:
            notes += " Data a confirmar."
            
        if not start_time or not end_time:
            notes += " Horário a confirmar."
        
        # Só adicionar aulas com data definida
        if lesson_date:
            # Verificar se já existe uma aula igual para evitar duplicação
            existing_lesson = Lesson.query.filter(
                Lesson.student_id == student.id,
                Lesson.date == lesson_date,
                Lesson.subject == subject,
                Lesson.lesson_type == 'extra'
            ).first()
            
            if not existing_lesson:
                new_lesson = Lesson(
                    student_id=student.id,
                    date=lesson_date,
                    start_time=start_time,
                    end_time=end_time,
                    subject=subject,
                    status=status,
                    lesson_type='extra',
                    notes=notes.strip()
                )
                
                db.session.add(new_lesson)
                lessons_added += 1
        else:
            # Para aulas sem data definida, adicionar apenas no console
            print(f"Aula sem data definida: {student_name} - {subject} - {notes}")
    
    db.session.commit()
    print(f"Aulas extras importadas: {lessons_added}")

def import_holidays():
    """Importa feriados e dias sem aula."""
    print("Importando feriados e dias sem aula...")
    
    # Dados dos feriados
    holidays = [
        "18/04/2025 - Feriado Prolongado",
        "19/04/2025 - Feriado Prolongado",
        "20/04/2025 - Feriado Prolongado",
        "21/04/2025 - Feriado Prolongado"
    ]
    
    # Para cada feriado, adicionar marcação no banco de dados
    for holiday_info in holidays:
        parts = holiday_info.split(' - ')
        if len(parts) >= 1:
            holiday_date = parse_date(parts[0])
            description = parts[1] if len(parts) > 1 else "Feriado"
            
            if holiday_date:
                # Verificar se já existe este feriado registrado
                existing_holiday = Holiday.query.filter_by(date=holiday_date).first()
                
                if not existing_holiday:
                    # Criar novo registro de feriado
                    new_holiday = Holiday(
                        date=holiday_date,
                        description=description,
                        notes="Importado automaticamente do script de dados."
                    )
                    db.session.add(new_holiday)
                
                # Marcar todas as aulas nesta data como canceladas
                lessons = Lesson.query.filter(
                    Lesson.date == holiday_date
                ).all()
                
                for lesson in lessons:
                    lesson.status = 'cancelled'
                    lesson.notes = f"{lesson.notes or ''}\nCancelada - {description}".strip()
                
                db.session.commit()
                print(f"Feriado importado: {holiday_date} - {description}")

def import_observations():
    """Importa observações gerais."""
    print("Importando observações gerais...")
    
    # Observações sobre realocação
    relocation_notes = [
        "Otávio (Filho da Gisele): pode ser realocado de quarta (15:30-17:00) para sexta (15:30-17:00)"
    ]
    
    # Observações sobre provas
    exam_notes = [
        "Pietro: Prova em 24/03, estudo marcado para 19/03",
        "Lorenzo: Conteúdo para aula 23/04 – modelos astrológicos (Heliocentrismo, Geocentrismo, Nicolau Copérnico, Galileu, Aristóteles, Aristarco)"
    ]
    
    # Processar observações de realocação
    for note in relocation_notes:
        # Extrair informações básicas
        if ':' in note:
            student_info, suggestion = note.split(':')
            student_name = student_info.split('(')[0].strip()
            
            # Encontrar o aluno
            student = find_or_create_student(student_name)
            
            # Atualizar observações do aluno
            if student.notes:
                student.notes += f"\n{note}"
            else:
                student.notes = note
                
            db.session.commit()
            print(f"Observação de realocação adicionada para: {student.name}")
    
    # Processar observações de provas
    for note in exam_notes:
        # Extrair informações básicas
        if ':' in note:
            student_info, exam_info = note.split(':')
            student_name = student_info.strip()
            
            # Encontrar o aluno
            student = find_or_create_student(student_name)
            
            # Atualizar observações do aluno
            if student.notes:
                student.notes += f"\n{exam_info.strip()}"
            else:
                student.notes = exam_info.strip()
                
            # Extrair data de prova, se houver
            exam_date_match = re.search(r'Prova em (\d{1,2}/\d{1,2})', exam_info)
            if exam_date_match:
                exam_date_str = exam_date_match.group(1)
                exam_date = parse_date(exam_date_str)
                
                if exam_date:
                    # Adicionar uma observação especial para o dia da prova
                    existing_lessons = Lesson.query.filter(
                        Lesson.student_id == student.id,
                        Lesson.date == exam_date
                    ).all()
                    
                    if existing_lessons:
                        for lesson in existing_lessons:
                            lesson.notes = f"{lesson.notes or ''}\nPROVA NESTE DIA: {exam_info.strip()}".strip()
                    else:
                        # Criar um evento de prova
                        new_lesson = Lesson(
                            student_id=student.id,
                            date=exam_date,
                            subject="Prova",
                            status='scheduled',
                            lesson_type='extra',
                            notes=f"PROVA: {exam_info.strip()}"
                        )
                        db.session.add(new_lesson)
            
            db.session.commit()
            print(f"Observação de prova adicionada para: {student.name}")

def main():
    """Função principal que coordena o processo de importação."""
    with app.app_context():
        try:
            print("Iniciando importação de dados...")
            
            # Importar aulas fixas
            import_fixed_lessons()
            
            # Importar aulas extras
            import_extra_lessons()
            
            # Importar feriados
            import_holidays()
            
            # Importar observações
            import_observations()
            
            print("Importação de dados concluída com sucesso!")
            
        except Exception as e:
            print(f"Erro durante a importação: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    main()