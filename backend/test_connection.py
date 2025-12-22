#!/usr/bin/env python3
"""
اختبار الاتصال بقاعدة بيانات RDS MySQL
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

def test_rds_connection():
    print("=" * 60)
    print("🔍 Testing RDS MySQL Connection")
    print("=" * 60)
    
    # إعدادات الاتصال من ملف .env
    config = {
        'host': os.getenv('DB_HOST'),
        'user': os.getenv('DB_USER'),
        'password': os.getenv('DB_PASSWORD'),
        'port': int(os.getenv('DB_PORT', 3306))
    }
    
    print(f"📡 Connecting to: {config['host']}")
    print(f"👤 Username: {config['user']}")
    
    connection = None
    try:
        # 1. اختبار الاتصال الأساسي
        print("\n1. Testing basic connection...")
        connection = mysql.connector.connect(**config)
        
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f"✅ Connected to MySQL Server version {db_info}")
            
            cursor = connection.cursor()
            
            # 2. إنشاء قاعدة البيانات
            print("\n2. Creating database if not exists...")
            cursor.execute("CREATE DATABASE IF NOT EXISTS library_db")
            print("✅ Database 'library_db' ready")
            
            cursor.execute("USE library_db")
            
            # 3. اختبار الاستعلامات البسيطة
            print("\n3. Testing basic queries...")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"   Found {len(tables)} tables")
            
            if tables:
                for table in tables:
                    print(f"   - {table[0]}")
            
            # 4. إضافة بيانات تجريبية
            print("\n4. Adding sample data if needed...")
            
            import hashlib
            def hash_password(pwd):
                return hashlib.sha256(pwd.encode()).hexdigest()
            
            # إضافة مستخدمين
            cursor.execute("SELECT COUNT(*) FROM users")
            if cursor.fetchone()[0] == 0:
                demo_users = [
                    ('admin', hash_password('admin123'), 'admin', 'System Admin', 'admin@library.com'),
                    ('librarian', hash_password('lib123'), 'librarian', 'Library Manager', 'librarian@library.com'),
                    ('user', hash_password('user123'), 'user', 'Regular User', 'user@library.com')
                ]
                
                cursor.executemany("""
                    INSERT INTO users (username, password_hash, role, full_name, email)
                    VALUES (%s, %s, %s, %s, %s)
                """, demo_users)
                print("✅ Demo users added")
            
            # إضافة كتب
            cursor.execute("SELECT COUNT(*) FROM books")
            if cursor.fetchone()[0] == 0:
                demo_books = [
                    ('The Great Gatsby', 'F. Scott Fitzgerald', 1925),
                    ('To Kill a Mockingbird', 'Harper Lee', 1960),
                    ('1984', 'George Orwell', 1949)
                ]
                
                cursor.executemany("""
                    INSERT INTO books (title, author, year)
                    VALUES (%s, %s, %s)
                """, demo_books)
                print("✅ Demo books added")
            
            # 5. عرض الإحصائيات
            print("\n5. Database statistics:")
            cursor.execute("SELECT COUNT(*) FROM users")
            print(f"   👥 Users: {cursor.fetchone()[0]}")
            
            cursor.execute("SELECT COUNT(*) FROM books")
            print(f"   📚 Books: {cursor.fetchone()[0]}")
            
            cursor.execute("SELECT COUNT(*) FROM books WHERE available = TRUE")
            print(f"   ✅ Available books: {cursor.fetchone()[0]}")
            
            print("\n" + "=" * 60)
            print("🎉 RDS MySQL Connection Test PASSED!")
            print("\n📝 Login credentials for testing:")
            print("   👑 Admin:     admin / admin123")
            print("   📖 Librarian: librarian / lib123")
            print("   👤 User:      user / user123")
            print("\n🌐 Access the app at: http://localhost:5000")
            print("=" * 60)
            
            return True
            
    except Error as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("   1. Check if RDS instance is running")
        print("   2. Verify security group allows inbound traffic on port 3306")
        print("   3. Confirm username and password in .env file")
        print("   4. Check if VPC settings allow connections")
        return False
        
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("\n✅ Connection closed properly")

if __name__ == "__main__":
    success = test_rds_connection()
    sys.exit(0 if success else 1)
