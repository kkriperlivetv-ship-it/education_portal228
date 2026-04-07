import sqlite3
import os

def find_db_files():
    """Находит все .db файлы в текущей папке и подпапках"""
    db_files = []
    
    # Ищем в текущей папке
    for file in os.listdir('.'):
        if file.endswith('.db'):
            db_files.append(file)
    
    # Ищем в папке instance
    if os.path.exists('instance'):
        for file in os.listdir('instance'):
            if file.endswith('.db'):
                db_files.append(os.path.join('instance', file))
    
    return db_files

def update_db(db_path):
    """Обновляет базу данных добавляя колонки для 2FA"""
    print(f"\n📁 Обновляем: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Добавляем twofa_secret
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN twofa_secret VARCHAR(255)")
            print("  ✅ Добавлена колонка: twofa_secret")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print("  ⚠️ Колонка twofa_secret уже есть")
            else:
                print(f"  ❌ Ошибка: {e}")
        
        # Добавляем twofa_enabled
        try:
            cursor.execute("ALTER TABLE user ADD COLUMN twofa_enabled BOOLEAN DEFAULT 0")
            print("  ✅ Добавлена колонка: twofa_enabled")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print("  ⚠️ Колонка twofa_enabled уже есть")
            else:
                print(f"  ❌ Ошибка: {e}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def main():
    print("="*50)
    print("🔍 ПОИСК БАЗ ДАННЫХ")
    print("="*50)
    
    db_files = find_db_files()
    
    if not db_files:
        print("❌ Базы данных не найдены!")
        print("\nСоздайте новую базу данных:")
        print("   python app.py")
        print("\nИли укажите путь к БД вручную")
        return
    
    print(f"\nНайдено {len(db_files)} баз(а):")
    for db in db_files:
        print(f"  - {db}")
    
    print("\n" + "="*50)
    print("🔄 ОБНОВЛЕНИЕ БАЗ ДАННЫХ")
    print("="*50)
    
    for db in db_files:
        update_db(db)
    
    print("\n" + "="*50)
    print("✅ ГОТОВО!")
    print("="*50)

if __name__ == '__main__':
    main()