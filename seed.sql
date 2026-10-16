/* ============================================================
   STUDENT SKILL AND PROJECT MATCHING SYSTEM — seed data
   ============================================================

   Loads demo data so the system is immediately explorable.
   Safe to run more than once (all inserts are idempotent).

   DEMO ACCOUNTS (password for all: demo123)
     arun@gmail.com     — STUDENT
     rahul@gmail.com    — STUDENT
     priya@gmail.com    — STUDENT
     saanvi@gmail.com   — STUDENT
     meena@college.com  — FACULTY
     kumar@college.com  — FACULTY
   ============================================================ */

USE student_skill_matching;

/* ---------- USERS (passwords are HASHES, never plain text) ---------- */

INSERT INTO users (name, email, password, role)
SELECT 'Arun Kumar', 'arun@gmail.com',
       'scrypt:32768:8:1$ZQyphkxHhvvpM4zv$5b8044d7e53358ce831c520b18fe6c4f713c11ba565a69a8e52a751186e0249aad3f6168a608ba08d584a9f3b52bb270c4f0544f6222570e4167cd67f62825f0',
       'STUDENT'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'arun@gmail.com');

INSERT INTO users (name, email, password, role)
SELECT 'Rahul Sharma', 'rahul@gmail.com',
       'scrypt:32768:8:1$ZQyphkxHhvvpM4zv$5b8044d7e53358ce831c520b18fe6c4f713c11ba565a69a8e52a751186e0249aad3f6168a608ba08d584a9f3b52bb270c4f0544f6222570e4167cd67f62825f0',
       'STUDENT'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'rahul@gmail.com');

INSERT INTO users (name, email, password, role)
SELECT 'Priya Nair', 'priya@gmail.com',
       'scrypt:32768:8:1$ZQyphkxHhvvpM4zv$5b8044d7e53358ce831c520b18fe6c4f713c11ba565a69a8e52a751186e0249aad3f6168a608ba08d584a9f3b52bb270c4f0544f6222570e4167cd67f62825f0',
       'STUDENT'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'priya@gmail.com');

INSERT INTO users (name, email, password, role)
SELECT 'Saanvi Rao', 'saanvi@gmail.com',
       'scrypt:32768:8:1$ZQyphkxHhvvpM4zv$5b8044d7e53358ce831c520b18fe6c4f713c11ba565a69a8e52a751186e0249aad3f6168a608ba08d584a9f3b52bb270c4f0544f6222570e4167cd67f62825f0',
       'STUDENT'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'saanvi@gmail.com');

INSERT INTO users (name, email, password, role)
SELECT 'Dr. Meena Rao', 'meena@college.com',
       'scrypt:32768:8:1$ZQyphkxHhvvpM4zv$5b8044d7e53358ce831c520b18fe6c4f713c11ba565a69a8e52a751186e0249aad3f6168a608ba08d584a9f3b52bb270c4f0544f6222570e4167cd67f62825f0',
       'FACULTY'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'meena@college.com');

INSERT INTO users (name, email, password, role)
SELECT 'Prof. Kumar Verma', 'kumar@college.com',
       'scrypt:32768:8:1$ZQyphkxHhvvpM4zv$5b8044d7e53358ce831c520b18fe6c4f713c11ba565a69a8e52a751186e0249aad3f6168a608ba08d584a9f3b52bb270c4f0544f6222570e4167cd67f62825f0',
       'FACULTY'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'kumar@college.com');

/* ---------- STUDENT PROFILES ---------- */

INSERT INTO students (user_id, department, year, experience, preferred_domain)
SELECT user_id, 'Computer Science', 3, 'Built a static portfolio site',
       'Web Development'
FROM users WHERE email = 'arun@gmail.com'
AND NOT EXISTS (SELECT 1 FROM students st WHERE st.user_id = users.user_id);

INSERT INTO students (user_id, department, year, experience, preferred_domain)
SELECT user_id, 'Information Technology', 3, 'Python scripting for a college tool',
       'Data Science'
FROM users WHERE email = 'rahul@gmail.com'
AND NOT EXISTS (SELECT 1 FROM students st WHERE st.user_id = users.user_id);

INSERT INTO students (user_id, department, year, experience, preferred_domain)
SELECT user_id, 'Computer Science', 3, 'Internship building REST APIs',
       'Web Development'
FROM users WHERE email = 'priya@gmail.com'
AND NOT EXISTS (SELECT 1 FROM students st WHERE st.user_id = users.user_id);

INSERT INTO students (user_id, department, year, experience, preferred_domain)
SELECT user_id, 'Information Technology', 3, 'Coursework in ML basics',
       'Machine Learning'
FROM users WHERE email = 'saanvi@gmail.com'
AND NOT EXISTS (SELECT 1 FROM students st WHERE st.user_id = users.user_id);

/* ---------- FACULTY PROFILES ---------- */

INSERT INTO faculty (user_id, department, designation)
SELECT user_id, 'Computer Science', 'Professor'
FROM users WHERE email = 'meena@college.com'
AND NOT EXISTS (SELECT 1 FROM faculty f WHERE f.user_id = users.user_id);

INSERT INTO faculty (user_id, department, designation)
SELECT user_id, 'Information Technology', 'Associate Professor'
FROM users WHERE email = 'kumar@college.com'
AND NOT EXISTS (SELECT 1 FROM faculty f WHERE f.user_id = users.user_id);

/* ---------- SKILLS CATALOGUE ---------- */

INSERT INTO skills (skill_name, category)
SELECT s.skill_name, s.category FROM (
    SELECT 'Python' AS skill_name, 'Programming' AS category UNION ALL
    SELECT 'Java', 'Programming' UNION ALL
    SELECT 'SQL', 'Database' UNION ALL
    SELECT 'MySQL', 'Database' UNION ALL
    SELECT 'HTML', 'Web Development' UNION ALL
    SELECT 'CSS', 'Web Development' UNION ALL
    SELECT 'JavaScript', 'Web Development' UNION ALL
    SELECT 'Flask', 'Web Development' UNION ALL
    SELECT 'Machine Learning', 'Data Science' UNION ALL
    SELECT 'Data Analysis', 'Data Science'
) s
WHERE NOT EXISTS (
    SELECT 1 FROM skills x WHERE x.skill_name = s.skill_name
);

/* ---------- STUDENT SKILLS (student_id, skill, level 1-5) ---------- */

INSERT INTO student_skills (student_id, skill_id, proficiency_level)
SELECT st.student_id, sk.skill_id, v.level
FROM users u
JOIN students st ON st.user_id = u.user_id
JOIN (
    SELECT 'arun@gmail.com' AS email, 'Python' AS skill_name, 4 AS level UNION ALL
    SELECT 'arun@gmail.com', 'HTML', 5 UNION ALL
    SELECT 'arun@gmail.com', 'CSS', 4 UNION ALL
    SELECT 'arun@gmail.com', 'SQL', 3 UNION ALL
    SELECT 'rahul@gmail.com', 'Python', 4 UNION ALL
    SELECT 'rahul@gmail.com', 'SQL', 3 UNION ALL
    SELECT 'rahul@gmail.com', 'Java', 3 UNION ALL
    SELECT 'priya@gmail.com', 'JavaScript', 5 UNION ALL
    SELECT 'priya@gmail.com', 'HTML', 4 UNION ALL
    SELECT 'priya@gmail.com', 'CSS', 4 UNION ALL
    SELECT 'priya@gmail.com', 'Flask', 3 UNION ALL
    SELECT 'saanvi@gmail.com', 'Python', 3 UNION ALL
    SELECT 'saanvi@gmail.com', 'Machine Learning', 2 UNION ALL
    SELECT 'saanvi@gmail.com', 'Data Analysis', 3
) v ON v.email = u.email
JOIN skills sk ON sk.skill_name = v.skill_name
WHERE NOT EXISTS (
    SELECT 1 FROM student_skills ss
    WHERE ss.student_id = st.student_id AND ss.skill_id = sk.skill_id
);

/* ---------- PROJECTS ---------- */

INSERT INTO projects (faculty_id, title, description, domain, team_size, status)
SELECT f.faculty_id, p.title, p.description, p.domain, p.team_size, 'OPEN'
FROM users u
JOIN faculty f ON f.user_id = u.user_id
JOIN (
    SELECT 'meena@college.com' AS email,
           'Smart Healthcare Platform' AS title,
           'Web platform for managing student health records and campus clinic appointments' AS description,
           'Web Development' AS domain, 4 AS team_size UNION ALL
    SELECT 'meena@college.com', 'Student Performance Prediction',
           'Machine learning system to predict student performance from study habits',
           'Machine Learning', 3 UNION ALL
    SELECT 'kumar@college.com', 'Campus Events Mobile App',
           'Cross-platform app for discovering and registering for campus events',
           'Mobile Development', 4 UNION ALL
    SELECT 'kumar@college.com', 'Library Seat Availability Tracker',
           'IoT + web dashboard showing real-time study seat availability',
           'Web Development', 3
) p ON p.email = u.email
WHERE NOT EXISTS (SELECT 1 FROM projects x WHERE x.title = p.title);

/* ---------- PROJECT SKILL REQUIREMENTS ---------- */

INSERT INTO project_skills (project_id, skill_id, required_proficiency, importance_level)
SELECT pr.project_id, sk.skill_id, v.level, 1
FROM projects pr
JOIN (
    SELECT 'Smart Healthcare Platform' AS title, 'Python' AS skill_name, 4 AS level UNION ALL
    SELECT 'Smart Healthcare Platform', 'HTML', 4 UNION ALL
    SELECT 'Smart Healthcare Platform', 'SQL', 3 UNION ALL
    SELECT 'Student Performance Prediction', 'Python', 4 UNION ALL
    SELECT 'Student Performance Prediction', 'Machine Learning', 3 UNION ALL
    SELECT 'Student Performance Prediction', 'Data Analysis', 3 UNION ALL
    SELECT 'Campus Events Mobile App', 'JavaScript', 4 UNION ALL
    SELECT 'Campus Events Mobile App', 'HTML', 3 UNION ALL
    SELECT 'Campus Events Mobile App', 'CSS', 3 UNION ALL
    SELECT 'Library Seat Availability Tracker', 'Python', 3 UNION ALL
    SELECT 'Library Seat Availability Tracker', 'Flask', 3 UNION ALL
    SELECT 'Library Seat Availability Tracker', 'SQL', 3
) v ON v.title = pr.title
JOIN skills sk ON sk.skill_name = v.skill_name
WHERE NOT EXISTS (
    SELECT 1 FROM project_skills ps
    WHERE ps.project_id = pr.project_id AND ps.skill_id = sk.skill_id
);

/* ---------- ONE DEMO TEAM (for skill-gap and teammate demos) ---------- */

INSERT INTO teams (project_id, team_name, status)
SELECT project_id, 'Smart Healthcare Team', 'ACTIVE'
FROM projects WHERE title = 'Smart Healthcare Platform'
AND NOT EXISTS (
    SELECT 1 FROM teams t
    JOIN projects p ON t.project_id = p.project_id
    WHERE p.title = 'Smart Healthcare Platform'
      AND t.team_name = 'Smart Healthcare Team'
);

INSERT INTO team_members (team_id, student_id, member_role)
SELECT t.team_id, st.student_id, 'Leader'
FROM teams t
JOIN projects p ON t.project_id = p.project_id
JOIN students st ON st.user_id = (SELECT user_id FROM users WHERE email = 'arun@gmail.com')
WHERE p.title = 'Smart Healthcare Platform' AND t.team_name = 'Smart Healthcare Team'
AND NOT EXISTS (
    SELECT 1 FROM team_members tm
    WHERE tm.team_id = t.team_id AND tm.student_id = st.student_id
);

/* ============================================================
   END OF SEED DATA
   ============================================================ */
