import socket
import pymysql
import time

print("=" * 60)
print("🔧 FINAL TEST - Fixed Endpoint")
print("=" * 60)

# الـ endpoint الصحيح
correct_endpoint = "library-project-db.cuuhnwdvvtih.us-east-1.rds.amazonaws.com"
print(f"🔗 Endpoint: {correct_endpoint}")

# اختبار 1: DNS Resolution
print("\n1. Testing DNS resolution...")
try:
    ip_address = socket.gethostbyname(correct_endpoint)
    print(f"✅ DNS Resolved: {correct_endpoint} → {ip_address}")
except socket.gaierror as e:
    print(f"❌ DNS Failed: {e}")
    exit(1)

# اختبار 2: Port 3306
print("\n2. Testing port 3306...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5)
result = sock.connect_ex((ip_address, 3306))
sock.close()

if result == 0:
    print(f"✅ Port 3306 is OPEN on {ip_address}")
else:
    print(f"❌ Port 3306 is CLOSED (Error: {result})")
    print("Check Security Group rules!")
    exit(1)

# اختبار 3: MySQL Connection
print("\n3. Testing MySQL connection...")
try:
    connection = pymysql.connect(
        host=correct_endpoint,
        user='admin',
        password='ahmed1911',
        port=3306,
        connect_timeout=10,
        database='mysql'  # Connect to default db first
    )
    
    print("✅ MySQL Connection SUCCESSFUL!")
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        print(f"📊 MySQL Version: {version}")
        
        cursor.execute("SELECT DATABASE()")
        db = cursor.fetchone()[0]
        print(f"📁 Current Database: {db}")
        
        cursor.execute("SHOW DATABASES")
        dbs = cursor.fetchall()
        print(f"📚 Total Databases: {len(dbs)}")
        
        # ابحث عن library_db
        library_exists = any('library_db' in str(db) for db in dbs)
        if library_exists:
            print("✅ library_db exists")
        else:
            print("⚠️  library_db will be created on first run")
    
    connection.close()
    
    print("\n" + "=" * 60)
    print("🎉 ALL TESTS PASSED!")
    print("\n🚀 Ready to run the application:")
    print("   python3 app.py")
    print("   http://localhost:5000")
    
except pymysql.Error as e:
    print(f"❌ MySQL Connection Failed: {e}")
    print(f"Error code: {e.args[0]}")
    print(f"Error message: {e.args[1]}")
    
    if e.args[0] == 1045:
        print("\n💡 Authentication failed - check username/password")
    elif e.args[0] == 2003:
        print("\n💡 Connection refused - check Security Group")

print("=" * 60)
