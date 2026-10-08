const API_BASE_URL = "https://modsense-ai-1.onrender.com";

function getCurrentUser() {
    try {
        return JSON.parse(localStorage.getItem("user") || "null");
    } catch {
        return null;
    }
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        throw new Error(data.error || data.message || "Request failed.");
    }
    return data;
}

function requireAdmin() {
    const user = getCurrentUser();

    if (!user || user.role !== "admin") {
        window.location.href = "../auth/login.html";
        return null;
    }

    document.querySelectorAll(".logged-user-name").forEach(el => {
        el.textContent = `${user.first_name || ""} ${user.last_name || ""}`.trim() || "Admin";
    });

    document.querySelectorAll(".profile-circle").forEach(el => {
        el.textContent = (user.first_name || "A").charAt(0).toUpperCase();
    });

    return user;
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

async function loadAnalytics() {
    try {
        const data = await apiRequest(
            `/api/admin/analytics?user_id=${requireAdmin().user_id}`
        );
        const a = data.analytics;

        setText("totalUsers", a.total_users);
        setText("totalCommunities", a.total_communities);
        setText("totalPosts", a.total_posts);
        setText("flaggedContent", a.pending_moderation);

        setText("analyticsTotalUsers", a.total_users);
        setText("analyticsActiveUsers", a.active_users);
        setText("analyticsInactiveUsers", a.inactive_users);
        setText("analyticsTotalCommunities", a.total_communities);
        setText("analyticsActiveCommunities", a.active_communities);
        setText("analyticsInactiveCommunities", a.inactive_communities);
        setText("analyticsTotalPosts", a.total_posts);
        setText("analyticsTotalComments", a.total_comments);
        setText("analyticsTotalLikes", a.total_likes);
        setText("analyticsPendingModeration", a.pending_moderation);
    } catch (error) {
        alert(error.message);
    }
}

async function loadUsers() {
    const body = document.getElementById("userTableBody");
    if (!body) return;

    try {
        const admin = requireAdmin();
        if (!admin) return;

        const data = await apiRequest(`/api/admin/users?user_id=${admin.user_id}`);

        body.innerHTML = data.users.map((user, index) => `
        <tr>
        <td>${data.users.length - index}</td>
        <td>${escapeHtml(user.first_name)} ${escapeHtml(user.last_name)}</td>
        <td>${escapeHtml(user.email)}</td>
        <td>${escapeHtml(user.role)}</td>
        <td>${escapeHtml(user.status)}</td>
        <td>
            <button class="btn btn-small" onclick="changeUserStatus(${user.user_id}, '${user.status === "active" ? "inactive" : "active"}')">
                ${user.status === "active" ? "Deactivate" : "Activate"}
            </button>
        </td>
        </tr>
        `).join("");
    } catch (error) {
        body.innerHTML = `<tr><td colspan="6">${escapeHtml(error.message)}</td></tr>`;
    }
}

async function changeUserStatus(userId, status) {
    const admin = requireAdmin();
    if (!admin) return;

    try {
        await apiRequest(`/api/admin/users/${userId}/status`, {
            method: "PUT",
            body: JSON.stringify({
                user_id: admin.user_id,
                status
            })
        });
        loadUsers();
    } catch (error) {
        alert(error.message);
    }
}

async function loadCommunities() {
    const body = document.getElementById("communityTableBody");
    if (!body) return;

    try {
        const admin = requireAdmin();
        if (!admin) return;

        const data = await apiRequest(`/api/admin/communities?user_id=${admin.user_id}`);

        body.innerHTML = data.communities.map(c => `
            <tr>
                <td>${c.community_id}</td>
                <td>${escapeHtml(c.name)}</td>
                <td>${escapeHtml(c.category_name || "General")}</td>
                <td>${c.member_count}</td>
                <td>${c.post_count}</td>
                <td>${escapeHtml(c.status)}</td>
                <td>
                    <button class="btn btn-small" onclick="changeCommunityStatus(${c.community_id}, '${c.status === "active" ? "inactive" : "active"}')">
                        ${c.status === "active" ? "Deactivate" : "Activate"}
                    </button>
                </td>
            </tr>
        `).join("");
    } catch (error) {
        body.innerHTML = `<tr><td colspan="7">${escapeHtml(error.message)}</td></tr>`;
    }
}

async function changeCommunityStatus(id, status) {
    const admin = requireAdmin();
    if (!admin) return;

    try {
        await apiRequest(`/api/admin/communities/${id}/status`, {
            method: "PUT",
            body: JSON.stringify({
                user_id: admin.user_id,
                status
            })
        });
        loadCommunities();
    } catch (error) {
        alert(error.message);
    }
}

async function loadModeration() {
    const body = document.getElementById("moderationTableBody");
    if (!body) return;

    try {
        const admin = requireAdmin();
        if (!admin) return;

        const data = await apiRequest(`/api/admin/moderation?user_id=${admin.user_id}`);

        body.innerHTML = data.moderation.map((item, index) => `
            <tr>
                <td>${data.moderation.length - index}</td>
                <td>${escapeHtml(item.title)}</td>
                <td>${escapeHtml(item.author_name)}</td>
                <td>${escapeHtml(item.flag_reason)}</td>
                <td><strong>${escapeHtml(item.risk_level)}</strong></td>
                <td>${Number(item.ai_score).toFixed(0)}</td>
                <td>${escapeHtml(item.status)}</td>
                <td>
                    <button class="btn btn-small" onclick="reanalyze(${item.post_id})">AI Analyze</button>
                    <button class="btn btn-small btn-success" onclick="moderationAction(${item.moderation_id}, 'approved')">Approve</button>
                    <button class="btn btn-small btn-danger" onclick="moderationAction(${item.moderation_id}, 'removed')">Remove</button>
                </td>
            </tr>
        `).join("") || `<tr><td colspan="8">No moderation records.</td></tr>`;
    } catch (error) {
        body.innerHTML = `<tr><td colspan="8">${escapeHtml(error.message)}</td></tr>`;
    }
}

async function reanalyze(postId) {
    const admin = requireAdmin();
    if (!admin) return;

    try {
        const data = await apiRequest(
            `/api/admin/moderation/analyze/${postId}`,
            {
                method: "POST",
                body: JSON.stringify({ user_id: admin.user_id })
            }
        );

        alert(
            `AI analysis complete.\nReason: ${data.analysis.reason}\n` +
            `Risk: ${data.analysis.risk_level}\nScore: ${data.analysis.ai_score}`
        );

        loadModeration();
    } catch (error) {
        alert(error.message);
    }
}

async function moderationAction(id, status) {
    const admin = requireAdmin();
    if (!admin) return;

    try {
        await apiRequest(`/api/admin/moderation/${id}`, {
            method: "PUT",
            body: JSON.stringify({
                user_id: admin.user_id,
                status
            })
        });
        loadModeration();
    } catch (error) {
        alert(error.message);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const user = requireAdmin();
    if (!user) return;

    document.querySelectorAll(".logout-btn").forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            localStorage.removeItem("user");
            window.location.href = "../auth/login.html";
        });
    });

    const page = window.location.pathname.split("/").pop();

    if (page === "admin-dashboard.html") loadAnalytics();
    if (page === "analytics.html") loadAnalytics();
    if (page === "user-management.html") loadUsers();
    if (page === "community-management.html") loadCommunities();
    if (page === "content-moderation.html") loadModeration();
});
