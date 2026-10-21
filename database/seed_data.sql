-- ====================================================================
-- STUDENT SKILL AND PROJECT MATCHING SYSTEM
-- Initial Seed Data
-- ====================================================================

USE skillmatch_db;

-- 1. Users (Passwords hashed using werkzeug pbkdf2 / plain demo 'password123')
-- Default passwords for testing: 'password123'
INSERT INTO users (id, name, email, password_hash, role) VALUES
(1, 'Saara Rafi', 'saara@example.com', 'scrypt:32768:8:1$TbxMANlovhpg2mzO$048cf4accf3c5ad539ee79ebb99508d46cce65e2151a8856bbc8a0776ea26f939baa9199cff480f2b8abeb70d77c20254c41c83f2132556bd8fc0077cd6f9a54', 'student'),
(2, 'Aisha Khan', 'aisha@example.com', 'scrypt:32768:8:1$TbxMANlovhpg2mzO$048cf4accf3c5ad539ee79ebb99508d46cce65e2151a8856bbc8a0776ea26f939baa9199cff480f2b8abeb70d77c20254c41c83f2132556bd8fc0077cd6f9a54', 'student'),
(3, 'Rahul Verma', 'rahul@example.com', 'scrypt:32768:8:1$TbxMANlovhpg2mzO$048cf4accf3c5ad539ee79ebb99508d46cce65e2151a8856bbc8a0776ea26f939baa9199cff480f2b8abeb70d77c20254c41c83f2132556bd8fc0077cd6f9a54', 'student'),
(4, 'Meera Patel', 'meera@example.com', 'scrypt:32768:8:1$TbxMANlovhpg2mzO$048cf4accf3c5ad539ee79ebb99508d46cce65e2151a8856bbc8a0776ea26f939baa9199cff480f2b8abeb70d77c20254c41c83f2132556bd8fc0077cd6f9a54', 'student'),
(5, 'Arjun Nair', 'arjun@example.com', 'scrypt:32768:8:1$TbxMANlovhpg2mzO$048cf4accf3c5ad539ee79ebb99508d46cce65e2151a8856bbc8a0776ea26f939baa9199cff480f2b8abeb70d77c20254c41c83f2132556bd8fc0077cd6f9a54', 'student'),
(6, 'Dr. Priya Sharma', 'priya.sharma@faculty.edu', 'scrypt:32768:8:1$TbxMANlovhpg2mzO$048cf4accf3c5ad539ee79ebb99508d46cce65e2151a8856bbc8a0776ea26f939baa9199cff480f2b8abeb70d77c20254c41c83f2132556bd8fc0077cd6f9a54', 'faculty'),
(7, 'Prof. Ramesh Kumar', 'ramesh.kumar@faculty.edu', 'scrypt:32768:8:1$TbxMANlovhpg2mzO$048cf4accf3c5ad539ee79ebb99508d46cce65e2151a8856bbc8a0776ea26f939baa9199cff480f2b8abeb70d77c20254c41c83f2132556bd8fc0077cd6f9a54', 'faculty');

-- 2. Students
INSERT INTO students (id, user_id, department, year, semester, availability, bio, github_url, linkedin_url) VALUES
(1, 1, 'Computer Science Engineering', '3rd Year', '5th Semester', 'Full-time', 'CSE student passionate about intelligent systems, full-stack web architectures, and algorithms. Looking for impactful multidisciplinary projects.', 'https://github.com/saararafi', 'https://linkedin.com/in/saararafi'),
(2, 2, 'Information Science', '3rd Year', '5th Semester', 'Part-time', 'Enthusiastic web and backend developer with expertise in Python and data engineering.', 'https://github.com/aisha-k', 'https://linkedin.com/in/aisha-k'),
(3, 3, 'Computer Science Engineering', '3rd Year', '5th Semester', 'Full-time', 'Backend specialist focusing on Flask, databases, and microservices.', 'https://github.com/rahul-v', 'https://linkedin.com/in/rahul-v'),
(4, 4, 'Computer Science Engineering', '3rd Year', '5th Semester', 'Part-time', 'Frontend & UI/UX specialist who loves modern responsive interfaces and user experience.', 'https://github.com/meera-p', 'https://linkedin.com/in/meera-p'),
(5, 5, 'Electronics & Communication', '3rd Year', '5th Semester', 'Full-time', 'Systems programmer passionate about C++, IoT, and real-time processing.', 'https://github.com/arjun-n', 'https://linkedin.com/in/arjun-n');

-- 3. Skills Master
INSERT INTO skills (id, name, category) VALUES
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
(12, 'Docker', 'DevOps & Deployment');

-- 4. Student Skills (with Certificate status)
INSERT INTO student_skills (student_id, skill_id, proficiency_level, certificate_filename, certificate_original_name, certificate_status, uploaded_at) VALUES
(1, 1, 4, 'cert_saara_python.pdf', 'Python_Specialization_Certificate.pdf', 'Verified', NOW()),
(1, 2, 3, NULL, NULL, 'None', NULL),
(1, 3, 5, 'cert_saara_html.pdf', 'Responsive_Web_Design.pdf', 'Verified', NOW()),
(1, 4, 4, NULL, NULL, 'None', NULL),
(1, 6, 3, 'cert_saara_sql.pdf', 'Database_Management_Coursera.pdf', 'Pending', NOW()),
(1, 7, 4, NULL, NULL, 'None', NULL),

(2, 1, 4, 'cert_aisha_py.pdf', 'Python_Complete_Bootcamp.pdf', 'Verified', NOW()),
(2, 5, 4, NULL, NULL, 'None', NULL),
(2, 3, 5, 'cert_aisha_frontend.pdf', 'Meta_Frontend_Certificate.pdf', 'Verified', NOW()),

(3, 2, 4, 'cert_rahul_java.pdf', 'Oracle_Certified_Associate_Java.pdf', 'Verified', NOW()),
(3, 7, 3, NULL, NULL, 'None', NULL),
(3, 6, 4, 'cert_rahul_mysql.pdf', 'MySQL_Database_Administration.pdf', 'Verified', NOW()),

(4, 5, 5, 'cert_meera_js.pdf', 'Advanced_JavaScript_NPTEL.pdf', 'Verified', NOW()),
(4, 8, 4, 'cert_meera_react.pdf', 'React_Developer_Certification.pdf', 'Verified', NOW()),
(4, 10, 5, 'cert_meera_uiux.pdf', 'Google_UX_Design_Certificate.pdf', 'Verified', NOW()),
(4, 4, 5, NULL, NULL, 'None', NULL),

(5, 11, 5, 'cert_arjun_cpp.pdf', 'CPP_Programming_Certification.pdf', 'Verified', NOW()),
(5, 2, 4, NULL, NULL, 'None', NULL),
(5, 1, 3, NULL, NULL, 'None', NULL);

-- 5. Student Interests
INSERT INTO student_interests (student_id, interest) VALUES
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
(5, 'Embedded Systems');

-- 6. Student Experiences
INSERT INTO student_experiences (student_id, experience_title) VALUES
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
(5, 'Network Security');

-- 7. Projects
INSERT INTO projects (id, faculty_id, title, description, domain, required_availability, team_size, status) VALUES
(1, 6, 'Smart Healthcare Management System', 'An intelligent healthcare portal that facilitates patient appointment management, automated triage scoring using predictive analytics, and electronic medical record management.', 'Healthcare', 'Full-time', 4, 'Open'),
(2, 6, 'Campus Resource & Lab Booking System', 'A centralized web portal for engineering college students and faculty to schedule laboratory sessions, reserve equipment, and manage shared departmental computing resources.', 'Education Technology', 'Part-time', 4, 'Open'),
(3, 7, 'AI-Powered Study & Quiz Assistant', 'A personalized AI tutoring system that generates context-aware quizzes, evaluates student progress, and recommends tailored study notes and references.', 'Artificial Intelligence', 'Full-time', 3, 'Open'),
(4, 7, 'Smart Campus E-Commerce & Book Exchange', 'A peer-to-peer campus marketplace where students can buy, sell, or exchange academic textbooks, stationery, and laboratory kits securely within the college network.', 'Web Development', 'Part-time', 4, 'Open'),
(5, 6, 'Automated Cybersecurity Threat Monitoring', 'A network packet inspection and anomaly detection system for collegiate networks to detect unauthorized intrusion attempts and flag anomalous activity.', 'Cybersecurity', 'Full-time', 3, 'Open');

-- 8. Project Required Skills
INSERT INTO project_skills (project_id, skill_id, required_level) VALUES
-- Smart Healthcare: Python (5), Machine Learning (4), Flask (3), MySQL (4), UI/UX Design (3)
(1, 1, 5),
(1, 9, 4),
(1, 7, 3),
(1, 6, 4),
(1, 10, 3),

-- Campus Resource System: HTML (5), CSS (4), JavaScript (4), Python (4), MySQL (3)
(2, 3, 5),
(2, 4, 4),
(2, 5, 4),
(2, 1, 4),
(2, 6, 3),

-- AI Study Assistant: Python (5), Machine Learning (5), Flask (4)
(3, 1, 5),
(3, 9, 5),
(3, 7, 4),

-- Campus E-Commerce: React (4), JavaScript (5), HTML (5), CSS (4), MySQL (4)
(4, 8, 4),
(4, 5, 5),
(4, 3, 5),
(4, 4, 4),
(4, 6, 4),

-- Cybersecurity Monitor: Python (4), C++ (4), MySQL (3)
(5, 1, 4),
(5, 11, 4),
(5, 6, 3);

-- 9. Project Interests
INSERT INTO project_interests (project_id, interest) VALUES
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
(5, 'Network Security');

-- 10. Project Experiences
INSERT INTO project_experiences (project_id, experience_title) VALUES
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
(5, 'Network Security');

-- 11. Teams
INSERT INTO teams (id, project_id, name, leader_id) VALUES
(1, 1, 'PulseCare Innovation Team', 1);

-- 12. Team Members
INSERT INTO team_members (team_id, student_id, role) VALUES
(1, 1, 'Team Lead & Backend Developer'),
(1, 3, 'Database Engineer');

-- 13. Applications
INSERT INTO applications (project_id, student_id, status, message, match_score) VALUES
(1, 1, 'Accepted', 'Excited to contribute to health informatics and backend architecture.', 88.50),
(2, 1, 'Pending', 'Interested in building the lab booking interface.', 91.25),
(3, 2, 'Pending', 'Passionate about AI-assisted education tools.', 79.00),
(4, 4, 'Accepted', 'Can build the entire front-end user experience in React.', 94.00);

-- 14. Notifications
INSERT INTO notifications (user_id, title, message, type, link) VALUES
(1, 'Certificate Approved', 'Your certificate for Python Specialization was verified successfully.', 'success', 'profile.html'),
(1, 'Application Update', 'Your application for Smart Healthcare Management System was accepted!', 'success', 'applications.html'),
(1, 'New Project Matching You', 'Campus Resource System has a 91% match with your profile.', 'info', 'projects.html');
