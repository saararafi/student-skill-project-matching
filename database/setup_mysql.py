"""
Helper script to initialize the MySQL database and import schema & seed data.
Run this script whenever you want to set up or reset your MySQL database:
    python database/setup_mysql.py
"""

import os
import sys
import getpass
import pymysql

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
SCHEMA_FILE = os.path.join(BASE_DIR, 'database', 'schema.sql')
SEED_FILE = os.path.join(BASE_DIR, 'database', 'seed_data.sql')

def setup_mysql():
    print("\n" + "=" * 65)
    print("  MySQL Database Setup - Student Skill & Project Matching")
    print("=" * 65)

    host = input("Enter MySQL Host [default: localhost]: ").strip() or "localhost"
    port_str = input("Enter MySQL Port [default: 3306]: ").strip() or "3306"
    port = int(port_str)
    user = input("Enter MySQL User [default: root]: ").strip() or "root"
    password = getpass.getpass("Enter MySQL Password (press Enter if empty): ")
    db_name = input("Enter Database Name [default: skillmatch_db]: ").strip() or "skillmatch_db"

    print("\n[1/3] Connecting to MySQL server...")
    try:
        conn = pymysql.connect(host=host, port=port, user=user, password=password, autocommit=True)
        print("✓ Connected to MySQL server successfully!")
    except Exception as e:
        print(f"✗ Failed to connect: {e}")
        sys.exit(1)

    print(f"\n[2/3] Creating and selecting database '{db_name}'...")
    try:
        with conn.cursor() as cur:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`;")
        conn.select_db(db_name)
        print(f"✓ Database '{db_name}' ready!")
    except Exception as e:
        print(f"✗ Error: {e}")
        conn.close()
        sys.exit(1)

    print("\n[3/3] Importing tables and sample seed records...")
    try:
        with conn.cursor() as cur:
            # Execute schema.sql
            with open(SCHEMA_FILE, 'r', encoding='utf-8') as f:
                statements = f.read().split(';')
                for stmt in statements:
                    cleaned = stmt.strip()
                    if cleaned and not cleaned.upper().startswith("CREATE DATABASE") and not cleaned.upper().startswith("USE"):
                        cur.execute(cleaned)

            # Execute seed_data.sql
            with open(SEED_FILE, 'r', encoding='utf-8') as f:
                statements = f.read().split(';')
                for stmt in statements:
                    cleaned = stmt.strip()
                    if cleaned and not cleaned.upper().startswith("USE"):
                        cur.execute(cleaned)

        print("✓ Schema and seed data successfully imported into MySQL!")
        conn.close()

        # Update or create .env file
        env_path = os.path.join(BASE_DIR, '.env')
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f"MYSQL_HOST={host}\n")
            f.write(f"MYSQL_PORT={port}\n")
            f.write(f"MYSQL_USER={user}\n")
            f.write(f"MYSQL_PASSWORD={password}\n")
            f.write(f"MYSQL_DATABASE={db_name}\n")
        print(f"✓ Created configuration file: {env_path}")
        print("\nAll done! You can now start the application with: python run.py\n")

    except Exception as e:
        print(f"✗ Error importing data: {e}")
        conn.close()
        sys.exit(1)

if __name__ == '__main__':
    setup_mysql()
