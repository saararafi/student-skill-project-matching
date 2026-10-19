import os
import sqlite3
import pymysql
from pymysql.cursors import DictCursor
from backend.config import Config

ENGINE_MYSQL = 'mysql'
ENGINE_SQLITE = 'sqlite'

active_engine = ENGINE_SQLITE
_mysql_conn_params = None

def get_connection():
    global active_engine, _mysql_conn_params
    
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


def adapt_sql(sql, target_engine):
    """Adapts MySQL-style %s placeholders to ? if target is SQLite."""
    if target_engine == ENGINE_SQLITE:
        # Replace %s placeholder with ? placeholder for sqlite3
        return sql.replace('%s', '?')
    return sql


def execute_query(sql, params=None):
    """Executes an INSERT, UPDATE, or DELETE query and returns the last inserted ID."""
    conn, engine = get_connection()
    adapted = adapt_sql(sql, engine)
    cursor = conn.cursor()
    try:
        if params is not None:
            cursor.execute(adapted, params)
        else:
            cursor.execute(adapted)
        
        if engine == ENGINE_SQLITE:
            conn.commit()
            last_id = cursor.lastrowid
        else:
            last_id = cursor.lastrowid
        return last_id
    finally:
        cursor.close()
        conn.close()


def fetch_one(sql, params=None):
    """Fetches a single row as a dictionary."""
    conn, engine = get_connection()
    adapted = adapt_sql(sql, engine)
    cursor = conn.cursor()
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
        return row
    finally:
        cursor.close()
        conn.close()


def fetch_all(sql, params=None):
    """Fetches all rows as a list of dictionaries."""
    conn, engine = get_connection()
    adapted = adapt_sql(sql, engine)
    cursor = conn.cursor()
    try:
        if params is not None:
            cursor.execute(adapted, params)
        else:
            cursor.execute(adapted)
        
        rows = cursor.fetchall()
        if engine == ENGINE_SQLITE:
            return [dict(r) for r in rows]
        return list(rows)
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


def init_db():
    """Initializes the database schema and seeds initial data."""
    global active_engine, _mysql_conn_params
    
    create_sample_certificates()
    
    # 1. Attempt MySQL connection
    mysql_success = False
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

    # 2. If MySQL failed, initialize SQLite
    if not mysql_success:
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
            # Password hashes for 'password123'
            pwd_hash = 'scrypt:32768:8:1$k1n1V7z6dI6u1V1G$7d7301c3bf1e0d37e50ebc72ad69324e9334d7d11f5feea49603e8ff6c8b939fa552ceba4a2ffea635904fc494ae6d2463e2a048a17d4a6ffc2547b311756209'
            
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
