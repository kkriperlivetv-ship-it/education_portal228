# update_db.py - Обновление базы данных для 2FA

import sqlite3
import os

def update_database():
    print("="*50)
    print("🔧 ОБНОВЛЕНИЕ БАЗЫ ДАННЫХ ДЛЯ 2FA")
    print("="*50)
    
    # Проверяем существование БД
    db_files = ['education_portal.db', 'site.db', 'app.db', 'database.db']
    db_file = None
    
    for file in db_files:
        if os.path.exists(file):
            db_file = file
            break
    
    if not db_file:
        print("❌ База данных не найдена!")
        print("   Сначала запустите python app.py для создания БД")
        return False
    
    print(f"📁 Найдена база данных: {db_file}")
    
    # Подключаемся к БД
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Проверяем и добавляем колонку twofa_secret
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN twofa_secret VARCHAR(255)")
        print("✅ Добавлена колонка: twofa_secret")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ Колонка twofa_secret уже существует")
        else:
            print(f"❌ Ошибка: {e}")
    
    # Проверяем и добавляем колонку twofa_enabled
    try:
        cursor.execute("ALTER TABLE user ADD COLUMN twofa_enabled BOOLEAN DEFAULT 0")
        print("✅ Добавлена колонка: twofa_enabled")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠️ Колонка twofa_enabled уже существует")
        else:
            print(f"❌ Ошибка: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*50)
    print("✅ БАЗА ДАННЫХ УСПЕШНО ОБНОВЛЕНА!")
    print("="*50)
    print("\nТеперь можно запускать приложение:")
    print("   python app.py")
    
    return True

if __name__ == '__main__':
    update_database()