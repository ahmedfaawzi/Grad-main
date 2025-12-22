import psycopg2
import hashlib
import secrets
from contextlib import contextmanager
import os
import logging

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LibraryManagementSystem:
    def __init__(self):
        # إعدادات RDS - تغيير هذه القيم لمعلومات قاعدة بياناتك على AWS
        self.db_config = {
            'host': os.getenv('DB_HOST', 'llibrary-project-db.cuuhnwdvvtih.us-east-1.rds.amazonaws.com'),
            'database': os.getenv('DB_NAME', 'library-project-db'),
            'user': os.getenv('DB_USER', 'admin'),
            'password': os.getenv('DB_PASSWORD', 'ahmed1911'),
            'port': os.getenv('DB_PORT', 5432)
        }
        self.db_url = f"postgresql://{self.db_config['user']}:{self.db_config['password']}@{self.db_config['host']}:{self.db_config['port']}/{self.db_config['database']}"
        logger.info(f"Connecting to database at: {self.db_config['host']}")
    
    @contextmanager
    def get_connection(self):
        """الحصول على اتصال بقاعدة البيانات"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("Database connection established")
            yield conn
        except psycopg2.OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            raise
        finally:
            if conn:
                conn.close()
                logger.info("Database connection closed")

    @contextmanager
    def get_cursor(self):
        """الحصول على Cursor لإجراء الاستعلامات"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
                logger.debug("Transaction committed")
            except Exception as e:
                conn.rollback()
                logger.error(f"Transaction rolled back: {e}")
                raise
            finally:
                cursor.close()

    def init_db(self):
        """تهيئة قاعدة البيانات وإنشاء الجداول"""
        try:
            with self.get_cursor() as cursor:
                # إنشاء جدول المستخدمين
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'librarian', 'user')),
                        full_name VARCHAR(100) NOT NULL,
                        email VARCHAR(100),
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # إنشاء جدول الكتب
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        author VARCHAR(100) NOT NULL,
                        year INTEGER,
                        available BOOLEAN DEFAULT TRUE,
                        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # إنشاء جدول الكتب المستعارة
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS borrowed_books (
                        id SERIAL PRIMARY KEY,
                        book_id INTEGER REFERENCES books(id),
                        borrower VARCHAR(100) NOT NULL,
                        borrow_date DATE DEFAULT CURRENT_DATE,
                        return_date DATE,
                        CONSTRAINT unique_active_borrow UNIQUE (book_id) WHERE return_date IS NULL
                    )
                """)
                
                logger.info("Database tables created/verified successfully")
                
                # إضافة المستخدمين الافتراضيين إذا لم يكن هناك مستخدمين
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    demo_users = [
                        ('admin', self.hash_password('admin123'), 'admin', 'System Administrator', 'admin@library.com'),
                        ('librarian', self.hash_password('lib123'), 'librarian', 'Library Manager', 'librarian@library.com'),
                        ('user', self.hash_password('user123'), 'user', 'Regular User', 'user@library.com')
                    ]
                    
                    for user in demo_users:
                        cursor.execute(
                            "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
                            user
                        )
                    
                    logger.info("Demo users added to database")
                    
                # إضافة كتب تجريبية إذا لم يكن هناك كتب
                cursor.execute("SELECT COUNT(*) FROM books")
                book_count = cursor.fetchone()[0]
                
                if book_count == 0:
                    demo_books = [
                        ('The Great Gatsby', 'F. Scott Fitzgerald', 1925),
                        ('To Kill a Mockingbird', 'Harper Lee', 1960),
                        ('1984', 'George Orwell', 1949),
                        ('Pride and Prejudice', 'Jane Austen', 1813),
                        ('The Catcher in the Rye', 'J.D. Salinger', 1951)
                    ]
                    
                    for book in demo_books:
                        cursor.execute(
                            "INSERT INTO books (title, author, year) VALUES (%s, %s, %s)",
                            book
                        )
                    
                    logger.info("Demo books added to database")
                    
            return True
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            return False

    def hash_password(self, password):
        """تجزئة كلمة المرور"""
        return hashlib.sha256(password.encode()).hexdigest()

    def authenticate_user(self, username, password):
        """مصادقة المستخدم من قاعدة البيانات"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "SELECT id, username, password_hash, role, full_name FROM users WHERE username = %s",
                    (username,)
                )
                user = cursor.fetchone()
                
                if user:
                    user_id, db_username, db_password_hash, role, full_name = user
                    input_password_hash = self.hash_password(password)
                    
                    if input_password_hash == db_password_hash:
                        logger.info(f"User {username} authenticated successfully")
                        return {
                            "id": user_id,
                            "username": db_username,
                            "role": role,
                            "full_name": full_name
                        }
                    else:
                        logger.warning(f"Failed authentication for user {username}: incorrect password")
                else:
                    logger.warning(f"Failed authentication: user {username} not found")
                    
        except Exception as e:
            logger.error(f"Authentication error: {e}")
        
        return None

    def create_user(self, username, password, role, full_name, email):
        """إنشاء مستخدم جديد"""
        try:
            password_hash = self.hash_password(password)
            with self.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (username, password_hash, role, full_name, email) VALUES (%s, %s, %s, %s, %s)",
                    (username, password_hash, role, full_name, email)
                )
            logger.info(f"User {username} created successfully")
            return True
        except psycopg2.IntegrityError:
            logger.error(f"User {username} already exists")
            return False
        except Exception as e:
            logger.error(f"Error creating user: {e}")
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
                return [
                    {
                        "id": row[0],
                        "username": row[1],
                        "role": row[2],
                        "full_name": row[3],
                        "email": row[4],
                        "created_date": row[5]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []

    def get_all_books(self):
        """الحصول على جميع الكتب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, author, year, available 
                    FROM books 
                    ORDER BY title
                """)
                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "author": row[2],
                        "year": row[3],
                        "available": row[4]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting books: {e}")
            return []

    def get_available_books(self):
        """الحصول على الكتب المتاحة"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, title, author, year 
                    FROM books 
                    WHERE available = TRUE 
                    ORDER BY title
                """)
                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "author": row[2],
                        "year": row[3]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting available books: {e}")
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
                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "author": row[2],
                        "borrower": row[3],
                        "borrow_date": row[4]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error getting borrowed books: {e}")
            return []

    def add_book(self, title, author, year=None):
        """إضافة كتاب جديد"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "INSERT INTO books (title, author, year) VALUES (%s, %s, %s)",
                    (title, author, year)
                )
            logger.info(f"Book '{title}' added successfully")
            return True
        except Exception as e:
            logger.error(f"Error adding book: {e}")
            return False

    def borrow_book(self, book_id, borrower_name):
        """استعارة كتاب"""
        try:
            with self.get_cursor() as cursor:
                # التحقق من توفر الكتاب
                cursor.execute("SELECT available FROM books WHERE id = %s", (book_id,))
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    logger.warning(f"Book {book_id} is not available for borrowing")
                    return False
                
                # تحديث حالة الكتاب
                cursor.execute("UPDATE books SET available = FALSE WHERE id = %s", (book_id,))
                
                # تسجيل الاستعارة
                cursor.execute(
                    "INSERT INTO borrowed_books (book_id, borrower) VALUES (%s, %s)",
                    (book_id, borrower_name)
                )
                
            logger.info(f"Book {book_id} borrowed by {borrower_name}")
            return True
        except Exception as e:
            logger.error(f"Error borrowing book: {e}")
            return False

    def return_book(self, book_id):
        """إرجاع كتاب"""
        try:
            with self.get_cursor() as cursor:
                # التحقق من أن الكتاب مستعار
                cursor.execute("SELECT available FROM books WHERE id = %s", (book_id,))
                result = cursor.fetchone()
                
                if result and result[0]:  # الكتاب متاح بالفعل
                    logger.warning(f"Book {book_id} is already available")
                    return False
                
                # تحديث حالة الكتاب
                cursor.execute("UPDATE books SET available = TRUE WHERE id = %s", (book_id,))
                
                # تحديث تاريخ الإرجاع
                cursor.execute(
                    "UPDATE borrowed_books SET return_date = CURRENT_DATE WHERE book_id = %s AND return_date IS NULL",
                    (book_id,)
                )
                
            logger.info(f"Book {book_id} returned successfully")
            return True
        except Exception as e:
            logger.error(f"Error returning book: {e}")
            return False

    def search_books(self, query):
        """بحث عن الكتب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, title, author, year, available 
                    FROM books 
                    WHERE title ILIKE %s OR author ILIKE %s
                    ORDER BY title
                    """,
                    (f'%{query}%', f'%{query}%')
                )
                return [
                    {
                        "id": row[0],
                        "title": row[1],
                        "author": row[2],
                        "year": row[3],
                        "available": row[4]
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Error searching books: {e}")
            return []

    def get_total_books(self):
        """الحصول على إجمالي عدد الكتب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM books")
                return cursor.fetchone()[0] or 0
        except Exception as e:
            logger.error(f"Error getting total books count: {e}")
            return 0

    def get_available_books_count(self):
        """الحصول على عدد الكتب المتاحة"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM books WHERE available = TRUE")
                return cursor.fetchone()[0] or 0
        except Exception as e:
            logger.error(f"Error getting available books count: {e}")
            return 0

    def get_borrowed_books_count(self):
        """الحصول على عدد الكتب المستعارة"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM books WHERE available = FALSE")
                return cursor.fetchone()[0] or 0
        except Exception as e:
            logger.error(f"Error getting borrowed books count: {e}")
            return 0

    def delete_book(self, book_id):
        """حذف كتاب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("DELETE FROM books WHERE id = %s", (book_id,))
                logger.info(f"Book {book_id} deleted successfully")
                return True
        except Exception as e:
            logger.error(f"Error deleting book: {e}")
            return False

    def update_book(self, book_id, title, author, year):
        """تحديث معلومات الكتاب"""
        try:
            with self.get_cursor() as cursor:
                cursor.execute(
                    "UPDATE books SET title = %s, author = %s, year = %s WHERE id = %s",
                    (title, author, year, book_id)
                )
                logger.info(f"Book {book_id} updated successfully")
                return True
        except Exception as e:
            logger.error(f"Error updating book: {e}")
            return False