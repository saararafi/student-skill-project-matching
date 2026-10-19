/* =========================================================
   STUDENT SKILL AND PROJECT MATCHING SYSTEM
   Full-Stack Frontend Controller
   ========================================================= */

const API_BASE = window.location.origin.includes('http')
    ? `${window.location.origin}/api`
    : 'http://127.0.0.1:5000/api';

document.addEventListener("DOMContentLoaded", () => {
    initializeLogin();
    initializeRevealAnimations();
    initializeMobileNavigation();

    // Live API Initializers
    initializeLiveProfile();
    setupCertificateModal();
    initializeLiveProjects();
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
            const res = await fetch(`${API_BASE}/auth/login`, {
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
                    window.location.href = "dashboard.html";
                }, 600);
            } else {
                showGardenToast(data.message || "Invalid credentials.");
            }
        } catch (err) {
            // Offline / fallback mode
            showGardenToast("Welcome to SkillMatch 🌿");
            setTimeout(() => {
                window.location.href = "dashboard.html";
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
        const res = await fetch(`${API_BASE}/student/profile`);
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

        // Update completeness
        const compBar = document.querySelector("[data-profile-completeness]");
        const compText = document.querySelector("[data-profile-completeness-text]");
        if (compBar) compBar.style.width = `${p.completeness}%`;
        if (compText) compText.textContent = `${p.completeness}% complete`;

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
                        <a href="${API_BASE}/certificates/${sk.certificate_filename}" target="_blank" class="skill-cert-badge verified" title="Verified certificate: ${sk.certificate_original_name || 'Proof'}">
                            Verified ✓
                        </a>
                    `;
                } else if (sk.certificate_status === "Pending") {
                    certBadge = `
                        <a href="${API_BASE}/certificates/${sk.certificate_filename}" target="_blank" class="skill-cert-badge pending" title="Verification pending">
                            Pending ⏳
                        </a>
                    `;
                } else {
                    certBadge = `
                        <button type="button" class="skill-cert-badge upload" onclick="openCertModal(${sk.skill_id}, '${sk.name}')" title="Upload verification certificate">
                            + Certificate
                        </button>
                    `;
                }

                const plant = document.createElement("div");
                plant.className = "skill-plant";
                plant.innerHTML = `
                    <div class="skill-plant-flower">${flower}</div>
                    <div class="skill-plant-name">${sk.name}</div>
                    <div class="skill-plant-level">${sk.proficiency_level} / 5 · ${pct}%</div>
                    ${certBadge}
                `;
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
                const res = await fetch(`${API_BASE}/student/upload-certificate`, {
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

    try {
        const res = await fetch(`${API_BASE}/projects`);
        if (!res.ok) return;
        const data = await res.json();
        if (!data.success || !data.projects || data.projects.length === 0) return;

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
                    ${s.skill}
                </span>
            `).join("");

            article.innerHTML = `
                <div class="project-card-top">
                    <div class="project-flower">✿</div>
                    <span class="project-status">${proj.status}</span>
                </div>

                <h2>${proj.title}</h2>

                <p class="project-description">
                    ${proj.description}
                </p>

                <div class="project-meta">
                    <span>🌿 ${proj.domain}</span>
                    <span>👥 ${proj.team_size} members</span>
                    <span>◷ ${proj.required_availability}</span>
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
        const res = await fetch(`${API_BASE}/projects/${projectId}/apply`, {
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
        showGardenToast("Application sent in demo mode 🌿");
        if (buttonElement) {
            buttonElement.textContent = "Applied ✓";
        }
    }
};


/* =========================================================
   LIVE SKILL GAPS
========================================================= */

async function initializeLiveGaps() {
    const gapList = document.querySelector(".gap-item-list") || document.querySelector(".skill-gap-list");
    if (!gapList) return;

    try {
        const res = await fetch(`${API_BASE}/matching/projects/1/gaps`);
        if (!res.ok) return;
        const json = await res.json();
        if (!json.success || !json.data) return;

        const breakdown = json.data.skill_breakdown;
        if (breakdown && breakdown.length > 0) {
            gapList.innerHTML = "";
            breakdown.forEach(item => {
                const el = document.createElement("div");
                el.className = "gap-item";
                
                let statusClass = "covered";
                let statusBadge = "Covered ✓";
                if (item.status === "Missing") {
                    statusClass = "missing";
                    statusBadge = "Missing 💧";
                } else if (item.status === "Insufficient") {
                    statusClass = "insufficient";
                    statusBadge = "Insufficient ⚠️";
                }

                const pct = Math.round((item.available_level / item.required_level) * 100);

                el.innerHTML = `
                    <div class="gap-item-heading" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <strong>${item.skill}</strong>
                        <span class="botanical-badge ${statusClass}" style="padding: 3px 10px; border-radius: 12px; font-size: 0.75rem;">
                            ${statusBadge}
                        </span>
                    </div>
                    <div style="font-size: 0.85rem; color: #555; margin-bottom: 6px;">
                        Required: ${item.required_level}/5 | Available in Team: ${item.available_level}/5
                    </div>
                    <div class="match-component-track">
                        <div class="match-component-fill" style="width: ${Math.min(pct, 100)}%;"></div>
                    </div>
                `;
                gapList.appendChild(el);
            });
        }
    } catch (e) {
        console.log("[Notice] Live gaps sync skipped.");
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
                return `<span class="botanical-badge" style="margin: 3px; font-size: 0.72rem;">${certIcon}${s.name} (Lvl ${s.level})</span>`;
            }).join("");

            card.innerHTML = `
                <div class="member-avatar" style="font-size: 2rem; margin-bottom: 8px;">🌱</div>
                <h3 style="margin: 4px 0;">${stu.name}</h3>
                <small style="color: #666; display: block; margin-bottom: 8px;">${stu.department} · ${stu.year}</small>
                
                <p style="font-size: 0.85rem; color: #444; margin-bottom: 12px;">
                    ${stu.bio || "Active academic collaborator with verified technical competencies."}
                </p>

                <div style="margin: 10px 0;">
                    <strong style="font-size: 0.8rem; display: block; margin-bottom: 5px; color: #26351b;">Matches Missing Gaps:</strong>
                    ${skillPills}
                </div>

                <div style="margin-top: 14px;">
                    <button type="button" class="garden-button secondary" onclick="showGardenToast('Invitation sent to ${stu.name} 🌿')">
                        Invite to Team
                    </button>
                </div>
            `;
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
                            ${app.project_title}
                        </h3>
                        <small style="color: #666;">🌿 ${app.domain}</small>
                    </div>
                    <span class="botanical-badge ${statusClass}" style="padding: 4px 10px; border-radius: 12px;">
                        ${app.status}
                    </span>
                </div>

                <p style="font-size: 0.88rem; color: #444; margin: 10px 0;">
                    ${app.message || "Application submitted for academic project matching."}
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
                    <h4>${n.title}</h4>
                    <p>${n.message}</p>
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

            try {
                const res = await fetch(`${API_BASE}/student/profile`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, department, year, semester, bio })
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
    const notifications = document.querySelectorAll("[data-notification]");

    notifications.forEach((notification) => {
        notification.addEventListener("click", () => {
            const item = notification.closest(".notification-item") || notification;
            item.classList.add("read");
            updateUnreadCount();
        });
    });

    const markAllButton = document.querySelector("#markAllRead");
    if (markAllButton) {
        markAllButton.addEventListener("click", () => {
            document.querySelectorAll(".notification-item").forEach((item) => {
                item.classList.add("read");
            });
            updateUnreadCount();
            showGardenToast("All notifications marked as read.");
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
            const message = button.dataset.gardenAction || "Your garden is growing 🌿";
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
        button.addEventListener("click", (event) => {
            event.preventDefault();
            sessionStorage.clear();
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

function updateProfileCompleteness() {
    const progress = document.querySelector("[data-profile-completeness]");
    const progressText = document.querySelector("[data-profile-completeness-text]");
    if (!progress && !progressText) return;

    const completeness = 85;
    if (progress) progress.style.width = `${completeness}%`;
    if (progressText) progressText.textContent = `${completeness}% complete`;
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