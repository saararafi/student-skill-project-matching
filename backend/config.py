import os


def _load_dotenv(path):
    """
    Loads KEY=VALUE pairs from a .env file into os.environ.

    Uses python-dotenv when it is installed, and falls back to a small
    built-in parser otherwise so the project works without extra packages.
    Existing environment variables always win.
    """
    if not os.path.isfile(path):
        return

    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=False)
        return
    except ImportError:
        pass

    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, value)
    except OSError:
        pass


BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# Picks up credentials written by database/setup_mysql.py
_load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'skillmatch-secret-key-2026')

    # Render.com (and most hosts) provide a PostgreSQL DATABASE_URL.
    # When it is present the app uses PostgreSQL; otherwise it falls back to
    # MySQL and then to a local SQLite file.
    DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

    # MySQL Database Settings
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'skillmatch_db')

    # SQLite Fallback Path
    SQLITE_DB_PATH = os.path.join(BASE_DIR, 'database', 'skillmatch.db')

    # Certificate Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'backend', 'uploads', 'certificates')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max

    # Session cookie
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '0') == '1'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # one week

