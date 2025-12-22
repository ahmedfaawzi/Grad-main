from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import library_mysql as library
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# تحميل credentials باستخدام KMS
def load_credentials_from_kms():
    """تحميل credentials من ملف KMS المشفر"""
    try:
        from kms_helper import KMSHelper
        kms = KMSHelper()
        credentials = kms.load_encrypted_credentials('encrypted_credentials.json')
        
        if credentials:
            logger.info("✅ Loaded credentials from KMS")
            return credentials
        else:
            raise Exception("Failed to load credentials from KMS")
            
    except Exception as e:
        logger.warning(f"⚠️  KMS not available: {e}")
        # Fallback إلى .env
        logger.info("Using .env file as fallback")
        return {
            "DB_HOST": os.getenv('DB_HOST', 'localhost'),
            "DB_USER": os.getenv('DB_USER', 'admin'),
            "DB_PASSWORD": os.getenv('DB_PASSWORD', ''),
            "DB_NAME": os.getenv('DB_NAME', 'library_db'),
            "DB_PORT": os.getenv('DB_PORT', '3306')
        }

# تحميل credentials
CREDENTIALS = load_credentials_from_kms()

# تعيين secret key من .env
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# تهيئة النظام مع credentials
lib_system = library.LibraryManagementSystem(credentials=CREDENTIALS)

# تهيئة قاعدة البيانات عند بدء التشغيل
with app.app_context():
    logger.info("Initializing database...")
    success = lib_system.init_db()
    if success:
        logger.info("Database initialized successfully")
    else:
        logger.error("Failed to initialize database")

# الديكوراتورات كما هي...
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def librarian_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'error')
            return redirect(url_for('login'))
        if session.get('role') not in ['admin', 'librarian']:
            flash('Access denied. Librarian or Admin privileges required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    """الصفحة الرئيسية"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    stats = {
        'total_books': lib_system.get_total_books(),
        'available_books': lib_system.get_available_books_count(),
        'borrowed_books': lib_system.get_borrowed_books_count(),
    }
    
    # الحصول على الكتب الجديدة المضافة
    try:
        all_books = lib_system.get_all_books()
        recent_books = all_books[:5] if len(all_books) > 5 else all_books
    except:
        recent_books = []
    
    return render_template("index.html", 
                         stats=stats, 
                         recent_books=recent_books,
                         username=session.get('username'),
                         role=session.get('role'),
                         full_name=session.get('full_name'))

@app.route("/dashboard")
@login_required
def dashboard():
    """لوحة التحكم"""
    stats = {
        'total_books': lib_system.get_total_books(),
        'available_books': lib_system.get_available_books_count(),
        'borrowed_books': lib_system.get_borrowed_books_count(),
    }
    
    borrowed_books = lib_system.get_borrowed_books()
    
    return render_template("dashboard.html",
                         stats=stats,
                         borrowed_books=borrowed_books,
                         username=session.get('username'),
                         role=session.get('role'))

@app.route("/books")
@login_required
def books():
    """صفحة عرض جميع الكتب"""
    all_books = lib_system.get_all_books()
    return render_template("books.html", 
                         books=all_books,
                         role=session.get('role'))

@app.route("/books/add", methods=["GET", "POST"])
@librarian_required
def add_book():
    """إضافة كتاب جديد"""
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        year = request.form.get("year", "").strip()
        
        if not title or not author:
            flash("Title and author are required!", "error")
            return render_template("add_book.html")
        
        try:
            year = int(year) if year else None
        except ValueError:
            flash("Please enter a valid year", "error")
            return render_template("add_book.html")
        
        success = lib_system.add_book(title, author, year)
        if success:
            flash(f"Book '{title}' added successfully!", "success")
            return redirect(url_for("books"))
        else:
            flash("Error adding book. Please try again.", "error")
    
    return render_template("add_book.html")

@app.route("/books/search", methods=["GET", "POST"])
@login_required
def search_books():
    """بحث عن الكتب"""
    results = []
    query = ""
    
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if query:
            results = lib_system.search_books(query)
            if not results:
                flash("No books found matching your search", "info")
    
    return render_template("search.html", 
                         results=results, 
                         query=query,
                         role=session.get('role'))

@app.route("/books/borrow", methods=["GET", "POST"])
@login_required
def borrow_book():
    """استعارة كتاب"""
    if request.method == "POST":
        book_id = request.form.get("book_id")
        borrower_name = f"{session.get('full_name')} ({session.get('username')})"
        
        if book_id:
            success = lib_system.borrow_book(int(book_id), borrower_name)
            if success:
                flash("Book borrowed successfully!", "success")
            else:
                flash("Book is already borrowed or not found", "error")
    
    available_books = lib_system.get_available_books()
    return render_template("borrow.html", 
                         books=available_books,
                         username=session.get('username'))

@app.route("/books/return", methods=["GET", "POST"])
@login_required
def return_book():
    """إرجاع كتاب"""
    if request.method == "POST":
        book_id = request.form.get("book_id")
        if book_id:
            success = lib_system.return_book(int(book_id))
            if success:
                flash("Book returned successfully!", "success")
            else:
                flash("Book is not currently borrowed", "error")
    
    borrowed_books = lib_system.get_borrowed_books()
    return render_template("return.html", books=borrowed_books)

@app.route("/users")
@admin_required
def users():
    """إدارة المستخدمين"""
    all_users = lib_system.get_all_users()
    return render_template("users.html", users=all_users)

@app.route("/users/add", methods=["GET", "POST"])
@admin_required
def add_user():
    """إضافة مستخدم جديد"""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "user")
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        
        if not username or not password:
            flash("Username and password are required!", "error")
            return render_template("add_user.html")
        
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return render_template("add_user.html")
        
        if role not in ['admin', 'librarian', 'user']:
            flash("Invalid role selected", "error")
            return render_template("add_user.html")
        
        success = lib_system.create_user(username, password, role, full_name, email)
        if success:
            flash(f"User '{username}' created successfully!", "success")
            return redirect(url_for("users"))
        else:
            flash("Username already exists. Please choose a different username.", "error")
    
    return render_template("add_user.html")

@app.route("/profile")
@login_required
def profile():
    """ملف المستخدم الشخصي"""
    return render_template("profile.html",
                         user_id=session.get('user_id'),
                         username=session.get('username'),
                         role=session.get('role'),
                         full_name=session.get('full_name'))

@app.route("/login", methods=["GET", "POST"])
def login():
    """تسجيل الدخول"""
    if 'user_id' in session:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        if not username or not password:
            flash("Please enter both username and password!", "error")
            return render_template("login.html")
        
        user = lib_system.authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            logger.info(f"User {username} logged in successfully")
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            logger.warning(f"Failed login attempt for user: {username}")
            flash("Invalid username or password!", "error")
    
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    """تسجيل الخروج"""
    username = session.get('username')
    session.clear()
    logger.info(f"User {username} logged out")
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

@app.route("/api/health")
def health_check():
    """فحص صحة التطبيق وقاعدة البيانات"""
    try:
        # اختبار الاتصال بقاعدة البيانات
        total_books = lib_system.get_total_books()
        
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "total_books": total_books,
            "timestamp": datetime.now().isoformat(),
            "credentials_source": "KMS" if 'DB_PASSWORD' in CREDENTIALS and CREDENTIALS['DB_PASSWORD'] else "ENV"
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route("/api/stats")
@login_required
def api_stats():
    """API للحصول على الإحصائيات"""
    stats = {
        'total_books': lib_system.get_total_books(),
        'available_books': lib_system.get_available_books_count(),
        'borrowed_books': lib_system.get_borrowed_books_count(),
    }
    return jsonify(stats)

# معالجة الأخطاء
@app.errorhandler(404)
def page_not_found(e):
    """معالجة خطأ 404"""
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """معالجة خطأ 500"""
    logger.error(f"Internal server error: {e}")
    return render_template('500.html'), 500

if __name__ == "__main__":
    # قراءة إعدادات المنفذ من متغير البيئة
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Library Management System on {host}:{port}")
    logger.info(f"Using credentials from: {'KMS' if 'DB_PASSWORD' in CREDENTIALS and CREDENTIALS['DB_PASSWORD'] else 'ENV'}")
    app.run(host=host, port=port, debug=debug)
