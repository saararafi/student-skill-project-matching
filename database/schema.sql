-- ====================================================================
-- STUDENT SKILL AND PROJECT MATCHING SYSTEM
-- Database Schema (MySQL 8.0+ compatible)
-- ====================================================================

CREATE DATABASE IF NOT EXISTS skillmatch_db;
USE skillmatch_db;

-- 1. Users Table (Supports Students, Faculty, and Administrators)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'faculty', 'admin') DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Students Profile Table
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    department VARCHAR(100) DEFAULT 'Computer Science Engineering',
    year VARCHAR(50) DEFAULT '3rd Year',
    semester VARCHAR(50) DEFAULT '5th Semester',
    availability VARCHAR(50) DEFAULT 'Full-time',
    bio TEXT,
    github_url VARCHAR(255) DEFAULT '',
    linkedin_url VARCHAR(255) DEFAULT '',
    email_notifications TINYINT DEFAULT 1,
    match_alerts TINYINT DEFAULT 1,
    weekly_digest TINYINT DEFAULT 0,
    profile_visibility VARCHAR(20) DEFAULT 'team',
    prioritise_skills TINYINT DEFAULT 1,
    consider_interests TINYINT DEFAULT 1,
    consider_experience TINYINT DEFAULT 1,
    consider_availability TINYINT DEFAULT 1,
    application_alerts TINYINT DEFAULT 1,
    team_alerts TINYINT DEFAULT 1,
    gap_alerts TINYINT DEFAULT 1,
    weekly_hours INT DEFAULT 20,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. Skills Master Table
CREATE TABLE IF NOT EXISTS skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(100) DEFAULT 'General'
);

-- 4. Student Skills (with Certificate Verification)
CREATE TABLE IF NOT EXISTS student_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level INT NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
    certificate_filename VARCHAR(255) DEFAULT NULL,
    certificate_original_name VARCHAR(255) DEFAULT NULL,
    certificate_status ENUM('None', 'Pending', 'Verified', 'Rejected') DEFAULT 'None',
    uploaded_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    UNIQUE KEY uq_student_skill (student_id, skill_id)
);

-- 5. Student Interests
CREATE TABLE IF NOT EXISTS student_interests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    interest VARCHAR(100) NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 6. Student Previous Experiences
CREATE TABLE IF NOT EXISTS student_experiences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    experience_title VARCHAR(150) NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 7. Projects Table
CREATE TABLE IF NOT EXISTS projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    domain VARCHAR(100) NOT NULL,
    required_availability VARCHAR(50) DEFAULT 'Part-time',
    team_size INT DEFAULT 4,
    status ENUM('Open', 'In Progress', 'Completed') DEFAULT 'Open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 8. Project Required Skills
CREATE TABLE IF NOT EXISTS project_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    skill_id INT NOT NULL,
    required_level INT NOT NULL CHECK (required_level BETWEEN 1 AND 5),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE,
    UNIQUE KEY uq_project_skill (project_id, skill_id)
);

-- 9. Project Required Interests / Domains
CREATE TABLE IF NOT EXISTS project_interests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    interest VARCHAR(100) NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 10. Project Required Experiences
CREATE TABLE IF NOT EXISTS project_experiences (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    experience_title VARCHAR(150) NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- 11. Teams Table
CREATE TABLE IF NOT EXISTS teams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    name VARCHAR(100) NOT NULL,
    leader_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (leader_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 12. Team Members Table
CREATE TABLE IF NOT EXISTS team_members (
    id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    student_id INT NOT NULL,
    role VARCHAR(100) DEFAULT 'Contributor',
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uq_team_student (team_id, student_id)
);

-- 13. Project Applications
CREATE TABLE IF NOT EXISTS applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    student_id INT NOT NULL,
    status ENUM('Pending', 'Accepted', 'Rejected') DEFAULT 'Pending',
    message TEXT,
    match_score DECIMAL(5,2) DEFAULT 0.00,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    UNIQUE KEY uq_project_application (project_id, student_id)
);

-- 14. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    message TEXT NOT NULL,
    type ENUM('info', 'success', 'warning', 'alert') DEFAULT 'info',
    link VARCHAR(255) DEFAULT '',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
