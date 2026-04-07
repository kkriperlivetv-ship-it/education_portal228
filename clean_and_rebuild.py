import os
import sqlite3
import shutil

# 1. Удаляем ВСЕ файлы БД
print("1. Удаляем старые базы данных...")
db_files = ['education_portal.db', 'site.db', 'app.db', 'database.db', 'test.db']
for file in db_files:
    if os.path.exists(file):
        os.remove(file)
        print(f"   Удален: {file}")

# 2. Удаляем папку instance
if os.path.exists('instance'):
    shutil.rmtree('instance')
    print("   Удалена папка: instance")

# 3. Создаем новую БД в корне проекта
print("\n2. Создаем новую базу данных...")
conn = sqlite3.connect('education_portal.db')
cursor = conn.cursor()

# Создаем таблицы
cursor.execute('''
CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    full_name TEXT,
    is_instructor BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS course (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category_id INTEGER,
    instructor_id INTEGER,
    price REAL DEFAULT 0,
    duration_hours INTEGER,
    difficulty_level TEXT DEFAULT 'beginner',
    image_url TEXT,
    is_published BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES category(id),
    FOREIGN KEY (instructor_id) REFERENCES user(id)
)
''')

# Добавляем пользователя
cursor.execute('''
INSERT OR REPLACE INTO user (id, username, email, password, full_name, is_instructor, is_admin)
VALUES (1, 'admin', 'admin@example.com', 'pbkdf2:sha256:260000$123456', 'Администратор', 1, 1)
''')

# Добавляем категории
categories = [
    ('Дизайн', 'Курсы по веб-дизайну, UI/UX', '🎨'),
    ('Игровая разработка', 'Создание игр, геймдизайн', '🎮'),
    ('Программирование', 'Веб-разработка, алгоритмы', '💻'),
    ('3D Моделирование', 'Blender, Maya, анимация', '🖌️'),
    ('Звуковой дизайн', 'Создание музыки и звуков', '🎵')
]

for cat in categories:
    cursor.execute('INSERT INTO category (name, description, icon) VALUES (?, ?, ?)', cat)

# Получаем ID категорий
cursor.execute('SELECT id, name FROM category')
cat_ids = {name: id for id, name in cursor.fetchall()}

# Добавляем 15 курсов
courses_data = [
    ('Основы веб-дизайна', 'Изучите Figma, прототипирование', cat_ids['Дизайн'], 0, 'beginner'),
    ('UI/UX дизайн', 'Проектирование интерфейсов', cat_ids['Дизайн'], 2990, 'intermediate'),
    ('Графический дизайн', 'Photoshop и Illustrator', cat_ids['Дизайн'], 4990, 'intermediate'),
    ('2D игры на Unity', 'Создание 2D игр', cat_ids['Игровая разработка'], 3990, 'beginner'),
    ('3D игры на Unreal', 'Unreal Engine 5', cat_ids['Игровая разработка'], 5990, 'advanced'),
    ('Геймдизайн', 'Проектирование игр', cat_ids['Игровая разработка'], 1990, 'beginner'),
    ('Python для начинающих', 'Основы Python', cat_ids['Программирование'], 0, 'beginner'),
    ('Flask веб-разработка', 'Сайты на Flask', cat_ids['Программирование'], 3990, 'intermediate'),
    ('JavaScript Frontend', 'React и JS', cat_ids['Программирование'], 2990, 'intermediate'),
    ('Blender 3D', '3D моделирование', cat_ids['3D Моделирование'], 0, 'beginner'),
    ('3D персонажи', 'Моделирование персонажей', cat_ids['3D Моделирование'], 4990, 'intermediate'),
    ('3D окружения', 'Ландшафты и сцены', cat_ids['3D Моделирование'], 5990, 'advanced'),
    ('FL Studio', 'Создание музыки', cat_ids['Звуковой дизайн'], 2990, 'beginner'),
    ('Звук для игр', 'Звуковые эффекты', cat_ids['Звуковой дизайн'], 3990, 'intermediate'),
    ('Сведение и мастеринг', 'Профессиональный звук', cat_ids['Звуковой дизайн'], 4990, 'advanced')
]

for course in courses_data:
    cursor.execute('''
    INSERT INTO course (title, description, category_id, instructor_id, price, difficulty_level, is_published)
    VALUES (?, ?, ?, 1, ?, ?, 1)
    ''', (course[0], course[1], course[2], course[3], course[4]))

conn.commit()
conn.close()

print("✅ Новая база данных создана!")

# 4. Проверяем результат
print("\n3. Проверяем базу данных...")
conn = sqlite3.connect('education_portal.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM course')
count = cursor.fetchone()[0]
print(f"   Курсов в БД: {count}")
conn.close()

print("\n" + "="*50)
print("✅ ГОТОВО! Теперь запустите сайт:")
print("   python app.py")
print("="*50)