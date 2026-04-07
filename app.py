from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import pyotp
import qrcode
from io import BytesIO
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///education_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Модели БД
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100))
    is_instructor = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    twofa_secret = db.Column(db.String(255), nullable=True)
    twofa_enabled = db.Column(db.Boolean, default=False)
    
    courses_created = db.relationship('Course', backref='instructor', lazy=True)
    enrollments = db.relationship('Enrollment', backref='student', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))
    
    courses = db.relationship('Course', backref='category_ref', lazy=True)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    @property
    def category(self):
        """Возвращает объект категории вместо category_id"""
        return Category.query.get(self.category_id)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    price = db.Column(db.Float, default=0.00)
    duration_hours = db.Column(db.Integer)
    difficulty_level = db.Column(db.String(20), default='beginner')
    image_url = db.Column(db.String(255))
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    lessons = db.relationship('Lesson', backref='course', lazy=True)
    enrollments = db.relationship('Enrollment', backref='course', lazy=True)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    video_url = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer)
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrolled_at = db.Column(db.DateTime, default=datetime.utcnow)
    progress_percent = db.Column(db.Integer, default=0)
    completed_at = db.Column(db.DateTime)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Создаем тестовые данные при первом запуске
def create_sample_data():
    # Проверяем, есть ли уже категории
    if Category.query.count() == 0:
        categories = [
            Category(name='Дизайн', description='Курсы по веб-дизайну, UI/UX', icon='palette'),
            Category(name='Игры', description='Создание игр, геймдизайн', icon='gamepad'),
            Category(name='Программирование', description='Веб и мобильная разработка', icon='code'),
        ]
        for cat in categories:
            db.session.add(cat)
        
        # Создаем тестового пользователя если нет
        if User.query.filter_by(username='admin').first() is None:
            admin = User(
                username='admin',
                email='admin@example.com',
                password=generate_password_hash('admin123'),
                full_name='Администратор',
                is_admin=True
            )
            db.session.add(admin)
        
        db.session.commit()

# Профиль пользователя
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', '')
        current_user.email = request.form.get('email', '')
        
        new_password = request.form.get('password', '')
        if new_password:
            current_user.password = generate_password_hash(new_password)
        
        db.session.commit()
        flash('Профиль обновлен!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('profile.html')

# Админ-панель
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Доступ запрещен!', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    courses = Course.query.all()
    enrollments = Enrollment.query.all()
    
    return render_template('admin.html', 
                         users=users, 
                         courses=courses, 
                         enrollments=enrollments)

# Маршруты (упрощенные версии)
@app.route('/')
def index():
    courses = Course.query.filter_by(is_published=True).limit(6).all()
    categories = Category.query.all()
    return render_template('index.html', courses=courses, categories=categories)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        full_name = request.form.get('full_name', '')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Пользователь уже существует!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            full_name=full_name,
            is_instructor=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            # Если у пользователя включена 2FA
            if user.twofa_enabled:
                # Сохраняем ID пользователя во временной сессии
                session['2fa_user_id'] = user.id
                flash('🔐 Введите код двухфакторной аутентификации', 'info')
                return redirect(url_for('verify_2fa_login'))
            else:
                login_user(user)
                flash('Вход выполнен успешно!', 'success')
                return redirect(url_for('dashboard'))
        else:
            flash('Неверные данные!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_courses = Course.query.filter_by(instructor_id=current_user.id).all()
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    return render_template('dashboard.html', 
                         created_courses=user_courses,
                         enrollments=enrollments)

@app.route('/courses')
def courses():
    all_courses = Course.query.filter_by(is_published=True).all()
    categories = Category.query.all()
    return render_template('courses.html', courses=all_courses, categories=categories)

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    course = Course.query.get_or_404(course_id)
    is_enrolled = False
    
    if current_user.is_authenticated:
        enrollment = Enrollment.query.filter_by(
            user_id=current_user.id, 
            course_id=course_id
        ).first()
        is_enrolled = enrollment is not None
    
    return render_template('course_detail.html', course=course, is_enrolled=is_enrolled)

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    enrollment = Enrollment.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()
    
    if not enrollment:
        new_enrollment = Enrollment(
            user_id=current_user.id,
            course_id=course_id
        )
        db.session.add(new_enrollment)
        db.session.commit()
        flash('Вы записались на курс!', 'success')
    
    return redirect(url_for('dashboard'))

@app.route('/create-course', methods=['GET', 'POST'])
@login_required
def create_course():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category_id = request.form.get('category_id')
        price = request.form.get('price', 0)
        
        course = Course(
            title=title,
            description=description,
            category_id=category_id if category_id else None,
            instructor_id=current_user.id,
            price=float(price) if price else 0.00
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash('Курс создан!', 'success')
        return redirect(url_for('dashboard'))
    
    categories = Category.query.all()
    return render_template('create_course.html', categories=categories)

@app.route('/edit-course/<int:course_id>', methods=['GET', 'POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    if course.instructor_id != current_user.id:
        flash('Нельзя редактировать чужой курс!', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        course.title = request.form['title']
        course.description = request.form['description']
        course.category_id = request.form.get('category_id')
        course.price = request.form.get('price', 0)
        course.difficulty_level = request.form.get('difficulty_level', 'beginner')
        
        db.session.commit()
        flash('Курс обновлен!', 'success')
        return redirect(url_for('dashboard'))
    
    categories = Category.query.all()
    return render_template('edit_course.html', course=course, categories=categories)

@app.route('/delete-course/<int:course_id>', methods=['POST'])
@login_required
def delete_course(course_id):
    course = Course.query.get_or_404(course_id)
    
    if course.instructor_id != current_user.id:
        flash('Нельзя удалить чужой курс!', 'danger')
        return redirect(url_for('dashboard'))
    
    db.session.delete(course)
    db.session.commit()
    flash('Курс удален!', 'info')
    return redirect(url_for('dashboard'))

@app.route('/my-courses')
@login_required
def my_courses():
    created_courses = Course.query.filter_by(instructor_id=current_user.id).all()
    enrollments = Enrollment.query.filter_by(user_id=current_user.id).all()
    enrolled_courses = [e.course for e in enrollments]
    
    return render_template('my_courses.html', 
                         created_courses=created_courses,
                         enrolled_courses=enrolled_courses)

@app.route('/setup-2fa')
@login_required
def setup_2fa():
    """Настройка двухфакторной аутентификации"""
    # Генерируем секретный ключ если его нет
    if not current_user.twofa_secret:
        current_user.twofa_secret = pyotp.random_base32()
        db.session.commit()
    
    # Создаем URI для Google Authenticator
    totp = pyotp.TOTP(current_user.twofa_secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="Education Portal")
    
    # Генерируем QR код
    qr = qrcode.make(uri)
    buffered = BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return render_template('setup_2fa.html', qr_code=qr_base64, secret=current_user.twofa_secret)

@app.route('/verify-2fa', methods=['POST'])
@login_required
def verify_2fa():
    """Подтверждение и активация 2FA"""
    code = request.form.get('code')
    
    if not current_user.twofa_secret:
        flash('Сначала настройте 2FA', 'danger')
        return redirect(url_for('setup_2fa'))
    
    totp = pyotp.TOTP(current_user.twofa_secret)
    
    if totp.verify(code):
        current_user.twofa_enabled = True
        db.session.commit()
        flash('✅ Двухфакторная аутентификация включена!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('❌ Неверный код. Попробуйте снова.', 'danger')
        return redirect(url_for('setup_2fa'))

@app.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    """Отключение двухфакторной аутентификации"""
    current_user.twofa_enabled = False
    current_user.twofa_secret = None
    db.session.commit()
    flash('🔓 Двухфакторная аутентификация отключена', 'info')
    return redirect(url_for('profile'))

# ИЗМЕНЕННЫЙ МАРШРУТ ВХОДА (с проверкой 2FA)
@app.route('/verify-2fa-login', methods=['GET', 'POST'])
def verify_2fa_login():
    """Страница ввода кода 2FA при входе"""
    if '2fa_user_id' not in session:
        flash('Сначала войдите в аккаунт', 'danger')
        return redirect(url_for('login'))
    
    user = User.query.get(session['2fa_user_id'])
    if not user:
        session.pop('2fa_user_id', None)
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        code = request.form.get('code')
        
        totp = pyotp.TOTP(user.twofa_secret)
        
        if totp.verify(code):
            login_user(user)
            session.pop('2fa_user_id', None)
            flash('✅ Вход выполнен успешно!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('❌ Неверный код 2FA. Попробуйте снова.', 'danger')
    
    return render_template('verify_2fa_login.html', email=user.email)

# Создаем БД и тестовые данные при запуске
with app.app_context():
    db.create_all()
    create_sample_data()

    # ============================================
# ДОБАВЛЕНИЕ ТЕСТОВЫХ КУРСОВ
# ============================================

def add_sample_courses():
    """Добавляет тестовые курсы в базу данных"""
    
    # Проверяем, есть ли уже курсы
    if Course.query.count() > 0:
        print(f"✅ В базе уже есть {Course.query.count()} курсов")
        return
    
    print("📚 Добавляем тестовые курсы...")
    
    # 1. Создаем категории
    categories_data = [
        {'name': 'Дизайн', 'description': 'Курсы по веб-дизайну, UI/UX, графическому дизайну', 'icon': '🎨'},
        {'name': 'Игровая разработка', 'description': 'Создание игр, геймдизайн, игровые движки', 'icon': '🎮'},
        {'name': 'Программирование', 'description': 'Веб-разработка, мобильные приложения, алгоритмы', 'icon': '💻'},
        {'name': '3D Моделирование', 'description': 'Blender, Maya, ZBrush, анимация', 'icon': '🖌️'},
        {'name': 'Звуковой дизайн', 'description': 'Создание музыки и звуковых эффектов для игр', 'icon': '🎵'}
    ]
    
    categories = {}
    for cat_data in categories_data:
        cat = Category.query.filter_by(name=cat_data['name']).first()
        if not cat:
            cat = Category(**cat_data)
            db.session.add(cat)
            db.session.flush()
        categories[cat_data['name']] = cat
    
    db.session.commit()
    print("✅ Категории добавлены")
    
    # 2. Создаем инструктора (текущий пользователь или новый)
    instructor = User.query.filter_by(is_instructor=True).first()
    if not instructor:
        instructor = User.query.first()
    
    if not instructor:
        # Создаем тестового инструктора
        instructor = User(
            username='instructor',
            email='instructor@example.com',
            password=generate_password_hash('instructor123'),
            full_name='Главный Инструктор',
            is_instructor=True
        )
        db.session.add(instructor)
        db.session.commit()
    
    print(f"✅ Инструктор: {instructor.username}")
    
    # 3. Данные курсов
    all_courses = [
        # Дизайн (3 курса)
        {'title': 'Основы веб-дизайна с нуля', 'description': 'Научитесь создавать современные и красивые веб-сайты с нуля. Изучите Figma, прототипирование, цветовую теорию и типографику.', 'category': 'Дизайн', 'price': 0, 'duration': 15, 'difficulty': 'beginner', 'image': 'https://images.unsplash.com/photo-1581291518633-83b4ebd1d83e?w=800'},
        {'title': 'UI/UX дизайн для начинающих', 'description': 'Полный курс по проектированию пользовательских интерфейсов. Изучите принципы юзабилити, создание пользовательских сценариев.', 'category': 'Дизайн', 'price': 2990, 'duration': 25, 'difficulty': 'intermediate', 'image': 'https://images.unsplash.com/photo-1561070791-2526d30994b5?w=800'},
        {'title': 'Графический дизайн: от идеи до макета', 'description': 'Освойте Adobe Photoshop и Illustrator. Научитесь создавать логотипы, баннеры, посты для соцсетей.', 'category': 'Дизайн', 'price': 4990, 'duration': 30, 'difficulty': 'intermediate', 'image': 'https://images.unsplash.com/photo-1626785774573-4b799315345d?w=800'},
        
        # Игровая разработка (3 курса)
        {'title': 'Создание 2D игр на Unity', 'description': 'Научитесь создавать 2D игры с нуля на движке Unity. Изучите C# для игр, физику, анимацию.', 'category': 'Игровая разработка', 'price': 3990, 'duration': 20, 'difficulty': 'beginner', 'image': 'https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800'},
        {'title': '3D игры на Unreal Engine 5', 'description': 'Полный курс по созданию 3D игр на Unreal Engine 5. Изучите Blueprints, создание уровней, освещение.', 'category': 'Игровая разработка', 'price': 5990, 'duration': 35, 'difficulty': 'advanced', 'image': 'https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800'},
        {'title': 'Геймдизайн: как придумать свою игру', 'description': 'Теоретический курс по геймдизайну. Изучите жанры игр, монетизацию, баланс, игровую экономику.', 'category': 'Игровая разработка', 'price': 1990, 'duration': 12, 'difficulty': 'beginner', 'image': 'https://images.unsplash.com/photo-1511512578047-dfb367046420?w=800'},
        
        # Программирование (3 курса)
        {'title': 'Python для начинающих', 'description': 'Изучите Python с нуля: синтаксис, функции, ООП, работа с файлами. Финальный проект: телеграм-бот.', 'category': 'Программирование', 'price': 0, 'duration': 20, 'difficulty': 'beginner', 'image': 'https://images.unsplash.com/photo-1526379095098-d400fd0bf935?w=800'},
        {'title': 'Веб-разработка на Flask', 'description': 'Создайте свой веб-сайт на Flask. Изучите маршруты, шаблоны, базы данных, аутентификацию.', 'category': 'Программирование', 'price': 3990, 'duration': 25, 'difficulty': 'intermediate', 'image': 'https://images.unsplash.com/photo-1547658719-da2b51169166?w=800'},
        {'title': 'JavaScript для Frontend', 'description': 'Освойте современный JavaScript: ES6+, асинхронность, работа с DOM, fetch API, React основы.', 'category': 'Программирование', 'price': 2990, 'duration': 18, 'difficulty': 'intermediate', 'image': 'https://images.unsplash.com/photo-1579468118864-1b9ea3c0db4a?w=800'},
        
        # 3D Моделирование (3 курса)
        {'title': 'Blender для начинающих', 'description': 'Создавайте 3D модели в Blender. Изучите интерфейс, моделирование, текстурирование, освещение.', 'category': '3D Моделирование', 'price': 0, 'duration': 22, 'difficulty': 'beginner', 'image': 'https://images.unsplash.com/photo-1633356122102-3fe601e05bd2?w=800'},
        {'title': '3D персонаж для игр', 'description': 'Научитесь создавать 3D персонажей для игр. Моделирование, риггинг, скининг, анимация.', 'category': '3D Моделирование', 'price': 4990, 'duration': 28, 'difficulty': 'intermediate', 'image': 'https://images.unsplash.com/photo-1633356122544-f134324a6cee?w=800'},
        {'title': 'Создание 3D окружений', 'description': 'Создавайте реалистичные 3D окружения для игр. Изучите ландшафтный дизайн, растения, воду.', 'category': '3D Моделирование', 'price': 5990, 'duration': 32, 'difficulty': 'advanced', 'image': 'https://images.unsplash.com/photo-1633356122102-3fe601e05bd2?w=800'},
        
        # Звуковой дизайн (3 курса)
        {'title': 'Создание музыки в FL Studio', 'description': 'Научитесь создавать электронную музыку в FL Studio. Изучите работу с паттернами, сведение.', 'category': 'Звуковой дизайн', 'price': 2990, 'duration': 15, 'difficulty': 'beginner', 'image': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800'},
        {'title': 'Звуковой дизайн для игр', 'description': 'Создавайте звуки для игр: шаги, выстрелы, окружение. Изучите работу с Audacity.', 'category': 'Звуковой дизайн', 'price': 3990, 'duration': 18, 'difficulty': 'intermediate', 'image': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800'},
        {'title': 'Сведение и мастеринг треков', 'description': 'Научитесь профессионально сводить и мастерить музыку. Изучите эквалайзеры, компрессоры.', 'category': 'Звуковой дизайн', 'price': 4990, 'duration': 20, 'difficulty': 'advanced', 'image': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?w=800'}
    ]
    
    # 4. Добавляем курсы
    courses_added = 0
    for course_data in all_courses:
        # Проверяем, нет ли уже такого курса
        existing = Course.query.filter_by(title=course_data['title']).first()
        if not existing:
            category = categories.get(course_data['category'])
            if category:
                course = Course(
                    title=course_data['title'],
                    description=course_data['description'],
                    category_id=category.id,
                    instructor_id=instructor.id,
                    price=course_data['price'],
                    duration_hours=course_data['duration'],
                    difficulty_level=course_data['difficulty'],
                    image_url=course_data['image'],
                    is_published=True
                )
                db.session.add(course)
                courses_added += 1
    
    db.session.commit()
    print(f"✅ Добавлено {courses_added} курсов")
    
    # 5. Добавляем уроки для первых курсов
    lessons_data = [
        {'course_title': 'Основы веб-дизайна с нуля', 'lessons': [
            {'title': 'Введение в веб-дизайн', 'content': 'Что такое веб-дизайн, роль дизайнера, инструменты, тренды 2024', 'duration': 15, 'order': 1},
            {'title': 'Основы Figma', 'content': 'Интерфейс Figma, работа со слоями, фреймы, компоненты, авто-лейауты', 'duration': 30, 'order': 2},
            {'title': 'Цветовая теория', 'content': 'Цветовые модели, психология цвета, подбор палитр, доступность цветов', 'duration': 25, 'order': 3}
        ]},
        {'course_title': 'Python для начинающих', 'lessons': [
            {'title': 'Установка Python', 'content': 'Скачивание и установка Python, настройка IDE, первый скрипт', 'duration': 10, 'order': 1},
            {'title': 'Переменные и типы данных', 'content': 'Числа, строки, списки, словари, приведение типов', 'duration': 25, 'order': 2},
            {'title': 'Условные операторы', 'content': 'if, elif, else, логические операторы, сравнения', 'duration': 20, 'order': 3}
        ]},
        {'course_title': 'Blender для начинающих', 'lessons': [
            {'title': 'Интерфейс Blender', 'content': 'Знакомство с интерфейсом, навигация, горячие клавиши', 'duration': 15, 'order': 1},
            {'title': 'Основы моделирования', 'content': 'Сетка, вершины, ребра, полигоны, экструзия', 'duration': 30, 'order': 2}
        ]},
        {'course_title': 'Создание 2D игр на Unity', 'lessons': [
            {'title': 'Установка Unity', 'content': 'Скачивание Unity Hub, установка редактора, создание первого проекта', 'duration': 15, 'order': 1},
            {'title': 'Основы C# для игр', 'content': 'Переменные, функции, классы, работа с GameObject', 'duration': 30, 'order': 2}
        ]}
    ]
    
    lessons_added = 0
    for item in lessons_data:
        course = Course.query.filter_by(title=item['course_title']).first()
        if course:
            for lesson_data in item['lessons']:
                existing_lesson = Lesson.query.filter_by(course_id=course.id, title=lesson_data['title']).first()
                if not existing_lesson:
                    lesson = Lesson(
                        course_id=course.id,
                        title=lesson_data['title'],
                        content=lesson_data['content'],
                        duration_minutes=lesson_data['duration'],
                        order_index=lesson_data['order']
                    )
                    db.session.add(lesson)
                    lessons_added += 1
    
    db.session.commit()
    print(f"✅ Добавлено {lessons_added} уроков")
    
    print("\n" + "="*50)
    print("🎉 ГОТОВО! На сайте теперь:")
    print(f"   - Категорий: {Category.query.count()}")
    print(f"   - Курсов: {Course.query.count()}")
    print(f"   - Уроков: {Lesson.query.count()}")
    print("="*50)

# Запускаем добавление курсов при старте приложения
with app.app_context():
    add_sample_courses()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)