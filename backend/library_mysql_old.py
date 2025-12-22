import pymysql
from pymysql import Error
from contextlib import contextmanager
import hashlib
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LibraryManagementSystem:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'library_db'),
            'user': os.getenv('DB_USER', 'admin'),
            'password': os.getenv('DB_PASSWORD', 'ahmed1911'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor,
            'autocommit': False
        }
        logger.info(f"Using MySQL at: {self.db_config['host']}:{self.db_config['port']}")
    
    def create_database_if_not_exists(self):
        """إنشاء قاعدة البيانات إذا لم تكن موجودة"""
        try:
            # اتصال بدون تحديد قاعدة بيانات
            temp_config = self.db_config.copy()
            temp_config.pop('database', None)
            
            connection = pymysql.connect(**temp_config)
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.db_config['database']}")
                cursor.execute(f"USE {self.db_config['database']}")
                logger.info(f"✅ Database '{self.db_config['database']}' created/selected")
            connection.commit()
            connection.close()
            return True
            
        except Error as e:
            logger.error(f"❌ Failed to create database: {e}")
            return False
    
    @contextmanager
    def get_connection(self):
        """الحصول على اتصال بقاعدة البيانات"""
        connection = None
        try:
            connection = pymysql.connect(**self.db_config)
            logger.debug("Database connection established")
            yield connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            # إذا كانت المشكلة أن قاعدة البيانات غير موجودة، أنشئها
            if e.args[0] == 1049:  # Unknown database
                logger.info("Database doesn't exist, creating it...")
                if self.create_database_if_not_exists():
                    connection = pymysql.connect(**self.db_config)
                    yield connection
                else:
                    raise
            else:
                raise
        finally:
            if connection:
                connection.close()
                logger.debug("Database connection closed")
    
    @contextmanager
    def get_cursor(self):
        """الحصول على cursor لإجراء الاستعلامات"""
        with self.get_connection() as connection:
            cursor = connection.cursor()
            try:
                yield cursor
                connection.commit()
                logger.debug("Transaction committed")
            except Error as e:
                connection.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise
            finally:
                cursor.close()
    
    def init_db(self):
        """تهيئة قاعدة البيانات وإنشاء الجداول"""
        try:
            # أولاً: تأكد من وجود قاعدة البيانات
            self.create_database_if_not_exists()
            
            with self.get_cursor() as cursor:
                # إنشاء جدول المستخدمين
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) NOT NULL,
                        full_name VARCHAR(100) NOT NULL,
                        email VARCHAR(100),
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_username (username)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # إنشاء جدول الكتب
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        author VARCHAR(100) NOT NULL,
                        year INT,
                        available BOOLEAN DEFAULT TRUE,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_title (title),
                        INDEX idx_author (author),
                        INDEX idx_available (available)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                # إنشاء جدول الكتب المستعارة
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS borrowed_books (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        book_id INT NOT NULL,
                        borrower VARCHAR(100) NOT NULL,
                        borrow_date DATE DEFAULT (CURRENT_DATE),
                        return_date DATE,
                        FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
                        INDEX idx_book_id (book_id),
                        INDEX idx_borrower (borrower)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)
                
                logger.info("✅ Database tables created/verified successfully")
                
                # التحقق من وجود المستخدمين الافتراضيين
                cursor.execute("SELECT COUNT(*) as count FROM users")
                result = cursor.fetchone()
                user_count = result['count'] if isinstance(result, dict) else result[0]
                
                if user_count == 0:
                    logger.info("Adding demo users...")
                    demo_users = [
                        ('admin', self.hash_password('admin123'), 'admin', 'System Administrator', 'admin@library.com'),
                        ('librarian', self.hash_password('lib123'), 'librarian', 'Library Manager', 'librarian@library.com'),
                        ('user', self.hash_password('user123'), 'user', 'Regular User', 'user@library.com')
                    ]
                    
                    for user in demo_users:
                        cursor.execute(
                            "INSERT IGNORE INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
                            user
                        )
                    logger.info("✅ Demo users added")
                
                # التحقق من وجود الكتب التجريبية
                cursor.execute("SELECT COUNT(*) as count FROM books")
                result = cursor.fetchone()
                book_count = result['count'] if isinstance(result, dict) else result[0]
                
                if book_count == 0:
                    logger.info("Adding demo books...")
                    demo_books = [
                        ('The Great Gatsby', 'F. Scott Fitzgerald', 1925),
                        ('To Kill a Mockingbird', 'Harper Lee', 1960),
                        ('1984', 'George Orwell', 1949),
                        ('Pride and Prejudice', 'Jane Austen', 1813),
                        ('The Catcher in the Rye', 'J.D. Salinger', 1951)
                    ]
                    
                    for book in demo_books:
                        cursor.execute(
                            "INSERT IGNORE INTO books (title, author, year) VALUES (%s, %s, %s)",
                            book
                        )
                    logger.info("✅ Demo books added")
                
                return True
                
        except Error as e:
            logger.error(f"❌ Error initializing database: {e}")
            return False
    
    def hash_password(self, password):
        """تجزئة كلمة المرور"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def authenticate_user(self, username, password):
        """مصادقة المستخدم"""
        try:
            with self.get_cursor() as cursor:
                query = "SELECT id, username, password_hash, role, full_name FROM users WHERE username = %s"
                cursor.execute(query, (username,))
                user = cursor.fetchone()
                
                if user:
                    input_password_hash = self.hash_password(password)
                    if input_password_hash == user['password_hash']:
                        logger.info(f"✅ User {username} authenticated")
                        return {
                            "id": user['id'],
                            "username": user['username'],
                            "role": user['role'],
                            "full_name": user['full_name']
                        }
        except Error as e:
            logger.error(f"❌ Authentication error: {e}")
        return None
    
    def get_all_books(self):
        """الحصول على جميع الكتب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT id, title, author, year, available FROM books ORDER BY title")
                return cursor.fetchall()
        except Error as e:
            logger.error(f"❌ Error getting books: {e}")
            return []
    
    def get_available_books(self):
        """الحصول على الكتب المتاحة"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT id, title, author, year FROM books WHERE available = TRUE ORDER BY title")
                return cursor.fetchall()
        except Error as e:
            logger.error(f"❌ Error getting available books: {e}")
            return []
    
    def get_borrowed_books(self):
        """الحصول على الكتب المستعارة"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT b.id, b.title, b.author, bb.borrower, bb.borrow_date 
                    FROM books b 
                    JOIN borrowed_books bb ON b.id = bb.book_id 
                    WHERE b.available = FALSE AND bb.return_date IS NULL
                    ORDER BY bb.borrow_date DESC
                """)
                return cursor.fetchall()
        except Error as e:
            logger.error(f"❌ Error getting borrowed books: {e}")
            return []
    
    def add_book(self, title, author, year=None):
        """إضافة كتاب جديد"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("INSERT INTO books (title, author, year) VALUES (%s, %s, %s)", (title, author, year))
                logger.info(f"✅ Book '{title}' added")
                return True
        except Error as e:
            logger.error(f"❌ Error adding book: {e}")
            return False
    
    def borrow_book(self, book_id, borrower_name):
        """استعارة كتاب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT available FROM books WHERE id = %s", (book_id,))
                book = cursor.fetchone()
                
                if not book or not book['available']:
                    return False
                
                cursor.execute("UPDATE books SET available = FALSE WHERE id = %s", (book_id,))
                cursor.execute("INSERT INTO borrowed_books (book_id, borrower) VALUES (%s, %s)", (book_id, borrower_name))
                logger.info(f"✅ Book {book_id} borrowed by {borrower_name}")
                return True
        except Error as e:
            logger.error(f"❌ Error borrowing book: {e}")
            return False
    
    def return_book(self, book_id):
        """إرجاع كتاب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT available FROM books WHERE id = %s", (book_id,))
                book = cursor.fetchone()
                
                if book and book['available']:
                    return False
                
                cursor.execute("UPDATE books SET available = TRUE WHERE id = %s", (book_id,))
                cursor.execute("UPDATE borrowed_books SET return_date = CURRENT_DATE WHERE book_id = %s AND return_date IS NULL", (book_id,))
                logger.info(f"✅ Book {book_id} returned")
                return True
        except Error as e:
            logger.error(f"❌ Error returning book: {e}")
            return False
    
    def search_books(self, query):
        """بحث عن الكتب"""
        try:
            with self.get_cursor() as cursor:
                search_query = f"%{query}%"
                cursor.execute("""
                    SELECT id, title, author, year, available 
                    FROM books 
                    WHERE title LIKE %s OR author LIKE %s
                    ORDER BY title
                """, (search_query, search_query))
                return cursor.fetchall()
        except Error as e:
            logger.error(f"❌ Error searching books: {e}")
            return []
    
    def get_total_books(self):
        """الحصول على إجمالي عدد الكتب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM books")
                result = cursor.fetchone()
                return result['count'] if isinstance(result, dict) else result[0]
        except Error as e:
            logger.error(f"❌ Error getting total books: {e}")
            return 0
    
    def get_available_books_count(self):
        """الحصول على عدد الكتب المتاحة"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM books WHERE available = TRUE")
                result = cursor.fetchone()
                return result['count'] if isinstance(result, dict) else result[0]
        except Error as e:
            logger.error(f"❌ Error getting available books count: {e}")
            return 0
    
    def get_borrowed_books_count(self):
        """الحصول على عدد الكتب المستعارة"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM books WHERE available = FALSE")
                result = cursor.fetchone()
                return result['count'] if isinstance(result, dict) else result[0]
        except Error as e:
            logger.error(f"❌ Error getting borrowed books count: {e}")
            return 0
    
    def create_user(self, username, password, role, full_name, email):
        """إنشاء مستخدم جديد"""
        try:
            password_hash = self.hash_password(password)
            with self.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
                    (username, password_hash, role, full_name, email)
                )
                logger.info(f"✅ User {username} created")
                return True
        except Error as e:
            logger.error(f"❌ Error creating user: {e}")
            return False
    
    def get_all_users(self):
        """الحصول على جميع المستخدمين"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, role, full_name, email, created_date 
                    FROM users 
                    ORDER BY created_date DESC
                """)
                return cursor.fetchall()
        except Error as e:
            logger.error(f"❌ Error getting users: {e}")
            return []
