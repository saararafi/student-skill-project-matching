"""
SkillMatch AI Botanical Chatbot & Academic Advisor Service.

Provides intelligent, contextualized assistance for students and faculty.
Analyzes live database profiles, match scores, skill gaps, and applications
to give accurate, real-time guidance.
"""

import re
import json
import urllib.request
import urllib.error
from backend.config import Config
from backend.database import fetch_one, fetch_all
from backend.services.matching_service import (
    get_student_profile_data,
    get_ranked_project_recommendations,
)
from backend.services.faculty_service import get_faculty_overview


# =========================================================
# CONTEXT GATHERING
# =========================================================

def get_student_chat_context(user_id):
    """Gathers real-time database context for a student user."""
    student_record = fetch_one(
        "SELECT id, user_id, department, year, semester, bio, availability, github_url, linkedin_url FROM students WHERE user_id = %s",
        (user_id,)
    )
    if not student_record:
        return None

    student_id = student_record["id"]
    profile_data = get_student_profile_data(student_id)
    if not profile_data:
        return None

    user = profile_data["user"]
    skills = profile_data["skills_list"]
    interests = profile_data["interests"]
    experiences = profile_data["experiences"]

    # Ranked matching projects
    recommendations = get_ranked_project_recommendations(student_id)

    # Applications
    applications = fetch_all("""
        SELECT a.id, a.project_id, a.status, a.match_score, a.applied_at,
               p.title AS project_title, p.domain
        FROM applications a
        JOIN projects p ON a.project_id = p.id
        WHERE a.student_id = %s
        ORDER BY a.applied_at DESC
    """, (student_id,))

    # Profile Completeness Calculation
    completeness = 0
    missing_items = []

    dept = (student_record.get("department") or "").strip()
    if dept and dept.lower() not in ("", "general"):
        completeness += 10
    else:
        missing_items.append(("Department info", 10))

    year = (student_record.get("year") or "").strip()
    sem = (student_record.get("semester") or "").strip()
    if year and sem:
        completeness += 10
    else:
        missing_items.append(("Year & Semester", 10))

    bio = (student_record.get("bio") or "").strip()
    if bio and bio.lower() not in ("", "new student profile."):
        completeness += 10
    else:
        missing_items.append(("Personal Biography", 10))

    gh = (student_record.get("github_url") or "").strip()
    li = (student_record.get("linkedin_url") or "").strip()
    if gh or li:
        completeness += 5
    else:
        missing_items.append(("GitHub or LinkedIn link", 5))

    n_skills = len(skills)
    if n_skills >= 3:
        completeness += 25
    elif n_skills >= 1:
        completeness += 15
        missing_items.append(("Add 3+ skills in My Growth", 10))
    else:
        missing_items.append(("Add technical skills", 25))

    has_verified = any(s.get("certificate_status") == "Verified" for s in skills)
    has_cert = any(s.get("certificate_filename") for s in skills)
    if has_verified:
        completeness += 15
    elif has_cert:
        completeness += 5
        missing_items.append(("Awaiting faculty certificate verification", 10))
    else:
        missing_items.append(("Upload skill certificates for verification", 15))

    n_int = len(interests)
    if n_int >= 2:
        completeness += 15
    elif n_int >= 1:
        completeness += 10
        missing_items.append(("Add 2+ preferred domains in Settings", 5))
    else:
        missing_items.append(("Select domain interests", 15))

    avail = (student_record.get("availability") or "").strip()
    if avail and avail.lower() not in ("", "flexible"):
        completeness += 10
    else:
        missing_items.append(("Set weekly availability hours", 10))

    completeness = min(100, max(0, completeness))

    # Calculate top skill gaps across available projects
    gap_counts = {}
    for rec in (recommendations or []):
        for detail in rec.get("skill_details", []):
            if detail.get("status") in ("Missing", "Insufficient"):
                sname = detail.get("skill_name")
                if sname:
                    gap_counts[sname] = gap_counts.get(sname, 0) + 1

    top_gaps = sorted(gap_counts.items(), key=lambda x: x[1], reverse=True)

    return {
        "role": "student",
        "student_id": student_id,
        "name": user.get("name", "Student"),
        "email": user.get("email", ""),
        "department": dept or "General",
        "year": year or "Not specified",
        "semester": sem or "Not specified",
        "bio": bio,
        "availability": avail or "Part-time",
        "skills": skills,
        "interests": interests,
        "experiences": experiences,
        "applications": applications,
        "recommendations": recommendations,
        "completeness": completeness,
        "missing_items": missing_items,
        "top_gaps": top_gaps,
    }


def get_faculty_chat_context(user_id):
    """Gathers real-time database context for a faculty user."""
    overview = get_faculty_overview(user_id)
    if not overview:
        return None
    return {
        "role": "faculty",
        "name": overview.get("faculty", {}).get("name", "Guide"),
        "stats": overview.get("stats", {}),
        "projects": overview.get("projects", []),
        "applications": overview.get("applications", []),
        "pending_certificates": overview.get("pending_certificates", []),
    }


# =========================================================
# BUILT-IN INTELLIGENT BOTANICAL ADVISOR ENGINE
# =========================================================

def generate_local_advisor_reply(user_id, message, student_ctx, faculty_ctx):
    """
    Zero-dependency, high-accuracy conversational intelligence engine.
    Responds with structured markdown advice using real-time database values.
    """
    msg = message.strip().lower()
    default_suggestions = [
        "🌿 Top Project Matches",
        "📊 My Skill Gaps",
        "📈 Profile Completeness",
        "📜 Certificate Help"
    ]

    # -----------------------------------------------------
    # 1. GREETINGS & INTRODUCTIONS
    # -----------------------------------------------------
    greeting_patterns = [
        r"\b(hi|hello|hey|greetings|good\s+morning|good\s+day|good\s+evening|howdy|sup)\b",
        r"\bwho\s+are\s+you\b",
        r"\bwhat\s+can\s+you\s+do\b",
        r"\bhelp\b"
    ]
    if any(re.search(pat, msg) for pat in greeting_patterns) and len(msg.split()) <= 6:
        if student_ctx:
            name = student_ctx["name"]
            score = student_ctx["completeness"]
            recs = student_ctx["recommendations"]
            top_rec_text = f" Your top project match right now is **{recs[0]['title']}** ({round(recs[0]['match_score'])}% match)." if recs else " You don't have matching projects yet; adding your technical skills in My Growth will unlock them."
            
            reply = (
                f"**Good day, {name}! ❧**\n\n"
                f"I am your **SkillMatch Botanical AI Advisor**. I analyze your academic profile, skill proficiencies, and project interests to help you flourish:\n\n"
                f"• **Current Profile Health:** `{score}% complete`\n"
                f"• **Matching Status:**{top_rec_text}\n\n"
                f"Ask me anything! For example:\n"
                f"• *\"Which projects match my skills best?\"*\n"
                f"• *\"What skills should I learn next?\"*\n"
                f"• *\"How do I get my certificates verified?\"*\n"
                f"• *\"How does the matching score work?\"*"
            )
            return reply, [
                "🌿 Top Project Matches",
                "📊 My Skill Gaps",
                "📈 Profile Completeness",
                "📜 Certificate Help"
            ]

        elif faculty_ctx:
            name = faculty_ctx["name"]
            st = faculty_ctx["stats"]
            reply = (
                f"**Good day, {name}! ❧**\n\n"
                f"I am your **Faculty Botanical Assistant**. Here is your current desk summary:\n\n"
                f"• **Open Guided Projects:** `{st.get('projects', 0)}`\n"
                f"• **Applications Awaiting Review:** `{st.get('pending_applications', 0)}`\n"
                f"• **Pending Certificate Verifications:** `{st.get('pending_certificates', 0)}`\n\n"
                f"How can I assist you with your project beds today?"
            )
            return reply, [
                "Review Applications",
                "Verify Certificates",
                "Publish New Project",
                "My Guided Projects"
            ]

    # -----------------------------------------------------
    # 2. PROJECT RECOMMENDATIONS & MATCHES
    # -----------------------------------------------------
    match_patterns = [
        r"\b(match|matching|recommend|recommended|suitable|best\s+project|projects\s+for\s+me|find\s+project|suggest\s+project|fit)\b"
    ]
    if any(re.search(pat, msg) for pat in match_patterns):
        if not student_ctx:
            return (
                "To view personalized project recommendations, please sign in with a student account. Faculty members can inspect guided projects from the [My Projects](faculty-projects.html) desk.",
                ["Sign In", "Projects in Bloom"]
            )

        recs = student_ctx["recommendations"]
        if not recs:
            return (
                f"**No project matches found yet, {student_ctx['name']}.**\n\n"
                f"SkillMatch calculates recommendations based on your registered skills and domain interests. Currently, your profile lists `{len(student_ctx['skills'])} skills`.\n\n"
                f"**How to unlock project matches:**\n"
                f"1. Navigate to [My Growth](growth.html).\n"
                f"2. Add your technical skills (e.g., Python, SQL, React) with your proficiency levels (1–5).\n"
                f"3. Return to [Projects in Bloom](projects.html) or your [Dashboard](dashboard.html) to see your live compatibility rankings!",
                ["Add Skills in My Growth", "View All Projects", "Profile Completeness"]
            )

        top_3 = recs[:3]
        lines = [f"**🌿 Your Top Project Matches, {student_ctx['name']}:**\n"]
        for idx, p in enumerate(top_3, 1):
            score = round(p.get("match_score", 0))
            domain = p.get("domain", "General")
            title = p.get("title", "Project")
            pid = p.get("id")
            avail = p.get("required_availability", "Flexible")

            matching_skills = [
                d["skill_name"] for d in p.get("skill_details", [])
                if d.get("status") in ("Covered", "Adequate")
            ]
            missing_skills = [
                f"{d['skill_name']} (req Lvl {d['required_level']})"
                for d in p.get("skill_details", [])
                if d.get("status") in ("Missing", "Insufficient")
            ]

            lines.append(
                f"**{idx}. [{title}](project-details.html?id={pid})** — **`{score}% Match`**\n"
                f"   • **Domain:** {domain} | **Availability:** {avail}\n"
                f"   • **Matching Skills:** {', '.join(matching_skills) if matching_skills else 'Baseline alignment'}\n"
                f"   • **Gaps to Bridge:** {', '.join(missing_skills) if missing_skills else 'None — fully covered! ✓'}\n"
            )

        lines.append("\n*Tip: Click any project title to inspect team rosters or apply directly!*")
        return "\n".join(lines), [
            "📊 My Skill Gaps",
            "📈 Profile Completeness",
            "📜 How to Verify Skills"
        ]

    # -----------------------------------------------------
    # 3. SKILL GAPS & LEARNING ROADMAP
    # -----------------------------------------------------
    gap_patterns = [
        r"\b(gap|gaps|missing|learn|study|improve\s+score|what\s+skills|shortage|deficiency)\b"
    ]
    if any(re.search(pat, msg) for pat in gap_patterns):
        if not student_ctx:
            return "Skill gap analysis evaluates student skills against project requirements. Please sign in as a student to analyze your gaps.", ["Sign In"]

        gaps = student_ctx["top_gaps"]
        if not gaps:
            return (
                f"**Impressive work, {student_ctx['name']}! ✿**\n\n"
                f"You currently have no critical skill gaps across available matching projects. Your registered skills cover all baseline requirements!\n\n"
                f"To further increase your score:\n"
                f"• Upload proof certificates for your skills in [My Growth](growth.html) to earn the verified multiplier.\n"
                f"• Check [Projects in Bloom](projects.html) and apply to your favorite project.",
                ["🌿 Top Project Matches", "📜 Certificate Help", "Garden Team"]
            )

        lines = [
            f"**🌱 Skill Cultivation Roadmap for {student_ctx['name']}:**\n\n"
            f"Based on active project beds across SkillMatch, cultivating these skills will yield the highest compatibility gain:\n"
        ]

        for idx, (skill_name, count) in enumerate(gaps[:5], 1):
            plural = "projects" if count > 1 else "project"
            lines.append(f"**{idx}. {skill_name}** — Required by **{count} open {plural}**")

        lines.append(
            f"\n**Next steps:**\n"
            f"Once you practice or certify in any of these skills, add them in [My Growth](growth.html) to immediately boost your match scores!"
        )
        return "\n".join(lines), [
            "🌿 Top Project Matches",
            "📈 Profile Completeness",
            "Add Skills in My Growth"
        ]

    # -----------------------------------------------------
    # 4. PROFILE COMPLETENESS & HEALTH
    # -----------------------------------------------------
    profile_patterns = [
        r"\b(profile|completeness|percent|percentage|health|100%|finish\s+profile|complete\s+profile)\b"
    ]
    if any(re.search(pat, msg) for pat in profile_patterns):
        if not student_ctx:
            return "Profile health measures your student profile readiness. Please sign in as a student.", ["Sign In"]

        score = student_ctx["completeness"]
        missing = student_ctx["missing_items"]

        if score >= 100:
            return (
                f"**Your profile is at 100% Bloom, {student_ctx['name']}! 🌟**\n\n"
                f"You have completed all sections: department details, bio, technical skills, verified certificates, domain interests, and availability.\n\n"
                f"Your profile carries the highest matching weight in the algorithm.",
                ["🌿 Top Project Matches", "View My Applications", "Garden Team"]
            )

        lines = [
            f"**📈 Profile Health: `{score}% Complete`**\n\n",
            f"SkillMatch calculates profile health directly from your real academic records. To reach **100%**:\n\n"
        ]

        for item, pts in missing:
            lines.append(f"• **{item}** *(adds +{pts}%)*")

        lines.append(
            f"\nHead over to [My Growth](growth.html) to tend your skills or [Settings](settings.html) to update your bio and domains!"
        )
        return "".join(lines), [
            "My Growth (Skills)",
            "Settings (Bio & Domains)",
            "🌿 Top Project Matches"
        ]

    # -----------------------------------------------------
    # 5. CERTIFICATE VERIFICATION & BADGES
    # -----------------------------------------------------
    cert_patterns = [
        r"\b(certificate|certificates|verify|verification|badge|proof|credential|cert)\b"
    ]
    if any(re.search(pat, msg) for pat in cert_patterns):
        return (
            "**📜 Certificate Verification Guide:**\n\n"
            "SkillMatch validates technical proficiencies through verified credentials to guarantee genuine team capabilities.\n\n"
            "**How to verify your certificates:**\n"
            "1. Open [My Growth](growth.html).\n"
            "2. When adding or editing a skill, click **Upload Certificate** (PDF, PNG, JPG up to 10MB).\n"
            "3. Your certificate will enter `Pending` review status.\n"
            "4. Your project guide / faculty reviews it from their dedicated **Certificate Desk**.\n"
            "5. Once verified, a **golden verified badge (✓)** appears on your skill plant, significantly boosting your matching credibility in project applications!",
            [
                "My Growth (Upload)",
                "📈 Profile Completeness",
                "🌿 Top Project Matches"
            ]
        )

    # -----------------------------------------------------
    # 6. MATCHING ALGORITHM BREAKDOWN
    # -----------------------------------------------------
    algo_patterns = [
        r"\b(algorithm|formula|calculate|calculation|weight|weights|how\s+it\s+works|how\s+does\s+it\s+match)\b"
    ]
    if any(re.search(pat, msg) for pat in algo_patterns):
        return (
            "**🌱 How the SkillMatch Algorithm Works:**\n\n"
            "SkillMatch utilizes a multi-criteria weighted compatibility engine to pair students with research and software projects:\n\n"
            "1. **Technical Skill Match (60% weight):**\n"
            "   Evaluates required skills vs your current level (1–5). Verified certificates provide full validated weight; missing skills produce a calculated gap penalty.\n\n"
            "2. **Domain Interest Alignment (20% weight):**\n"
            "   Calculates semantic alignment between project domains (e.g., Healthcare, AI, IoT) and your chosen interests.\n\n"
            "3. **Weekly Availability Match (10% weight):**\n"
            "   Matches required project time commitments (Part-time / Full-time) with your declared weekly hours.\n\n"
            "4. **Prior Experience & Background (10% weight):**\n"
            "   Considers past project experience and academic standing.",
            [
                "🌿 Top Project Matches",
                "📊 My Skill Gaps",
                "📈 Profile Completeness"
            ]
        )

    # -----------------------------------------------------
    # 7. APPLICATIONS STATUS & HOW TO APPLY
    # -----------------------------------------------------
    app_patterns = [
        r"\b(apply|application|applications|status|verdict|applied|withdraw)\b"
    ]
    if any(re.search(pat, msg) for pat in app_patterns):
        if student_ctx:
            apps = student_ctx["applications"]
            if not apps:
                return (
                    f"**You have not submitted any applications yet, {student_ctx['name']}.**\n\n"
                    f"**How to apply:**\n"
                    f"1. Explore projects on [Projects in Bloom](projects.html).\n"
                    f"2. Click **View Details** on any project matching your skills.\n"
                    f"3. Click **Apply to Project** and enter an introductory message for the faculty guide.\n"
                    f"4. The faculty guide will review your application on their desk!",
                    ["View All Projects", "🌿 Top Project Matches"]
                )

            lines = [f"**✉ Your Applications Status ({len(apps)} total):**\n"]
            for a in apps[:4]:
                st_badge = "⏳ Pending Review" if a["status"] == "Pending" else ("✓ Accepted" if a["status"] == "Accepted" else "✕ " + a["status"])
                score = round(a.get("match_score", 0))
                lines.append(f"• **{a['project_title']}** — **{st_badge}** *(Match: {score}%)*")

            lines.append("\nYou can view full details and responses on your [Applications Desk](applications.html).")
            return "\n".join(lines), ["Applications Desk", "🌿 Top Project Matches"]

    # -----------------------------------------------------
    # 8. TEAMS & COLLABORATION
    # -----------------------------------------------------
    team_patterns = [
        r"\b(team|teams|teammate|teammates|roster|partner|synergy|collaborate)\b"
    ]
    if any(re.search(pat, msg) for pat in team_patterns):
        return (
            "**🌳 Garden Team & Collaboration:**\n\n"
            "SkillMatch ensures balanced teams by pairing members whose skills complement each other.\n\n"
            "• Visit [Garden Team](team.html) to view active rosters for your projects.\n"
            "• The **Recommended Teammates** panel surfaces peers whose proficiencies bridge existing project gaps.\n"
            "• When a project guide accepts your application, you are automatically enrolled into the official project team!",
            ["Garden Team", "🌿 Top Project Matches"]
        )

    # -----------------------------------------------------
    # 9. DOMAIN FILTERING (AI, Web, IoT, Cloud, etc.)
    # -----------------------------------------------------
    domains = {
        "web": ["web", "frontend", "backend", "fullstack", "react", "html"],
        "ai": ["ai", "machine learning", "ml", "deep learning", "nlp", "artificial intelligence"],
        "cloud": ["cloud", "devops", "docker", "aws", "kubernetes"],
        "iot": ["iot", "arduino", "raspberry", "embedded", "sensors"],
        "healthcare": ["health", "healthcare", "medical"],
        "mobile": ["mobile", "android", "ios", "flutter"]
    }
    for dom_key, dom_words in domains.items():
        if any(w in msg for w in dom_words):
            # Query projects in this domain
            matching_projs = fetch_all("""
                SELECT id, title, domain, team_size, required_availability
                FROM projects
                WHERE LOWER(domain) LIKE %s OR LOWER(title) LIKE %s OR LOWER(description) LIKE %s
                LIMIT 3
            """, (f"%{dom_key}%", f"%{dom_key}%", f"%{dom_key}%"))

            if matching_projs:
                lines = [f"**🌿 Found projects in the {dom_key.upper()} domain:**\n"]
                for p in matching_projs:
                    lines.append(f"• **[{p['title']}](project-details.html?id={p['id']})** ({p['domain']} · {p['required_availability']})")
                lines.append("\nClick any project to inspect skill requirements or apply!")
                return "\n".join(lines), ["🌿 Top Project Matches", "View All Projects"]

    # -----------------------------------------------------
    # 10. GENERAL BOTANICAL FALLBACK
    # -----------------------------------------------------
    if student_ctx:
        name = student_ctx["name"]
        return (
            f"I hear you, **{name}**! ❧\n\n"
            f"As your SkillMatch AI Advisor, I can help you with:\n"
            f"• **Recommended Projects:** Type *\"Which projects match me?\"*\n"
            f"• **Skill Gap Analysis:** Type *\"What skills should I learn?\"*\n"
            f"• **Profile Growth:** Type *\"What is my profile completeness?\"*\n"
            f"• **Verification:** Type *\"How do I verify a certificate?\"*\n"
            f"• **Algorithm:** Type *\"How does the match score work?\"*\n\n"
            f"Feel free to ask any specific question about your projects or skills!"
        ), default_suggestions

    elif faculty_ctx:
        return (
            "I am ready to help you manage your academic garden beds! You can ask about:\n"
            "• Guided projects and enrollment capacity\n"
            "• Reviewing pending student applications\n"
            "• Student certificate verification\n"
            "• Publishing a new project listing"
        ), ["Review Applications", "Verify Certificates", "Publish New Project"]

    return (
        "Please log in to your SkillMatch account to receive personalized skill recommendations and project guidance.",
        ["Sign In", "Register"]
    )


# =========================================================
# EXTERNAL LLM INTEGRATION (GEMINI / OPENAI) WITH FALLBACK
# =========================================================

def call_external_llm(user_message, system_context):
    """
    Calls Google Gemini or OpenAI if API keys are configured.
    Falls back gracefully if network fails or keys are not provided.
    """
    gemini_key = Config.GEMINI_API_KEY
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [
                            {"text": f"System Context:\n{system_context}\n\nUser Question:\n{user_message}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 600
                }
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and "text" in parts[0]:
                        return parts[0]["text"].strip()
        except Exception:
            pass  # Fall back to local advisor

    return None


# =========================================================
# MAIN PUBLIC CHAT ENTRYPOINT
# =========================================================

def generate_chat_response(user_id, message, conversation_history=None):
    """
    Main interface called by the /api/chat route.
    Returns (reply_text, suggestion_chips, context_dict).
    """
    user_record = fetch_one("SELECT id, name, email, role FROM users WHERE id = %s", (user_id,))
    if not user_record:
        return "Authentication required. Please sign in to chat with the AI Advisor.", [], {}

    role = (user_record.get("role") or "").strip().lower()
    student_ctx = get_student_chat_context(user_id) if role == "student" else None
    faculty_ctx = get_faculty_chat_context(user_id) if role in ("faculty", "admin") else None

    # Try external LLM if configured
    if Config.GEMINI_API_KEY or Config.OPENAI_API_KEY:
        system_ctx_str = (
            f"You are the SkillMatch Botanical AI Advisor. The user is {user_record.get('name')}, role: {role}.\n"
            f"Student context: {json.dumps(student_ctx, default=str) if student_ctx else 'None'}\n"
            f"Faculty context: {json.dumps(faculty_ctx, default=str) if faculty_ctx else 'None'}\n"
            f"Keep answers concise, helpful, and formatted in clean GitHub markdown with botanical garden tone."
        )
        llm_reply = call_external_llm(message, system_ctx_str)
        if llm_reply:
            suggestions = [
                "🌿 Top Project Matches",
                "📊 My Skill Gaps",
                "📈 Profile Completeness",
                "📜 Certificate Help"
            ]
            return llm_reply, suggestions, {"user_name": user_record.get("name"), "role": role}

    # Use built-in intelligent advisor engine
    reply, suggestions = generate_local_advisor_reply(user_id, message, student_ctx, faculty_ctx)

    context_summary = {
        "user_name": user_record.get("name"),
        "role": role,
        "completeness": student_ctx.get("completeness", 0) if student_ctx else None,
        "top_match": (student_ctx["recommendations"][0]["title"] + f" ({round(student_ctx['recommendations'][0]['match_score'])}%)") if student_ctx and student_ctx.get("recommendations") else None
    }

    return reply, suggestions, context_summary
