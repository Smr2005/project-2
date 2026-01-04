#!/usr/bin/env python3
import sys
import os

try:
    import mariadb
except ImportError:
    try:
        import mysql.connector as mariadb
    except ImportError:
        print("❌ Neither mariadb nor mysql.connector is installed")
        print("Install with: pip install mariadb mysql-connector-python")
        sys.exit(1)

def run_sql_script(script_path):
    """Execute SQL script on MariaDB"""
    
    try:
        print(f"📄 Reading SQL script: {script_path}")
        with open(script_path, 'r') as f:
            sql_content = f.read()
        
        print("🔗 Connecting to MariaDB...")
        
        try:
            conn = mariadb.connect(
                host="127.0.0.1",
                user="root",
                password="",
                database=None,
                autocommit=True
            )
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("Make sure MariaDB is running on 127.0.0.1")
            return False
        
        cursor = conn.cursor()
        
        print("⚙️  Executing SQL script...")
        
        statements = sql_content.split(';')
        executed = 0
        
        for statement in statements:
            statement = statement.strip()
            if not statement or statement.startswith('--'):
                continue
            
            try:
                cursor.execute(statement)
                executed += 1
                print(f"  ✓ Executed: {statement[:60]}...")
            except Exception as e:
                print(f"  ⚠️  Statement error: {e}")
                print(f"     Statement: {statement[:60]}...")
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ Success! Executed {executed} SQL statements")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    script = os.path.join(os.path.dirname(__file__), "db", "init_db.sql")
    
    if not os.path.exists(script):
        print(f"❌ Script not found: {script}")
        sys.exit(1)
    
    if run_sql_script(script):
        sys.exit(0)
    else:
        sys.exit(1)
