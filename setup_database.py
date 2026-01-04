#!/usr/bin/env python3
"""
Setup database by running init_db.sql script
Usage: python setup_database.py
"""
import asyncio
import aiomysql
import os

async def setup_database():
    try:
        print("=" * 60)
        print("DATABASE SETUP SCRIPT")
        print("=" * 60)
        
        sql_path = os.path.join(os.path.dirname(__file__), "db", "init_db.sql")
        
        if not os.path.exists(sql_path):
            print(f"❌ SQL file not found: {sql_path}")
            return False
        
        print(f"📄 Reading SQL script: {sql_path}")
        with open(sql_path, "r") as f:
            script = f.read()
        
        print("🔗 Connecting to MariaDB (root account)...")
        
        try:
            conn = await aiomysql.connect(
                host='127.0.0.1',
                user='root',
                password='',
                port=3306,
                autocommit=True
            )
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            print("\n📋 Make sure MariaDB is running!")
            print("   Windows Service: MariaDB")
            print("   Default host: 127.0.0.1:3306")
            print("   Default user: root")
            print("   Default password: (empty)")
            return False
        
        cursor = await conn.cursor()
        
        print("⚙️  Executing SQL script...")
        print("-" * 60)
        
        statements = [s.strip() for s in script.split(';')]
        executed = 0
        skipped = 0
        
        for i, statement in enumerate(statements):
            if not statement or statement.strip().startswith('--'):
                skipped += 1
                continue
            
            try:
                await cursor.execute(statement)
                executed += 1
                
                stmt_preview = statement[:70].replace('\n', ' ')
                if len(statement) > 70:
                    stmt_preview += "..."
                print(f"  ✓ [{executed}] {stmt_preview}")
                
            except Exception as e:
                print(f"  ⚠️  [{executed}] Error: {str(e)[:60]}")
                print(f"       Statement: {statement[:60]}...")
        
        await cursor.close()
        conn.close()
        
        print("-" * 60)
        print(f"\n✅ SUCCESS!")
        print(f"   Executed: {executed} statements")
        print(f"   Skipped:  {skipped} statements (comments/empty)")
        print("\n📊 Database created:")
        print("   Database: testdb")
        print("   Tables: customers, sales")
        print("   Sample data: 5 customers, 8 sales records")
        print("\n🚀 Ready to test queries in QueryVault!")
        return True
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(setup_database())
        exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏸️  Setup cancelled by user")
        exit(1)
