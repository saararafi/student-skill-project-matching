"""
STUDENT SKILL AND PROJECT MATCHING SYSTEM — configuration.

Reads secrets from a .env file (which is NEVER committed to GitHub)
and exposes them as db_config for the rest of the application.

Why this file exists:
  Hardcoding passwords in source code is a security risk, and Git
  remembers everything ever committed. So the real .env stays on your
  machine (listed in .gitignore), and we commit only .env.example
  as a template for your teammates.
"""

import os

from dotenv import load_dotenv  # pip install python-dotenv

# Reads the .env file sitting next to this file and loads its
# values into os.environ
load_dotenv()

db_config = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "student_skill_matching"),
}
