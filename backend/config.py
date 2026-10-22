import os
import secrets


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

# Picks up credentials written by database/setup_mysql.py or custom setup
_load_dotenv(os.path.join(BASE_DIR, '.env'))

# Environment detection
ENV = os.environ.get('FLASK_ENV', os.environ.get('ENVIRONMENT', 'development')).strip().lower()
IS_PRODUCTION = ENV in ('production', 'prod')

# Insecure default keys that must never be accepted in production
INSECURE_SECRET_KEYS = {
    'skillmatch-secret-key-2026',
    'skillmatch-academic-secret-key-2026',
    'change-me-to-a-long-random-string',
    'change-me',
    'secret',
    'default'
}


def _get_secret_key():
    key = os.environ.get('SECRET_KEY', '').strip()
    if IS_PRODUCTION:
        if not key or key.lower() in INSECURE_SECRET_KEYS or len(key) < 16:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: "
                "A strong, non-default SECRET_KEY environment variable is required in production (min 16 chars). "
                "Generate one with `python -c \"import secrets; print(secrets.token_hex(32))\"`."
            )
        return key
    # Development / Testing fallback
    return key or 'skillmatch-secret-key-2026'


class Config:
    # The project root, used to find the schema and seed files.
    BASE_DIR = BASE_DIR
    ENV = ENV
    IS_PRODUCTION = IS_PRODUCTION

    SECRET_KEY = _get_secret_key()

    # Explicit Database Engine Selection: 'postgres', 'mysql', 'sqlite', or '' (auto)
    DB_ENGINE = os.environ.get('DB_ENGINE', '').strip().lower()

    # Render.com (and most hosts) provide a PostgreSQL DATABASE_URL.
    DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()

    # MySQL Database Settings
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'skillmatch_db')

    # SQLite Path
    SQLITE_DB_PATH = os.path.join(BASE_DIR, 'database', 'skillmatch.db')

    # Certificate Uploads
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'backend', 'uploads', 'certificates')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max

    # Session cookie
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', '1' if IS_PRODUCTION else '0') == '1'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # one week

    # CSRF Protection
    CSRF_ENABLED = os.environ.get('CSRF_ENABLED', '1') == '1'

    # CORS Allowed Origins (explicit list; never wildcard in credentialed mode)
    CORS_ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.environ.get(
            'CORS_ALLOWED_ORIGINS',
            'http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:3000,http://localhost:3000'
        ).split(',')
        if origin.strip()
    ]

    # Predefined demo data seeding (0 = clean database for real user inputs; 1 = seed demo accounts)
    SEED_DEMO_DATA = os.environ.get('SEED_DEMO_DATA', '0') == '1'

    # Optional AI Chatbot LLM API Keys (defaults to intelligent local botanical NLP engine)
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '').strip()
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '').strip()

    @classmethod
    def validate_production_keys(cls):
        env = os.environ.get('FLASK_ENV', os.environ.get('ENVIRONMENT', 'development')).strip().lower()
        key = os.environ.get('SECRET_KEY', '').strip()
        if env in ('production', 'prod'):
            if not key or key.lower() in INSECURE_SECRET_KEYS or len(key) < 16:
                raise RuntimeError(
                    "CRITICAL SECURITY CONFIGURATION ERROR: "
                    "A strong, non-default SECRET_KEY environment variable is required in production (min 16 chars). "
                    "Generate one with `python -c \"import secrets; print(secrets.token_hex(32))\"`."
                )

