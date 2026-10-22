/* =========================================================
   SKILLMATCH — LIVE DATA LAYER
   -------------------------------------------------------
   Renders every page from the database and wires up the
   forms. Loaded after main.js; it targets the same garden
   containers and adds the missing live panels.

   Every panel degrades to an empty state when the database
   has no rows, so nothing ever shows stale demo content.
   ========================================================= */

const API = window.location.origin.includes("http")
    ? `${window.location.origin}/api`
    : "http://127.0.0.1:5000/api";

const $  = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/* ------------------------------------------------------------
   Helpers
   ------------------------------------------------------------ */

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

async function api(path, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = { ...(options.headers || {}) };
    if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    if (["POST", "PUT", "DELETE", "PATCH"].includes(method)) {
        const csrfToken = getCookie("csrf_token");
        if (csrfToken && !headers["X-CSRF-Token"]) {
            headers["X-CSRF-Token"] = csrfToken;
        }
    }
    const res = await fetch(API + path, {
        credentials: "include",
        ...options,
        headers
    });
    let data = null;
    try { data = await res.json(); } catch (e) { data = {}; }
    return { ok: res.ok, status: res.status, data };
}

function toast(message) {
    let el = $(".garden-toast");
    if (!el) {
        el = document.createElement("div");
        el.className = "garden-toast";
        document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove("show"), 3200);
}

function emptyState(container, message) {
    container.innerHTML = `
        <div class="empty-state">
            <p>${escapeHtml(message)}</p>
        </div>`;
}

let resolvedProjectId = null;

/** Resolves the active project ID: URL ?id= first, then first available project. */
async function resolveProjectId() {
    const id = new URLSearchParams(window.location.search).get("id");
    if (id) {
        resolvedProjectId = id;
        return id;
    }
    if (resolvedProjectId) return resolvedProjectId;
    try {
        const { ok, data } = await api("/projects");
        const list = (ok && data.projects) || [];
        if (list.length > 0) {
            resolvedProjectId = String(list[0].id);
            return resolvedProjectId;
        }
    } catch (e) {}
    return null;
}

/** The project currently being viewed (?id=), defaulting to resolved project. */
function currentProjectId() {
    const id = new URLSearchParams(window.location.search).get("id");
    return id || resolvedProjectId || "1";
}

/* ------------------------------------------------------------
   Dashboard
   ------------------------------------------------------------ */

async function renderDashboard() {
    const card = $(".project-match-card");
    if (!card) return;

    const { ok, data } = await api("/matching/dashboard");
    if (!ok || !data.dashboard) {
        const stats = $(".dashboard-grid");
        if (stats) emptyState(stats, "Sign in to see your garden.");
        return;
    }

    const d = data.dashboard;

    // Greet the signed-in student by name.
    const welcome = $("[data-dashboard-welcome]");
    if (welcome) {
        const name = (d.profile && d.profile.name) || "";
        welcome.textContent = name ? name.split(" ")[0].toUpperCase() : "THERE";
    }

    // Profile completeness
    if (d.profile && d.profile.completeness !== undefined) {
        const healthEm = $("[data-dashboard-completeness-text]") || $(".profile-health-card em");
        if (healthEm) healthEm.textContent = `${d.profile.completeness}% complete.`;
        const healthBar = $("[data-dashboard-completeness-bar]") || $(".profile-health-card div[style*='background:linear-gradient']");
        if (healthBar) healthBar.style.width = `${d.profile.completeness}%`;
    }

    // Avatar initials
    const avatars = $$(".user-avatar");
    if (avatars.length && d.profile && d.profile.name) {
        const initial = d.profile.name.trim().charAt(0).toUpperCase() || "S";
        avatars.forEach(av => av.textContent = initial);
    }

    // Statistic cards
    const statMap = {
        skills: d.stats.skills,
        interests: d.stats.interests,
        experiences: d.stats.experiences
    };
    $$(".stat-card").forEach((el) => {
        const heading = (el.querySelector("h3") || {}).textContent || "";
        const key = Object.keys(statMap).find(k => heading.toLowerCase().includes(k));
        const number = el.querySelector(".stat-number");
        if (key && number) number.textContent = String(statMap[key]).padStart(2, "0");
    });

    // Featured project
    if (d.top_match) {
        const m = d.top_match;
        const domain = $(".project-match-domain", card);
        if (domain) domain.textContent = `${m.domain.toUpperCase()} · TEAM OF ${m.team_size}`;

        const title = $(".project-match-title", card);
        if (title) title.textContent = m.title;

        const desc = $(".project-match-description", card);
        if (desc) desc.textContent = m.description;

        const score = $("[data-score]", card);
        if (score) {
            score.dataset.score = Math.round(m.final_score);
            score.textContent = `${Math.round(m.final_score)}%`;
        }
        const circle = $(".match-score-circle", card);
        if (circle) circle.style.setProperty("--score", Math.round(m.final_score));

        const tags = $(".project-tags", card);
        if (tags) {
            tags.innerHTML = (m.skill_details || [])
                .map(s => `<span>${s.skill}</span>`).join("");
        }

        const badge = $(".botanical-badge", card);
        if (badge) badge.textContent = "Strong skill compatibility";

        const viewBtn = $("a.garden-button", card);
        if (viewBtn && m.project_id) {
            viewBtn.textContent = "View Project →";
            viewBtn.href = `project-details.html?id=${m.project_id}`;
        }
    } else {
        const domain = $(".project-match-domain", card);
        if (domain) domain.textContent = "RECOMMENDATION";

        const title = $(".project-match-title", card);
        if (title) title.textContent = "No Projects Available Yet";

        const desc = $(".project-match-description", card);
        if (desc) desc.textContent = "Add your skills in My Growth, or publish a project from the Faculty desk to start matching!";

        const score = $("[data-score]", card);
        if (score) {
            score.dataset.score = 0;
            score.textContent = "0%";
        }
        const circle = $(".match-score-circle", card);
        if (circle) circle.style.setProperty("--score", 0);

        const tags = $(".project-tags", card);
        if (tags) tags.innerHTML = "<span>Add skills to start matching</span>";

        const badge = $(".botanical-badge", card);
        if (badge) badge.textContent = "Awaiting projects & skills";

        const viewBtn = $("a.garden-button", card);
        if (viewBtn) {
            viewBtn.textContent = "Explore Projects →";
            viewBtn.href = "projects.html";
        }
    }

    // Match breakdown bars on dashboard
    const breakdownSection = $(".match-components");
    if (breakdownSection) {
        const m = d.top_match;
        const comps = m ? [
            { label: "Skill Compatibility", score: m.skill_score || 0 },
            { label: "Interest Compatibility", score: m.interest_score || 0 },
            { label: "Previous Experience", score: m.experience_score || 0 },
            { label: "Availability", score: m.availability_score || 0 }
        ] : [
            { label: "Skill Compatibility", score: 0 },
            { label: "Interest Compatibility", score: 0 },
            { label: "Previous Experience", score: 0 },
            { label: "Availability", score: 0 }
        ];
        breakdownSection.innerHTML = comps.map(c => `
            <div class="match-component">
                <span class="match-component-label">${c.label}</span>
                <div class="match-component-track">
                    <div class="match-component-fill" style="width:${Math.round(c.score)}%;"></div>
                </div>
                <span class="match-component-value">${Math.round(c.score)}%</span>
            </div>
        `).join("");
    }

    // Skill garden
    const plants = $(".skill-plants");
    if (plants) {
        const flowers = ["✿", "❀", "✾", "❁", "✽"];
        if (!d.skills.length) {
            plants.innerHTML = `<p class="muted-text">No skills planted yet.</p>`;
        } else {
            plants.innerHTML = d.skills.map((sk, i) => {
                const pct = Math.round((sk.proficiency_level / 5) * 100);
                const stage = pct >= 90 ? "BLOOMING" : pct >= 70 ? "GROWING" : "SPROUTING";
                const cert = sk.certificate_status === "Verified"
                    ? `<div class="skill-plant-cert verified">📜 Verified</div>`
                    : sk.certificate_status === "Pending"
                        ? `<div class="skill-plant-cert pending">📜 Pending ⏳</div>` : "";
                return `
                    <div class="skill-plant">
                        <div class="skill-plant-flower">${flowers[i % flowers.length]}</div>
                        <div class="skill-plant-name">${sk.name}</div>
                        <div class="skill-plant-level">${sk.proficiency_level} / 5 · ${pct}% · ${stage}</div>
                        ${cert}
                    </div>`;
            }).join("");
        }
    }

    // Garden team
    const team = $(".team-branch");
    if (team) {
        const pid = (d.top_match && d.top_match.project_id) || await resolveProjectId();
        if (!pid) {
            team.innerHTML = `<p class="muted-text">Explore projects to join a garden team.</p>`;
        } else {
            const { ok, data } = await api(`/projects/${pid}`);
            const members = (ok && data.project && data.project.team_members) || [];
            if (!members.length) {
                team.innerHTML = `<p class="muted-text">No team members yet.</p>`;
            } else {
                team.innerHTML = members.map(m => `
                    <div class="team-member">
                        <div class="team-member-avatar">${escapeHtml((m.name || "?").charAt(0).toUpperCase())}</div>
                        <div>
                            <div class="team-member-name">${escapeHtml((m.name || "").split(" ")[0])}</div>
                            <div class="team-member-role">${escapeHtml(m.role || "Contributor")}</div>
                        </div>
                    </div>`).join("");
            }
        }
    }

    // Recent activity
    const timeline = $(".growth-timeline");
    if (timeline) {
        const events = [];
        (d.applications || []).forEach(a => events.push({
            when: "RECENT",
            title: `Applied to ${a.project_title}`,
            body: `Your compatibility score was ${Math.round(a.match_score || 0)}%.`
        }));
        (d.notifications || []).slice(0, 3).forEach(n => events.push({
            when: "LATEST",
            title: n.title,
            body: n.message
        }));
        if (!events.length) {
            timeline.innerHTML = `<p class="muted-text">Your growth story starts with your first skill.</p>`;
        } else {
            timeline.innerHTML = events.map(ev => `
                <div class="growth-item">
                    <div class="growth-year">${ev.when}</div>
                    <div>
                        <h3>${ev.title}</h3>
                        <p>${ev.body}</p>
                    </div>
                </div>`).join("");
        }
    }
}

/* ------------------------------------------------------------
   Applications
   ------------------------------------------------------------ */

async function renderApplications() {
    const container = $("#applicationsListItems");
    if (!container) return;

    const { ok, data } = await api("/applications");
    if (!ok || !data.applications) {
        emptyState(container, "Your applications will appear here.");
        return;
    }
    if (!data.applications.length) {
        emptyState(container, "You have not applied to any project yet.");
        return;
    }

    container.innerHTML = data.applications.map(app => {
        const cls = app.status === "Accepted" ? "accepted"
            : app.status === "Rejected" ? "rejected" : "pending";
        const label = app.status === "Accepted" ? "Accepted ✓"
            : app.status === "Rejected" ? "Rejected" : "Pending Review";
        const applied = app.applied_at
            ? new Date(app.applied_at).toLocaleDateString() : "—";
        const withdraw = app.status === "Accepted" ? "" : `
            <button class="garden-button secondary" type="button"
                    data-withdraw-app="${app.id}"
                    data-project-title="${app.project_title}">Withdraw</button>`;
        return `
            <article class="garden-card application-card">
                <div class="application-card-top">
                    <div>
                        <span class="application-project-status open">${app.domain || "Open Project"}</span>
                        <h3>${app.project_title}</h3>
                        <p>${app.message || "Application submitted for academic project matching."}</p>
                    </div>
                    <div class="application-match">
                        <small>MATCH</small>
                        <strong>${Math.round(app.match_score || 0)}%</strong>
                    </div>
                </div>
                <div class="application-meta">
                    <span>📅 Applied ${applied}</span>
                    <span>✿ ${app.status}</span>
                </div>
                <div class="application-status-row">
                    <div class="application-status ${cls}">
                        <span class="status-dot"></span>${label}
                    </div>
                    <div class="application-actions">
                        <a href="project-details.html?id=${app.project_id}" class="garden-button">View Project</a>
                        ${withdraw}
                    </div>
                </div>
            </article>`;
    }).join("");

    // Withdraw buttons
    $$("[data-withdraw-app]", container).forEach(btn => {
        btn.addEventListener("click", async () => {
            const id = btn.dataset.withdrawApp;
            const title = btn.dataset.projectTitle || "this project";
            if (!window.confirm(`Withdraw your application for ${title}?`)) return;
            btn.disabled = true;
            const { ok, data } = await api(`/applications/${id}/withdraw`, { method: "POST" });
            if (ok && data.success) {
                toast("Application withdrawn.");
                renderApplications();
            } else {
                toast(data.message || "Could not withdraw the application.");
                btn.disabled = false;
            }
        });
    });
}

/* ------------------------------------------------------------
   Notifications
   ------------------------------------------------------------ */

async function renderNotifications() {
    const container = $(".notification-list");
    if (!container) return;

    const { ok, data } = await api("/notifications");
    if (!ok || !data.notifications) return;

    if (!data.notifications.length) {
        emptyState(container, "No notifications yet.");
        return;
    }

    container.innerHTML = data.notifications.map(n => `
        <article class="garden-card notification-item ${n.is_read ? "read" : "unread"}"
                 data-notification="${n.id}">
            <div class="notification-icon ${n.type || "info"}">🔔</div>
            <div class="notification-content">
                <div class="notification-top">
                    <h3>${n.title}</h3>
                    <span>${n.created_at ? new Date(n.created_at).toLocaleDateString() : ""}</span>
                </div>
                <p>${n.message}</p>
                ${n.link ? `<a href="${n.link}" class="notification-link">View →</a>` : ""}
            </div>
            ${n.is_read ? "" : `<span class="unread-dot"></span>`}
        </article>`).join("");

    // Clicking marks as read
    $$("[data-notification]", container).forEach(item => {
        item.addEventListener("click", async () => {
            if (item.classList.contains("read")) return;
            item.classList.add("read");
            const dot = $(".unread-dot", item);
            if (dot) dot.remove();
            await api(`/notifications/${item.dataset.notification}/read`, { method: "POST" });
            updateUnreadBadge();
        });
    });
    updateUnreadBadge();
}

function updateUnreadBadge() {
    const unread = $$(".notification-item:not(.read)").length;
    const badge = $("[data-unread-count]");
    if (badge) {
        badge.textContent = unread;
        badge.style.display = unread > 0 ? "" : "none";
    }
}

/* ------------------------------------------------------------
   Skill gaps  (gaps.html and the gaps panel on the dashboard)
   ------------------------------------------------------------ */

async function renderGaps() {
    const list = $(".gap-list");
    if (!list) return;

    const projectId = await resolveProjectId();
    if (!projectId) {
        emptyState(list, "No projects available to analyze. Projects published by faculty will appear here.");
        return;
    }
    const { ok, data } = await api(`/matching/projects/${projectId}/gaps`);
    // The API returns the payload under "gaps"; older builds used "data".
    const payload = data.gaps || data.data;
    if (!ok || !payload) return;

    const breakdown = payload.skill_breakdown || [];
    if (!breakdown.length) {
        emptyState(list, "This project does not list any required skills yet.");
        return;
    }

    list.innerHTML = breakdown.map(item => {
        const pct = Math.round((item.available_level / item.required_level) * 100);
        const badge = item.status === "Missing" ? "Missing 💧"
            : item.status === "Insufficient" ? "Insufficient ⚠️" : "Covered ✓";
        const cls = item.status === "Missing" ? "missing"
            : item.status === "Insufficient" ? "insufficient" : "covered";
        return `
            <article class="gap-item garden-card">
                <div class="gap-item-icon">${item.status === "Covered" ? "❧" : "🌱"}</div>
                <div class="gap-item-content">
                    <div class="gap-item-heading">
                        <div>
                            <h4>${item.skill}</h4>
                            <p>Required level ${item.required_level}/5 · team has ${item.available_level}/5</p>
                        </div>
                        <span class="gap-percentage">${Math.min(pct, 100)}%</span>
                    </div>
                    <div class="gap-progress">
                        <div class="gap-progress-track">
                            <div class="gap-progress-fill" style="width:${Math.min(pct, 100)}%;"></div>
                        </div>
                    </div>
                    <div class="gap-item-footer">
                        <span class="botanical-badge ${cls}">${badge}</span>
                    </div>
                </div>
            </article>`;
    }).join("");

    // Summary counts
    const counts = {
        tracked: breakdown.length,
        developing: breakdown.filter(i => i.status === "Insufficient").length,
        priority: breakdown.filter(i => i.status === "Missing").length
    };
    Object.entries(counts).forEach(([key, value]) => {
        const el = $(`[data-gap-stat="${key}"]`);
        if (el) el.textContent = value;
    });

    // Team coverage cards
    const teamGrid = $(".team-gap-grid");
    if (teamGrid) {
        const gaps = breakdown.filter(i => i.status !== "Covered");
        if (!gaps.length) {
            teamGrid.innerHTML = `
                <article class="team-gap-card garden-card">
                    <div class="team-gap-icon">❧</div>
                    <div>
                        <h4>Nothing missing</h4>
                        <p>The team already covers every skill this project needs.</p>
                    </div>
                </article>`;
        } else {
            teamGrid.innerHTML = gaps.map(item => {
                const pct = Math.min(100, Math.round((item.available_level / item.required_level) * 100));
                return `
                    <article class="team-gap-card garden-card">
                        <div class="team-gap-icon">${item.status === "Missing" ? "🌧" : "🌱"}</div>
                        <div>
                            <h4>${item.skill}</h4>
                            <p>Current team coverage: <strong>${pct}%</strong></p>
                            <div class="gap-progress-track">
                                <div class="gap-progress-fill" style="width:${pct}%;"></div>
                            </div>
                        </div>
                    </article>`;
            }).join("");
        }
    }
}

/* ------------------------------------------------------------
   Team page
   ------------------------------------------------------------ */

async function renderTeam() {
    const roster = $(".team-members-grid");
    const mates = $(".recommended-teammates-grid");
    const coverage = $(".team-skill-coverage-grid");
    if (!roster && !mates && !coverage) return;

    const projectId = await resolveProjectId();
    if (!projectId) {
        if (roster) roster.innerHTML = `<div class="empty-state"><p>No projects available yet. Explore published projects or create one as faculty.</p></div>`;
        if (mates) mates.innerHTML = `<div class="empty-state"><p>No projects available yet.</p></div>`;
        if (coverage) coverage.innerHTML = `<div class="empty-state"><p>No project selected.</p></div>`;
        const heroTitle = $(".team-hero-card h2");
        if (heroTitle) heroTitle.textContent = "No Project Selected";
        return;
    }

    // Current team and project hero
    let members = [];
    if (roster || $(".team-hero-card") || $(".team-tree")) {
        const { ok, data } = await api(`/projects/${projectId}`);
        const project = (ok && data.project) || null;
        members = (project && project.team_members) || [];

        const heroTitle = $(".team-hero-card h2");
        if (heroTitle && project) heroTitle.textContent = project.title;

        const heroStatus = $(".team-status-row");
        if (heroStatus && project) {
            heroStatus.innerHTML = `
                <span>● ${escapeHtml(project.domain || "Team Formation")}</span>
                <span>👥 ${members.length} / ${project.team_size || 5} members</span>
                <span>◷ ${escapeHtml(project.required_availability || "Regular")}</span>
            `;
        }

        // Update team tree visual
        const tree = $(".team-tree");
        if (tree && project) {
            const memberNodes = [
                { cls: "member-one" },
                { cls: "member-two" },
                { cls: "member-three" },
                { cls: "member-four" }
            ];
            let nodesHtml = "";
            if (members.length === 0) {
                nodesHtml = `
                    <div class="member-node member-one">
                        <div class="member-avatar">?</div>
                        <strong>Open</strong>
                        <small>Awaiting team</small>
                    </div>`;
            } else {
                members.slice(0, 4).forEach((m, idx) => {
                    const cfg = memberNodes[idx] || { cls: "member-one" };
                    const initial = (m.name || "?").charAt(0).toUpperCase();
                    const shortName = (m.name || "Member").split(" ")[0];
                    const role = m.role || "Contributor";
                    nodesHtml += `
                        <div class="member-node ${cfg.cls}">
                            <div class="member-avatar">${escapeHtml(initial)}</div>
                            <strong>${escapeHtml(shortName)}</strong>
                            <small>${escapeHtml(role)}</small>
                        </div>`;
                });
            }
            tree.innerHTML = `
                <div class="tree-trunk"></div>
                <div class="tree-branch-line"></div>
                <div class="team-center">
                    <strong>${escapeHtml(project.title.slice(0, 25))}</strong>
                    <small>PROJECT</small>
                </div>
                ${nodesHtml}
            `;
        }

        if (roster) {
            if (!members.length) {
                roster.innerHTML = `<div class="empty-state"><p>No team members yet — this project is waiting for its first gardener.</p></div>`;
            } else {
                roster.innerHTML = members.map(m => `
                    <article class="team-member-card garden-card">
                        <div class="team-member-avatar">${escapeHtml((m.name || "?").charAt(0).toUpperCase())}</div>
                        <div class="team-member-info">
                            <h3>${escapeHtml(m.name)}</h3>
                            <span>${escapeHtml(m.role || "Contributor")}</span>
                        </div>
                        <div class="team-member-skills">
                            ${(m.skills || []).map(s => `<span>${escapeHtml(s.name)} · ${s.proficiency_level}/5</span>`).join("")
                                || "<span>No skills listed</span>"}
                        </div>
                        <span class="team-role-badge">${escapeHtml(m.department || "Student")}</span>
                    </article>`).join("");
            }
        }
    }

    // Recommended teammates
    if (mates) {
        const { ok, data } = await api(`/matching/projects/${projectId}/teammates`);
        const list = (ok && data.teammates) || [];
        if (!list.length) {
            mates.innerHTML = `<div class="empty-state"><p>No teammates are needed — the team covers every skill.</p></div>`;
        } else {
            mates.innerHTML = list.map(stu => {
                const skills = (stu.matching_skills_detailed || [])
                    .map(s => `<span>${s.has_certificate ? "📜 " : ""}${escapeHtml(s.name)} (Lvl ${s.level})</span>`).join("");
                const stuId = stu.id || stu.student_id || "";
                return `
                    <article class="recommended-teammate garden-card" data-search-item>
                        <div class="recommended-avatar">${escapeHtml((stu.name || "?").charAt(0).toUpperCase())}</div>
                        <div class="recommended-info">
                            <h3>${escapeHtml(stu.name)}</h3>
                            <p>${escapeHtml(stu.department || "")} · ${escapeHtml(stu.year || "")}</p>
                            <div class="skill-list">${skills}</div>
                        </div>
                        <div class="teammate-match">
                            <small>GAPS FILLED</small>
                            <strong>${stu.gaps_filled ?? (stu.matching_skills || []).length}</strong>
                            <button type="button" class="garden-button" data-invite-btn data-student-id="${stuId}" data-student-name="${escapeHtml(stu.name)}" style="margin-top: 8px;">
                                ✿ Invite
                            </button>
                        </div>
                    </article>`;
            }).join("");

            mates.querySelectorAll("[data-invite-btn]").forEach(btn => {
                btn.addEventListener("click", async () => {
                    const sId = btn.dataset.studentId;
                    const sName = btn.dataset.studentName;
                    btn.disabled = true;
                    btn.textContent = "Invited ✓";
                    btn.classList.add("applied");
                    try {
                        await api(`/matching/projects/${projectId}/invite`, {
                            method: "POST",
                            body: JSON.stringify({ student_id: sId, student_name: sName })
                        });
                    } catch (e) {}
                    toast(`Invitation sent to ${sName}! 🌿`);
                });
            });
        }
    }

    // Skill coverage
    if (coverage) {
        const { ok, data } = await api(`/matching/projects/${projectId}/gaps`);
        const payload = data.gaps || data.data;
        const breakdown = (ok && payload && payload.skill_breakdown) || [];
        if (!breakdown.length) {
            coverage.innerHTML = `<div class="empty-state"><p>No skill requirements listed.</p></div>`;
        } else {
            coverage.innerHTML = breakdown.map(item => {
                const pct = Math.min(100, Math.round((item.available_level / item.required_level) * 100));
                return `
                    <div class="coverage-item">
                        <span>${item.skill}</span>
                        <strong>${pct}%</strong>
                        <div class="match-component-track">
                            <div class="match-component-fill" style="width:${pct}%;"></div>
                        </div>
                    </div>`;
            }).join("");

            // Name the skills the team is still weak in.
            const note = $("[data-team-gap-note]");
            if (note) {
                const weak = breakdown
                    .filter(i => i.status !== "Covered")
                    .map(i => i.skill);
                note.textContent = weak.length
                    ? `The current team has weaker coverage in ` +
                      `${weak.join(", ")}. ` +
                      `Finding a teammate with these skills could improve ` +
                      `the team's overall coverage.`
                    : `The team covers every skill this project needs.`;
            }

            const covered = breakdown.filter(i => i.status === "Covered").length;
            const total = breakdown.length;
            const pct = Math.round((covered / total) * 100);
            const number = $("[data-team-coverage]");
            if (number) number.textContent = `${pct}%`;
            const bar = $(".team-coverage-fill");
            if (bar) bar.style.width = `${pct}%`;
        }
    }
}

/* ------------------------------------------------------------
   Project details
   ------------------------------------------------------------ */

async function renderProjectDetails() {
    const skillsBox = $("[data-detail-skills]");
    const gapBox = $("[data-detail-gaps]");
    const applyBtn = $("[data-apply]");
    if (!skillsBox && !gapBox && !applyBtn) return;

    const projectId = await resolveProjectId();
    if (!projectId) {
        if (skillsBox) skillsBox.innerHTML = "<p class='muted-text'>No project selected.</p>";
        return;
    }
    const { ok, data } = await api(`/projects/${projectId}`);
    if (!ok || !data.project) return;
    const p = data.project;

    if (skillsBox) {
        const mine = {};
        ((p.match && p.match.skill_details) || []).forEach(s => { mine[s.skill] = s.student_level; });
        const list = p.required_skills || [];
        skillsBox.innerHTML = list.length ? list.map(s => {
            const level = mine[s.name] || 0;
            const covered = level >= s.required_level;
            const pct = Math.round((s.required_level / 5) * 100);
            return `
                <div class="required-skill">
                    <div>
                        <strong>${s.name}</strong>
                        <span>Required Level: ${s.required_level}/5</span>
                        <span class="muted-text">Your level: ${level}/5 ${covered ? "✓" : ""}</span>
                    </div>
                    <div class="skill-level-bar">
                        <div class="skill-level-fill" style="width:${pct}%;"></div>
                    </div>
                </div>`;
        }).join("") : `<p class="muted-text">No specific skills are required.</p>`;
    }

    if (gapBox) {
        const detail = (p.match && p.match.skill_details) || [];
        const weak = detail.filter(s => s.student_level < s.required_level);
        gapBox.innerHTML = weak.length ? weak.map(s => {
            const pct = Math.round((s.student_level / 5) * 100);
            return `
                <div class="skill-gap-detail">
                    <div class="gap-detail-flower">🌱</div>
                    <div>
                        <h3>${s.skill}</h3>
                        <p>Your current level: ${s.student_level}/5</p>
                        <div class="skill-level-bar">
                            <div class="skill-level-fill" style="width:${pct}%;"></div>
                        </div>
                    </div>
                </div>`;
        }).join("") : `<div class="empty-state"><p>You already meet every required level for this project. 🌿</p></div>`;
    }

    if (applyBtn) {
        applyBtn.dataset.applyId = p.id;
        if (p.application) {
            applyBtn.disabled = true;
            applyBtn.textContent = p.application.status === "Accepted" ? "Accepted ✓" : "Applied ✓";
            applyBtn.classList.add("applied");
        }
    }
}

/** Applying to a project (used on both the list and the details page). */
async function applyToProject(projectId, button) {
    if (!button || button.disabled) return;
    const messageBox = $("#applyMessage");
    const message = (messageBox && messageBox.value.trim())
        ? messageBox.value.trim()
        : "Excited to contribute to this academic project!";

    button.disabled = true;
    button.textContent = "Applying... ⏳";

    const { ok, data } = await api(`/projects/${projectId}/apply`, {
        method: "POST",
        body: JSON.stringify({ message })
    });

    if (ok && data.success) {
        toast(`Application submitted! Match score: ${Math.round(data.match_score || 0)}% 🌿`);
        button.textContent = "Applied ✓";
        button.classList.add("applied");
    } else {
        toast(data.message || "Could not apply to this project.");
        button.disabled = false;
        button.textContent = "Apply ✿";
    }
}

/* ------------------------------------------------------------
   Faculty console
   ------------------------------------------------------------ */

async function renderFacultyConsole() {
    const isFacultyPage = document.body.dataset.page === "faculty" ||
        $("#facultyApplicationsList") ||
        $("#facultyCertificatesList") ||
        $("#facultyProjectsList") ||
        $("#facultyProjectForm") ||
        $("#facultyOverviewApplicationsList") ||
        $("#facultyOverviewCertificatesList") ||
        $("[data-faculty-stat]");
    if (!isFacultyPage) return;

    const { ok, status, data } = await api("/faculty/overview");
    // The payload is returned at the top level by some builds and nested
    // under "overview" by others.
    const o = (data && (data.overview || data)) || {};
    if (!ok || !o || !o.faculty) {
        if (status === 401) {
            window.location.href = "login.html";
            return;
        }
        if (status === 403) {
            toast("Faculty or Admin access required.");
            setTimeout(() => { window.location.href = "dashboard.html"; }, 1200);
            return;
        }
        const container = $("#facultyApplicationsList") || $("#facultyProjectsList") || $("#facultyCertificatesList") || $(".app-main");
        if (container) emptyState(container, "Sign in with a faculty account to open the console.");
        return;
    }

    const nameEl = $("[data-faculty-name]");
    if (nameEl) nameEl.textContent = (o.faculty.name || "Guide").replace(/^Dr\.?\s+/, "");

    const statMap = {
        projects: (o.stats && o.stats.projects) || 0,
        applications: (o.stats && o.stats.applications) || 0,
        pending_applications: (o.stats && o.stats.pending_applications) || 0
    };
    $$("[data-faculty-stat]").forEach(el => {
        const key = el.dataset.facultyStat;
        if (statMap[key] !== undefined) {
            el.textContent = String(statMap[key]).padStart(2, "0");
        }
    });

    const badge = $("#facultyPendingBadge");
    if (badge) {
        const pending = ((o.stats && o.stats.pending_applications) || 0) + ((o.stats && o.stats.pending_certificates) || 0);
        badge.textContent = `${pending} AWAITING REVIEW`;
        badge.style.display = pending > 0 ? "" : "none";
    }

    // Applications module
    const apps = $("#facultyApplicationsList");
    if (apps) {
        const allApplications = o.applications || [];
        const filterSelect = $("#facultyStatusFilter");

        const renderApps = (statusFilter) => {
            const list = (!statusFilter || statusFilter === "all")
                ? allApplications
                : allApplications.filter(a => a.status === statusFilter);

            if (!list.length) {
                emptyState(apps, statusFilter && statusFilter !== "all"
                    ? `No ${statusFilter.toLowerCase()} applications found.`
                    : "No applications have been submitted yet.");
                return;
            }

            apps.innerHTML = list.map(a => `
                <article class="garden-card application-card">
                    <div class="application-card-top">
                        <div>
                            <span class="application-project-status open">${escapeHtml(a.domain || "Project")}</span>
                            <h3>${escapeHtml(a.student_name)}</h3>
                            <p>${escapeHtml(a.department || "")} · ${escapeHtml(a.year || "")} — applied to <strong>${escapeHtml(a.project_title)}</strong></p>
                        </div>
                        <div class="application-match">
                            <small>MATCH</small>
                            <strong>${Math.round(a.match_score || 0)}%</strong>
                        </div>
                    </div>
                    ${a.message ? `<p class="muted-text" style="font-size:0.85rem;">"${escapeHtml(a.message)}"</p>` : ""}
                    <div class="application-status-row">
                        <div class="application-status ${a.status === "Accepted" ? "accepted" : a.status === "Rejected" ? "rejected" : "pending"}">
                            <span class="status-dot"></span>${escapeHtml(a.status)}
                        </div>
                        <div class="application-actions">
                            <button class="garden-button" type="button"
                                    data-faculty-review="${a.id}" data-status="Accepted">Accept</button>
                            <button class="garden-button secondary" type="button"
                                    data-faculty-review="${a.id}" data-status="Rejected">Reject</button>
                        </div>
                    </div>
                </article>`).join("");

            $$("[data-faculty-review]", apps).forEach(btn => {
                btn.onclick = async () => {
                    btn.disabled = true;
                    const { ok, data } = await api(`/faculty/applications/${btn.dataset.facultyReview}/status`, {
                        method: "PUT",
                        body: JSON.stringify({ status: btn.dataset.status })
                    });
                    if (ok && data.success) {
                        toast(`Application ${btn.dataset.status.toLowerCase()} ✓`);
                        renderFacultyConsole();
                    } else {
                        toast(data.message || "Could not update the application.");
                        btn.disabled = false;
                    }
                };
            });
        };

        if (filterSelect && !filterSelect.dataset.wired) {
            filterSelect.dataset.wired = "true";
            filterSelect.addEventListener("change", (e) => {
                renderApps(e.target.value);
            });
        }

        renderApps(filterSelect ? filterSelect.value : "all");
    }

    // Certificates module
    const certs = $("#facultyCertificatesList");
    if (certs) {
        const pending = o.pending_certificates || [];
        if (!pending.length) {
            emptyState(certs, "No certificates are waiting for verification.");
        } else {
            certs.innerHTML = pending.map(c => `
                <article class="garden-card application-card">
                    <div class="application-card-top">
                        <div>
                            <span class="application-project-status open">${escapeHtml(c.category || "Skill")}</span>
                            <h3>${escapeHtml(c.skill_name)}</h3>
                            <p>${escapeHtml(c.student_name)} — ${escapeHtml(c.student_email)}</p>
                        </div>
                        <div class="application-match">
                            <small>LEVEL</small>
                            <strong>${c.proficiency_level}/5</strong>
                        </div>
                    </div>
                    <div class="application-meta">
                        <span>📄 ${escapeHtml(c.certificate_original_name || "Certificate")}</span>
                    </div>
                    <div class="application-status-row">
                        <div class="application-status pending">
                            <span class="status-dot"></span>Awaiting verification
                        </div>
                        <div class="application-actions">
                            ${c.certificate_filename
                                ? `<a class="garden-button secondary" target="_blank"
                                      href="${API}/certificates/${encodeURIComponent(c.certificate_filename)}">View</a>` : ""}
                            <button class="garden-button" type="button"
                                    data-faculty-verify="${c.student_id}:${c.skill_id}"
                                    data-status="Verified">Verify</button>
                            <button class="garden-button secondary" type="button"
                                    data-faculty-verify="${c.student_id}:${c.skill_id}"
                                    data-status="Rejected">Reject</button>
                        </div>
                    </div>
                </article>`).join("");

            $$("[data-faculty-verify]", certs).forEach(btn => {
                btn.onclick = async () => {
                    btn.disabled = true;
                    const [studentId, skillId] = btn.dataset.facultyVerify.split(":");
                    const { ok, data } = await api(`/faculty/certificates/${studentId}/${skillId}`, {
                        method: "PUT",
                        body: JSON.stringify({ status: btn.dataset.status })
                    });
                    if (ok && data.success) {
                        toast(`Certificate ${btn.dataset.status.toLowerCase()} ✓`);
                        renderFacultyConsole();
                    } else {
                        toast(data.message || "Could not update the certificate.");
                        btn.disabled = false;
                    }
                };
            });
        }
    }

    // Projects module
    const projects = $("#facultyProjectsList");
    if (projects) {
        const list2 = o.projects || [];
        if (!list2.length) {
            emptyState(projects, "You have not published any projects yet. Click '+ Publish Project' to create one.");
        } else {
            projects.innerHTML = list2.map(p => `
                <article class="garden-card application-card">
                    <div class="application-card-top">
                        <div>
                            <span class="application-project-status ${p.status === "Open" ? "open" : "closed"}">${escapeHtml(p.status)}</span>
                            <h3>${escapeHtml(p.title)}</h3>
                            <p>${escapeHtml(p.domain || "")} · ${escapeHtml(p.required_availability)}</p>
                        </div>
                        <div class="application-match">
                            <small>TEAM</small>
                            <strong>${p.member_count}/${p.team_size}</strong>
                        </div>
                    </div>
                    <div class="application-meta">
                        <span>✉ ${p.application_count} application(s)</span>
                        <span>◷ ${p.pending_count} pending</span>
                    </div>
                    <div class="application-status-row">
                        <div class="application-status ${p.pending_count > 0 ? "pending" : "accepted"}">
                            <span class="status-dot"></span>${p.pending_count > 0 ? "Needs attention" : "On track"}
                        </div>
                        <div class="application-actions">
                            <a href="project-details.html?id=${p.id}" class="garden-button">View</a>
                        </div>
                    </div>
                </article>`).join("");
        }
    }

    // Overview Quick Action Lists (on faculty.html)
    const overviewApps = $("#facultyOverviewApplicationsList");
    if (overviewApps) {
        const pendingApps = (o.applications || []).filter(a => a.status === "Pending");
        if (!pendingApps.length) {
            overviewApps.innerHTML = `<div class="empty-state"><p>No pending applications. All caught up! ✿</p></div>`;
        } else {
            overviewApps.innerHTML = pendingApps.slice(0, 3).map(a => `
                <article class="garden-card application-card">
                    <div class="application-card-top">
                        <div>
                            <span class="application-project-status open">${escapeHtml(a.domain || "Project")}</span>
                            <h3>${escapeHtml(a.student_name)}</h3>
                            <p>${escapeHtml(a.project_title)} · Match ${Math.round(a.match_score || 0)}%</p>
                        </div>
                    </div>
                    <div class="application-status-row">
                        <div class="application-status pending"><span class="status-dot"></span>Pending</div>
                        <div class="application-actions">
                            <a href="faculty-applications.html" class="garden-button">Review →</a>
                        </div>
                    </div>
                </article>`).join("");
        }
    }

    const overviewCerts = $("#facultyOverviewCertificatesList");
    if (overviewCerts) {
        const pendingCerts = o.pending_certificates || [];
        if (!pendingCerts.length) {
            overviewCerts.innerHTML = `<div class="empty-state"><p>No pending certificates to verify. 🌿</p></div>`;
        } else {
            overviewCerts.innerHTML = pendingCerts.slice(0, 3).map(c => `
                <article class="garden-card application-card">
                    <div class="application-card-top">
                        <div>
                            <span class="application-project-status open">${escapeHtml(c.category || "Skill")}</span>
                            <h3>${escapeHtml(c.skill_name)}</h3>
                            <p>${escapeHtml(c.student_name)} (${c.proficiency_level}/5)</p>
                        </div>
                    </div>
                    <div class="application-status-row">
                        <div class="application-status pending"><span class="status-dot"></span>Pending</div>
                        <div class="application-actions">
                            <a href="faculty-certificates.html" class="garden-button">Verify →</a>
                        </div>
                    </div>
                </article>`).join("");
        }
    }
}

/* ------------------------------------------------------------
   Profile editing
   ------------------------------------------------------------ */

async function renderProfileManagement() {
    const skillForm = $("#addSkillForm");
    const interestForm = $("#addInterestForm");
    const expForm = $("#addExperienceForm");
    const availForm = $("#availabilityForm");
    if (!skillForm && !interestForm && !expForm && !availForm) return;

    // Load skills
    refreshSkillPlants();

    // Interests
    const interestBox = $("#profileInterests");
    if (interestBox) {
        const { ok, status, data } = await api("/student/interests");
        if (status === 401) {
            window.location.href = "login.html";
            return;
        }
        renderInterestChips((ok && data.interests) || []);
    }

    // Experiences
    const expBox = $("#profileExperiences");
    if (expBox) {
        const { ok, data } = await api("/student/experiences");
        const list = (ok && data.experiences) || [];
        expBox.innerHTML = list.length ? list.map(e => `
            <div class="growth-item">
                <div class="growth-year">EXPERIENCE</div>
                <div>
                    <h3>${e.title}</h3>
                    <p>Previous work</p>
                    <button class="chip-remove" type="button" data-remove-exp="${e.id}" title="Remove">×</button>
                </div>
            </div>`).join("")
            : `<p class="muted-text">No previous work added yet.</p>`;

        $$("[data-remove-exp]", expBox).forEach(btn => {
            btn.addEventListener("click", async () => {
                btn.disabled = true;
                const { ok, data } = await api(`/student/experiences/${btn.dataset.removeExp}`, { method: "DELETE" });
                if (ok && data.success) {
                    toast("Experience removed.");
                    renderProfileManagement();
                } else {
                    toast(data.message || "Could not remove the experience.");
                    btn.disabled = false;
                }
            });
        });
    }

    // Availability
    const slider = $("#weeklyHoursSlider");
    if (slider) {
        const { ok, data } = await api("/student/settings");
        const hours = (ok && data.settings && data.settings.weekly_hours);
        if (hours !== undefined && hours !== null) {
            slider.value = hours;
            const readout = $("[data-weekly-hours]");
            if (readout) readout.textContent = hours;
            updateCapacityRing(hours);
        }
    }
}

/** Shows the weekly capacity as a ring and a percentage. */
function updateCapacityRing(hours) {
    const value = Number(hours) || 0;
    const percent = Math.min(100, Math.round((value / 40) * 100));

    const ring = $("[data-capacity-ring]");
    if (ring) ring.style.setProperty("--capacity", percent);

    const label = $("[data-capacity-value]");
    if (label) label.textContent = `${percent}%`;
}


/** Renders the interest chips and wires their remove buttons. */
function renderInterestChips(list) {
    const box = $("#profileInterests");
    if (!box) return;

    box.innerHTML = list.length ? list.map(i => `
        <span class="settings-chip selected">
            <span>${escapeHtml(i)}</span>
            <button class="chip-remove" type="button"
                    data-remove-interest="${escapeHtml(i)}" title="Remove">×</button>
        </span>`).join("")
        : `<p class="muted-text">No interests selected yet.</p>`;

    $$("[data-remove-interest]", box).forEach(btn => {
        btn.addEventListener("click", async () => {
            const name = btn.dataset.removeInterest;
            const next = list.filter(i => i !== name);
            btn.disabled = true;
            const { ok, data } = await api("/student/interests", {
                method: "PUT",
                body: JSON.stringify({ interests: next })
            });
            if (ok && data.success) {
                toast("Interest removed.");
                renderInterestChips(next);
            } else {
                toast(data.message || "Could not remove the interest.");
                btn.disabled = false;
            }
        });
    });
}


/** Re-renders the skill garden after a skill is added or removed. */
async function refreshSkillPlants() {
    const plants = $("#skillPlantsContainer");
    if (!plants) return;

    const { ok, data } = await api("/student/skills");
    const skills = (ok && data.student_skills) || [];
    if (!skills.length) {
        plants.innerHTML = `<p class="muted-text">No skills planted yet.</p>`;
        return;
    }

    const flowers = ["✿", "❀", "✾", "❁", "✽"];
    plants.innerHTML = skills.map((sk, i) => {
        const pct = Math.round((sk.proficiency_level / 5) * 100);
        const cert = sk.certificate_status === "Verified"
            ? `<a href="${API}/certificates/${encodeURIComponent(sk.certificate_filename || '')}" target="_blank"
                   class="skill-cert-badge verified">Verified ✓</a>`
            : sk.certificate_status === "Pending"
                ? `<a href="${API}/certificates/${encodeURIComponent(sk.certificate_filename || '')}" target="_blank"
                       class="skill-cert-badge pending">Pending ⏳</a>`
                : `<button type="button" class="skill-cert-badge upload"
                           data-skill-id="${sk.skill_id}" data-skill-name="${escapeHtml(sk.name)}">+ Certificate</button>`;
        return `
            <div class="skill-plant">
                <div class="skill-plant-flower">${flowers[i % flowers.length]}</div>
                <div class="skill-plant-name">${escapeHtml(sk.name)}</div>
                <div class="skill-plant-level">${sk.proficiency_level} / 5 · ${pct}%</div>
                ${cert}
                <button type="button" class="chip-remove skill-remove" title="Remove ${escapeHtml(sk.name)}"
                        data-remove-skill="${sk.skill_id}">×</button>
            </div>`;
    }).join("");

    $$("button.skill-cert-badge.upload", plants).forEach(btn => {
        btn.addEventListener("click", () => {
            const sid = btn.dataset.skillId;
            const sname = btn.dataset.skillName;
            if (typeof openCertModal === "function") {
                openCertModal(sid, sname);
            }
        });
    });

    $$("[data-remove-skill]", plants).forEach(btn => {
        btn.addEventListener("click", async () => {
            const name = btn.title.replace("Remove ", "");
            if (!window.confirm(`Remove ${name} from your profile?`)) return;
            btn.disabled = true;
            const { ok, data } = await api(`/student/skills/${btn.dataset.removeSkill}`, { method: "DELETE" });
            if (ok && data.success) {
                toast(`${name} removed.`);
                refreshSkillPlants();
            } else {
                toast(data.message || "Could not remove the skill.");
                btn.disabled = false;
            }
        });
    });
}


function wireProfileManagement() {
    // Add a skill
    const skillForm = $("#addSkillForm");
    if (skillForm) {
        skillForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const name = $("#newSkillName").value.trim();
            const level = $("#newSkillLevel") ? $("#newSkillLevel").value : 3;
            if (!name) { toast("Please type a skill."); return; }
            const { ok, data } = await api("/student/skills", {
                method: "POST",
                body: JSON.stringify({ skill_name: name, proficiency_level: parseInt(level, 10) })
            });
            if (ok && data.success) {
                $("#newSkillName").value = "";
                toast(`Added ${name} to your skill garden 🌱`);
                refreshSkillPlants();
            } else {
                toast(data.message || "Could not add the skill.");
            }
        });
    }

    // Add an interest
    const interestForm = $("#addInterestForm");
    if (interestForm) {
        interestForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const name = $("#newInterestName").value.trim();
            if (!name) { toast("Please type an interest."); return; }
            const { ok, data } = await api("/student/interests");
            const list = ((ok && data.interests) || []).filter(
                i => i.toLowerCase() !== name.toLowerCase());
            list.push(name);
            const res = await api("/student/interests", {
                method: "PUT",
                body: JSON.stringify({ interests: list })
            });
            if (res.ok && res.data.success) {
                $("#newInterestName").value = "";
                toast("Interest added — your matches have been recalculated 🌿");
                renderInterestChips(list);
            } else {
                toast(res.data.message || "Could not add the interest.");
            }
        });
    }

    // Add an experience
    const expForm = $("#addExperienceForm");
    if (expForm) {
        expForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const title = $("#newExperienceTitle").value.trim();
            if (!title) { toast("Please type what you worked on."); return; }
            const { ok, data } = await api("/student/experiences", {
                method: "POST",
                body: JSON.stringify({ title })
            });
            if (ok && data.success) {
                $("#newExperienceTitle").value = "";
                toast("Experience added 🌿");
                renderProfileManagement();
            } else {
                toast(data.message || "Could not add the experience.");
            }
        });
    }

    // Availability slider
    const availForm = $("#availabilityForm");
    if (availForm) {
        availForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const value = $("#availabilitySelect") ? $("#availabilitySelect").value : null;
            if (!value) return;
            const { ok, data } = await api("/student/profile", {
                method: "PUT",
                body: JSON.stringify({ availability: value })
            });
            if (ok && data.success) {
                toast("Availability updated 🌿");
                window.dispatchEvent(new CustomEvent("skillmatch:refresh-profile"));
            } else {
                toast(data.message || "Could not update availability.");
            }
        });
    }

    // Weekly hours slider
    const slider = $("#weeklyHoursSlider");
    if (slider) {
        const readout = $("[data-weekly-hours]");
        slider.addEventListener("input", () => {
            if (readout) readout.textContent = slider.value;
            updateCapacityRing(slider.value);
        });
        slider.addEventListener("change", async () => {
            const hours = parseInt(slider.value, 10);
            const { ok, data } = await api("/student/settings", {
                method: "PUT",
                body: JSON.stringify({ weekly_hours: hours })
            });
            if (ok && data.success) {
                toast(`Weekly availability set to ${hours} hours 🌿`);
                updateCapacityRing(hours);
            } else {
                toast(data.message || "Could not save your availability.");
            }
        });
    }
}

/* ------------------------------------------------------------
   Settings page
   ------------------------------------------------------------ */

async function renderSettings() {
    const section = $("[data-settings-panel]");
    if (!section) return;

    const { ok, data } = await api("/student/settings");
    if (!ok || !data.settings) return;
    const s = data.settings;

    const set = (key, value) => {
        const field = $(`[data-setting="${key}"]`);
        if (!field || value === undefined || value === null) return;
        if (field.type === "checkbox") field.checked = !!Number(value);
        else field.value = value;
    };

    ["name", "email", "department", "year", "semester", "availability",
     "email_notifications", "match_alerts", "weekly_digest", "profile_visibility",
     "prioritise_skills", "consider_interests", "consider_experience",
     "consider_availability", "application_alerts", "team_alerts", "gap_alerts",
     "weekly_hours"].forEach(k => set(k, s[k]));

    // Update availability display numbers on settings page
    if (s.weekly_hours !== undefined && s.weekly_hours !== null) {
        const availText = $(".availability-number strong");
        if (availText) availText.textContent = s.weekly_hours;
        const capNote = $(".capacity-note strong");
        if (capNote) capNote.textContent = `${Math.max(0, s.weekly_hours - 10)} hours`;
    }

    // Interest chips
    const chips = $$("[data-interest-chip]");
    if (chips.length) {
        const { ok: ok2, data: d2 } = await api("/student/interests");
        const stored = ((ok2 && d2.interests) || []).map(i => i.toLowerCase());
        chips.forEach(chip => {
            const label = chip.parentElement.querySelector("span");
            const name = label ? label.textContent.trim().toLowerCase() : "";
            const active = stored.includes(name);
            chip.checked = active;
            chip.parentElement.classList.toggle("selected", active);
            chip.addEventListener("change", () => saveInterestChips(true));
        });
    }
}

async function saveInterestChips(notify = true) {
    const chips = $$("[data-interest-chip]");
    const interests = chips
        .filter(c => c.checked)
        .map(c => {
            const label = c.parentElement.querySelector("span");
            return label ? label.textContent.trim() : "";
        })
        .filter(Boolean);

    const { ok, data } = await api("/student/interests", {
        method: "PUT",
        body: JSON.stringify({ interests })
    });
    if (ok && data.success && notify) {
        toast("Interests updated — your matches have been recalculated 🌿");
    }
}

function wireSettings() {
    const saveButton = $('[data-garden-action="save-settings"]');
    if (saveButton) {
        saveButton.addEventListener("click", async () => {
            const values = {};
            $$("[data-setting]").forEach(field => {
                values[field.dataset.setting] = field.type === "checkbox"
                    ? (field.checked ? 1 : 0)
                    : field.value;
            });

            const { ok, data } = await api("/student/settings", {
                method: "PUT",
                body: JSON.stringify(values)
            });
            if (ok && data.success) {
                await saveInterestChips(false);
                toast("Settings saved successfully 🌿");
            } else {
                toast(data.message || "Could not save your settings.");
            }
        });
    }

    // Availability slider live readout
    const availSlider = $("#settingsWeeklyHours");
    if (availSlider) {
        const availText = $(".availability-number strong");
        const capNote = $(".capacity-note strong");
        availSlider.addEventListener("input", () => {
            const val = parseInt(availSlider.value, 10) || 0;
            if (availText) availText.textContent = val;
            if (capNote) capNote.textContent = `${Math.max(0, val - 10)} hours`;
        });
    }

    // Change Password Modal & Action
    const cpBtn = $("#changePasswordBtn");
    const cpModal = $("#changePasswordModal");
    const closeCpModal = $("#closeChangePasswordModal");
    const cancelCp = $("#cancelChangePassword");
    const cpForm = $("#changePasswordForm");

    if (cpBtn && cpModal) {
        const openModal = () => cpModal.classList.add("active");
        const closeModal = () => {
            cpModal.classList.remove("active");
            if (cpForm) cpForm.reset();
        };
        cpBtn.addEventListener("click", openModal);
        if (closeCpModal) closeCpModal.addEventListener("click", closeModal);
        if (cancelCp) cancelCp.addEventListener("click", closeModal);
        cpModal.addEventListener("click", (e) => {
            if (e.target === cpModal) closeModal();
        });

        if (cpForm) {
            cpForm.addEventListener("submit", async (e) => {
                e.preventDefault();
                const current_password = $("#currentPassword").value;
                const new_password = $("#newPassword").value;
                const confirm_password = $("#confirmNewPassword").value;

                if (new_password.length < 8) {
                    toast("New password must be at least 8 characters.");
                    return;
                }
                if (new_password !== confirm_password) {
                    toast("New passwords do not match.");
                    return;
                }

                const { ok, data } = await api("/auth/change-password", {
                    method: "POST",
                    body: JSON.stringify({ current_password, new_password, confirm_password })
                });
                if (ok && data.success) {
                    toast("Password changed successfully 🌿");
                    closeModal();
                } else {
                    toast(data.message || "Failed to change password.");
                }
            });
        }
    }

    // Reset Preferences
    const resetBtn = $("#resetPreferencesBtn");
    if (resetBtn) {
        resetBtn.addEventListener("click", async () => {
            if (!confirm("Are you sure you want to reset your matching and notification preferences to defaults?")) return;
            const { ok, data } = await api("/student/reset-settings", { method: "POST" });
            if (ok && data.success) {
                toast("Preferences reset to defaults 🌿");
                renderSettings();
            } else {
                toast(data.message || "Could not reset preferences.");
            }
        });
    }
}

/* ------------------------------------------------------------
   Registration
   ------------------------------------------------------------ */

function wireRegistration() {
    const toggle = $("[data-register-toggle]");
    const form = $("#registerForm");
    const login = $("#loginForm");
    if (!form) return;

    // On the standalone registration page there is no toggle: the form is
    // simply on screen, so only the submit handler is wired up.
    if (toggle) toggle.addEventListener("click", () => {
        const showing = form.style.display !== "none";
        form.style.display = showing ? "none" : "";
        if (login) login.style.display = showing ? "" : "none";
        const heading = $("[data-auth-heading]");
        if (heading) heading.innerHTML = showing ? "Enter your <em>garden.</em>" : "Plant your <em>first seed.</em>";
        toggle.textContent = showing ? "Create your profile" : "Back to sign in";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const name = $("#registerName").value.trim();
        const email = $("#registerEmail").value.trim();
        const password = $("#registerPassword").value;
        if (!name || !email || !password) {
            toast("Please fill in all required fields.");
            return;
        }
        if (password.length < 6) {
            toast("Password must be at least 6 characters.");
            return;
        }

        const { ok, data } = await api("/auth/register", {
            method: "POST",
            body: JSON.stringify({
                name, email, password,
                role: "student",
                // Leave a blank field to the server default rather
                // than sending an empty string.
                department: ($("#registerDepartment") && $("#registerDepartment").value.trim()) || undefined,
                year: ($("#registerYear") && $("#registerYear").value.trim()) || undefined
            })
        });
        if (ok && data.success) {
            sessionStorage.setItem("user", JSON.stringify(data.user));
            toast(`Welcome to the garden, ${name}! 🌿`);
            setTimeout(() => { window.location.href = "profile.html"; }, 800);
        } else {
            toast(data.message || "Could not create the account.");
        }
    });
}

/* ------------------------------------------------------------
   Project picker
   ------------------------------------------------------------ */

async function wireProjectPicker() {
    const picker = $("[data-project-picker]");
    if (!picker) return;

    const { ok, data } = await api("/projects");
    const projects = (ok && data.projects) || [];
    if (!projects.length) {
        picker.innerHTML = "<option value=''>No projects available</option>";
        return;
    }

    const current = await resolveProjectId();
    picker.innerHTML = "";
    projects.forEach(p => {
        const option = document.createElement("option");
        option.value = p.id;
        option.textContent = p.title;
        if (String(p.id) === String(current)) option.selected = true;
        picker.appendChild(option);
    });

    picker.addEventListener("change", () => {
        const url = new URL(window.location.href);
        url.searchParams.set("id", picker.value);
        window.location.href = url.toString();
    });
}

/* ------------------------------------------------------------
   Faculty: publish a project
   ------------------------------------------------------------ */

function wireFacultyForm() {
    const form = $("#facultyProjectForm");
    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const skillsRaw = $("#facultyProjectSkills").value.trim();
        const skills = skillsRaw ? skillsRaw.split(",").map(part => {
            const [name, level] = part.split(":").map(s => s.trim());
            return { name, required_level: parseInt(level, 10) || 3 };
        }).filter(s => s.name) : [];

        const payload = {
            title: $("#facultyProjectTitle").value.trim(),
            description: $("#facultyProjectDescription").value.trim(),
            domain: $("#facultyProjectDomain").value.trim() || "General",
            required_availability: $("#facultyProjectAvailability").value,
            team_size: parseInt($("#facultyProjectTeamSize").value, 10) || 4,
            skills
        };
        if (!payload.title || !payload.description) {
            toast("Title and description are required.");
            return;
        }

        const { ok, data } = await api("/projects", {
            method: "POST",
            body: JSON.stringify(payload)
        });
        if (ok && data.success) {
            toast("Project published successfully ✿");
            form.reset();
            renderFacultyConsole();
            if (window.location.pathname.includes("faculty-new-project")) {
                setTimeout(() => {
                    window.location.href = "faculty-projects.html";
                }, 800);
            }
        } else {
            toast(data.message || "Could not publish the project.");
        }
    });
}

/* ------------------------------------------------------------
   Apply buttons (list + details)
   ------------------------------------------------------------ */

function wireApplyButtons() {
    document.addEventListener("click", (event) => {
        const button = event.target.closest("[data-apply]");
        if (!button) return;
        const id = button.dataset.applyId || currentProjectId();
        applyToProject(id, button);
    });
}

/* ------------------------------------------------------------
   Botanical AI Chatbot & Advisor
   ------------------------------------------------------------ */

function formatChatMarkdown(raw) {
    if (!raw) return "";
    let s = escapeHtml(raw);
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>");
    s = s.replace(/`([^`]+)`/g, "<code style='background:rgba(198,161,91,0.18); padding:1px 5px; border-radius:4px; font-size:0.9em; font-family:monospace;'>$1</code>");
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (match, txt, url) => {
        return `<a href="${safeUrl(url)}">${txt}</a>`;
    });
    const lines = s.split("\n");
    let html = "";
    let inList = false;
    for (let line of lines) {
        let trimmed = line.trim();
        if (trimmed.startsWith("• ") || trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
            if (!inList) { html += "<ul>"; inList = true; }
            html += `<li>${trimmed.substring(2)}</li>`;
        } else {
            if (inList) { html += "</ul>"; inList = false; }
            if (trimmed) {
                html += `<p>${line}</p>`;
            }
        }
    }
    if (inList) html += "</ul>";
    return html;
}

function mountBotanicalChatbot() {
    const loc = window.location.pathname.toLowerCase();
    if (loc.endsWith("login.html") || loc.endsWith("register.html") || loc.endsWith("index.html") || loc === "/" || loc.endsWith("/")) {
        return;
    }
    if ($("#botanicalChatLauncher")) return;

    // 1. Launcher button
    const launcher = document.createElement("button");
    launcher.type = "button";
    launcher.className = "botanical-chat-launcher";
    launcher.id = "botanicalChatLauncher";
    launcher.setAttribute("aria-label", "Ask SkillMatch AI Advisor");
    launcher.title = "Ask SkillMatch AI Advisor";
    launcher.innerHTML = `
        <span class="botanical-chat-pulse" title="AI Advisor Online"></span>
        <span style="font-family:'Cormorant Garamond', Georgia, serif; font-size: 28px; line-height: 1;">❧</span>
    `;

    // 2. Chat window
    const win = document.createElement("aside");
    win.className = "botanical-chat-window";
    win.id = "botanicalChatWindow";
    win.setAttribute("aria-label", "SkillMatch AI Chat Window");
    win.innerHTML = `
        <div class="botanical-chat-header">
            <div class="botanical-chat-header-info">
                <span class="botanical-chat-header-icon">❧</span>
                <div>
                    <div class="botanical-chat-header-title">SkillMatch AI Advisor</div>
                    <div class="botanical-chat-header-sub">Online · Botanical Academic Guide</div>
                </div>
            </div>
            <button type="button" class="botanical-chat-close-btn" id="botanicalChatClose" aria-label="Close Chat Window">×</button>
        </div>
        <div class="botanical-chat-messages" id="botanicalChatMessages"></div>
        <div class="botanical-chat-suggestions" id="botanicalChatSuggestions"></div>
        <form class="botanical-chat-form" id="botanicalChatForm">
            <input type="text" class="botanical-chat-input" id="botanicalChatInput" placeholder="Ask about matching, skills, or projects..." autocomplete="off">
            <button type="submit" class="botanical-chat-send" id="botanicalChatSend" title="Send message">✿</button>
        </form>
    `;

    document.body.appendChild(launcher);
    document.body.appendChild(win);

    const messagesEl = $("#botanicalChatMessages");
    const suggestionsEl = $("#botanicalChatSuggestions");
    const formEl = $("#botanicalChatForm");
    const inputEl = $("#botanicalChatInput");
    const closeBtn = $("#botanicalChatClose");

    let history = [];
    try {
        const stored = sessionStorage.getItem("skillmatch_chat_history");
        if (stored) history = JSON.parse(stored);
    } catch (e) {
        history = [];
    }

    const saveHistory = () => {
        try {
            sessionStorage.setItem("skillmatch_chat_history", JSON.stringify(history.slice(-20)));
        } catch (e) {}
    };

    const renderSuggestions = (list) => {
        if (!list || !list.length) {
            suggestionsEl.innerHTML = "";
            return;
        }
        suggestionsEl.innerHTML = list.map(s => `
            <button type="button" class="botanical-chat-chip" data-chat-suggestion="${escapeHtml(s)}">${escapeHtml(s)}</button>
        `).join("");

        $$("[data-chat-suggestion]", suggestionsEl).forEach(btn => {
            btn.onclick = () => {
                const text = btn.dataset.chatSuggestion;
                sendUserMessage(text);
            };
        });
    };

    const appendUserBubble = (text) => {
        const div = document.createElement("div");
        div.className = "botanical-chat-msg botanical-chat-msg-user";
        div.textContent = text;
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    };

    const appendBotBubble = (markdownText) => {
        const div = document.createElement("div");
        div.className = "botanical-chat-msg botanical-chat-msg-bot";
        div.innerHTML = formatChatMarkdown(markdownText);
        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    };

    let typingEl = null;
    const showTyping = () => {
        if (typingEl) return;
        typingEl = document.createElement("div");
        typingEl.className = "botanical-chat-typing";
        typingEl.innerHTML = "<span></span><span></span><span></span>";
        messagesEl.appendChild(typingEl);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    };

    const hideTyping = () => {
        if (typingEl) {
            typingEl.remove();
            typingEl = null;
        }
    };

    const sendUserMessage = async (text) => {
        if (!text || !text.trim()) return;
        text = text.trim();
        appendUserBubble(text);
        inputEl.value = "";
        showTyping();

        history.push({ role: "user", content: text });
        saveHistory();

        const { ok, status, data } = await api("/chat", {
            method: "POST",
            body: JSON.stringify({ message: text, history })
        });

        hideTyping();

        if (status === 401) {
            appendBotBubble("Your session has expired. Please [log in again](login.html) to continue chatting with the AI Advisor.");
            return;
        }

        if (ok && data.success) {
            appendBotBubble(data.reply);
            history.push({ role: "assistant", content: data.reply });
            saveHistory();
            renderSuggestions(data.suggestions);
        } else {
            appendBotBubble((data && data.message) || "I apologize, but I could not process your query at this moment. Please try again.");
        }
    };

    const initChatStatus = async () => {
        if (history.length) {
            messagesEl.innerHTML = "";
            history.forEach(item => {
                if (item.role === "user") appendUserBubble(item.content);
                else appendBotBubble(item.content);
            });
            renderSuggestions([
                "🌿 Top Project Matches",
                "📊 My Skill Gaps",
                "📈 Profile Completeness",
                "📜 Certificate Help"
            ]);
            return;
        }

        const { ok, data } = await api("/chat/status");
        if (ok && data.success) {
            appendBotBubble(data.greeting);
            renderSuggestions(data.suggestions);
        } else {
            appendBotBubble("Good day! ❧ I am your **SkillMatch AI Advisor**. Please log in with a student or faculty account to unlock personalized recommendations.");
            renderSuggestions(["Sign In", "Register"]);
        }
    };

    launcher.onclick = () => {
        const isOpen = win.classList.toggle("is-open");
        if (isOpen) {
            inputEl.focus();
            if (!messagesEl.children.length) {
                initChatStatus();
            }
        }
    };

    closeBtn.onclick = () => {
        win.classList.remove("is-open");
    };

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && win.classList.contains("is-open")) {
            win.classList.remove("is-open");
        }
    });

    formEl.onsubmit = (e) => {
        e.preventDefault();
        sendUserMessage(inputEl.value);
    };

    initChatStatus();
}

/* ------------------------------------------------------------
   Boot
   ------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
    wireApplyButtons();
    wireProfileManagement();
    wireSettings();
    wireRegistration();
    wireFacultyForm();

    // The faculty console has its own panels; the garden pages belong to
    // students, so each page only loads what it needs.
    if (document.body.dataset.page === "faculty") {
        wireProjectPicker();
        renderFacultyConsole();
        mountBotanicalChatbot();
        return;
    }

    wireProjectPicker();
    renderProfileManagement();
    renderSettings();
    renderNotifications();
    renderFacultyConsole();
    mountBotanicalChatbot();

    // Page specific panels
    if ($(".project-match-card") && $(".dashboard-grid")) renderDashboard();
    if ($(".gap-list")) renderGaps();
    if ($(".team-members-grid") || $(".recommended-teammates-grid")) renderTeam();
    if ($("[data-detail-skills]") || $("[data-apply]")) renderProjectDetails();
    if ($("#applicationsListItems")) renderApplications();
});
