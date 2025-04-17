from flask import render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date, timedelta
from app import db
from models import Student, Guardian, Lesson, Payment, Holiday
import plotly.express as px
import plotly.graph_objects as go
import plotly.utils
import json
from xhtml2pdf import pisa
from io import BytesIO
import os

def register_routes(app):
    # Injetar feriados em todas as páginas
    @app.context_processor
    def inject_holidays():
        """Adiciona os próximos feriados para uso em todas as páginas"""
        today = date.today()
        next_month = today + timedelta(days=30)
        
        upcoming_holidays = Holiday.query.filter(
            Holiday.date >= today,
            Holiday.date <= next_month
        ).order_by(Holiday.date).all()
        
        return {'upcoming_holidays': upcoming_holidays}
    
    # Dashboard
    @app.route('/')
    def dashboard():
        # Count statistics for dashboard
        student_count = Student.query.count()
        guardian_count = Guardian.query.count()
        
        # Get upcoming lessons (next 7 days)
        today = date.today()
        week_later = today + timedelta(days=7)
        upcoming_lessons = Lesson.query.filter(
            Lesson.date >= today,
            Lesson.date <= week_later,
            Lesson.status != 'cancelled'
        ).order_by(Lesson.date, Lesson.start_time).all()
        
        # Get total payments for this month
        first_day = date(today.year, today.month, 1)
        if today.month == 12:
            last_day = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(today.year, today.month + 1, 1) - timedelta(days=1)
        
        payments = Payment.query.filter(
            Payment.payment_date >= first_day,
            Payment.payment_date <= last_day
        ).all()
        
        total_payments = sum(payment.amount for payment in payments)
        
        # Dados da agenda semanal
        agenda_semana = {
            "segunda": {
                "fixed": [
                    {"aluno": "Maria", "horario": "15h00–16h30", "local": "Apto 111, Torre 1"},
                    {"aluno": "João", "horario": "16h40–17h40", "local": "Apto 91, Torre 2"}
                ],
                "extra": [
                    {"aluno": "Pietro", "horario": "17h30–19h00", "data": "14/04", "obs": "Química"}
                ]
            },
            "terca": {
                "fixed": [
                    {"aluno": "Lourenço", "horario": "15h30–17h00"},
                    {"aluno": "Gabi", "horario": "17h00–18h00"}
                ],
                "extra": [
                    {"aluno": "Lourenço", "horario": "14h30–16h00", "data": "08/04"},
                    {"aluno": "João Couto", "horario": "16h00–17h00", "data": "08/04"},
                    {"aluno": "Maria", "horario": "18h30–19h30", "data": "08/04"}
                ]
            },
            "quarta": {
                "fixed": [
                    {"aluno": "Lorenzo", "horario": "14h30–15h30", "obs": "1ª aula"},
                    {"aluno": "Otavio (Filho da Gisele)", "horario": "15h30–17h00"},
                    {"aluno": "Pietro", "horario": "17h30–19h00"}
                ],
                "extra": [
                    {"aluno": "Pietro", "horario": "17h30–19h00", "data": "09/04", "obs": "Geometria"},
                    {"aluno": "Pietro", "horario": "17h30–19h00", "data": "23/04", "obs": "Física"}
                ]
            },
            "quinta": {
                "fixed": [
                    {"aluno": "Pedro / Carol", "horario": "15h00–17h00"}
                ],
                "extra": [
                    {"aluno": "Felipe", "horario": "17h30–19h00", "data": "24/04", "obs": "Química"}
                ]
            },
            "sexta": {
                "fixed": [
                    {"aluno": "Lourenço", "horario": "14h30–16h00"},
                    {"aluno": "Gui / Pedrão", "horario": "16h00–17h30"}
                ],
                "extra": []
            }
        }
        
        # Dias da semana em português para mostrar na tabela
        dias_semana = {
            "segunda": "Segunda-feira",
            "terca": "Terça-feira",
            "quarta": "Quarta-feira",
            "quinta": "Quinta-feira",
            "sexta": "Sexta-feira"
        }
        
        return render_template(
            'dashboard.html',
            student_count=student_count,
            guardian_count=guardian_count,
            upcoming_lessons=upcoming_lessons,
            total_payments=total_payments,
            agenda_semana=agenda_semana,
            dias_semana=dias_semana
        )

    # Students routes
    @app.route('/students')
    def list_students():
        students = Student.query.all()
        return render_template('students.html', students=students)

    @app.route('/students/new', methods=['GET', 'POST'])
    def new_student():
        if request.method == 'POST':
            guardian_id = request.form.get('guardian_id')
            
            # Validate guardian exists
            guardian = Guardian.query.get(guardian_id)
            if not guardian:
                flash('Guardian not found. Please select a valid guardian.', 'danger')
                guardians = Guardian.query.all()
                return render_template('forms/student_form.html', guardians=guardians)
            
            student = Student(
                name=request.form.get('name'),
                age=request.form.get('age') or None,
                grade=request.form.get('grade'),
                school=request.form.get('school'),
                whatsapp=request.form.get('whatsapp'),
                guardian_id=guardian_id,
                notes=request.form.get('notes')
            )
            
            db.session.add(student)
            db.session.commit()
            
            flash('Student created successfully!', 'success')
            return redirect(url_for('list_students'))
        
        guardians = Guardian.query.all()
        return render_template('forms/student_form.html', guardians=guardians)

    @app.route('/students/<int:id>/edit', methods=['GET', 'POST'])
    def edit_student(id):
        student = Student.query.get_or_404(id)
        
        if request.method == 'POST':
            guardian_id = request.form.get('guardian_id')
            
            # Validate guardian exists
            guardian = Guardian.query.get(guardian_id)
            if not guardian:
                flash('Guardian not found. Please select a valid guardian.', 'danger')
                guardians = Guardian.query.all()
                return render_template('forms/student_form.html', student=student, guardians=guardians)
            
            student.name = request.form.get('name')
            student.age = request.form.get('age') or None
            student.grade = request.form.get('grade')
            student.school = request.form.get('school')
            student.whatsapp = request.form.get('whatsapp')
            student.guardian_id = guardian_id
            student.notes = request.form.get('notes')
            
            db.session.commit()
            
            flash('Student updated successfully!', 'success')
            return redirect(url_for('list_students'))
        
        guardians = Guardian.query.all()
        return render_template('forms/student_form.html', student=student, guardians=guardians)

    @app.route('/students/<int:id>/delete', methods=['POST'])
    def delete_student(id):
        student = Student.query.get_or_404(id)
        
        # Check if student has lessons before deletion
        if student.lessons:
            flash('Cannot delete student with associated lessons. Delete the lessons first.', 'danger')
            return redirect(url_for('list_students'))
        
        db.session.delete(student)
        db.session.commit()
        
        flash('Student deleted successfully!', 'success')
        return redirect(url_for('list_students'))

    # Guardians routes
    @app.route('/guardians')
    def list_guardians():
        guardians = Guardian.query.all()
        return render_template('guardians.html', guardians=guardians)

    @app.route('/guardians/new', methods=['GET', 'POST'])
    def new_guardian():
        if request.method == 'POST':
            guardian = Guardian(
                name=request.form.get('name'),
                email=request.form.get('email'),
                phone=request.form.get('phone'),
                whatsapp=request.form.get('whatsapp'),
                address=request.form.get('address')
            )
            
            db.session.add(guardian)
            db.session.commit()
            
            flash('Guardian created successfully!', 'success')
            return redirect(url_for('list_guardians'))
        
        return render_template('forms/guardian_form.html')

    @app.route('/guardians/<int:id>/edit', methods=['GET', 'POST'])
    def edit_guardian(id):
        guardian = Guardian.query.get_or_404(id)
        
        if request.method == 'POST':
            guardian.name = request.form.get('name')
            guardian.email = request.form.get('email')
            guardian.phone = request.form.get('phone')
            guardian.whatsapp = request.form.get('whatsapp')
            guardian.address = request.form.get('address')
            
            db.session.commit()
            
            flash('Guardian updated successfully!', 'success')
            return redirect(url_for('list_guardians'))
        
        return render_template('forms/guardian_form.html', guardian=guardian)

    @app.route('/guardians/<int:id>/delete', methods=['POST'])
    def delete_guardian(id):
        guardian = Guardian.query.get_or_404(id)
        
        # Check if guardian has students before deletion
        if guardian.primary_students:
            flash('Cannot delete guardian with associated students. Delete the students first.', 'danger')
            return redirect(url_for('list_guardians'))
        
        db.session.delete(guardian)
        db.session.commit()
        
        flash('Guardian deleted successfully!', 'success')
        return redirect(url_for('list_guardians'))

    # Lessons routes
    @app.route('/lessons')
    def list_lessons():
        # Default to current week
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Allow date range filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_of_week = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_of_week = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        lessons = Lesson.query.filter(
            Lesson.date >= start_of_week,
            Lesson.date <= end_of_week
        ).order_by(Lesson.date, Lesson.start_time).all()
        
        return render_template(
            'lessons.html', 
            lessons=lessons, 
            start_date=start_of_week, 
            end_date=end_of_week
        )

    @app.route('/lessons/new', methods=['GET', 'POST'])
    def new_lesson():
        if request.method == 'POST':
            try:
                student_id = request.form.get('student_id')
                lesson_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
                start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
                end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
                
                lesson = Lesson(
                    student_id=student_id,
                    date=lesson_date,
                    start_time=start_time,
                    end_time=end_time,
                    subject=request.form.get('subject'),
                    topic=request.form.get('topic'),
                    status=request.form.get('status', 'scheduled'),
                    notes=request.form.get('notes'),
                    homework=request.form.get('homework'),
                    payment_status=request.form.get('payment_status', 'unpaid'),
                    payment_amount=float(request.form.get('payment_amount') or 0)
                )
                
                db.session.add(lesson)
                db.session.commit()
                
                flash('Lesson created successfully!', 'success')
                return redirect(url_for('list_lessons'))
            except Exception as e:
                flash(f'Error creating lesson: {str(e)}', 'danger')
        
        students = Student.query.all()
        return render_template('forms/lesson_form.html', students=students)

    @app.route('/lessons/<int:id>/edit', methods=['GET', 'POST'])
    def edit_lesson(id):
        lesson = Lesson.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                student_id = request.form.get('student_id')
                lesson_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
                start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
                end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
                
                lesson.student_id = student_id
                lesson.date = lesson_date
                lesson.start_time = start_time
                lesson.end_time = end_time
                lesson.subject = request.form.get('subject')
                lesson.topic = request.form.get('topic')
                lesson.status = request.form.get('status')
                lesson.notes = request.form.get('notes')
                lesson.homework = request.form.get('homework')
                lesson.payment_status = request.form.get('payment_status')
                lesson.payment_amount = float(request.form.get('payment_amount') or 0)
                
                db.session.commit()
                
                flash('Lesson updated successfully!', 'success')
                return redirect(url_for('list_lessons'))
            except Exception as e:
                flash(f'Error updating lesson: {str(e)}', 'danger')
        
        students = Student.query.all()
        return render_template('forms/lesson_form.html', lesson=lesson, students=students)

    @app.route('/lessons/<int:id>/delete', methods=['POST'])
    def delete_lesson(id):
        lesson = Lesson.query.get_or_404(id)
        
        db.session.delete(lesson)
        db.session.commit()
        
        flash('Lesson deleted successfully!', 'success')
        return redirect(url_for('list_lessons'))

    # Reports
    @app.route('/reports')
    def reports():
        # Get date range for filtering
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        today = date.today()
        if not start_date_str:
            # Default to first day of current month
            start_date = date(today.year, today.month, 1)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            
        if not end_date_str:
            # Default to last day of current month
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Get all lessons in the date range
        lessons = Lesson.query.filter(
            Lesson.date >= start_date,
            Lesson.date <= end_date
        ).order_by(Lesson.date).all()
        
        # Get all payments in the date range
        payments = Payment.query.filter(
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).order_by(Payment.payment_date).all()
        
        # Calculate statistics
        total_lessons = len(lessons)
        total_lesson_hours = sum((lesson.end_time.hour - lesson.start_time.hour) + 
                              (lesson.end_time.minute - lesson.start_time.minute) / 60 
                              for lesson in lessons)
        total_earnings = sum(lesson.payment_amount for lesson in lessons)
        total_payments = sum(payment.amount for payment in payments)
        
        return render_template(
            'reports.html',
            start_date=start_date,
            end_date=end_date,
            lessons=lessons,
            payments=payments,
            total_lessons=total_lessons,
            total_lesson_hours=total_lesson_hours,
            total_earnings=total_earnings,
            total_payments=total_payments
        )

    # API Endpoints
    @app.route('/api/students')
    def api_students():
        students = Student.query.all()
        result = [{
            'id': student.id,
            'name': student.name,
            'age': student.age,
            'grade': student.grade,
            'school': student.school
        } for student in students]
        return jsonify(result)
        
    # Daily Lessons Management
    @app.route('/daily-lessons')
    def daily_lessons():
        # Get date from request, default to today
        selected_date_str = request.args.get('selected_date')
        date_today = date.today()
        
        if selected_date_str:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        else:
            selected_date = date_today
        
        # Get day of week in Portuguese
        days_of_week = {
            0: "Segunda-feira",
            1: "Terça-feira",
            2: "Quarta-feira",
            3: "Quinta-feira",
            4: "Sexta-feira",
            5: "Sábado",
            6: "Domingo"
        }
        day_of_week = days_of_week[selected_date.weekday()]
        
        # Get fixed lessons for the day
        fixed_lessons = Lesson.query.filter(
            Lesson.date == selected_date,
            Lesson.lesson_type == 'fixed'
        ).order_by(Lesson.start_time).all()
        
        # Get extra lessons for the day
        extra_lessons = Lesson.query.filter(
            Lesson.date == selected_date,
            Lesson.lesson_type == 'extra'
        ).order_by(Lesson.start_time).all()
        
        # Get all students for quick lesson form
        students = Student.query.all()
        
        return render_template(
            'daily_lessons.html',
            selected_date=selected_date,
            date_today=date_today,
            day_of_week=day_of_week,
            fixed_lessons=fixed_lessons,
            extra_lessons=extra_lessons,
            students=students
        )
    
    @app.route('/lessons/new-extra', methods=['GET', 'POST'])
    def new_extra_lesson():
        # Get date from request, default to today
        date_str = request.args.get('date')
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = date.today()
        
        if request.method == 'POST':
            try:
                student_id = request.form.get('student_id')
                lesson_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
                start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
                end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
                
                lesson = Lesson(
                    student_id=student_id,
                    date=lesson_date,
                    start_time=start_time,
                    end_time=end_time,
                    subject=request.form.get('subject'),
                    topic=request.form.get('topic'),
                    status=request.form.get('status', 'scheduled'),
                    lesson_type='extra',  # Extra lesson
                    notes=request.form.get('notes'),
                    homework=request.form.get('homework'),
                    payment_status=request.form.get('payment_status', 'unpaid'),
                    payment_amount=float(request.form.get('payment_amount') or 0)
                )
                
                db.session.add(lesson)
                db.session.commit()
                
                flash('Aula extra criada com sucesso!', 'success')
                return redirect(url_for('daily_lessons', selected_date=lesson_date.strftime('%Y-%m-%d')))
            except Exception as e:
                flash(f'Erro ao criar aula extra: {str(e)}', 'danger')
        
        students = Student.query.all()
        return render_template('forms/extra_lesson_form.html', students=students, selected_date=selected_date)
    
    @app.route('/lessons/<int:id>/confirm', methods=['GET', 'POST'])
    def confirm_lesson(id):
        lesson = Lesson.query.get_or_404(id)
        
        if request.method == 'POST':
            lesson.status = 'completed'
            lesson.subject = request.form.get('subject', lesson.subject)
            lesson.topic = request.form.get('topic')
            lesson.notes = request.form.get('notes')
            lesson.homework = request.form.get('homework')
            
            db.session.commit()
            
            flash('Aula confirmada com sucesso!', 'success')
            return redirect(url_for('daily_lessons', selected_date=lesson.date.strftime('%Y-%m-%d')))
            
        # Quick confirmation (GET request)
        if request.args.get('quick') == '1':
            lesson.status = 'completed'
            db.session.commit()
            
            flash('Aula confirmada com sucesso!', 'success')
            return redirect(url_for('daily_lessons', selected_date=lesson.date.strftime('%Y-%m-%d')))
            
        return render_template('forms/confirm_lesson.html', lesson=lesson)
    
    @app.route('/lessons/<int:id>/cancel', methods=['GET', 'POST'])
    def cancel_lesson(id):
        lesson = Lesson.query.get_or_404(id)
        
        if request.method == 'POST':
            lesson.status = 'cancelled'
            lesson.notes = request.form.get('notes', lesson.notes)
            
            db.session.commit()
            
            flash('Aula cancelada com sucesso!', 'success')
            return redirect(url_for('daily_lessons', selected_date=lesson.date.strftime('%Y-%m-%d')))
            
        # Quick cancellation (GET request)
        if request.args.get('quick') == '1':
            lesson.status = 'cancelled'
            db.session.commit()
            
            flash('Aula cancelada com sucesso!', 'success')
            return redirect(url_for('daily_lessons', selected_date=lesson.date.strftime('%Y-%m-%d')))
            
        return render_template('forms/cancel_lesson.html', lesson=lesson)
    
    @app.route('/lessons/<int:id>/reschedule', methods=['GET', 'POST'])
    def reschedule_lesson(id):
        lesson = Lesson.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                new_date = datetime.strptime(request.form.get('new_date'), '%Y-%m-%d').date()
                
                # Create new lesson based on the old one
                new_lesson = Lesson(
                    student_id=lesson.student_id,
                    date=new_date,
                    start_time=lesson.start_time,
                    end_time=lesson.end_time,
                    subject=lesson.subject,
                    topic=lesson.topic,
                    status='scheduled',
                    lesson_type=lesson.lesson_type,
                    notes=f"Remarcada da aula de {lesson.date.strftime('%d/%m/%Y')}. " + (lesson.notes or ''),
                    homework=lesson.homework,
                    payment_status=lesson.payment_status,
                    payment_amount=lesson.payment_amount
                )
                
                # Mark old lesson as cancelled
                lesson.status = 'cancelled'
                lesson.notes = f"Remarcada para {new_date.strftime('%d/%m/%Y')}. " + (lesson.notes or '')
                
                db.session.add(new_lesson)
                db.session.commit()
                
                flash('Aula remarcada com sucesso!', 'success')
                return redirect(url_for('daily_lessons', selected_date=new_date.strftime('%Y-%m-%d')))
            except Exception as e:
                flash(f'Erro ao remarcar aula: {str(e)}', 'danger')
                
        return render_template('forms/reschedule_lesson.html', lesson=lesson)
        
    @app.route('/quick-lesson-update', methods=['POST'])
    def quick_lesson_update():
        """Registro rápido de aula na página daily_lessons"""
        try:
            student_id = request.form.get('student_id')
            lesson_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
            start_time = datetime.strptime(request.form.get('start_time'), '%H:%M').time()
            end_time = datetime.strptime(request.form.get('end_time'), '%H:%M').time()
            lesson_type = request.form.get('lesson_type', 'fixed')
            
            # Verificar se já existe uma aula neste horário
            existing_lesson = Lesson.query.filter(
                Lesson.date == lesson_date,
                Lesson.student_id == student_id,
                Lesson.start_time == start_time
            ).first()
            
            if existing_lesson:
                # Atualizar aula existente
                existing_lesson.end_time = end_time
                existing_lesson.subject = request.form.get('subject')
                existing_lesson.topic = request.form.get('topic')
                existing_lesson.status = request.form.get('status')
                existing_lesson.notes = request.form.get('notes')
                existing_lesson.homework = request.form.get('homework')
                existing_lesson.lesson_type = lesson_type
                
                db.session.commit()
                flash('Aula atualizada com sucesso!', 'success')
            else:
                # Criar nova aula
                lesson = Lesson(
                    student_id=student_id,
                    date=lesson_date,
                    start_time=start_time,
                    end_time=end_time,
                    subject=request.form.get('subject'),
                    topic=request.form.get('topic'),
                    status=request.form.get('status', 'completed'),
                    lesson_type=lesson_type,
                    notes=request.form.get('notes'),
                    homework=request.form.get('homework'),
                )
                
                db.session.add(lesson)
                db.session.commit()
                flash('Aula registrada com sucesso!', 'success')
                
            return redirect(url_for('daily_lessons', selected_date=lesson_date.strftime('%Y-%m-%d')))
        except Exception as e:
            flash(f'Erro ao registrar aula: {str(e)}', 'danger')
            return redirect(url_for('daily_lessons'))
            
    # Análise de Pareto
    @app.route('/pareto-chart')
    def pareto_chart():
        """Gera um gráfico de Pareto das matérias mais estudadas"""
        # Obter parâmetros de filtro
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        student_id = request.args.get('student_id')
        
        # Configurar datas (padrão: mês atual)
        today = date.today()
        if not start_date_str:
            # Primeiro dia do mês atual
            start_date = date(today.year, today.month, 1)
        else:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            
        if not end_date_str:
            # Último dia do mês atual
            if today.month == 12:
                end_date = date(today.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(today.year, today.month + 1, 1) - timedelta(days=1)
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        
        # Base query para aulas completadas no período
        query = Lesson.query.filter(
            Lesson.date >= start_date,
            Lesson.date <= end_date,
            Lesson.status == 'completed'
        )
        
        # Filtrar por aluno se especificado
        if student_id:
            query = query.filter(Lesson.student_id == student_id)
        
        # Executar a consulta
        lessons = query.all()
        
        # Agrupar por matéria
        subject_counts = {}
        subject_hours = {}
        
        for lesson in lessons:
            subject = lesson.subject
            if subject not in subject_counts:
                subject_counts[subject] = 0
                subject_hours[subject] = 0
            
            subject_counts[subject] += 1
            subject_hours[subject] += lesson.duration_hours
        
        # Ordenar por contagem (decrescente)
        sorted_subjects = sorted(subject_counts.keys(), key=lambda x: subject_counts[x], reverse=True)
        
        # Preparar dados para o gráfico de Pareto
        if sorted_subjects:
            # Calcular porcentagens e valores acumulados
            total_count = sum(subject_counts.values())
            total_hours = sum(subject_hours.values())
            
            subject_data = []
            cumulative_percentage = 0
            
            for subject in sorted_subjects:
                count = subject_counts[subject]
                hours = subject_hours[subject]
                percentage = (count / total_count) * 100
                cumulative_percentage += percentage
                
                subject_data.append({
                    'name': subject,
                    'count': count,
                    'hours': hours,
                    'percentage': percentage,
                    'cumulative': cumulative_percentage
                })
            
            # Criar gráfico com Plotly
            subjects = [item['name'] for item in subject_data]
            counts = [item['count'] for item in subject_data]
            cumulative = [item['cumulative'] for item in subject_data]
            
            # Criar figura com dois eixos Y
            fig = go.Figure()
            
            # Adicionar barras para contagem
            fig.add_trace(go.Bar(
                x=subjects,
                y=counts,
                name='Aulas',
                marker_color='rgba(55, 83, 109, 0.7)'
            ))
            
            # Adicionar linha para porcentagem acumulada
            fig.add_trace(go.Scatter(
                x=subjects,
                y=cumulative,
                name='% Acumulada',
                yaxis='y2',
                marker_color='rgb(26, 118, 255)',
                mode='lines+markers'
            ))
            
            # Configurar layout com eixos duplos
            fig.update_layout(
                title='Análise de Pareto das Matérias Mais Estudadas',
                xaxis=dict(
                    title='Matéria',
                    tickfont=dict(size=12)
                ),
                yaxis=dict(
                    title='Quantidade de Aulas',
                    tickfont=dict(size=12)
                ),
                yaxis2=dict(
                    title='Porcentagem Acumulada',
                    titlefont=dict(color='rgb(26, 118, 255)'),
                    tickfont=dict(color='rgb(26, 118, 255)'),
                    overlaying='y',
                    side='right',
                    range=[0, 100]
                ),
                legend=dict(x=0.01, y=0.99),
                margin=dict(l=50, r=50, t=80, b=50),
                template='plotly_dark'
            )
            
            # Converter para HTML
            plot_html = fig.to_html(full_html=False)
        else:
            # Sem dados para exibir
            plot_html = None
            subject_data = []
        
        # Buscar todos os alunos para o filtro
        students = Student.query.all()
        
        return render_template(
            'pareto_chart.html',
            plot_html=plot_html,
            subject_data=subject_data,
            start_date=start_date,
            end_date=end_date,
            student_id=student_id,
            students=students
        )
        
    # Relatório por Aluno
    @app.route('/student-report')
    def student_report():
        """Gera um relatório mensal por aluno"""
        # Obter parâmetros de filtro
        student_id = request.args.get('student_id')
        month = request.args.get('month')
        year = request.args.get('year')
        
        # Verificar se o aluno foi especificado
        if not student_id:
            flash('É necessário selecionar um aluno para gerar o relatório.', 'warning')
            return redirect(url_for('list_students'))
            
        # Buscar aluno
        student = Student.query.get_or_404(student_id)
        
        # Configurar mês/ano padrão (mês atual)
        today = date.today()
        if not month:
            month = today.month
        else:
            month = int(month)
            
        if not year:
            year = today.year
        else:
            year = int(year)
            
        # Calcular período do relatório
        start_date = date(year, month, 1)
        
        # Calcular último dia do mês
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
            
        # Buscar aulas do aluno no período
        lessons = Lesson.query.filter(
            Lesson.student_id == student_id,
            Lesson.date >= start_date,
            Lesson.date <= end_date
        ).order_by(Lesson.date, Lesson.start_time).all()
        
        # Calcular estatísticas
        total_hours = sum(lesson.duration_hours for lesson in lessons if lesson.status == 'completed')
        
        # Contar ocorrências de matérias
        subjects = {}
        for lesson in lessons:
            if lesson.status == 'completed':
                if lesson.subject not in subjects:
                    subjects[lesson.subject] = 0
                subjects[lesson.subject] += 1
                
        # Ordenar matérias por ocorrência (decrescente)
        subjects = dict(sorted(subjects.items(), key=lambda x: x[1], reverse=True))
        
        # Obter anos para o seletor (desde o primeiro registro até o ano atual)
        first_lesson = Lesson.query.filter(Lesson.student_id == student_id).order_by(Lesson.date).first()
        
        if first_lesson:
            first_year = first_lesson.date.year
        else:
            first_year = today.year
            
        years = list(range(first_year, today.year + 1))
        
        return render_template(
            'student_report.html',
            student=student,
            lessons=lessons,
            total_hours=total_hours,
            subjects=subjects,
            month=month,
            year=year,
            years=years
        )
        
    @app.route('/export-student-report-pdf/<int:student_id>/<int:month>/<int:year>')
    def export_student_report_pdf(student_id, month, year):
        """Exporta o relatório do aluno em PDF"""
        # Buscar aluno
        student = Student.query.get_or_404(student_id)
        
        # Calcular período do relatório
        start_date = date(year, month, 1)
        
        # Calcular último dia do mês
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
            
        # Buscar aulas do aluno no período
        lessons = Lesson.query.filter(
            Lesson.student_id == student_id,
            Lesson.date >= start_date,
            Lesson.date <= end_date
        ).order_by(Lesson.date, Lesson.start_time).all()
        
        # Calcular estatísticas
        total_hours = sum(lesson.duration_hours for lesson in lessons if lesson.status == 'completed')
        
        # Contar ocorrências de matérias
        subjects = {}
        for lesson in lessons:
            if lesson.status == 'completed':
                if lesson.subject not in subjects:
                    subjects[lesson.subject] = 0
                subjects[lesson.subject] += 1
                
        # Ordenar matérias por ocorrência (decrescente)
        subjects = dict(sorted(subjects.items(), key=lambda x: x[1], reverse=True))
        
        # Nome dos meses em português
        meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        # Renderizar o template HTML para o PDF
        html = render_template(
            'pdf/student_report_pdf.html',
            student=student,
            lessons=lessons,
            total_hours=total_hours,
            subjects=subjects,
            month=month,
            year=year,
            month_name=meses[month-1],
            start_date=start_date,
            end_date=end_date
        )
        
        # Criar PDF a partir do HTML
        pdf_buffer = BytesIO()
        pisa.CreatePDF(html, dest=pdf_buffer)
        
        # Preparar resposta
        pdf_buffer.seek(0)
        response = app.response_class(
            pdf_buffer,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=relatorio_{student.name.replace(" ", "_")}_{meses[month-1]}_{year}.pdf'
            }
        )
        
        return response
        
    # Relatório por Responsável
    @app.route('/guardian-report')
    def guardian_report():
        """Gera um relatório mensal por responsável"""
        # Obter parâmetros de filtro
        guardian_id = request.args.get('guardian_id')
        month = request.args.get('month')
        year = request.args.get('year')
        
        # Verificar se o responsável foi especificado
        if not guardian_id:
            flash('É necessário selecionar um responsável para gerar o relatório.', 'warning')
            return redirect(url_for('list_guardians'))
            
        # Buscar responsável
        guardian = Guardian.query.get_or_404(guardian_id)
        
        # Configurar mês/ano padrão (mês atual)
        today = date.today()
        if not month:
            month = today.month
        else:
            month = int(month)
            
        if not year:
            year = today.year
        else:
            year = int(year)
            
        # Calcular período do relatório
        start_date = date(year, month, 1)
        
        # Calcular último dia do mês
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
            
        # Obter todos os alunos do responsável
        students = set(guardian.primary_students + guardian.students)
        
        # Buscar aulas de todos os alunos no período
        student_lessons = {}
        total_lessons = 0
        total_hours = 0
        total_amount = 0
        
        for student in students:
            lessons = Lesson.query.filter(
                Lesson.student_id == student.id,
                Lesson.date >= start_date,
                Lesson.date <= end_date,
                Lesson.status == 'completed'
            ).order_by(Lesson.date, Lesson.start_time).all()
            
            student_hours = sum(lesson.duration_hours for lesson in lessons)
            student_amount = sum(lesson.payment_amount for lesson in lessons)
            
            student_lessons[student] = {
                'lessons': lessons,
                'hours': student_hours,
                'amount': student_amount
            }
            
            total_lessons += len(lessons)
            total_hours += student_hours
            total_amount += student_amount
            
        # Buscar pagamentos do responsável no período
        payments = Payment.query.filter(
            Payment.guardian_id == guardian_id,
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).order_by(Payment.payment_date).all()
        
        total_payments = sum(payment.amount for payment in payments)
        
        # Obter anos para o seletor (desde o primeiro registro até o ano atual)
        first_payment = Payment.query.filter(Payment.guardian_id == guardian_id).order_by(Payment.payment_date).first()
        
        if first_payment:
            first_year = first_payment.payment_date.year
        else:
            # Verificar primeira aula de qualquer aluno do responsável
            student_ids = [student.id for student in students]
            first_lesson = Lesson.query.filter(Lesson.student_id.in_(student_ids)).order_by(Lesson.date).first()
            
            if first_lesson:
                first_year = first_lesson.date.year
            else:
                first_year = today.year
                
        years = list(range(first_year, today.year + 1))
        
        return render_template(
            'guardian_report.html',
            guardian=guardian,
            student_lessons=student_lessons,
            payments=payments,
            total_lessons=total_lessons,
            total_hours=total_hours,
            total_amount=total_amount,
            total_payments=total_payments,
            month=month,
            year=year,
            years=years
        )
        
    @app.route('/export-guardian-report-pdf/<int:guardian_id>/<int:month>/<int:year>')
    def export_guardian_report_pdf(guardian_id, month, year):
        """Exporta o relatório do responsável em PDF"""
        # Buscar responsável
        guardian = Guardian.query.get_or_404(guardian_id)
        
        # Calcular período do relatório
        start_date = date(year, month, 1)
        
        # Calcular último dia do mês
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
            
        # Obter todos os alunos do responsável
        students = set(guardian.primary_students + guardian.students)
        
        # Buscar aulas de todos os alunos no período
        student_lessons = {}
        total_lessons = 0
        total_hours = 0
        total_amount = 0
        
        for student in students:
            lessons = Lesson.query.filter(
                Lesson.student_id == student.id,
                Lesson.date >= start_date,
                Lesson.date <= end_date,
                Lesson.status == 'completed'
            ).order_by(Lesson.date, Lesson.start_time).all()
            
            student_hours = sum(lesson.duration_hours for lesson in lessons)
            student_amount = sum(lesson.payment_amount for lesson in lessons)
            
            student_lessons[student] = {
                'lessons': lessons,
                'hours': student_hours,
                'amount': student_amount
            }
            
            total_lessons += len(lessons)
            total_hours += student_hours
            total_amount += student_amount
            
        # Buscar pagamentos do responsável no período
        payments = Payment.query.filter(
            Payment.guardian_id == guardian_id,
            Payment.payment_date >= start_date,
            Payment.payment_date <= end_date
        ).order_by(Payment.payment_date).all()
        
        total_payments = sum(payment.amount for payment in payments)
        
        # Nome dos meses em português
        meses = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 
                'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        
        # Renderizar o template HTML para o PDF
        html = render_template(
            'pdf/guardian_report_pdf.html',
            guardian=guardian,
            student_lessons=student_lessons,
            payments=payments,
            total_lessons=total_lessons,
            total_hours=total_hours,
            total_amount=total_amount,
            total_payments=total_payments,
            month=month,
            year=year,
            month_name=meses[month-1],
            start_date=start_date,
            end_date=end_date
        )
        
        # Criar PDF a partir do HTML
        pdf_buffer = BytesIO()
        pisa.CreatePDF(html, dest=pdf_buffer)
        
        # Preparar resposta
        pdf_buffer.seek(0)
        response = app.response_class(
            pdf_buffer,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=relatorio_responsavel_{guardian.name.replace(" ", "_")}_{meses[month-1]}_{year}.pdf'
            }
        )
        
        return response
    
    # Holidays routes
    @app.route('/holidays')
    def list_holidays():
        """Lista todos os feriados e dias bloqueados."""
        # Ordenar por data
        holidays = Holiday.query.order_by(Holiday.date).all()
        return render_template('holidays.html', holidays=holidays)
    
    @app.route('/holidays/new', methods=['GET', 'POST'])
    def new_holiday():
        """Adiciona um novo feriado ou dia bloqueado."""
        if request.method == 'POST':
            try:
                holiday_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
                
                # Verificar se já existe um feriado nesta data
                existing_holiday = Holiday.query.filter_by(date=holiday_date).first()
                if existing_holiday:
                    flash(f'Já existe um feriado registrado para {holiday_date.strftime("%d/%m/%Y")}.', 'warning')
                    return redirect(url_for('list_holidays'))
                
                # Criar novo feriado
                holiday = Holiday(
                    date=holiday_date,
                    description=request.form.get('description'),
                    notes=request.form.get('notes')
                )
                
                # Cancelar aulas agendadas neste dia
                lessons = Lesson.query.filter(Lesson.date == holiday_date).all()
                for lesson in lessons:
                    lesson.status = 'cancelled'
                    lesson.notes = f"{lesson.notes or ''}\nCancelada - {holiday.description}".strip()
                
                db.session.add(holiday)
                db.session.commit()
                
                flash('Feriado adicionado com sucesso!', 'success')
                return redirect(url_for('list_holidays'))
            except Exception as e:
                flash(f'Erro ao adicionar feriado: {str(e)}', 'danger')
        
        return render_template('forms/holiday_form.html')
    
    @app.route('/holidays/<int:id>/edit', methods=['GET', 'POST'])
    def edit_holiday(id):
        """Edita um feriado existente."""
        holiday = Holiday.query.get_or_404(id)
        
        if request.method == 'POST':
            try:
                holiday_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
                
                # Verificar se já existe outro feriado nesta data
                if holiday_date != holiday.date:
                    existing_holiday = Holiday.query.filter_by(date=holiday_date).first()
                    if existing_holiday and existing_holiday.id != holiday.id:
                        flash(f'Já existe um feriado registrado para {holiday_date.strftime("%d/%m/%Y")}.', 'warning')
                        return render_template('forms/holiday_form.html', holiday=holiday)
                
                # Atualizar feriado
                holiday.date = holiday_date
                holiday.description = request.form.get('description')
                holiday.notes = request.form.get('notes')
                
                db.session.commit()
                
                flash('Feriado atualizado com sucesso!', 'success')
                return redirect(url_for('list_holidays'))
            except Exception as e:
                flash(f'Erro ao atualizar feriado: {str(e)}', 'danger')
        
        return render_template('forms/holiday_form.html', holiday=holiday)
    
    @app.route('/holidays/<int:id>/delete', methods=['POST'])
    def delete_holiday(id):
        """Remove um feriado."""
        holiday = Holiday.query.get_or_404(id)
        
        db.session.delete(holiday)
        db.session.commit()
        
        flash('Feriado removido com sucesso!', 'success')
        return redirect(url_for('list_holidays'))
    
    @app.route('/import-schedule-data')
    def import_schedule_data_view():
        """Página para importar dados de agendamento."""
        return render_template('import_schedule_data.html')
        
    @app.route('/run-import-script', methods=['POST'])
    def run_import_script():
        """Executa o script de importação de dados."""
        if request.method == 'POST':
            # Verificar se o usuário confirmou a importação
            if 'confirm' in request.form:
                try:
                    # Importar o script manualmente para controlar a execução
                    import sys
                    import os
                    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scripts')
                    sys.path.insert(0, script_dir)
                    
                    import import_schedule_data
                    
                    # Executar a função principal do script
                    import_schedule_data.main()
                    
                    flash('Importação de dados concluída com sucesso!', 'success')
                except Exception as e:
                    flash(f'Erro durante a importação: {str(e)}', 'danger')
            else:
                flash('É necessário confirmar a importação para prosseguir.', 'warning')
        
        return redirect(url_for('import_schedule_data_view'))