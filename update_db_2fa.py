import sqlite3
import os

def update_database():
    # Находим файл БД
    db_file = 'education_portal.db'
    
    if not os.path.exists(db_file):
        print(f"❌ Файл {db_file} не найден!")
        return False
    
    print(f"📁 Обновляем базу данных: {db_file}")
    
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
    
    print("\n✅ База данных успешно обновлена!")
    return True

if __name__ == '__main__':
    update_database()