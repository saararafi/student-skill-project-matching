import os
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
from werkzeug.security import check_password_hash, generate_password_hash
from backend.config import Config

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

ENGINE_MYSQL = 'mysql'
ENGINE_SQLITE = 'sqlite'
ENGINE_POSTGRES = 'postgres'

# Demo accounts seeded for evaluation. All share the same demo password.
DEMO_PASSWORD = 'password123'
DEMO_EMAILS = (
    'saara@example.com',
    'aisha@example.com',
    'rahul@example.com',
    'meera@example.com',
    'arjun@example.com',
    'priya.sharma@faculty.edu',
    'ramesh.kumar@faculty.edu',
)

active_engine = ENGINE_SQLITE
_mysql_conn_params = None

def get_connection():
    global active_engine, _mysql_conn_params

    # PostgreSQL is preferred when a DATABASE_URL is provided (Render).
    if Config.DATABASE_URL and PSYCOPG2_AVAILABLE:
        try:
            conn = psycopg2.connect(Config.DATABASE_URL)
            conn.autocommit = True
            return conn, ENGINE_POSTGRES
        except Exception:
            pass

    # Try MySQL first if configured or available
    if active_engine == ENGINE_MYSQL or _mysql_conn_params is not None:
        try:
            conn = pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DATABASE,
                cursorclass=DictCursor,
                autocommit=True
            )
            return conn, ENGINE_MYSQL
        except Exception:
            pass

    # SQLite fallback
    os.makedirs(os.path.dirname(Config.SQLITE_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(Config.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, ENGINE_SQLITE


def _make_cursor(conn, engine):
    """Returns a cursor that yields dict-like rows on every engine."""
    if engine == ENGINE_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()


def adapt_sql(sql, target_engine):
    """Adapts %s placeholders to ? when the target is SQLite."""
    if target_engine == ENGINE_SQLITE:
        # Replace %s placeholder with ? placeholder for sqlite3
        return sql.replace('%s', '?')
    return sql


def execute_query(sql, params=None):
    """Executes an INSERT, UPDATE, or DELETE query and returns the last inserted ID."""
    conn, engine = get_connection()
    adapted = adapt_sql(sql, engine)
    cursor = _make_cursor(conn, engine)
    try:
        if params is not None:
            cursor.execute(adapted, params)
        else:
            cursor.execute(adapted)

        if engine == ENGINE_SQLITE:
            conn.commit()
            return cursor.lastrowid

        if engine == ENGINE_POSTGRES:
            # psycopg2 has no cursor.lastrowid; lastval() gives the last
            # sequence value generated in this session.
            cursor.execute("SELECT lastval() AS id")
            row = cursor.fetchone()
            return row['id'] if row else None

        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


def fetch_one(sql, params=None):
    """Fetches a single row as a dictionary."""
    conn, engine = get_connection()
    adapted = adapt_sql(sql, engine)
    cursor = _make_cursor(conn, engine)
    try:
        if params is not None:
            cursor.execute(adapted, params)
        else:
            cursor.execute(adapted)

        row = cursor.fetchone()
        if row is None:
            return None
        if engine == ENGINE_SQLITE:
            return dict(row)
        return dict(row)
    finally:
        cursor.close()
        conn.close()


def fetch_all(sql, params=None):
    """Fetches all rows as a list of dictionaries."""
    conn, engine = get_connection()
    adapted = adapt_sql(sql, engine)
    cursor = _make_cursor(conn, engine)
    try:
        if params is not None:
            cursor.execute(adapted, params)
        else:
            cursor.execute(adapted)

        rows = cursor.fetchall()
        if engine == ENGINE_SQLITE:
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]
    finally:
        cursor.close()
        conn.close()


def create_sample_certificates():
    """Generates standard sample PDF certificates if they don't already exist."""
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    sample_files = [
        "cert_saara_python.pdf",
        "cert_saara_html.pdf",
        "cert_saara_sql.pdf",
        "cert_aisha_py.pdf",
        "cert_aisha_frontend.pdf",
        "cert_rahul_java.pdf",
        "cert_rahul_mysql.pdf",
        "cert_meera_js.pdf",
        "cert_meera_react.pdf",
        "cert_meera_uiux.pdf",
        "cert_arjun_cpp.pdf"
    ]
    
    # Valid minimal PDF structure
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000115 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
    )
    
    for filename in sample_files:
        path = os.path.join(Config.UPLOAD_FOLDER, filename)
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(minimal_pdf)


def run_migrations():
    """
    Adds columns that were introduced after a database was first created.

    Keeps existing SQLite/MySQL installations working after the schema gains
    new fields, without requiring the user to recreate their database.
    """
    # (table, column, SQLite definition, MySQL definition, PostgreSQL definition)
    migrations = [
        ('students', 'email_notifications', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'match_alerts', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'weekly_digest', 'INTEGER DEFAULT 0', 'TINYINT DEFAULT 0', 'SMALLINT DEFAULT 0'),
        ('students', 'profile_visibility', "TEXT DEFAULT 'team'", "VARCHAR(20) DEFAULT 'team'", "VARCHAR(20) DEFAULT 'team'"),
        ('students', 'prioritise_skills', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'consider_interests', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'consider_experience', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'consider_availability', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'application_alerts', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'team_alerts', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'gap_alerts', 'INTEGER DEFAULT 1', 'TINYINT DEFAULT 1', 'SMALLINT DEFAULT 1'),
        ('students', 'weekly_hours', 'INTEGER DEFAULT 20', 'INT DEFAULT 20', 'INT DEFAULT 20'),
    ]

    conn, engine = get_connection()
    try:
        cur = conn.cursor()
        for table, column, sqlite_def, mysql_def, pg_def in migrations:
            if engine == ENGINE_SQLITE:
                definition = sqlite_def
            elif engine == ENGINE_POSTGRES:
                definition = pg_def
            else:
                definition = mysql_def

            if engine == ENGINE_SQLITE:
                cur.execute(f"PRAGMA table_info({table})")
                existing = [row[1] for row in cur.fetchall()]
            elif engine == ENGINE_POSTGRES:
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = %s AND column_name = %s",
                    (table, column)
                )
                existing = [row['column_name'] for row in cur.fetchall()]
            else:
                cur.execute(f"SHOW COLUMNS FROM {table} LIKE '{column}'")
                existing = [row[0] for row in cur.fetchall()]

            if column not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
                print(f"[Database] Migrated: added {table}.{column}.")
        if engine == ENGINE_SQLITE:
            conn.commit()
        cur.close()
    except Exception as e:
        print(f"[Database Notice] Migration skipped ({e}).")
    finally:
        conn.close()


def ensure_demo_passwords():
    """
    Repairs the demo account password hashes.

    A hard-coded hash stops validating when Werkzeug changes its hashing
    parameters. When that happens the seeded demo accounts would become
    unusable, so the hash is regenerated for the demo accounts only.
    """
    repaired = 0
    for email in DEMO_EMAILS:
        user = fetch_one(
            "SELECT id, password_hash FROM users WHERE LOWER(email) = %s",
            (email.lower(),)
        )
        if not user:
            continue
        stored = user['password_hash'] or ''
        try:
            if check_password_hash(stored, DEMO_PASSWORD):
                continue
        except Exception:
            pass
        execute_query(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (generate_password_hash(DEMO_PASSWORD), user['id'])
        )
        repaired += 1
    if repaired:
        print(f"[Database] Regenerated {repaired} stale demo password hash(es).")
    return repaired


def _run_sql_script(conn, path, skip_prefixes=()):
    """Runs a .sql file statement by statement."""
    with open(path, 'r', encoding='utf-8') as f:
        for statement in f.read().split(';'):
            stmt = statement.strip()
            if not stmt:
                continue
            if any(stmt.upper().startswith(p) for p in skip_prefixes):
                continue
            conn.cursor().execute(stmt)


def init_db():
    """Initializes the database schema and seeds initial data."""
    global active_engine, _mysql_conn_params

    create_sample_certificates()

    # 1. PostgreSQL (Render) when a DATABASE_URL is present
    postgres_success = False
    if Config.DATABASE_URL and PSYCOPG2_AVAILABLE:
        try:
            conn = psycopg2.connect(Config.DATABASE_URL)
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'users'"
            )
            if not cur.fetchone():
                schema_path = os.path.join(
                    Config.BASE_DIR, 'database', 'schema_postgres.sql')
                seed_path = os.path.join(
                    Config.BASE_DIR, 'database', 'seed_data.sql')
                _run_sql_script(conn, schema_path)
                _run_sql_script(conn, seed_path, skip_prefixes=('USE ',))
            cur.close()
            conn.close()
            active_engine = ENGINE_POSTGRES
            postgres_success = True
            print("[Database] Using PostgreSQL (DATABASE_URL).")
        except Exception as e:
            print(f"[Database Notice] PostgreSQL could not be reached ({e}).")

    # 2. MySQL
    mysql_success = False
    if not postgres_success:
        try:
            conn = pymysql.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                autocommit=True
            )
            with conn.cursor() as cur:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.MYSQL_DATABASE}`;")
            conn.select_db(Config.MYSQL_DATABASE)

            # Check if users table exists
            with conn.cursor() as cur:
                cur.execute("SHOW TABLES LIKE 'users';")
                if not cur.fetchone():
                    # Read schema.sql and seed_data.sql
                    schema_path = os.path.join(Config.BASE_DIR, 'database', 'schema.sql')
                    seed_path = os.path.join(Config.BASE_DIR, 'database', 'seed_data.sql')

                    with open(schema_path, 'r', encoding='utf-8') as f:
                        for statement in f.read().split(';'):
                            stmt = statement.strip()
                            if stmt and not stmt.upper().startswith("CREATE DATABASE") and not stmt.upper().startswith("USE"):
                                cur.execute(stmt)

                    with open(seed_path, 'r', encoding='utf-8') as f:
                        for statement in f.read().split(';'):
                            stmt = statement.strip()
                            if stmt and not stmt.upper().startswith("USE"):
                                cur.execute(stmt)

            conn.close()
            active_engine = ENGINE_MYSQL
            _mysql_conn_params = True
            mysql_success = True
            print(f"[Database] Successfully initialized MySQL engine on database '{Config.MYSQL_DATABASE}'.")
        except Exception as e:
            print(f"[Database Notice] MySQL connection could not be established ({e}). Falling back to SQLite.")

    # 3. If neither PostgreSQL nor MySQL worked, fall back to SQLite
    if not postgres_success and not mysql_success:
        active_engine = ENGINE_SQLITE
        os.makedirs(os.path.dirname(Config.SQLITE_DB_PATH), exist_ok=True)
        conn = sqlite3.connect(Config.SQLITE_DB_PATH)
        cur = conn.cursor()
        
        # Check if tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        if not cur.fetchone():
            # Create SQLite Schema
            cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                department TEXT DEFAULT 'Computer Science Engineering',
                year TEXT DEFAULT '3rd Year',
                semester TEXT DEFAULT '5th Semester',
                availability TEXT DEFAULT 'Full-time',
                bio TEXT,
                github_url TEXT DEFAULT '',
                linkedin_url TEXT DEFAULT '',
                email_notifications INTEGER DEFAULT 1,
                match_alerts INTEGER DEFAULT 1,
                weekly_digest INTEGER DEFAULT 0,
                profile_visibility TEXT DEFAULT 'team',
                prioritise_skills INTEGER DEFAULT 1,
                consider_interests INTEGER DEFAULT 1,
                consider_experience INTEGER DEFAULT 1,
                consider_availability INTEGER DEFAULT 1,
                application_alerts INTEGER DEFAULT 1,
                team_alerts INTEGER DEFAULT 1,
                gap_alerts INTEGER DEFAULT 1,
                weekly_hours INTEGER DEFAULT 20,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT DEFAULT 'General'
            );

            CREATE TABLE IF NOT EXISTS student_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                proficiency_level INTEGER NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
                certificate_filename TEXT DEFAULT NULL,
                certificate_original_name TEXT DEFAULT NULL,
                certificate_status TEXT DEFAULT 'None',
                uploaded_at TIMESTAMP NULL DEFAULT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
                UNIQUE (student_id, skill_id)
            );

            CREATE TABLE IF NOT EXISTS student_interests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                interest TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS student_experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                experience_title TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                faculty_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                domain TEXT NOT NULL,
                required_availability TEXT DEFAULT 'Part-time',
                team_size INTEGER DEFAULT 4,
                status TEXT DEFAULT 'Open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS project_skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                required_level INTEGER NOT NULL CHECK (required_level BETWEEN 1 AND 5),
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
                UNIQUE (project_id, skill_id)
            );

            CREATE TABLE IF NOT EXISTS project_interests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                interest TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS project_experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                experience_title TEXT NOT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                leader_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (leader_id) REFERENCES students(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                role TEXT DEFAULT 'Contributor',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE (team_id, student_id)
            );

            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                status TEXT DEFAULT 'Pending',
                message TEXT,
                match_score REAL DEFAULT 0.00,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP NULL DEFAULT NULL,
                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                UNIQUE (project_id, student_id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                link TEXT DEFAULT '',
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """)

            # Seed SQLite Data
            # Generate the demo password hash at runtime so it always matches
            # the installed Werkzeug version (hard-coded hashes go stale).
            pwd_hash = generate_password_hash(DEMO_PASSWORD)
            
            cur.executemany("INSERT INTO users (id, name, email, password_hash, role) VALUES (?, ?, ?, ?, ?)", [
                (1, 'Saara Rafi', 'saara@example.com', pwd_hash, 'student'),
                (2, 'Aisha Khan', 'aisha@example.com', pwd_hash, 'student'),
                (3, 'Rahul Verma', 'rahul@example.com', pwd_hash, 'student'),
                (4, 'Meera Patel', 'meera@example.com', pwd_hash, 'student'),
                (5, 'Arjun Nair', 'arjun@example.com', pwd_hash, 'student'),
                (6, 'Dr. Priya Sharma', 'priya.sharma@faculty.edu', pwd_hash, 'faculty'),
                (7, 'Prof. Ramesh Kumar', 'ramesh.kumar@faculty.edu', pwd_hash, 'faculty')
            ])

            cur.executemany("INSERT INTO students (id, user_id, department, year, semester, availability, bio, github_url, linkedin_url) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [
                (1, 1, 'Computer Science Engineering', '3rd Year', '5th Semester', 'Full-time', 'CSE student passionate about intelligent systems, full-stack web architectures, and algorithms. Looking for impactful multidisciplinary projects.', 'https://github.com/saararafi', 'https://linkedin.com/in/saararafi'),
                (2, 2, 'Information Science', '3rd Year', '5th Semester', 'Part-time', 'Enthusiastic web and backend developer with expertise in Python and data engineering.', 'https://github.com/aisha-k', 'https://linkedin.com/in/aisha-k'),
                (3, 3, 'Computer Science Engineering', '3rd Year', '5th Semester', 'Full-time', 'Backend specialist focusing on Flask, databases, and microservices.', 'https://github.com/rahul-v', 'https://linkedin.com/in/rahul-v'),
                (4, 4, 'Computer Science Engineering', '3rd Year', '5th Semester', 'Part-time', 'Frontend & UI/UX specialist who loves modern responsive interfaces and user experience.', 'https://github.com/meera-p', 'https://linkedin.com/in/meera-p'),
                (5, 5, 'Electronics & Communication', '3rd Year', '5th Semester', 'Full-time', 'Systems programmer passionate about C++, IoT, and real-time processing.', 'https://github.com/arjun-n', 'https://linkedin.com/in/arjun-n')
            ])

            cur.executemany("INSERT INTO skills (id, name, category) VALUES (?, ?, ?)", [
                (1, 'Python', 'Programming Languages'),
                (2, 'Java', 'Programming Languages'),
                (3, 'HTML', 'Frontend Development'),
                (4, 'CSS', 'Frontend Development'),
                (5, 'JavaScript', 'Frontend Development'),
                (6, 'MySQL', 'Database Systems'),
                (7, 'Flask', 'Backend Frameworks'),
                (8, 'React', 'Frontend Frameworks'),
                (9, 'Machine Learning', 'Artificial Intelligence'),
                (10, 'UI/UX Design', 'Design & Prototyping'),
                (11, 'C++', 'Programming Languages'),
                (12, 'Docker', 'DevOps & Deployment')
            ])

            cur.executemany("INSERT INTO student_skills (student_id, skill_id, proficiency_level, certificate_filename, certificate_original_name, certificate_status, uploaded_at) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))", [
                (1, 1, 4, 'cert_saara_python.pdf', 'Python_Specialization_Certificate.pdf', 'Verified'),
                (1, 2, 3, None, None, 'None'),
                (1, 3, 5, 'cert_saara_html.pdf', 'Responsive_Web_Design.pdf', 'Verified'),
                (1, 4, 4, None, None, 'None'),
                (1, 6, 3, 'cert_saara_sql.pdf', 'Database_Management_Coursera.pdf', 'Pending'),
                (1, 7, 4, None, None, 'None'),

                (2, 1, 4, 'cert_aisha_py.pdf', 'Python_Complete_Bootcamp.pdf', 'Verified'),
                (2, 5, 4, None, None, 'None'),
                (2, 3, 5, 'cert_aisha_frontend.pdf', 'Meta_Frontend_Certificate.pdf', 'Verified'),

                (3, 2, 4, 'cert_rahul_java.pdf', 'Oracle_Certified_Associate_Java.pdf', 'Verified'),
                (3, 7, 3, None, None, 'None'),
                (3, 6, 4, 'cert_rahul_mysql.pdf', 'MySQL_Database_Administration.pdf', 'Verified'),

                (4, 5, 5, 'cert_meera_js.pdf', 'Advanced_JavaScript_NPTEL.pdf', 'Verified'),
                (4, 8, 4, 'cert_meera_react.pdf', 'React_Developer_Certification.pdf', 'Verified'),
                (4, 10, 5, 'cert_meera_uiux.pdf', 'Google_UX_Design_Certificate.pdf', 'Verified'),
                (4, 4, 5, None, None, 'None'),

                (5, 11, 5, 'cert_arjun_cpp.pdf', 'CPP_Programming_Certification.pdf', 'Verified'),
                (5, 2, 4, None, None, 'None'),
                (5, 1, 3, None, None, 'None')
            ])

            cur.executemany("INSERT INTO student_interests (student_id, interest) VALUES (?, ?)", [
                (1, 'Artificial Intelligence'),
                (1, 'Web Development'),
                (1, 'Cybersecurity'),
                (1, 'Data Science'),
                (2, 'Web Development'),
                (2, 'Data Science'),
                (3, 'Database Management'),
                (3, 'Web Development'),
                (4, 'Frontend Development'),
                (4, 'UI/UX Design'),
                (4, 'Web Development'),
                (5, 'Cybersecurity'),
                (5, 'Embedded Systems')
            ])

            cur.executemany("INSERT INTO student_experiences (student_id, experience_title) VALUES (?, ?)", [
                (1, 'Web Development'),
                (1, 'Python Projects'),
                (1, 'Database Projects'),
                (2, 'Web Development'),
                (2, 'API Development'),
                (3, 'Database Projects'),
                (3, 'Backend Systems'),
                (4, 'UI/UX Design'),
                (4, 'React Development'),
                (5, 'C++ Systems'),
                (5, 'Network Security')
            ])

            cur.executemany("INSERT INTO projects (id, faculty_id, title, description, domain, required_availability, team_size, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
                (1, 6, 'Smart Healthcare Management System', 'An intelligent healthcare portal that facilitates patient appointment management, automated triage scoring using predictive analytics, and electronic medical record management.', 'Healthcare', 'Full-time', 4, 'Open'),
                (2, 6, 'Campus Resource & Lab Booking System', 'A centralized web portal for engineering college students and faculty to schedule laboratory sessions, reserve equipment, and manage shared departmental computing resources.', 'Education Technology', 'Part-time', 4, 'Open'),
                (3, 7, 'AI-Powered Study & Quiz Assistant', 'A personalized AI tutoring system that generates context-aware quizzes, evaluates student progress, and recommends tailored study notes and references.', 'Artificial Intelligence', 'Full-time', 3, 'Open'),
                (4, 7, 'Smart Campus E-Commerce & Book Exchange', 'A peer-to-peer campus marketplace where students can buy, sell, or exchange academic textbooks, stationery, and laboratory kits securely within the college network.', 'Web Development', 'Part-time', 4, 'Open'),
                (5, 6, 'Automated Cybersecurity Threat Monitoring', 'A network packet inspection and anomaly detection system for collegiate networks to detect unauthorized intrusion attempts and flag anomalous activity.', 'Cybersecurity', 'Full-time', 3, 'Open')
            ])

            cur.executemany("INSERT INTO project_skills (project_id, skill_id, required_level) VALUES (?, ?, ?)", [
                (1, 1, 5),
                (1, 9, 4),
                (1, 7, 3),
                (1, 6, 4),
                (1, 10, 3),

                (2, 3, 5),
                (2, 4, 4),
                (2, 5, 4),
                (2, 1, 4),
                (2, 6, 3),

                (3, 1, 5),
                (3, 9, 5),
                (3, 7, 4),

                (4, 8, 4),
                (4, 5, 5),
                (4, 3, 5),
                (4, 4, 4),
                (4, 6, 4),

                (5, 1, 4),
                (5, 11, 4),
                (5, 6, 3)
            ])

            cur.executemany("INSERT INTO project_interests (project_id, interest) VALUES (?, ?)", [
                (1, 'Artificial Intelligence'),
                (1, 'Healthcare'),
                (1, 'Web Development'),
                (2, 'Web Development'),
                (2, 'Education Technology'),
                (3, 'Artificial Intelligence'),
                (3, 'Data Science'),
                (4, 'Web Development'),
                (4, 'E-Commerce'),
                (5, 'Cybersecurity'),
                (5, 'Network Security')
            ])

            cur.executemany("INSERT INTO project_experiences (project_id, experience_title) VALUES (?, ?)", [
                (1, 'Python Projects'),
                (1, 'Database Projects'),
                (1, 'Machine Learning'),
                (2, 'Web Development'),
                (2, 'Database Projects'),
                (3, 'Python Projects'),
                (3, 'Machine Learning'),
                (4, 'Web Development'),
                (4, 'React Development'),
                (5, 'C++ Systems'),
                (5, 'Network Security')
            ])

            cur.executemany("INSERT INTO teams (id, project_id, name, leader_id) VALUES (?, ?, ?, ?)", [
                (1, 1, 'PulseCare Innovation Team', 1)
            ])

            cur.executemany("INSERT INTO team_members (team_id, student_id, role) VALUES (?, ?, ?)", [
                (1, 1, 'Team Lead & Backend Developer'),
                (1, 3, 'Database Engineer')
            ])

            cur.executemany("INSERT INTO applications (project_id, student_id, status, message, match_score) VALUES (?, ?, ?, ?, ?)", [
                (1, 1, 'Accepted', 'Excited to contribute to health informatics and backend architecture.', 88.50),
                (2, 1, 'Pending', 'Interested in building the lab booking interface.', 91.25),
                (3, 2, 'Pending', 'Passionate about AI-assisted education tools.', 79.00),
                (4, 4, 'Accepted', 'Can build the entire front-end user experience in React.', 94.00)
            ])

            cur.executemany("INSERT INTO notifications (user_id, title, message, type, link) VALUES (?, ?, ?, ?, ?)", [
                (1, 'Certificate Approved', 'Your certificate for Python Specialization was verified successfully.', 'success', 'profile.html'),
                (1, 'Application Update', 'Your application for Smart Healthcare Management System was accepted!', 'success', 'applications.html'),
                (1, 'New Project Matching You', 'Campus Resource System has a 91% match with your profile.', 'info', 'projects.html')
            ])

            conn.commit()
            print("[Database] Successfully initialized and seeded SQLite database at database/skillmatch.db.")
        conn.close()

    # Make sure the seeded demo accounts can still be logged into.
    ensure_demo_passwords()

    # Bring existing databases up to date with the current schema.
    run_migrations()
