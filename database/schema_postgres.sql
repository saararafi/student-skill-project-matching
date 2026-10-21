-- ====================================================================
-- STUDENT SKILL AND PROJECT MATCHING SYSTEM
-- PostgreSQL Schema (Render.com compatible)
-- ====================================================================

-- 1. Users Table (Supports Students, Faculty, and Administrators)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Students Profile Table
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    department VARCHAR(100) DEFAULT 'Computer Science Engineering',
    year VARCHAR(50) DEFAULT '3rd Year',
    semester VARCHAR(50) DEFAULT '5th Semester',
    availability VARCHAR(50) DEFAULT 'Full-time',
    bio TEXT,
    github_url VARCHAR(255) DEFAULT '',
    linkedin_url VARCHAR(255) DEFAULT '',
    email_notifications SMALLINT DEFAULT 1,
    match_alerts SMALLINT DEFAULT 1,
    weekly_digest SMALLINT DEFAULT 0,
    profile_visibility VARCHAR(20) DEFAULT 'team',
    prioritise_skills SMALLINT DEFAULT 1,
    consider_interests SMALLINT DEFAULT 1,
    consider_experience SMALLINT DEFAULT 1,
    consider_availability SMALLINT DEFAULT 1,
    application_alerts SMALLINT DEFAULT 1,
    team_alerts SMALLINT DEFAULT 1,
    gap_alerts SMALLINT DEFAULT 1,
    weekly_hours INT DEFAULT 20,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Skills Master Table
CREATE TABLE IF NOT EXISTS skills (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(100) DEFAULT 'General'
);

-- 4. Student Skills (with Certificate Verification)
CREATE TABLE IF NOT EXISTS student_skills (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level INT NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
    certificate_filename VARCHAR(255) DEFAULT NULL,
    certificate_original_name VARCHAR(255) DEFAULT NULL,
    certificate_status VARCHAR(20) DEFAULT 'None',
    uploaded_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    UNIQUE (student_id, skill_id)
);

-- 5. Student Interests
CREATE TABLE IF NOT EXISTS student_interests (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    interest VARCHAR(100) NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 6. Student Previous Experiences
CREATE TABLE IF NOT EXISTS student_experiences (
    id SERIAL PRIMARY KEY,
    student_id INT NOT NULL,
    experience_title VARCHAR(150) NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 7. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    faculty_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    domain VARCHAR(100) NOT NULL,
    required_availability VARCHAR(50) DEFAULT 'Part-time',
    team_size INT DEFAULT 4,
    status VARCHAR(20) DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 8. Project Required Skills
CREATE TABLE IF NOT EXISTS project_skills (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    skill_id INT NOT NULL,
    required_level INT NOT NULL CHECK (required_level BETWEEN 1 AND 5),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    UNIQUE (project_id, skill_id)
);

-- 9. Project Required Interests / Domains
CREATE TABLE IF NOT EXISTS project_interests (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    interest VARCHAR(100) NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 10. Project Required Experiences
CREATE TABLE IF NOT EXISTS project_experiences (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    experience_title VARCHAR(150) NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 11. Teams Table
CREATE TABLE IF NOT EXISTS teams (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    leader_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (leader_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 12. Team Members Table
CREATE TABLE IF NOT EXISTS team_members (
    id SERIAL PRIMARY KEY,
    team_id INT NOT NULL,
    student_id INT NOT NULL,
    role VARCHAR(100) DEFAULT 'Contributor',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE (team_id, student_id)
);

-- 13. Project Applications
CREATE TABLE IF NOT EXISTS applications (
    id SERIAL PRIMARY KEY,
    project_id INT NOT NULL,
    student_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',
    message TEXT,
    match_score DECIMAL(5,2) DEFAULT 0.00,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP DEFAULT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE (project_id, student_id)
);

-- 14. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(20) DEFAULT 'info',
    link VARCHAR(255) DEFAULT '',
    is_read SMALLINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Indexes for the columns the application queries most often
CREATE INDEX IF NOT EXISTS idx_student_skills_student ON student_skills (student_id);
CREATE INDEX IF NOT EXISTS idx_student_interests_student ON student_interests (student_id);
CREATE INDEX IF NOT EXISTS idx_student_experiences_student ON student_experiences (student_id);
CREATE INDEX IF NOT EXISTS idx_project_skills_project ON project_skills (project_id);
CREATE INDEX IF NOT EXISTS idx_applications_student ON applications (student_id);
CREATE INDEX IF NOT EXISTS idx_applications_project ON applications (project_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id);
CREATE INDEX IF NOT EXISTS idx_team_members_team ON team_members (team_id);
CREATE INDEX IF NOT EXISTS idx_teams_project ON teams (project_id);
