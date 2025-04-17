from app import db
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# Tabela de associação entre alunos e responsáveis
student_guardian = db.Table('student_guardian',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('guardian_id', db.Integer, db.ForeignKey('guardian.id'), primary_key=True)
)


class User(UserMixin, db.Model):
    """User model for authentication and user management."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        """Hash and set the user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Guardian(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(255))  # Campo para armazenar número do WhatsApp
    address = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com alunos (muitos para muitos)
    students = db.relationship('Student', 
                             secondary=student_guardian,
                             lazy='subquery',
                             backref=db.backref('guardians', lazy=True))
    
    def __repr__(self):
        return f'<Guardian {self.name}>'


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    grade = db.Column(db.String(20))
    school = db.Column(db.String(100))
    whatsapp = db.Column(db.String(255))  # Campo para armazenar número do WhatsApp
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Manter o relacionamento principal para compatibilidade com o código existente
    guardian_id = db.Column(db.Integer, db.ForeignKey('guardian.id'), nullable=True)
    guardian = db.relationship('Guardian', 
                              foreign_keys=[guardian_id],
                              backref=db.backref('primary_students', lazy=True))
    
    # Relationship with lessons
    lessons = db.relationship('Lesson', backref='student', lazy=True)
    
    def __repr__(self):
        return f'<Student {self.name}>'


class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200))
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    lesson_type = db.Column(db.String(20), default='fixed')  # fixed, extra
    notes = db.Column(db.Text)
    homework = db.Column(db.Text)
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid, paid
    payment_amount = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Lesson {self.subject} - {self.date}>'
    
    @property
    def duration_hours(self):
        """Retorna a duração da aula em horas (float)"""
        if not self.start_time or not self.end_time:
            return 0.0
        
        start_minutes = self.start_time.hour * 60 + self.start_time.minute
        end_minutes = self.end_time.hour * 60 + self.end_time.minute
        
        # Se end_time for menor que start_time, assume que a aula passou da meia-noite
        if end_minutes < start_minutes:
            end_minutes += 24 * 60
            
        duration_minutes = end_minutes - start_minutes
        return duration_minutes / 60.0


class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    guardian_id = db.Column(db.Integer, db.ForeignKey('guardian.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    payment_method = db.Column(db.String(50))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with guardian
    guardian = db.relationship('Guardian', backref='payments')
    
    def __repr__(self):
        return f'<Payment {self.amount} - {self.payment_date}>'


class Holiday(db.Model):
    """Modelo para armazenar feriados e dias sem aula."""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    description = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Holiday {self.date} - {self.description}>'
