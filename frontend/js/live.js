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
                .map(s => `<span>${escapeHtml(s.skill)}</span>`).join("");
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
        if (desc) desc.textContent = "Add your skills and interests in My Growth to get matched with projects as soon as faculty publish them!";

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
                        <div class="skill-plant-name">${escapeHtml(sk.name)}</div>
                        <div class="skill-plant-level">${sk.proficiency_level} / 5 · ${pct}% · ${stage}</div>
                        ${cert}
                    </div>`;
            }).join("");
        }
    }

    // Garden team
    const team = $(".team-branch");
    const dashCov = $("[data-dashboard-team-coverage]");
    if (team || dashCov) {
        const pid = (d.top_match && d.top_match.project_id) || await resolveProjectId();
        if (!pid) {
            if (team) team.innerHTML = `<p class="muted-text">Explore projects to join a garden team.</p>`;
            if (dashCov) dashCov.textContent = "0%";
        } else {
            const { ok, data } = await api(`/projects/${pid}`);
            const members = (ok && data.project && data.project.team_members) || [];
            if (team) {
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
            if (dashCov) {
                const { ok: covOk, data: covData } = await api(`/matching/projects/${pid}/gaps`);
                const gapsPayload = covOk && (covData.gaps || covData.data);
                const breakdown = (gapsPayload && gapsPayload.skill_breakdown) || [];
                const covered = breakdown.filter(i => i.status === "Covered").length;
                const total = breakdown.length;
                const covPct = total ? Math.round((covered / total) * 100) : 0;
                dashCov.textContent = `${covPct}%`;
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
                        <h3>${escapeHtml(ev.title)}</h3>
                        <p>${escapeHtml(ev.body)}</p>
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
    const closedContainer = $("#closedApplicationsList");
    const totalEl = $("#totalApplicationsCount");
    const pendingEl = $("#pendingApplicationsCount");
    const acceptedEl = $("#acceptedApplicationsCount");
    const closedEl = $("#closedApplicationsCount");
    const activeBadge = $("#activeApplicationsBadge");
    const closedBadge = $("#closedApplicationsBadge");

    const flowStep1 = $("#flowStep1");
    const flowStep2 = $("#flowStep2");
    const flowStep3 = $("#flowStep3");
    const flowStep4 = $("#flowStep4");
    const flowLine1 = $("#flowLine1");
    const flowLine2 = $("#flowLine2");
    const flowLine3 = $("#flowLine3");

    if (!container && !totalEl) return;

    const { ok, status, data } = await api("/applications");

    if (!ok || !data || !Array.isArray(data.applications)) {
        if (totalEl) totalEl.textContent = "00";
        if (pendingEl) pendingEl.textContent = "00";
        if (acceptedEl) acceptedEl.textContent = "00";
        if (closedEl) closedEl.textContent = "00";
        if (activeBadge) activeBadge.textContent = "0 ACTIVE";
        if (closedBadge) closedBadge.textContent = "0 CLOSED";

        if (container) {
            container.innerHTML = `
                <div class="garden-card empty-state" id="applicationsEmptyState" style="padding: 40px 20px; text-align: center; border-radius: 14px;">
                    <div style="font-size: 36px; margin-bottom: 12px;">🌱</div>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 24px; color: var(--olive-deep); font-weight: 600;">
                        ${status === 401 ? "Sign in to see your applications." : "No active applications yet."}
                    </h3>
                    <p style="color: var(--muted); margin: 8px auto 18px; font-size: 14px; max-width: 480px; line-height: 1.6;">
                        ${status === 401 ? "Log in as a student to track your submitted project applications in real time." : "You have not applied to any project beds yet. Browse the open projects in bloom, review required skills, and apply to begin your project journey."}
                    </p>
                    <a href="${status === 401 ? 'login.html' : 'projects.html'}" class="garden-button">${status === 401 ? 'Sign In ✿' : 'Explore Projects in Bloom 🌿'}</a>
                </div>`;
        }
        if (closedContainer) {
            closedContainer.innerHTML = `
                <div class="garden-card empty-state" id="closedEmptyState" style="padding: 36px 20px; text-align: center; border-radius: 14px;">
                    <div style="font-size: 32px; margin-bottom: 10px;">🍂</div>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 22px; color: var(--olive-deep); font-weight: 600;">
                        No previous or closed applications.
                    </h3>
                    <p style="color: var(--muted); margin: 6px auto 0; font-size: 14px; max-width: 460px; line-height: 1.5;">
                        Completed projects, past reviews, or archived applications will appear here.
                    </p>
                </div>`;
        }
        return;
    }

    const apps = data.applications;
    const total = apps.length;
    const pendingApps = apps.filter(a => (a.status || "").toLowerCase() === "pending");
    const acceptedApps = apps.filter(a => (a.status || "").toLowerCase() === "accepted");
    const closedApps = apps.filter(a => (a.status || "").toLowerCase() === "rejected" || (a.status || "").toLowerCase() === "closed");
    const activeApps = apps.filter(a => (a.status || "").toLowerCase() !== "rejected" && (a.status || "").toLowerCase() !== "closed");

    if (totalEl) totalEl.textContent = String(total).padStart(2, "0");
    if (pendingEl) pendingEl.textContent = String(pendingApps.length).padStart(2, "0");
    if (acceptedEl) acceptedEl.textContent = String(acceptedApps.length).padStart(2, "0");
    if (closedEl) closedEl.textContent = String(closedApps.length).padStart(2, "0");
    if (activeBadge) activeBadge.textContent = `${activeApps.length} ACTIVE`;
    if (closedBadge) closedBadge.textContent = `${closedApps.length} CLOSED`;

    // Dynamic journey flow progression based on real user actions
    const hasApplied = total > 0;
    const hasReview = pendingApps.length > 0 || acceptedApps.length > 0 || closedApps.length > 0;
    const hasAccepted = acceptedApps.length > 0;

    if (flowStep1) flowStep1.classList.toggle("active", true);
    if (flowLine1) flowLine1.classList.toggle("active", hasApplied);
    if (flowStep2) flowStep2.classList.toggle("active", hasApplied);
    if (flowLine2) flowLine2.classList.toggle("active", hasApplied && hasReview);
    if (flowStep3) flowStep3.classList.toggle("active", hasReview);
    if (flowLine3) flowLine3.classList.toggle("active", hasAccepted);
    if (flowStep4) flowStep4.classList.toggle("active", hasAccepted);

    // Active applications
    if (container) {
        if (!activeApps.length) {
            container.innerHTML = `
                <div class="garden-card empty-state" id="applicationsEmptyState" style="padding: 40px 20px; text-align: center; border-radius: 14px;">
                    <div style="font-size: 36px; margin-bottom: 12px;">🌱</div>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 24px; color: var(--olive-deep); font-weight: 600;">
                        No active applications yet.
                    </h3>
                    <p style="color: var(--muted); margin: 8px auto 18px; font-size: 14px; max-width: 480px; line-height: 1.6;">
                        You have not applied to any project beds yet. Browse the open projects in bloom, review required skills, and apply to begin your project journey.
                    </p>
                    <a href="projects.html" class="garden-button">Explore Projects in Bloom 🌿</a>
                </div>`;
        } else {
            container.innerHTML = activeApps.map(app => {
                const isAccepted = (app.status || "").toLowerCase() === "accepted";
                const cls = isAccepted ? "accepted" : "pending";
                const label = isAccepted ? "Accepted ✓" : "Pending Review";
                const applied = app.applied_at ? new Date(app.applied_at).toLocaleDateString() : "—";
                const actionBtn = isAccepted
                    ? `<a href="team.html?id=${app.project_id}" class="garden-button">Go to Team Bed 🌳</a>`
                    : `<button class="garden-button secondary" type="button"
                               data-withdraw-app="${app.id}"
                               data-project-title="${escapeHtml(app.project_title)}">Withdraw</button>`;

                return `
                    <article class="garden-card application-card ${isAccepted ? 'accepted-application' : ''}">
                        <div class="application-card-top">
                            <div>
                                <span class="application-project-status ${isAccepted ? 'accepted' : 'open'}">${escapeHtml(app.domain || "Open Project")}</span>
                                <h3>${escapeHtml(app.project_title)}</h3>
                                <p>${escapeHtml(app.message || "Application submitted for academic project matching.")}</p>
                            </div>
                            <div class="application-match">
                                <small>MATCH</small>
                                <strong>${Math.round(app.match_score || 0)}%</strong>
                            </div>
                        </div>
                        <div class="application-meta">
                            <span>📅 Applied ${applied}</span>
                            <span>👥 ${escapeHtml(String(app.team_size || 4))} students</span>
                            <span>✿ ${escapeHtml(app.status)}</span>
                        </div>
                        <div class="application-status-row">
                            <div class="application-status ${cls}">
                                <span class="status-dot"></span>${label}
                            </div>
                            <div class="application-actions">
                                <a href="project-details.html?id=${app.project_id}" class="garden-button secondary">View Project</a>
                                ${actionBtn}
                            </div>
                        </div>
                    </article>`;
            }).join("");

            // Wire withdraw buttons
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
    }

    // Closed applications
    if (closedContainer) {
        if (!closedApps.length) {
            closedContainer.innerHTML = `
                <div class="garden-card empty-state" id="closedEmptyState" style="padding: 36px 20px; text-align: center; border-radius: 14px;">
                    <div style="font-size: 32px; margin-bottom: 10px;">🍂</div>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 22px; color: var(--olive-deep); font-weight: 600;">
                        No previous or closed applications.
                    </h3>
                    <p style="color: var(--muted); margin: 6px auto 0; font-size: 14px; max-width: 460px; line-height: 1.5;">
                        Completed projects, past reviews, or archived applications will appear here.
                    </p>
                </div>`;
        } else {
            closedContainer.innerHTML = closedApps.map(app => {
                const applied = app.applied_at ? new Date(app.applied_at).toLocaleDateString() : "—";
                return `
                    <article class="garden-card application-card closed-application">
                        <div class="application-card-top">
                            <div>
                                <span class="application-project-status closed">CLOSED</span>
                                <h3>${escapeHtml(app.project_title)}</h3>
                                <p>${escapeHtml(app.message || "Application concluded.")}</p>
                            </div>
                            <div class="application-match">
                                <small>MATCH</small>
                                <strong>${Math.round(app.match_score || 0)}%</strong>
                            </div>
                        </div>
                        <div class="application-meta">
                            <span>🌿 ${escapeHtml(app.domain || "Project")}</span>
                            <span>👥 ${escapeHtml(String(app.team_size || 4))} students</span>
                            <span>📅 Applied ${applied}</span>
                        </div>
                        <div class="application-status-row">
                            <div class="application-status rejected">
                                <span class="status-dot"></span>Not Selected
                            </div>
                            <div class="application-actions">
                                <a href="projects.html" class="garden-button secondary">Explore Other Projects</a>
                            </div>
                        </div>
                    </article>`;
            }).join("");
        }
    }
}

/* ------------------------------------------------------------
   Notifications
   ------------------------------------------------------------ */

function formatTimeAgo(dateStr) {
    if (!dateStr) return "";
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return String(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);
    if (diffSec < 60) return "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `${diffHour}h ago`;
    const diffDays = Math.floor(diffHour / 24);
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
}

async function renderNotifications() {
    const container = $("#notificationsContainer") || $(".notification-feed") || $(".notification-list");
    const summaryText = $("#unreadNotificationSummary");
    const countEl = $("#unreadNotificationCount");
    const unreadBadge = $("#notificationUnreadBadge") || $("[data-unread-count]");
    const markAllBtn = $("#markAllRead");

    if (!container && !markAllBtn) return;

    const { ok, status, data } = await api("/notifications");

    if (!ok || !data || !Array.isArray(data.notifications)) {
        if (countEl) countEl.textContent = "0 unread notifications";
        if (unreadBadge) unreadBadge.style.display = "none";
        if (container) {
            container.innerHTML = `
                <div class="garden-card empty-state" style="padding: 48px 24px; text-align: center; border-radius: 14px;">
                    <div style="font-size: 38px; margin-bottom: 12px;">♧</div>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 26px; color: var(--olive-deep); font-weight: 600;">
                        ${status === 401 ? "Sign in to view your notifications." : "Your garden is calm and peaceful."}
                    </h3>
                    <p style="color: var(--muted); margin: 8px auto 20px; font-size: 14px; max-width: 480px; line-height: 1.6;">
                        ${status === 401 ? "Log in with your student or faculty account to track your latest garden messages." : "No notifications at the moment. When projects are recommended or applications reviewed, updates will bloom here."}
                    </p>
                    <a href="${status === 401 ? 'login.html' : 'projects.html'}" class="garden-button">${status === 401 ? 'Sign In ✿' : 'Explore Projects 🌿'}</a>
                </div>`;
        }
        return;
    }

    const notifs = data.notifications;

    function refreshUnreadHeader() {
        const remainingUnread = $$(".notification-item:not(.read)", container).length;
        if (countEl) {
            countEl.textContent = `${remainingUnread} unread notification${remainingUnread === 1 ? '' : 's'}`;
        }
        if (summaryText) {
            if (remainingUnread === 0) {
                summaryText.innerHTML = `You have <strong>0 unread notifications</strong>. All caught up! ✿`;
            } else {
                summaryText.innerHTML = `You have <strong id="unreadNotificationCount">${remainingUnread} unread notification${remainingUnread === 1 ? '' : 's'}</strong>. Here's what has been happening.`;
            }
        }
        if (unreadBadge) {
            if (remainingUnread > 0) {
                unreadBadge.textContent = `${remainingUnread} UNREAD`;
                unreadBadge.style.display = "";
            } else {
                unreadBadge.style.display = "none";
            }
        }
    }

    if (!notifs.length) {
        refreshUnreadHeader();
        if (container) {
            container.innerHTML = `
                <div class="garden-card empty-state" id="notificationsEmptyBed" style="padding: 48px 24px; text-align: center; border-radius: 14px;">
                    <div style="font-size: 38px; margin-bottom: 12px;">♧</div>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 26px; color: var(--olive-deep); font-weight: 600;">
                        Your garden is calm and peaceful.
                    </h3>
                    <p style="color: var(--muted); margin: 8px auto 20px; font-size: 14px; max-width: 480px; line-height: 1.6;">
                        No new notifications at the moment. When faculty members review your applications or publish new matching projects, your updates will appear here.
                    </p>
                    <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">
                        <a href="projects.html" class="garden-button">Explore Projects in Bloom 🌿</a>
                        <a href="growth.html" class="garden-button secondary">Tend Your Skills ✿</a>
                    </div>
                </div>`;
        }
        return;
    }

    const typeIcons = {
        project: "🌿",
        application: "✉",
        team: "🌳",
        growth: "🌱",
        skill: "🌾",
        success: "✿",
        warning: "🍂",
        info: "♧"
    };

    if (container) {
        container.innerHTML = notifs.map(n => {
            const isRead = Boolean(n.is_read);
            const icon = typeIcons[n.type] || "♧";
            const timeStr = n.created_at ? formatTimeAgo(n.created_at) : "";

            return `
                <article class="garden-card notification-item ${isRead ? 'read' : 'unread'}"
                         data-notification-id="${n.id}"
                         data-notification="${n.id}"
                         style="cursor: pointer; margin-bottom: 14px;">
                    <div class="notification-icon ${escapeHtml(n.type || 'info')}">
                        ${icon}
                    </div>
                    <div class="notification-content">
                        <div class="notification-top">
                            <h3>${escapeHtml(n.title)}</h3>
                            <span>${timeStr}</span>
                        </div>
                        <p>${escapeHtml(n.message)}</p>
                        ${n.link ? `<a href="${safeUrl(n.link)}" class="notification-link" style="margin-top: 8px; display: inline-block;">View details →</a>` : ''}
                    </div>
                    ${isRead ? '' : '<span class="unread-dot"></span>'}
                </article>`;
        }).join("");

        // Wire click to mark individual notification as read
        $$(".notification-item", container).forEach(item => {
            item.addEventListener("click", async (e) => {
                const notifId = item.dataset.notificationId || item.dataset.notification;
                if (!notifId) return;

                const isAlreadyRead = item.classList.contains("read");
                if (!isAlreadyRead) {
                    item.classList.remove("unread");
                    item.classList.add("read");
                    const dot = $(".unread-dot", item);
                    if (dot) dot.remove();

                    // Persist to backend
                    await api(`/notifications/${notifId}/read`, { method: "POST" });
                    refreshUnreadHeader();
                }
            });
        });

        refreshUnreadHeader();
    }

    // Wire Mark All as Read button
    if (markAllBtn) {
        markAllBtn.onclick = async () => {
            if (markAllBtn.disabled) return;
            markAllBtn.disabled = true;
            markAllBtn.textContent = "Marking... ✓";

            const { ok, data } = await api("/notifications/read-all", { method: "POST" });
            if (ok && data.success) {
                toast("All notifications marked as read.");
                if (container) {
                    $$(".notification-item", container).forEach(item => {
                        item.classList.remove("unread");
                        item.classList.add("read");
                        const dot = $(".unread-dot", item);
                        if (dot) dot.remove();
                    });
                }
                refreshUnreadHeader();
            } else {
                toast(data.message || "Could not mark notifications as read.");
            }
            markAllBtn.disabled = false;
            markAllBtn.textContent = "✓ Mark All as Read";
        };
    }
}

function updateUnreadBadge() {
    const unread = $$(".notification-item:not(.read)").length;
    const badge = $("#notificationUnreadBadge") || $("[data-unread-count]");
    if (badge) {
        badge.textContent = unread > 0 ? `${unread} UNREAD` : "0 UNREAD";
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
        const badge = $("[data-gap-badge]") || $(".gap-overview .botanical-badge");
        if (badge) badge.textContent = "0 areas to grow";
        const statTracked = $('[data-gap-stat="tracked"]');
        if (statTracked) statTracked.textContent = "0";
        const statDeveloping = $('[data-gap-stat="developing"]');
        if (statDeveloping) statDeveloping.textContent = "0";
        const statPriority = $('[data-gap-stat="priority"]');
        if (statPriority) statPriority.textContent = "0";
        const sugTitle = $("[data-gap-suggestion-title]");
        if (sugTitle) sugTitle.textContent = "Tend Your Garden Skills";
        const sugBody = $("[data-gap-suggestion-body]");
        if (sugBody) sugBody.textContent = "No projects are currently published. Head to My Growth to record your technical skills and prepare for future project matches.";
        const sugLink = $("[data-gap-suggestion-link]");
        if (sugLink) {
            sugLink.textContent = "Tend Your Skills (My Growth) →";
            sugLink.href = "growth.html";
        }
        const teamGrid = $(".team-gap-grid");
        if (teamGrid) emptyState(teamGrid, "No project selected.");
        return;
    }

    const { ok, data } = await api(`/matching/projects/${projectId}/gaps`);
    const payload = ok && (data.gaps || data.data);
    if (!ok || !payload) {
        emptyState(list, "Could not load skill gap analysis for this project.");
        return;
    }

    const breakdown = payload.skill_breakdown || [];
    if (!breakdown.length) {
        emptyState(list, "This project does not list any required skills yet.");
        const badge = $("[data-gap-badge]") || $(".gap-overview .botanical-badge");
        if (badge) badge.textContent = "All skills covered ✓";
        const statTracked = $('[data-gap-stat="tracked"]');
        if (statTracked) statTracked.textContent = "0";
        const statDeveloping = $('[data-gap-stat="developing"]');
        if (statDeveloping) statDeveloping.textContent = "0";
        const statPriority = $('[data-gap-stat="priority"]');
        if (statPriority) statPriority.textContent = "0";
        const sugTitle = $("[data-gap-suggestion-title]");
        if (sugTitle) sugTitle.textContent = "No Gaps Identified";
        const sugBody = $("[data-gap-suggestion-body]");
        if (sugBody) sugBody.textContent = "This project does not define specific technical skill requirements.";
        const sugLink = $("[data-gap-suggestion-link]");
        if (sugLink) {
            sugLink.textContent = "Explore Projects →";
            sugLink.href = "projects.html";
        }
        const teamGrid = $(".team-gap-grid");
        if (teamGrid) emptyState(teamGrid, "No team gaps.");
        return;
    }

    list.innerHTML = breakdown.map(item => {
        const req = Math.max(1, item.required_level || 1);
        const avail = Math.max(0, item.available_level || 0);
        const pct = Math.min(100, Math.round((avail / req) * 100));
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
                            <h4>${escapeHtml(item.skill)}</h4>
                            <p>Required level ${req}/5 · team has ${avail}/5</p>
                        </div>
                        <span class="gap-percentage">${pct}%</span>
                    </div>
                    <div class="gap-progress">
                        <div class="gap-progress-track">
                            <div class="gap-progress-fill" style="width:${pct}%;"></div>
                        </div>
                    </div>
                    <div class="gap-item-footer">
                        <span class="botanical-badge ${cls}">${badge}</span>
                    </div>
                </div>
            </article>`;
    }).join("");

    // Summary counts
    const developing = breakdown.filter(i => i.status === "Insufficient");
    const priority = breakdown.filter(i => i.status === "Missing");
    const totalGaps = developing.length + priority.length;

    const badge = $("[data-gap-badge]") || $(".gap-overview .botanical-badge");
    if (badge) {
        badge.textContent = totalGaps === 0 
            ? "All skills covered ✓" 
            : `${totalGaps} area${totalGaps === 1 ? '' : 's'} to grow`;
    }

    const statTracked = $('[data-gap-stat="tracked"]');
    if (statTracked) statTracked.textContent = breakdown.length;
    const statDeveloping = $('[data-gap-stat="developing"]');
    if (statDeveloping) statDeveloping.textContent = developing.length;
    const statPriority = $('[data-gap-stat="priority"]');
    if (statPriority) statPriority.textContent = priority.length;

    // Growth suggestion card
    const sugTitle = $("[data-gap-suggestion-title]");
    const sugBody = $("[data-gap-suggestion-body]");
    const sugLink = $("[data-gap-suggestion-link]");

    const topGap = priority[0] || developing[0];
    if (topGap) {
        if (sugTitle) sugTitle.textContent = `Start with ${topGap.skill}`;
        if (sugBody) {
            sugBody.textContent = `${topGap.skill} is a required competency for this project (requires level ${topGap.required_level}/5, team currently has ${topGap.available_level}/5). Leveling up this skill in My Growth will strengthen your team readiness and compatibility.`;
        }
        if (sugLink) {
            sugLink.textContent = "Tend Your Skills (My Growth) →";
            sugLink.href = "growth.html";
        }
    } else {
        if (sugTitle) sugTitle.textContent = "All Project Skills Covered ✿";
        if (sugBody) {
            sugBody.textContent = "Every skill required for this project is fully covered by the team. Explore other projects to discover more learning opportunities!";
        }
        if (sugLink) {
            sugLink.textContent = "Explore More Projects →";
            sugLink.href = "projects.html";
        }
    }

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
                const req = Math.max(1, item.required_level || 1);
                const avail = Math.max(0, item.available_level || 0);
                const pct = Math.min(100, Math.round((avail / req) * 100));
                return `
                    <article class="team-gap-card garden-card">
                        <div class="team-gap-icon">${item.status === "Missing" ? "🌧" : "🌱"}</div>
                        <div>
                            <h4>${escapeHtml(item.skill)}</h4>
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
        const covNumber = $("[data-team-coverage]") || $(".team-coverage-number");
        if (covNumber) covNumber.textContent = "0%";
        const covBar = $(".team-coverage-fill");
        if (covBar) covBar.style.width = "0%";
        const covSummary = $("[data-team-coverage-summary]") || $(".team-coverage-bar + p");
        if (covSummary) covSummary.textContent = "No team skills recorded yet.";
        const countBadge = $("[data-team-count-badge]") || $(".garden-section-title .botanical-badge");
        if (countBadge) countBadge.textContent = "0 Members";
        const gapNote = $("[data-team-gap-note]");
        if (gapNote) gapNote.textContent = "Team skill requirements and missing areas will appear here when a project is active.";
        const gapList = $("[data-team-gap-list]") || $(".watering-card .gap-list");
        if (gapList) gapList.innerHTML = `<div class="empty-state"><p>No project gaps identified yet.</p></div>`;
        const tree = $(".team-tree");
        if (tree) {
            tree.innerHTML = `
                <div class="tree-trunk"></div>
                <div class="tree-branch-line"></div>
                <div class="team-center">
                    <strong>Project<br>Team</strong>
                    <small>PROJECT</small>
                </div>
                <div class="member-node member-one">
                    <div class="member-avatar">?</div>
                    <strong>Open</strong>
                    <small>Awaiting team</small>
                </div>
            `;
        }
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
        const countBadge = $("[data-team-count-badge]") || $(".garden-section-title .botanical-badge");
        if (countBadge && project) {
            countBadge.textContent = `${members.length} Member${members.length === 1 ? '' : 's'}`;
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
        const covNumber = $("[data-team-coverage]") || $(".team-coverage-number");
        const covBar = $(".team-coverage-fill");
        const covSummary = $("[data-team-coverage-summary]") || $(".team-coverage-bar + p");
        const gapList = $("[data-team-gap-list]") || $(".watering-card .gap-list");
        const note = $("[data-team-gap-note]");

        if (!breakdown.length) {
            coverage.innerHTML = `<div class="empty-state"><p>No skill requirements listed for this project.</p></div>`;
            if (covNumber) covNumber.textContent = "0%";
            if (covBar) covBar.style.width = "0%";
            if (covSummary) covSummary.textContent = "No skill requirements defined yet.";
            if (note) note.textContent = "No skills required for this project.";
            if (gapList) gapList.innerHTML = `<div class="empty-state"><p>No project gaps identified.</p></div>`;
        } else {
            coverage.innerHTML = breakdown.map(item => {
                const pct = item.required_level > 0 ? Math.min(100, Math.round((item.available_level / item.required_level) * 100)) : 100;
                return `
                    <div class="coverage-item">
                        <span>${escapeHtml(item.skill)}</span>
                        <strong>${pct}%</strong>
                        <div class="match-component-track">
                            <div class="match-component-fill" style="width:${pct}%;"></div>
                        </div>
                    </div>`;
            }).join("");

            const weak = breakdown.filter(i => i.status !== "Covered");
            const covered = breakdown.filter(i => i.status === "Covered").length;
            const total = breakdown.length;
            const pct = total ? Math.round((covered / total) * 100) : 0;

            if (covNumber) covNumber.textContent = `${pct}%`;
            if (covBar) covBar.style.width = `${pct}%`;
            if (covSummary) {
                if (pct === 0) {
                    covSummary.textContent = "The team currently has 0% coverage of the skills required by this project.";
                } else if (pct === 100) {
                    covSummary.textContent = "The team covers 100% of the skills required by this project.";
                } else {
                    covSummary.textContent = `The team currently covers ${pct}% of the skills required by the project.`;
                }
            }

            if (note) {
                note.textContent = weak.length
                    ? `The current team has weaker coverage in ${weak.map(i => i.skill).join(", ")}. Finding a teammate with these skills could improve the team's overall coverage.`
                    : `The team covers every skill this project needs.`;
            }

            if (gapList) {
                if (!weak.length) {
                    gapList.innerHTML = `<div class="empty-state"><p>The team already covers every skill this project needs. 🌿</p></div>`;
                } else {
                    gapList.innerHTML = weak.map(item => {
                        const pctSkill = item.required_level > 0 ? Math.min(100, Math.round((item.available_level / item.required_level) * 100)) : 100;
                        return `
                            <div class="gap-item">
                                <span>${escapeHtml(item.skill)}</span>
                                <strong>${pctSkill}%</strong>
                            </div>`;
                    }).join("");
                }
            }
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
                        <strong>${escapeHtml(s.name)}</strong>
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
                        <h3>${escapeHtml(s.skill)}</h3>
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

    const appCountEl = $("#detailApplicationCount");
    if (appCountEl) {
        const count = p.application_count || 0;
        appCountEl.textContent = `${count} received`;
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

async function renderFacultyProjectDetail(projectId) {
    const section = $("#facultyProjectDetailSection");
    const listSection = $("#facultyProjectsSection");
    const content = $("#facultyProjectDetailContent");
    if (!section || !content) return;

    if (listSection) listSection.style.display = "none";
    section.style.display = "";
    content.innerHTML = `<div class="empty-state" style="padding: 40px; text-align: center;"><p>Loading project analytics... ⏳</p></div>`;

    const { ok, data } = await api(`/faculty/projects/${projectId}`);
    if (!ok || !data || !data.project) {
        content.innerHTML = `
            <div class="garden-card empty-state" style="padding: 30px; text-align: center;">
                <p>Could not load project details. Please try again.</p>
                <button type="button" class="garden-button secondary" id="backToProjectsBtn">← Back to Guided Projects</button>
            </div>`;
        const backBtn = $("#backToProjectsBtn", content);
        if (backBtn) {
            backBtn.onclick = () => {
                section.style.display = "none";
                if (listSection) listSection.style.display = "";
                history.pushState(null, "", "faculty-projects.html");
            };
        }
        return;
    }

    const p = data.project;
    const stats = data.stats || {};
    const teamMembers = data.team_members || [];
    const applications = data.applications || [];
    const skills = data.required_skills || [];

    // Calculations for Pie/Donut Chart 1: Team Capacity
    const teamSize = stats.team_size || 4;
    const memberCount = stats.member_count || 0;
    const openSpots = stats.open_spots !== undefined ? stats.open_spots : Math.max(0, teamSize - memberCount);
    const fillPct = stats.fill_percentage || (teamSize > 0 ? Math.round((memberCount / teamSize) * 100) : 0);
    const circumference = 263.89; // 2 * PI * 42
    const strokeDashoffset = circumference - (fillPct / 100 * circumference);

    // Calculations for Pie/Donut Chart 2: Application Pipeline
    const totalApps = stats.total_applications || applications.length;
    const pendingApps = stats.pending_applications || applications.filter(a => a.status === "Pending").length;
    const acceptedApps = stats.accepted_applications || applications.filter(a => a.status === "Accepted").length;
    const rejectedApps = stats.rejected_applications || applications.filter(a => a.status === "Rejected").length;

    // SVG donut segments for applications
    let appSegments = "";
    if (totalApps === 0) {
        appSegments = `<circle cx="60" cy="60" r="42" fill="none" stroke="#e8ede0" stroke-width="14" />`;
    } else {
        const pAcc = (acceptedApps / totalApps) * circumference;
        const pPen = (pendingApps / totalApps) * circumference;
        const pRej = (rejectedApps / totalApps) * circumference;

        let offset = 0;
        if (acceptedApps > 0) {
            appSegments += `<circle cx="60" cy="60" r="42" fill="none" stroke="#c6a15b" stroke-width="14"
                stroke-dasharray="${pAcc} ${circumference}" stroke-dashoffset="${-offset}"
                transform="rotate(-90 60 60)" />`;
            offset += pAcc;
        }
        if (pendingApps > 0) {
            appSegments += `<circle cx="60" cy="60" r="42" fill="none" stroke="#536b32" stroke-width="14"
                stroke-dasharray="${pPen} ${circumference}" stroke-dashoffset="${-offset}"
                transform="rotate(-90 60 60)" />`;
            offset += pPen;
        }
        if (rejectedApps > 0) {
            appSegments += `<circle cx="60" cy="60" r="42" fill="none" stroke="#a9927d" stroke-width="14"
                stroke-dasharray="${pRej} ${circumference}" stroke-dashoffset="${-offset}"
                transform="rotate(-90 60 60)" />`;
        }
    }

    // Milestones / Process stage
    const currentStage = stats.current_stage || 1;
    const stages = [
        { num: "01", title: "Project Published", desc: "Project bed configured and open for student discovery", icon: "🌱", done: currentStage >= 1 },
        { num: "02", title: "Candidate Review", desc: `${totalApps} application(s) received · ${pendingApps} pending evaluation`, icon: "✉", done: currentStage >= 2 },
        { num: "03", title: "Team Assembly", desc: `${memberCount} of ${teamSize} members accepted into team bed`, icon: "🌳", done: currentStage >= 3 },
        { num: "04", title: "Active Bloom", desc: memberCount >= teamSize ? "Full team assembled & underway" : "Forming final team complement", icon: "✿", done: currentStage >= 4 }
    ];

    content.innerHTML = `
        <div style="margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
            <button type="button" class="garden-button secondary" id="backToProjectsBtn">
                ← Back to All Guided Projects
            </button>
            <span class="botanical-badge">
                ${escapeHtml(p.status || "Open")} Project Bed
            </span>
        </div>

        <!-- Project Hero Card -->
        <article class="garden-card reveal" style="padding: 28px; margin-bottom: 24px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; flex-wrap: wrap;">
                <div>
                    <span class="application-project-status open" style="margin-bottom: 8px;">${escapeHtml(p.domain || "Academic Project")}</span>
                    <h2 style="font-family: 'Cormorant Garamond', serif; font-size: 2rem; margin: 6px 0 10px; color: var(--olive-deep);">
                        ${escapeHtml(p.title)}
                    </h2>
                    <p style="color: var(--muted); font-size: 0.95rem; max-width: 720px; line-height: 1.6;">
                        ${escapeHtml(p.description || "Guided academic project for student skill development and cross-functional team matching.")}
                    </p>
                </div>
                <div style="text-align: right; min-width: 140px;">
                    <small style="display: block; font-size: 0.7rem; color: var(--muted); letter-spacing: 1px;">COMMITMENT</small>
                    <strong style="font-size: 1.1rem; color: var(--olive-deep);">${escapeHtml(p.required_availability || "Medium commitment")}</strong>
                    <small style="display: block; margin-top: 6px; font-size: 0.7rem; color: var(--muted); letter-spacing: 1px;">DIFFICULTY</small>
                    <span style="font-size: 0.9rem; color: var(--gold-deep);">${escapeHtml(p.difficulty || "Intermediate")}</span>
                </div>
            </div>

            <div class="application-meta" style="margin-top: 18px;">
                <span>👥 Target Team: ${teamSize} Students</span>
                <span>📅 Published: ${p.created_at ? new Date(p.created_at).toLocaleDateString() : "Active"}</span>
                <span>✿ Status: ${escapeHtml(p.status)}</span>
            </div>
        </article>

        <!-- Process / Progress Milestones -->
        <section class="garden-card reveal" style="padding: 26px; margin-bottom: 24px;">
            <div class="garden-section-title" style="margin-bottom: 18px;">
                <div>
                    <span>PROJECT PROGRESS & MILESTONES</span>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 1.5rem;">How Much Progress Has Been Made</h3>
                </div>
                <span class="botanical-badge">Stage ${currentStage} of 4</span>
            </div>

            <!-- Progress Bar -->
            <div style="width: 100%; height: 8px; background: #e8ede0; border-radius: 4px; overflow: hidden; margin-bottom: 22px;">
                <div style="width: ${(currentStage / 4) * 100}%; height: 100%; background: linear-gradient(90deg, var(--olive, #536b32), var(--gold, #c6a15b)); transition: width 0.4s ease;"></div>
            </div>

            <!-- Milestone Steps -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px;">
                ${stages.map((st, i) => `
                    <div style="padding: 16px; border-radius: 12px; border: 1px solid ${st.done ? 'rgba(83, 107, 50, 0.3)' : 'rgba(0,0,0,0.06)'}; background: ${st.done ? 'rgba(83, 107, 50, 0.05)' : '#faf8f5'};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 1.3rem;">${st.icon}</span>
                            <span style="font-size: 0.72rem; font-weight: 600; padding: 2px 8px; border-radius: 10px; background: ${st.done ? '#536b32' : '#bbb'}; color: white;">
                                ${st.done ? '✓ Done' : '○ Upcoming'}
                            </span>
                        </div>
                        <h4 style="margin: 4px 0 6px; font-family: 'Cormorant Garamond', serif; font-size: 1.15rem; color: var(--olive-deep);">
                            ${st.title}
                        </h4>
                        <p style="margin: 0; font-size: 0.78rem; color: var(--muted); line-height: 1.4;">
                            ${escapeHtml(st.desc)}
                        </p>
                    </div>
                `).join("")}
            </div>
        </section>

        <!-- Pie / Donut Charts Section -->
        <section class="garden-card reveal" style="padding: 26px; margin-bottom: 24px;">
            <div class="garden-section-title" style="margin-bottom: 20px;">
                <div>
                    <span>PROJECT ANALYTICS</span>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 1.5rem;">Capacity & Applications Breakdown</h3>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 24px; align-items: center;">
                
                <!-- Chart 1: Team Capacity Donut -->
                <div style="display: flex; align-items: center; gap: 20px; padding: 20px; border-radius: 14px; background: rgba(247, 242, 229, 0.4); border: 1px solid rgba(120, 110, 70, 0.12);">
                    <div style="position: relative; width: 120px; height: 120px; flex-shrink: 0;">
                        <svg viewBox="0 0 120 120" width="120" height="120">
                            <!-- Background track (open spots) -->
                            <circle cx="60" cy="60" r="42" fill="none" stroke="#e1e7d4" stroke-width="14" />
                            <!-- Filled track -->
                            <circle cx="60" cy="60" r="42" fill="none" stroke="#536b32" stroke-width="14"
                                    stroke-dasharray="${circumference}" stroke-dashoffset="${strokeDashoffset}"
                                    stroke-linecap="round" transform="rotate(-90 60 60)" />
                            <!-- Center text -->
                            <text x="60" y="56" text-anchor="middle" font-size="20" font-family="'Cormorant Garamond', serif" font-weight="bold" fill="#26351b">${memberCount}/${teamSize}</text>
                            <text x="60" y="73" text-anchor="middle" font-size="9" fill="#7c8274" letter-spacing="0.8">MEMBERS</text>
                        </svg>
                    </div>
                    <div>
                        <h4 style="margin: 0 0 6px; font-family: 'Cormorant Garamond', serif; font-size: 1.25rem; color: var(--olive-deep);">
                            Team Capacity
                        </h4>
                        <div style="font-size: 0.82rem; color: var(--muted); margin-bottom: 8px;">
                            ${fillPct}% filled · ${openSpots} spot(s) remaining
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 4px; font-size: 0.78rem;">
                            <span style="display: flex; align-items: center; gap: 6px;">
                                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #536b32;"></span>
                                Active Members: <strong>${memberCount}</strong>
                            </span>
                            <span style="display: flex; align-items: center; gap: 6px;">
                                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #e1e7d4;"></span>
                                Open Seats: <strong>${openSpots}</strong>
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Chart 2: Applications Pipeline Donut -->
                <div style="display: flex; align-items: center; gap: 20px; padding: 20px; border-radius: 14px; background: rgba(247, 242, 229, 0.4); border: 1px solid rgba(120, 110, 70, 0.12);">
                    <div style="position: relative; width: 120px; height: 120px; flex-shrink: 0;">
                        <svg viewBox="0 0 120 120" width="120" height="120">
                            ${appSegments}
                            <text x="60" y="56" text-anchor="middle" font-size="20" font-family="'Cormorant Garamond', serif" font-weight="bold" fill="#26351b">${totalApps}</text>
                            <text x="60" y="73" text-anchor="middle" font-size="9" fill="#7c8274" letter-spacing="0.8">APPLIED</text>
                        </svg>
                    </div>
                    <div>
                        <h4 style="margin: 0 0 6px; font-family: 'Cormorant Garamond', serif; font-size: 1.25rem; color: var(--olive-deep);">
                            Applications Funnel
                        </h4>
                        <div style="font-size: 0.82rem; color: var(--muted); margin-bottom: 8px;">
                            ${pendingApps} awaiting your review
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 4px; font-size: 0.78rem;">
                            <span style="display: flex; align-items: center; gap: 6px;">
                                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #c6a15b;"></span>
                                Accepted: <strong>${acceptedApps}</strong>
                            </span>
                            <span style="display: flex; align-items: center; gap: 6px;">
                                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #536b32;"></span>
                                Pending: <strong>${pendingApps}</strong>
                            </span>
                            <span style="display: flex; align-items: center; gap: 6px;">
                                <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #a9927d;"></span>
                                Rejected: <strong>${rejectedApps}</strong>
                            </span>
                        </div>
                    </div>
                </div>

            </div>
        </section>

        <!-- Active Team Members Section -->
        <section class="garden-card" style="padding: 26px; margin-bottom: 24px;">
            <div class="garden-section-title" style="margin-bottom: 18px;">
                <div>
                    <span>WORKING ON PROJECT</span>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 1.5rem;">Active Team Members (${memberCount}/${teamSize})</h3>
                </div>
            </div>

            ${teamMembers.length === 0 ? `
                <div class="empty-state" style="padding: 25px; text-align: center;">
                    <p style="color: var(--muted); margin: 0 0 10px;">No students have joined this team bed yet.</p>
                    <small>Review pending candidate applications below and click "Accept into Team" to fill your project team.</small>
                </div>
            ` : `
                <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 14px;">
                    ${teamMembers.map(m => `
                        <div style="padding: 16px; border-radius: 12px; border: 1px solid rgba(83, 107, 50, 0.2); background: white;">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                                <div style="width: 36px; height: 36px; border-radius: 50%; background: #536b32; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;">
                                    ${escapeHtml((m.student_name || "S")[0].toUpperCase())}
                                </div>
                                <div>
                                    <strong style="display: block; font-size: 0.95rem; color: var(--olive-deep);">${escapeHtml(m.student_name)}</strong>
                                    <span style="font-size: 0.72rem; color: var(--muted);">${escapeHtml(m.department || "")} · ${escapeHtml(m.year || "")}</span>
                                </div>
                            </div>
                            <span class="application-project-status accepted" style="font-size: 0.65rem; margin-bottom: 8px;">
                                ${escapeHtml(m.role || "Team Member")}
                            </span>
                            <div style="margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px;">
                                ${(m.skills || []).map(sk => `
                                    <span style="font-size: 0.68rem; padding: 2px 7px; border-radius: 10px; background: #e8ede0; color: #444;">
                                        ${escapeHtml(sk.name)} (${sk.proficiency_level}/5)
                                    </span>
                                `).join("")}
                            </div>
                        </div>
                    `).join("")}
                </div>
            `}
        </section>

        <!-- Candidate Applications Section -->
        <section class="garden-card" style="padding: 26px; margin-bottom: 24px;">
            <div class="garden-section-title" style="margin-bottom: 18px;">
                <div>
                    <span>APPLICATIONS</span>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 1.5rem;">Candidate Applicants (${applications.length})</h3>
                </div>
            </div>

            ${applications.length === 0 ? `
                <div class="empty-state" style="padding: 25px; text-align: center;">
                    <p style="color: var(--muted); margin: 0;">No student applications received for this project bed yet.</p>
                </div>
            ` : `
                <div style="display: flex; flex-direction: column; gap: 12px;">
                    ${applications.map(a => `
                        <article class="garden-card application-card" style="margin-bottom: 0;">
                            <div class="application-card-top">
                                <div>
                                    <span class="application-project-status ${a.status === 'Accepted' ? 'accepted' : a.status === 'Rejected' ? 'closed' : 'open'}">
                                        ${escapeHtml(a.status)}
                                    </span>
                                    <h3 style="margin: 6px 0 4px;">${escapeHtml(a.student_name)}</h3>
                                    <p>${escapeHtml(a.department || "")} · ${escapeHtml(a.year || "")} — Applied ${a.applied_at ? new Date(a.applied_at).toLocaleDateString() : ""}</p>
                                </div>
                                <div class="application-match">
                                    <small>MATCH</small>
                                    <strong>${Math.round(a.match_score || 0)}%</strong>
                                </div>
                            </div>
                            ${a.message ? `<p class="muted-text" style="font-size: 0.85rem; margin: 8px 0; font-style: italic;">"${escapeHtml(a.message)}"</p>` : ""}
                            <div class="application-status-row" style="margin-top: 12px;">
                                <div class="application-status ${a.status === 'Accepted' ? 'accepted' : a.status === 'Rejected' ? 'rejected' : 'pending'}">
                                    <span class="status-dot"></span>${escapeHtml(a.status)}
                                </div>
                                <div class="application-actions">
                                    ${a.status === 'Pending' ? `
                                        <button class="garden-button" type="button"
                                                data-project-review="${a.id}" data-status="Accepted">Accept into Team ✓</button>
                                        <button class="garden-button secondary" type="button"
                                                data-project-review="${a.id}" data-status="Rejected">Reject</button>
                                    ` : `
                                        <span style="font-size: 0.8rem; color: var(--muted);">Verdict recorded</span>
                                    `}
                                </div>
                            </div>
                        </article>
                    `).join("")}
                </div>
            `}
        </section>

        <!-- Required Skills Coverage Section -->
        <section class="garden-card reveal" style="padding: 26px; margin-bottom: 24px;">
            <div class="garden-section-title" style="margin-bottom: 14px;">
                <div>
                    <span>SKILL REQUIREMENTS</span>
                    <h3 style="font-family: 'Cormorant Garamond', serif; font-size: 1.5rem;">Target Competencies</h3>
                </div>
            </div>

            ${skills.length === 0 ? `
                <p class="muted-text">No specific required skills listed for this project.</p>
            ` : `
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                    ${skills.map(s => `
                        <span style="padding: 6px 14px; border-radius: 20px; font-size: 0.85rem; background: #e8ede0; border: 1px solid rgba(83, 107, 50, 0.2); color: var(--olive-deep);">
                            🌿 ${escapeHtml(s.name)} · Level ${s.required_level}/5
                        </span>
                    `).join("")}
                </div>
            `}
        </section>

        <div style="text-align: center; margin-top: 20px; margin-bottom: 20px;">
            <button type="button" class="garden-button secondary" id="backToProjectsBtnBottom">
                ← Back to All Guided Projects
            </button>
        </div>
    `;

    // Wire back buttons
    const handleBack = () => {
        section.style.display = "none";
        if (listSection) listSection.style.display = "";
        history.pushState(null, "", "faculty-projects.html");
        renderFacultyConsole();
    };
    if (window.initializeRevealAnimations) {
        window.initializeRevealAnimations(content);
    }

    const bTop = $("#backToProjectsBtn", content);
    const bBottom = $("#backToProjectsBtnBottom", content);
    if (bTop) bTop.onclick = handleBack;
    if (bBottom) bBottom.onclick = handleBack;

    // Wire in-place Accept/Reject reviews
    $$("[data-project-review]", content).forEach(btn => {
        btn.onclick = async () => {
            btn.disabled = true;
            const newStatus = btn.dataset.status;
            const { ok, data: resData } = await api(`/faculty/applications/${btn.dataset.projectReview}/status`, {
                method: "PUT",
                body: JSON.stringify({ status: newStatus })
            });
            if (ok && resData.success) {
                toast(`Application ${newStatus.toLowerCase()} ✓`);
                renderFacultyProjectDetail(projectId);
            } else {
                toast(resData.message || "Could not update application.");
                btn.disabled = false;
            }
        };
    });
}

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
            setTimeout(() => { window.location.href = "projects.html"; }, 1200);
            return;
        }
        if (status >= 500) {
            toast("Server error loading faculty console.");
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
                            <button type="button" class="garden-button" data-faculty-view-project="${p.id}">View Project & Progress ✿</button>
                        </div>
                    </div>
                </article>`).join("");

            $$("[data-faculty-view-project]", projects).forEach(btn => {
                btn.onclick = () => renderFacultyProjectDetail(btn.dataset.facultyViewProject);
            });

            const urlProjId = new URLSearchParams(window.location.search).get("id");
            if (urlProjId && $("#facultyProjectDetailSection")) {
                renderFacultyProjectDetail(urlProjId);
            }
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
                    <h3>${escapeHtml(e.title)}</h3>
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
        if (password.length < 8) {
            toast("Password must be at least 8 characters.");
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
        return;
    }

    wireProjectPicker();
    renderProfileManagement();
    renderSettings();
    renderNotifications();

    // Page specific panels
    if ($(".project-match-card") && $(".dashboard-grid")) renderDashboard();
    if ($(".gap-overview") || $(".team-gap-grid")) renderGaps();
    if ($(".team-members-grid") || $(".recommended-teammates-grid")) renderTeam();
    if ($("[data-detail-skills]") || $(".project-detail-hero")) renderProjectDetails();
    if ($("#applicationsListItems")) renderApplications();
});
