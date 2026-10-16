# Student Skill and Project Matching System

A web-based platform that helps students find academic projects matching their
skills, and find teammates with complementary abilities. Built with **Flask +
MySQL**, using a rule-based weighted matching algorithm.

## Quick start

```bash
# 1. Install dependencies (once)
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate          # Mac/Linux
pip install -r requirements.txt

# 2. Configure secrets (once)
copy .env.example .env            # Windows
cp .env.example .env              # Mac/Linux
# then open .env and set your MySQL password + a long random SECRET_KEY

# 3. Create the database and load schema + demo data (once)
#    Run these in MySQL Workbench, or from a terminal:
mysql -u root -p < schema.sql
mysql -u root -p < seed.sql

# 4. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

## Verify the setup

Visit these in your browser:

| URL | What you should see |
|---|---|
| `/` | Landing page (garden theme) |
| `/api/health` | `{"status": "ok", "database": "connected"}` |
| `/api/skills` | JSON list of skills |
| `/api/projects` | JSON list of projects with required skills |

## Demo accounts

All demo accounts use the password `demo123`:

| Email | Role |
|---|---|
| arun@gmail.com | Student |
| rahul@gmail.com | Student |
| priya@gmail.com | Student |
| saanvi@gmail.com | Student |
| meena@college.com | Faculty |
| kumar@college.com | Faculty |

## Run the tests

```bash
pytest tests/ -v
```

## Project structure

```
app.py           Flask routes (pages + JSON API)
config.py        Reads .env, holds DB settings
db.py            MySQL helpers (always parameterized queries)
algorithm/       Matching modules (importable, each runnable standalone)
templates/       HTML pages (Flask renders these)
static/          CSS + JavaScript
schema.sql       Database tables
seed.sql         Demo data (safe to run repeatedly)
tests/           pytest tests for the matching algorithm
```

## How the matching works

Each student's skills (proficiency 1-5) are compared with each project's
required skills:

- **Skill score** — student level ÷ required level, capped at 100%, averaged
  across required skills
- **Final score** — weighted combination: 50% skills, 20% interests,
  20% experience, 10% availability

Each algorithm module can be run standalone to see it work:
`python algorithm/matching.py`
