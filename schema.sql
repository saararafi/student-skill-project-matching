/* ============================================================
   STUDENT SKILL AND PROJECT MATCHING SYSTEM
   Database: MySQL
   Final Database SQL File
   ============================================================ */


/* ============================================================
   1. CREATE DATABASE
   ============================================================ */

CREATE DATABASE IF NOT EXISTS student_skill_matching;

USE student_skill_matching;


/* ============================================================
   2. USERS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('STUDENT', 'FACULTY', 'ADMIN') NOT NULL
);


/* ============================================================
   3. STUDENTS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    experience TEXT,
    preferred_domain VARCHAR(100),

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);


/* ============================================================
   4. FACULTY TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS faculty (
    faculty_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    designation VARCHAR(100) NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(user_id)
);


/* ============================================================
   5. SKILLS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS skills (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(100)
);


/* ============================================================
   6. STUDENT_SKILLS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS student_skills (
    student_skill_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency_level INT NOT NULL,

    FOREIGN KEY (student_id)
        REFERENCES students(student_id),

    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
);


/* ============================================================
   7. PROJECTS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    faculty_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    domain VARCHAR(100),
    team_size INT,
    status VARCHAR(30) DEFAULT 'OPEN',

    FOREIGN KEY (faculty_id)
        REFERENCES faculty(faculty_id)
);


/* ============================================================
   8. PROJECT_SKILLS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS project_skills (
    project_skill_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    skill_id INT NOT NULL,
    required_proficiency INT NOT NULL,
    importance_level INT DEFAULT 1,

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id),

    FOREIGN KEY (skill_id)
        REFERENCES skills(skill_id)
);


/* ============================================================
   9. APPLICATIONS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    project_id INT NOT NULL,
    application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) DEFAULT 'PENDING',

    FOREIGN KEY (student_id)
        REFERENCES students(student_id),

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
);


/* ============================================================
   10. TEAMS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS teams (
    team_id INT AUTO_INCREMENT PRIMARY KEY,
    project_id INT NOT NULL,
    team_name VARCHAR(100),
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) DEFAULT 'ACTIVE',

    FOREIGN KEY (project_id)
        REFERENCES projects(project_id)
);


/* ============================================================
   11. TEAM_MEMBERS TABLE
   ============================================================ */

CREATE TABLE IF NOT EXISTS team_members (
    team_member_id INT AUTO_INCREMENT PRIMARY KEY,
    team_id INT NOT NULL,
    student_id INT NOT NULL,
    joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    member_role VARCHAR(50),

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id),

    FOREIGN KEY (student_id)
        REFERENCES students(student_id)
);


/* ============================================================
   END OF SCHEMA — demo data lives in seed.sql
   ============================================================ */
