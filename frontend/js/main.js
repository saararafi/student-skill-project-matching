/* =========================================================
   STUDENT SKILL AND PROJECT MATCHING SYSTEM
   Full-Stack Frontend Controller
   ========================================================= */

const API_BASE = window.location.origin.includes('http')
    ? `${window.location.origin}/api`
    : 'http://127.0.0.1:5000/api';

function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : null;
}

function escapeHtml(str) {
    if (str === null || str === undefined) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function safeUrl(url) {
    if (!url) return "#";
    const trimmed = String(url).trim();
    if (/^(https?:\/\/|mailto:|\/)/i.test(trimmed)) {
        return trimmed;
    }
    return "#";
}

async function secureFetch(url, options = {}) {
    const opts = { ...options };
    opts.credentials = opts.credentials || "include";
    const method = (opts.method || "GET").toUpperCase();
    opts.headers = { ...(opts.headers || {}) };
    if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
        const csrf = getCookie("csrf_token");
        if (csrf && !opts.headers["X-CSRF-Token"]) {
            opts.headers["X-CSRF-Token"] = csrf;
        }
    }
    return fetch(url, opts);
}

document.addEventListener("DOMContentLoaded", () => {
    initializeLogin();
    initializeRevealAnimations();
    initializeMobileNavigation();

    // Faculty and admins work from the project guide console; the garden
    // pages are for students, so send them to the right place.
    if (document.body.dataset.page === "faculty") {
        initializeLogout();
        initializeGardenButtons();
        return;
    }

    // Live API Initializers
    initializeLiveProfile();
    setupCertificateModal();
    initializeLiveProjects();
    initializeLiveProjectDetails();
    initializeLiveGaps();
    initializeLiveTeammates();
    initializeLiveApplications();
    initializeLiveNotifications();

    // UI Features
    initializeProfileEditing();
    initializeProjectSearchAndFilters();
    initializeMatchAnimations();
    initializeSkillInteractions();
    initializeApplicationButtons();
    initializeApplicationActions();
    initializeNotifications();
    initializeSettings();
    initializeTeamSearch();
    initializeGardenButtons();
    initializeLogout();
    initializeProfileCompleteness();
});


/* =========================================================
   LOGIN
========================================================= */

function initializeLogin() {
    const loginForm = document.querySelector("#loginForm");
    if (!loginForm) return;

    loginForm.addEventListener("submit", async (event) => {
        event.preventDefault();

        const email = document.querySelector("#email");
        const password = document.querySelector("#password");

        if (!email || !password) return;

        if (!email.value.trim() || !password.value.trim()) {
            showGardenToast("Please fill in all required fields.");
            return;
        }

        try {
            const res = await secureFetch(`${API_BASE}/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    email: email.value.trim(),
                    password: password.value.trim()
                })
            });

            const data = await res.json();
            if (data.success) {
                sessionStorage.setItem("user", JSON.stringify(data.user));
                showGardenToast(`Welcome back, ${data.user.name} 🌿`);
                setTimeout(() => {
                    const isFaculty = data.user && (data.user.role === "faculty" || data.user.role === "admin");
                    window.location.href = isFaculty ? "faculty.html" : "projects.html";
                }, 600);
            } else {
                showGardenToast(data.message || "Invalid credentials.");
            }
        } catch (err) {
            // Offline / fallback mode
            showGardenToast("Welcome to SkillMatch 🌿");
            setTimeout(() => {
                window.location.href = "projects.html";
            }, 600);
        }
    });
}


/* =========================================================
   LIVE PROFILE & SKILL CERTIFICATES
========================================================= */

async function initializeLiveProfile() {
    const skillContainer = document.querySelector("#skillPlantsContainer") || document.querySelector(".skill-plants");
    const nameEl = document.querySelector('[data-profile-display="name"]');
    
    // Only execute if on a page with profile elements
    if (!skillContainer && !nameEl) return;

    try {
        const res = await fetch(`${API_BASE}/student/profile`, {
            credentials: "include"
        });
        if (res.status === 401) {
            window.location.href = "login.html";
            return;
        }
        if (!res.ok) return;
        const json = await res.json();
        if (!json.success || !json.profile) return;

        const p = json.profile;

        // Populate text fields
        const setVal = (sel, val) => {
            document.querySelectorAll(sel).forEach(el => {
                if (val !== undefined && val !== null) el.textContent = val;
            });
        };
        setVal('[data-profile-display="name"]', p.name);
        setVal('[data-profile-display="department"]', p.department);
        setVal('[data-profile-display="year"]', p.year);
        setVal('[data-profile-display="semester"]', p.semester);
        setVal('[data-profile-display="bio"]', p.bio);
        setVal('[data-profile-display="availability"]', p.availability);
        setVal('[data-profile-display="email"]', p.email);
        setVal('[data-profile-display="github"]', p.github_url || "Not provided");
        setVal('[data-profile-display="linkedin"]', p.linkedin_url || "Not provided");

        // Update avatar initials
        const avatar = document.querySelector("[data-profile-avatar]") || document.querySelector(".profile-avatar");
        if (avatar && p.name) {
            const initials = p.name.split(" ").filter(Boolean).map(n => n[0]).join("").slice(0, 2).toUpperCase();
            avatar.textContent = initials || "S";
        }

        // Prepopulate edit form fields if present
        const setInput = (id, val) => {
            const el = document.getElementById(id);
            if (el && val) el.value = val;
        };
        setInput("profileName", p.name);
        setInput("profileDepartment", p.department);
        setInput("profileYear", p.year);
        setInput("profileSemester", p.semester);
        setInput("profileBio", p.bio);
        setInput("profileGithub", p.github_url);
        setInput("profileLinkedin", p.linkedin_url);

        // Update completeness
        const compBar = document.querySelector("[data-profile-completeness]");
        const compText = document.querySelector("[data-profile-completeness-text]");
        if (compBar) compBar.style.width = `${p.completeness}%`;
        if (compText) compText.textContent = `${p.completeness}%`;

        // Render skill plants with live certificates
        if (skillContainer && p.skills && p.skills.length > 0) {
            skillContainer.innerHTML = "";
            const flowers = ["✿", "❀", "✾", "❁", "✽"];

            p.skills.forEach((sk, idx) => {
                const flower = flowers[idx % flowers.length];
                const pct = Math.round((sk.proficiency_level / 5) * 100);

                let certBadge = "";
                if (sk.certificate_status === "Verified") {
                    certBadge = `
                        <a href="${API_BASE}/certificates/${encodeURIComponent(sk.certificate_filename || '')}" target="_blank" class="skill-cert-badge verified" title="Verified certificate: ${escapeHtml(sk.certificate_original_name || 'Proof')}">
                            Verified ✓
                        </a>
                    `;
                } else if (sk.certificate_status === "Pending") {
                    certBadge = `
                        <a href="${API_BASE}/certificates/${encodeURIComponent(sk.certificate_filename || '')}" target="_blank" class="skill-cert-badge pending" title="Verification pending">
                            Pending ⏳
                        </a>
                    `;
                } else {
                    certBadge = `
                        <button type="button" class="skill-cert-badge upload" data-skill-id="${sk.skill_id}" data-skill-name="${escapeHtml(sk.name)}" title="Upload verification certificate">
                            + Certificate
                        </button>
                    `;
                }

                const plant = document.createElement("div");
                plant.className = "skill-plant";
                plant.innerHTML = `
                    <div class="skill-plant-flower">${flower}</div>
                    <div class="skill-plant-name">${escapeHtml(sk.name)}</div>
                    <div class="skill-plant-level">${sk.proficiency_level} / 5 · ${pct}%</div>
                    ${certBadge}
                `;
                const uploadBtn = plant.querySelector("button.skill-cert-badge.upload");
                if (uploadBtn) {
                    uploadBtn.addEventListener("click", () => openCertModal(sk.skill_id, sk.name));
                }
                skillContainer.appendChild(plant);
            });
        }
    } catch (err) {
        console.log("[Notice] Using local profile data.");
    }
}


/* =========================================================
   CERTIFICATE UPLOAD MODAL
========================================================= */

window.openCertModal = function(skillId, skillName) {
    const modal = document.querySelector("#certModalOverlay");
    const skillTitle = document.querySelector("#certModalSkillTitle");
    const skillIdInput = document.querySelector("#certSkillId");
    const skillNameInput = document.querySelector("#certSkillName");
    const fileInput = document.querySelector("#certFileInput");
    const chosenText = document.querySelector("#certChosenText");

    if (!modal) return;
    if (skillTitle) skillTitle.textContent = skillName;
    if (skillIdInput) skillIdInput.value = skillId;
    if (skillNameInput) skillNameInput.value = skillName;
    if (fileInput) fileInput.value = "";
    if (chosenText) {
        chosenText.textContent = "No file selected yet";
        chosenText.style.color = "#777";
    }

    modal.classList.add("active");
};

function setupCertificateModal() {
    const modal = document.querySelector("#certModalOverlay");
    const closeBtn = document.querySelector("#closeCertModal");
    const cancelBtn = document.querySelector("#cancelCertBtn");
    const form = document.querySelector("#certUploadForm");
    const fileInput = document.querySelector("#certFileInput");
    const chosenText = document.querySelector("#certChosenText");

    if (!modal) return;

    const closeModal = () => modal.classList.remove("active");
    if (closeBtn) closeBtn.addEventListener("click", closeModal);
    if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

    modal.addEventListener("click", (e) => {
        if (e.target === modal) closeModal();
    });

    if (fileInput && chosenText) {
        fileInput.addEventListener("change", () => {
            if (fileInput.files.length > 0) {
                const f = fileInput.files[0];
                chosenText.textContent = `Selected: ${f.name} (${Math.round(f.size / 1024)} KB)`;
                chosenText.style.color = "#2e7d32";
            } else {
                chosenText.textContent = "No file selected yet";
                chosenText.style.color = "#777";
            }
        });
    }

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const submitBtn = document.querySelector("#submitCertBtn");

            if (!fileInput || fileInput.files.length === 0) {
                showGardenToast("Please select a certificate file.");
                return;
            }

            const formData = new FormData(form);
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.textContent = "Uploading... ⏳";
            }

            try {
                const res = await secureFetch(`${API_BASE}/student/upload-certificate`, {
                    method: "POST",
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    showGardenToast("Certificate uploaded! Verification pending 📜");
                    closeModal();
                    initializeLiveProfile();
                } else {
                    showGardenToast(data.message || "Failed to upload.");
                }
            } catch (err) {
                showGardenToast("Upload failed. Please check file format.");
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.textContent = "🌿 Upload & Request Verification";
                }
            }
        });
    }
}


/* =========================================================
   LIVE PROJECTS
========================================================= */

async function initializeLiveProjects() {
    const projectGrid = document.querySelector(".project-match-grid");
    if (!projectGrid) return;

    const renderEmptyProjects = () => {
        const badge = document.querySelector("#projectCountBadge") || document.querySelector(".garden-section-title .botanical-badge");
        if (badge) {
            badge.textContent = "00 Matches";
        }
        projectGrid.innerHTML = `
            <div class="garden-card empty-state" id="projectEmptyBed" style="grid-column: 1 / -1; padding: 48px 25px; text-align: center; border-radius: 16px;">
                <div style="font-size: 38px; margin-bottom: 12px;">🌱</div>
                <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 26px; color: var(--olive-deep); font-weight: 600;">Nothing has bloomed here yet.</h3>
                <p style="color: var(--muted); margin: 8px auto 20px; font-size: 14px; max-width: 520px; line-height: 1.6;">
                    No projects have been published by faculty yet. As soon as a faculty member adds a project from the Faculty Console, it will appear here with live compatibility matching.
                </p>
                <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                    <a href="growth.html" class="garden-button">Tend Your Skills (My Growth) →</a>
                </div>
            </div>
        `;
    };

    try {
        const res = await fetch(`${API_BASE}/projects`, { credentials: "include" });
        if (!res.ok) {
            renderEmptyProjects();
            return;
        }
        const data = await res.json();
        if (!data.success) {
            renderEmptyProjects();
            return;
        }

        const count = (data.projects || []).length;
        const badge = document.querySelector("#projectCountBadge") || document.querySelector(".garden-section-title .botanical-badge");
        if (badge) {
            badge.textContent = `${count < 10 ? '0' + count : count} ${count === 1 ? 'Match' : 'Matches'}`;
        }

        if (!data.projects || data.projects.length === 0) {
            renderEmptyProjects();
            return;
        }

        projectGrid.innerHTML = "";

        data.projects.forEach((proj) => {
            const article = document.createElement("article");
            article.className = "project-match-card garden-card";
            article.dataset.searchItem = "";
            article.dataset.domain = proj.domain.toLowerCase();
            article.dataset.team = proj.team_size;
            article.dataset.availability = proj.required_availability.toLowerCase();

            const isApplied = proj.user_application !== null;
            const appStatus = isApplied ? proj.user_application.status : "";

            const skillsTags = (proj.skill_details || []).map(s => `
                <span title="Req Level: ${s.required_level}/5 | Your Level: ${s.student_level}/5">
                    ${escapeHtml(s.skill)}
                </span>
            `).join("");

            article.innerHTML = `
                <div class="project-card-top">
                    <div class="project-flower">✿</div>
                    <span class="project-status">${escapeHtml(proj.status)}</span>
                </div>

                <h2>${escapeHtml(proj.title)}</h2>

                <p class="project-description">
                    ${escapeHtml(proj.description)}
                </p>

                <div class="project-meta">
                    <span>🌿 ${escapeHtml(proj.domain)}</span>
                    <span>👥 ${proj.team_size} members</span>
                    <span>◷ ${escapeHtml(proj.required_availability)}</span>
                </div>

                <div class="skill-list">
                    ${skillsTags}
                </div>

                <div class="project-match-score">
                    <div>
                        <small>YOUR COMPATIBILITY</small>
                        <strong data-score="${Math.round(proj.match_score)}">
                            ${proj.match_score}%
                        </strong>
                    </div>

                    <div class="match-score-circle small">
                        <span>${Math.round(proj.match_score)}%</span>
                    </div>
                </div>

                <div class="match-components">
                    <div class="match-component">
                        <div><span>Skills (50%)</span><strong>${proj.skill_score}%</strong></div>
                        <div class="match-component-track">
                            <div class="match-component-fill" style="width: ${proj.skill_score}%;"></div>
                        </div>
                    </div>

                    <div class="match-component">
                        <div><span>Interests (20%)</span><strong>${proj.interest_score}%</strong></div>
                        <div class="match-component-track">
                            <div class="match-component-fill" style="width: ${proj.interest_score}%;"></div>
                        </div>
                    </div>

                    <div class="match-component">
                        <div><span>Experience (20%)</span><strong>${proj.experience_score}%</strong></div>
                        <div class="match-component-track">
                            <div class="match-component-fill" style="width: ${proj.experience_score}%;"></div>
                        </div>
                    </div>

                    <div class="match-component">
                        <div><span>Availability (10%)</span><strong>${proj.availability_score}%</strong></div>
                        <div class="match-component-track">
                            <div class="match-component-fill" style="width: ${proj.availability_score}%;"></div>
                        </div>
                    </div>
                </div>

                <div class="project-card-actions">
                    <a href="project-details.html?id=${proj.id}" class="garden-button garden-button-secondary">
                        View Details
                    </a>

                    <button class="garden-button ${isApplied ? 'applied' : ''}" type="button" 
                            ${isApplied ? 'disabled' : ''} onclick="applyToProjectLive(${proj.id}, this)">
                        ${isApplied ? (appStatus === 'Accepted' ? 'Accepted ✓' : 'Applied ✓') : 'Apply ✿'}
                    </button>
                </div>
            `;
            projectGrid.appendChild(article);
        });

        initializeMatchAnimations();
    } catch (e) {
        console.log("[Notice] Live projects sync skipped or in offline mode.");
    }
}

window.applyToProjectLive = async function(projectId, buttonElement) {
    if (buttonElement && buttonElement.disabled) return;
    if (buttonElement) {
        buttonElement.disabled = true;
        buttonElement.textContent = "Applying... ⏳";
    }

    try {
        const res = await secureFetch(`${API_BASE}/projects/${projectId}/apply`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: "Excited to collaborate on this academic project!" })
        });
        const data = await res.json();
        if (data.success) {
            showGardenToast(`Application submitted! Match score: ${data.match_score}% 🌿`);
            if (buttonElement) {
                buttonElement.textContent = "Applied ✓";
                buttonElement.classList.add("applied");
            }
        } else {
            showGardenToast(data.message || "Could not apply.");
            if (buttonElement) {
                buttonElement.disabled = false;
                buttonElement.textContent = "Apply ✿";
            }
        }
    } catch (err) {
        showGardenToast("Unable to submit application. Please check your connection.");
        if (buttonElement) {
            buttonElement.textContent = "Applied ✓";
        }
    }
};

async function initializeLiveProjectDetails() {
    const heroTitle = document.querySelector(".project-detail-heading h2");
    if (!heroTitle) return;

    const urlParams = new URLSearchParams(window.location.search);
    const projectId = urlParams.get('id');

    if (!projectId) {
        heroTitle.textContent = "No Project Selected";
        const heroDesc = document.querySelector(".project-detail-heading p");
        if (heroDesc) heroDesc.textContent = "Please select a project from Projects in Bloom to view its details.";
        const applyBtn = document.querySelector(".project-detail-actions button, button[data-apply]");
        if (applyBtn) applyBtn.style.display = "none";
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/projects/${projectId}`, { credentials: "include" });
        if (!res.ok) {
            heroTitle.textContent = "Project Not Found";
            const heroDesc = document.querySelector(".project-detail-heading p");
            if (heroDesc) heroDesc.textContent = "The requested project could not be found or has not bloomed yet.";
            const applyBtn = document.querySelector(".project-detail-actions button, button[data-apply]");
            if (applyBtn) applyBtn.style.display = "none";
            return;
        }
        const json = await res.json();
        if (!json.success || !json.project) return;
        const p = json.project;

        heroTitle.textContent = p.title;
        const heroDesc = document.querySelector(".project-detail-heading p");
        if (heroDesc) heroDesc.textContent = p.description;

        const matchCircle = document.querySelector(".project-detail-match .match-score-circle span");
        if (matchCircle && p.match) {
            matchCircle.textContent = `${Math.round(p.match.final_score)}%`;
        }

        const applyBtn = document.querySelector(".project-detail-actions button, button[data-apply]");
        if (applyBtn) {
            const isApplied = p.application !== null;
            if (isApplied) {
                applyBtn.disabled = true;
                applyBtn.textContent = p.application.status === 'Accepted' ? 'Accepted ✓' : 'Applied ✓';
                applyBtn.classList.add('applied');
            } else {
                applyBtn.onclick = () => applyToProjectLive(p.id, applyBtn);
            }
        }
    } catch (e) {
        console.log("[Notice] Live project details sync skipped.");
    }
}

/* =========================================================
   LIVE SKILL GAPS — FIXED FOR gaps.html
   Keeps the existing page visible if the API is unavailable.
========================================================= */

async function initializeLiveGaps() {
    // gaps.html is managed dynamically with project picker and full summary in live.js (renderGaps)
    if (typeof renderGaps === "function") return;

    // Match the actual container used in gaps.html.
    const gapList = document.querySelector(
        ".gap-list, .gap-item-list, .skill-gap-list"
    );

    // This function should only run on the skill-gap page.
    if (!gapList) return;

    try {
        const response = await fetch(
            `${API_BASE}/matching/projects/1/gaps`
        );

        if (!response.ok) {
            console.warn(
                "Skill gaps API unavailable:",
                response.status
            );
            return; // Keep the existing HTML cards visible.
        }

        const json = await response.json();

        if (!json.success || !json.data) {
            console.warn("Skill gaps response has no data.");
            return; // Keep the existing HTML cards visible.
        }

        const breakdown = json.data.skill_breakdown;

        if (!Array.isArray(breakdown)) {
            console.warn("No skill breakdown was returned.");
            return;
        }

        if (breakdown.length === 0) {
            gapList.innerHTML = `
                <div class="garden-card" style="padding:24px;">
                    <h4>Your skills are growing well 🌱</h4>
                    <p>
                        No skill gaps were returned for this project.
                        Check other project requirements to find
                        new areas for growth.
                    </p>
                </div>
            `;
            return;
        }

        // Build the updated list safely.
        gapList.replaceChildren();

        breakdown.forEach((item) => {
            const skillName = item.skill || "Unnamed skill";
            const required = Math.max(
                1,
                Math.min(5, Number(item.required_level) || 1)
            );
            const available = Math.max(
                0,
                Math.min(5, Number(item.available_level) || 0)
            );

            const percentage = Math.round(
                (available / required) * 100
            );

            let statusClass = "covered";
            let statusText = "Covered ✓";

            if (
                item.status === "Missing" ||
                available === 0
            ) {
                statusClass = "missing";
                statusText = "Needs attention 💧";
            } else if (
                item.status === "Insufficient" ||
                available < required
            ) {
                statusClass = "insufficient";
                statusText = "Still growing 🌱";
            }

            const card = document.createElement("article");
            card.className = "gap-item garden-card";

            const heading = document.createElement("div");
            heading.className = "gap-item-heading";
            heading.style.display = "flex";
            heading.style.justifyContent = "space-between";
            heading.style.alignItems = "center";
            heading.style.gap = "12px";
            heading.style.marginBottom = "8px";

            const name = document.createElement("strong");
            name.textContent = skillName;

            const badge = document.createElement("span");
            badge.className = `botanical-badge ${statusClass}`;
            badge.textContent = statusText;

            heading.append(name, badge);

            const levels = document.createElement("p");
            levels.textContent =
                `Your level: ${available}/5 · Required: ${required}/5`;
            levels.style.margin = "0 0 10px";

            const track = document.createElement("div");
            track.className = "gap-progress-track";
            track.setAttribute(
                "aria-label",
                `${skillName}: ${percentage}% of required proficiency`
            );

            const fill = document.createElement("div");
            fill.className = "gap-progress-fill";
            fill.style.width = `${Math.min(percentage, 100)}%`;

            track.appendChild(fill);
            card.append(heading, levels, track);
            gapList.appendChild(card);
        });

    } catch (error) {
        // Do not erase the HTML fallback if the server is offline.
        console.error("Could not load live skill gaps:", error);
    }
}

/* =========================================================
   LIVE TEAMMATE RECOMMENDATIONS
========================================================= */

async function initializeLiveTeammates() {
    const teamGrid = document.querySelector(".teammate-grid");
    if (!teamGrid) return;

    try {
        const res = await fetch(`${API_BASE}/matching/projects/1/teammates`);
        if (!res.ok) return;
        const json = await res.json();
        if (!json.success || !json.teammates || json.teammates.length === 0) return;

        teamGrid.innerHTML = "";

        json.teammates.forEach(stu => {
            const card = document.createElement("article");
            card.className = "team-member garden-card";

            const skillPills = stu.matching_skills_detailed.map(s => {
                const certIcon = s.has_certificate ? "📜 " : "";
                return `<span class="botanical-badge" style="margin: 3px; font-size: 0.72rem;">${certIcon}${escapeHtml(s.name)} (Lvl ${s.level})</span>`;
            }).join("");

            card.innerHTML = `
                <div class="member-avatar" style="font-size: 2rem; margin-bottom: 8px;">🌱</div>
                <h3 style="margin: 4px 0;">${escapeHtml(stu.name)}</h3>
                <small style="color: #666; display: block; margin-bottom: 8px;">${escapeHtml(stu.department)} · ${escapeHtml(stu.year)}</small>
                
                <p style="font-size: 0.85rem; color: #444; margin-bottom: 12px;">
                    ${escapeHtml(stu.bio || "Active academic collaborator with verified technical competencies.")}
                </p>

                <div style="margin: 10px 0;">
                    <strong style="font-size: 0.8rem; display: block; margin-bottom: 5px; color: #26351b;">Matches Missing Gaps:</strong>
                    ${skillPills}
                </div>

                <div style="margin-top: 14px;">
                    <button type="button" class="garden-button secondary invite-btn">
                        Invite to Team
                    </button>
                </div>
            `;
            const inviteBtn = card.querySelector(".invite-btn");
            if (inviteBtn) {
                inviteBtn.addEventListener("click", () => {
                    showGardenToast(`Invitation sent to ${stu.name} 🌿`);
                });
            }
            teamGrid.appendChild(card);
        });
    } catch (e) {
        console.log("[Notice] Live teammates sync skipped.");
    }
}


/* =========================================================
   LIVE APPLICATIONS
========================================================= */

async function initializeLiveApplications() {
    const appContainer = document.querySelector(".applications-grid") || document.querySelector("#applicationsList");
    if (!appContainer) return;

    try {
        const res = await fetch(`${API_BASE}/applications`);
        if (!res.ok) return;
        const json = await res.json();
        if (!json.success || !json.applications || json.applications.length === 0) return;

        appContainer.innerHTML = "";

        json.applications.forEach(app => {
            const card = document.createElement("article");
            card.className = "application-card garden-card";

            let statusClass = "status-pending";
            if (app.status === "Accepted") statusClass = "status-accepted";
            if (app.status === "Rejected") statusClass = "status-rejected";

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                    <div>
                        <h3 style="margin: 0; font-family: 'Cormorant Garamond', serif; font-size: 1.3rem;">
                            ${escapeHtml(app.project_title)}
                        </h3>
                        <small style="color: #666;">🌿 ${escapeHtml(app.domain)}</small>
                    </div>
                    <span class="botanical-badge ${statusClass}" style="padding: 4px 10px; border-radius: 12px;">
                        ${escapeHtml(app.status)}
                    </span>
                </div>

                <p style="font-size: 0.88rem; color: #444; margin: 10px 0;">
                    ${escapeHtml(app.message || "Application submitted for academic project matching.")}
                </p>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; font-size: 0.82rem; color: #666;">
                    <span>Compatibility: <strong style="color: #26351b;">${app.match_score}%</strong></span>
                    <span>Applied: ${new Date(app.applied_at || Date.now()).toLocaleDateString()}</span>
                </div>
            `;
            appContainer.appendChild(card);
        });
    } catch (e) {
        console.log("[Notice] Live applications sync skipped.");
    }
}


/* =========================================================
   LIVE NOTIFICATIONS
========================================================= */

async function initializeLiveNotifications() {
    const notifContainer = document.querySelector(".notifications-list") || document.querySelector("#notificationsList");
    if (!notifContainer) return;

    try {
        const res = await fetch(`${API_BASE}/notifications`);
        if (!res.ok) return;
        const json = await res.json();
        if (!json.success || !json.notifications || json.notifications.length === 0) return;

        notifContainer.innerHTML = "";

        json.notifications.forEach(n => {
            const item = document.createElement("div");
            item.className = `notification-item ${n.is_read ? 'read' : ''}`;
            item.innerHTML = `
                <div class="notification-icon">🔔</div>
                <div class="notification-content">
                    <h4>${escapeHtml(n.title)}</h4>
                    <p>${escapeHtml(n.message)}</p>
                    <small>${new Date(n.created_at || Date.now()).toLocaleDateString()}</small>
                </div>
            `;
            notifContainer.appendChild(item);
        });
    } catch (e) {
        console.log("[Notice] Live notifications sync skipped.");
    }
}


/* =========================================================
   REVEAL ANIMATIONS
========================================================= */

function initializeRevealAnimations() {
    const elements = document.querySelectorAll(
        ".reveal, .garden-card, .project-card, .team-member, .notification-item, .application-card"
    );

    if (!elements.length) return;

    elements.forEach((element, index) => {
        element.style.animationDelay = `${Math.min(index * 0.05, 0.4)}s`;
    });
}


/* =========================================================
   MOBILE NAVIGATION
========================================================= */

function initializeMobileNavigation() {
    const menuButton = document.querySelector(".mobile-menu-button");
    const sidebar = document.querySelector(".sidebar");

    if (!menuButton || !sidebar) return;

    menuButton.addEventListener("click", () => {
        sidebar.classList.toggle("mobile-open");
        menuButton.classList.toggle("active");
    });

    document.addEventListener("click", (event) => {
        if (
            window.innerWidth <= 760 &&
            sidebar.classList.contains("mobile-open") &&
            !sidebar.contains(event.target) &&
            !menuButton.contains(event.target)
        ) {
            sidebar.classList.remove("mobile-open");
            menuButton.classList.remove("active");
        }
    });

    window.addEventListener("resize", () => {
        if (window.innerWidth > 760) {
            sidebar.classList.remove("mobile-open");
            menuButton.classList.remove("active");
        }
    });
}


/* =========================================================
   PROFILE EDITING
========================================================= */

function initializeProfileEditing() {
    const editButton = document.querySelector("#editProfileButton");
    const editPanel = document.querySelector("#profileEditPanel");
    const cancelButton = document.querySelector("#cancelProfileEdit");
    const profileForm = document.querySelector("#profileForm");

    if (!editButton || !editPanel) return;

    editButton.addEventListener("click", () => {
        editPanel.hidden = false;
        editPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    if (cancelButton) {
        cancelButton.addEventListener("click", () => {
            editPanel.hidden = true;
        });
    }

    if (profileForm) {
        profileForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const name = document.querySelector("#profileName")?.value || "";
            const department = document.querySelector("#profileDepartment")?.value || "";
            const year = document.querySelector("#profileYear")?.value || "";
            const semester = document.querySelector("#profileSemester")?.value || "";
            const bio = document.querySelector("#profileBio")?.value || "";
            const github_url = document.querySelector("#profileGithub")?.value || "";
            const linkedin_url = document.querySelector("#profileLinkedin")?.value || "";

            try {
                const res = await secureFetch(`${API_BASE}/student/profile`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, department, year, semester, bio, github_url, linkedin_url })
                });
                const data = await res.json();
                if (data.success) {
                    showGardenToast("Your profile has been saved to the database 🌱");
                    initializeLiveProfile();
                }
            } catch (err) {
                showGardenToast("Your profile has been updated 🌱");
            }

            editPanel.hidden = true;
            updateProfileCompleteness();
        });
    }
}


/* =========================================================
   PROJECT SEARCH + FILTERS
========================================================= */

function initializeProjectSearchAndFilters() {
    const searchInput = document.querySelector("[data-search]");
    const filterControls = document.querySelectorAll("[data-filter]");
    const emptyState = document.querySelector("#projectEmptyState");

    if (!searchInput && !filterControls.length) return;

    function applyProjectFilters() {
        const projectCards = document.querySelectorAll(".project-card, .project-match-card");
        const searchTerm = searchInput ? searchInput.value.trim().toLowerCase() : "";
        let visibleCount = 0;

        projectCards.forEach((card) => {
            const text = card.textContent.toLowerCase();
            const matchesSearch = !searchTerm || text.includes(searchTerm);
            let matchesFilters = true;

            filterControls.forEach((filter) => {
                const selectedValue = filter.value;
                if (!selectedValue || selectedValue === "all" || selectedValue === "All") return;

                const filterType = filter.dataset.filter;
                const cardValue = (card.dataset[filterType] || text).toLowerCase();

                if (!cardValue.includes(selectedValue.toLowerCase())) {
                    matchesFilters = false;
                }
            });

            const visible = matchesSearch && matchesFilters;
            card.style.display = visible ? "" : "none";
            if (visible) visibleCount++;
        });

        if (emptyState) {
            emptyState.hidden = visibleCount !== 0;
        }
    }

    if (searchInput) searchInput.addEventListener("input", applyProjectFilters);
    filterControls.forEach(f => f.addEventListener("change", applyProjectFilters));
}


/* =========================================================
   MATCH SCORE ANIMATION
========================================================= */

function initializeMatchAnimations() {
    const scoreElements = document.querySelectorAll("[data-score]");

    scoreElements.forEach((element) => {
        const target = parseFloat(element.dataset.score);
        if (isNaN(target)) return;

        let current = 0;
        const duration = 1200;
        const start = performance.now();

        function step(timestamp) {
            const progress = Math.min((timestamp - start) / duration, 1);
            current = Math.floor(progress * target);
            element.textContent = `${current}%`;

            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = `${target}%`;
            }
        }

        requestAnimationFrame(step);
    });
}


/* =========================================================
   SKILL INTERACTIONS
========================================================= */

function initializeSkillInteractions() {
    const skillPills = document.querySelectorAll(".skill-pill, .skill-plant");

    skillPills.forEach((pill) => {
        pill.addEventListener("mouseenter", () => {
            pill.style.transform = "translateY(-3px)";
        });

        pill.addEventListener("mouseleave", () => {
            pill.style.transform = "";
        });
    });
}


/* =========================================================
   APPLICATION BUTTONS
========================================================= */

function initializeApplicationButtons() {
    const buttons = document.querySelectorAll("[data-apply]");

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            if (button.disabled) return;
            const projectName = button.dataset.apply || "this project";
            button.disabled = true;
            button.textContent = "Applied ✓";
            button.classList.add("applied");
            showGardenToast(`Application sent for ${projectName} 🌱`);
        });
    });
}


/* =========================================================
   APPLICATION ACTIONS
========================================================= */

function initializeApplicationActions() {
    const withdrawButtons = document.querySelectorAll("[data-withdraw]");

    withdrawButtons.forEach((button) => {
        button.addEventListener("click", () => {
            const card = button.closest(".application-card");
            const projectName = button.dataset.withdraw || "this project";

            const confirmed = window.confirm(`Withdraw your application for ${projectName}?`);
            if (!confirmed) return;

            if (card) {
                card.classList.add("application-withdrawn");
                const status = card.querySelector(".application-status");
                if (status) {
                    status.textContent = "Withdrawn";
                    status.classList.add("status-withdrawn");
                }
                button.disabled = true;
                button.textContent = "Withdrawn";
            }

            showGardenToast("Application withdrawn.");
        });
    });
}


/* =========================================================
   NOTIFICATIONS
========================================================= */

function initializeNotifications() {
    if (document.querySelector("#notificationsContainer")) return;
    const notifications = document.querySelectorAll("[data-notification]");

    notifications.forEach((notification) => {
        notification.addEventListener("click", async () => {
            const item = notification.closest(".notification-item") || notification;
            item.classList.add("read");
            updateUnreadCount();
            const notifId = item.dataset.notificationId;
            if (notifId) {
                try {
                    await secureFetch(`${API_BASE}/notifications/${notifId}/read`, { method: "POST" });
                } catch (e) {}
            }
        });
    });

    const markAllButton = document.querySelector("#markAllRead");
    if (markAllButton) {
        markAllButton.addEventListener("click", async () => {
            document.querySelectorAll(".notification-item").forEach((item) => {
                item.classList.add("read");
            });
            updateUnreadCount();
            try {
                await secureFetch(`${API_BASE}/notifications/read-all`, { method: "POST" });
                showGardenToast("All notifications marked as read.");
            } catch (e) {
                showGardenToast("All notifications marked as read.");
            }
        });
    }
}

function updateUnreadCount() {
    const unread = document.querySelectorAll(".notification-item:not(.read)").length;
    const badge = document.querySelector("[data-unread-count]");
    if (badge) {
        badge.textContent = unread;
        badge.style.display = unread > 0 ? "" : "none";
    }
}


/* =========================================================
   SETTINGS
========================================================= */

function initializeSettings() {
    const settingsForm = document.querySelector("#settingsForm");
    if (!settingsForm) return;

    settingsForm.addEventListener("submit", (event) => {
        event.preventDefault();
        showGardenToast("Settings saved successfully 🌿");
    });
}


/* =========================================================
   TEAM SEARCH
========================================================= */

function initializeTeamSearch() {
    const searchInput = document.querySelector("#teamSearchInput");
    const teammateCards = document.querySelectorAll(".team-member");

    if (!searchInput || !teammateCards.length) return;

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.trim().toLowerCase();
        teammateCards.forEach((card) => {
            const matches = !query || card.textContent.toLowerCase().includes(query);
            card.style.display = matches ? "" : "none";
        });
    });
}


/* =========================================================
   GARDEN BUTTONS
========================================================= */

function initializeGardenButtons() {
    const buttons = document.querySelectorAll("[data-garden-action]");
    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            const action = button.dataset.gardenAction;
            if (["save-settings", "change-password", "reset-settings", "invite"].includes(action)) {
                return;
            }
            const message = action || "Your garden is growing 🌿";
            showGardenToast(message);
        });
    });
}


/* =========================================================
   LOGOUT
========================================================= */

function initializeLogout() {
    const logoutButtons = document.querySelectorAll("[data-logout]");
    logoutButtons.forEach((button) => {
        button.addEventListener("click", async (event) => {
            event.preventDefault();
            try {
                await secureFetch(`${API_BASE}/auth/logout`, {
                    method: "POST"
                });
            } catch (err) {
                // Ignore network errors on logout
            }
            sessionStorage.clear();
            localStorage.clear();
            showGardenToast("Leaving the garden...");
            setTimeout(() => {
                window.location.href = "index.html";
            }, 500);
        });
    });
}


/* =========================================================
   PROFILE COMPLETENESS
========================================================= */

function initializeProfileCompleteness() {
    updateProfileCompleteness();
}

async function updateProfileCompleteness() {
    const progress = document.querySelector("[data-profile-completeness]");
    const progressText = document.querySelector("[data-profile-completeness-text]");
    if (!progress && !progressText) return;

    try {
        const res = await fetch(`${API_BASE}/student/profile`, { credentials: "include" });
        if (res.ok) {
            const data = await res.json();
            if (data && data.success && data.profile) {
                const completeness = data.profile.completeness || 0;
                if (progress) progress.style.width = `${completeness}%`;
                if (progressText) progressText.textContent = `${completeness}%`;
            }
        }
    } catch (e) {}
}


/* =========================================================
   GARDEN TOAST NOTIFICATION
========================================================= */

function showGardenToast(message) {
    let toast = document.querySelector(".garden-toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.className = "garden-toast";
        document.body.appendChild(toast);
    }

    toast.textContent = message;
    toast.classList.add("show");

    clearTimeout(toast.hideTimer);
    toast.hideTimer = setTimeout(() => {
        toast.classList.remove("show");
    }, 2800);
}

/* =========================================================
   SKILLMATCH — LIVE STUDENT DASHBOARD
   Uses the existing Flask API and botanical HTML.
========================================================= */

async function initializeStudentDashboard() {
    if (!document.querySelector(".app-layout")) return;

    // The faculty console has its own dashboard; this one is for students.
    if (document.body.dataset.page === "faculty") return;

    const $ = (selector) => document.querySelector(selector);

    try {
        const [profileResponse, projectsResponse] = await Promise.all([
            fetch(`${API_BASE}/student/profile`, {
                credentials: "same-origin"
            }),
            fetch(`${API_BASE}/matching/recommendations`, {
                credentials: "same-origin"
            })
        ]);

        if (profileResponse.status === 401) {
            window.location.href = "login.html";
            return;
        }

        if (!profileResponse.ok) {
            throw new Error("Could not load your student profile.");
        }

        if (!projectsResponse.ok) {
            throw new Error("Could not load project recommendations.");
        }

        const profileData = await profileResponse.json();
        const projectData = await projectsResponse.json();

        if (!profileData.success) {
            throw new Error(profileData.message || "Profile unavailable.");
        }

        const profile = profileData.profile;
        const recommendations = projectData.recommendations || [];

        // Welcome name and avatar
        // Greet the student by their first name. When the page provides a
        // dedicated element for it, fill that instead of the whole block.
        const welcomeSlot = $("[data-dashboard-welcome]");
        if (welcomeSlot) {
            const firstName = (profile.name || "").trim().split(/\s+/)[0];
            welcomeSlot.textContent = (firstName || "there").toUpperCase();
        } else {
            const welcome = $(".app-welcome small");
            if (welcome) {
                welcome.textContent = `WELCOME BACK, ${(profile.name || "STUDENT").toUpperCase()}`;
            }
        }

        const avatar = $(".user-avatar");
        if (avatar) {
            avatar.textContent = (profile.name || "S").trim().charAt(0).toUpperCase();
        }

        // Real profile completion
        const completeness = Math.max(
            0,
            Math.min(100, Number(profile.completeness) || 0)
        );

        const healthHeading = $(".profile-health-card h2");
        if (healthHeading) {
            healthHeading.replaceChildren(
                document.createTextNode("Your profile is "),
                Object.assign(document.createElement("em"), {
                    textContent: `${completeness}% complete.`
                })
            );
        }

        const healthBar = $(".profile-health-card [style*='width:82%']");
        if (healthBar) {
            healthBar.style.width = `${completeness}%`;
        }

        // Actual profile statistics
        const statCards = document.querySelectorAll(".stat-card");

        const stats = [
            (profile.skills || []).length,
            (profile.interests || []).length,
            (profile.experiences || []).length
        ];

        statCards.forEach((card, index) => {
            const number = card.querySelector(".stat-number");
            if (number && stats[index] !== undefined) {
                number.textContent = String(stats[index]).padStart(2, "0");
            }
        });

        // Display the highest-ranked project from Flask
        const project = recommendations[0];
        if (project) {
            const title = $(".project-match-title");
            if (title) title.textContent = project.title;

            const domain = $(".project-match-domain");
            if (domain) {
                domain.textContent =
                    `${project.domain || "ACADEMIC PROJECT"} · TEAM OF ${project.team_size || "—"}`;
            }

            const description = $(".project-match-description");
            if (description) description.textContent = project.description || "";

            const score = Math.round(Number(project.match_score) || 0);
            const scoreCircle = $(".project-match-card .match-score-circle");

            if (scoreCircle) {
                scoreCircle.style.setProperty("--score", score);
                const scoreText = scoreCircle.querySelector("[data-score]");
                if (scoreText) {
                    scoreText.dataset.score = score;
                    scoreText.textContent = `${score}%`;
                }
            }

            const tags = $(".project-match-card .project-tags");
            if (tags) {
                tags.replaceChildren();

                (project.skill_details || []).forEach(skill => {
                    const tag = document.createElement("span");
                    tag.textContent = skill.skill;
                    tags.appendChild(tag);
                });
            }

            const projectLink = $(".project-match-card .project-match-footer a");
            if (projectLink) {
                projectLink.href = `project-details.html?id=${encodeURIComponent(project.id)}`;
            }

            // Actual weighted match breakdown
            const scoreValues = [
                project.skill_score,
                project.interest_score,
                project.experience_score,
                project.availability_score
            ];

            document.querySelectorAll(".match-components .match-component")
                .forEach((component, index) => {
                    const value = Math.max(
                        0,
                        Math.min(100, Number(scoreValues[index]) || 0)
                    );

                    const fill = component.querySelector(".match-component-fill");
                    const label = component.querySelector(".match-component-value");

                    if (fill) fill.style.width = `${value}%`;
                    if (label) label.textContent = `${Math.round(value)}%`;
                });
        } else {
            const title = $(".project-match-title");
            if (title) title.textContent = "Your next project is waiting";

            const description = $(".project-match-description");
            if (description) {
                description.textContent =
                    "No recommendations are available yet. Add skills and interests to your profile, or check back when projects are available.";
            }
        }

    } catch (error) {
        console.error("Dashboard loading error:", error);

        if (typeof showGardenToast === "function") {
            showGardenToast("Some garden details could not load. Please refresh.");
        }
    }
}

// Run after the page is ready
document.addEventListener("DOMContentLoaded", initializeStudentDashboard);
