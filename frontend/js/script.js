const API_BASE_URL = "https://modsense-ai-1.onrender.com";

function getCurrentUser() {
    try {
        return JSON.parse(localStorage.getItem("user") || "null");
    } catch {
        return null;
    }
}

function saveUser(user) {
    localStorage.setItem("user", JSON.stringify(user));
}

function logoutUser() {
    localStorage.removeItem("user");
    window.location.href = "../auth/login.html";
}

function requireUser() {
    const user = getCurrentUser();
    if (!user) {
        window.location.href = "../auth/login.html";
        return null;
    }
    return user;
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

function setUserHeader() {
    const user = getCurrentUser();
    if (!user) return;

    const name = `${user.first_name || ""} ${user.last_name || ""}`.trim();
    document.querySelectorAll(".logged-user-name").forEach(el => {
        el.textContent = name || "User";
    });

    document.querySelectorAll(".profile-circle").forEach(el => {
        el.textContent = (user.first_name || "U").charAt(0).toUpperCase();
    });
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function loadExploreCommunities() {
    const container = document.getElementById("exploreCommunitiesContainer");
    if (!container) return;

    try {
        const data = await apiRequest("/api/communities");
        const communities = data.communities || [];

        container.innerHTML = communities.map(c => `
            <div class="card">
                <span class="tag">${escapeHtml(c.category_name || "General")}</span>
                <h3>${escapeHtml(c.name)}</h3>
                <p>${escapeHtml(c.description)}</p>
                <p class="muted">${escapeHtml(c.about || "")}</p>
                <button class="btn btn-primary" onclick="joinCommunity(${c.community_id})">
                    Join Community
                </button>
                <button class="btn btn-secondary" onclick="viewCommunity(${c.community_id})">
                    View
                </button>
            </div>
        `).join("") || `<div class="card"><h3>No active communities found.</h3></div>`;

        const search = document.getElementById("communitySearch");
        if (search) {
            search.oninput = () => {
                const q = search.value.toLowerCase();
                document.querySelectorAll("#exploreCommunitiesContainer .card").forEach(card => {
                    card.style.display = card.textContent.toLowerCase().includes(q) ? "" : "none";
                });
            };
        }
    } catch (error) {
        container.innerHTML = `<div class="card error">${escapeHtml(error.message)}</div>`;
    }
}

async function joinCommunity(id) {
    const user = requireUser();
    if (!user) return;

    try {
        const data = await apiRequest(`/api/communities/${id}/join`, {
            method: "POST",
            body: JSON.stringify({ user_id: user.user_id })
        });
        alert(data.message);
    } catch (error) {
        alert(error.message);
    }
}

function viewCommunity(id) {
    window.location.href = `community-details.html?id=${id}`;
}

async function loadMyCommunities() {
    const container = document.getElementById("myCommunityList");
    if (!container) return;

    const user = requireUser();
    if (!user) return;

    try {
        const data = await apiRequest(`/api/users/${user.user_id}/communities`);
        const communities = data.communities || [];

        if (!communities.length) {
            container.innerHTML = `
                <div class="card">
                    <h3>No Communities Joined</h3>
                    <p>You have not joined any communities yet.</p>
                    <a class="btn btn-primary" href="explore-community.html">Explore Communities</a>
                </div>
            `;
            return;
        }

        container.innerHTML = communities.map(c => `
            <div class="card">
                <h3>${escapeHtml(c.name)}</h3>
                <p>${escapeHtml(c.description)}</p>
                <p class="muted">Category: ${escapeHtml(c.category_name || "General")}</p>
                <button class="btn btn-primary" onclick="viewCommunity(${c.community_id})">
                    View Community
                </button>
                <button class="btn btn-danger" onclick="leaveCommunity(${c.community_id})">
                    Leave
                </button>
            </div>
        `).join("");
    } catch (error) {
        container.innerHTML = `<div class="card error">${escapeHtml(error.message)}</div>`;
    }
}

async function leaveCommunity(id) {
    const user = requireUser();
    if (!user || !confirm("Leave this community?")) return;

    try {
        await apiRequest(`/api/communities/${id}/leave?user_id=${user.user_id}`, {
            method: "DELETE"
        });
        loadMyCommunities();
    } catch (error) {
        alert(error.message);
    }
}

async function loadCommunityDetails() {
    const container = document.getElementById("communityDetailsContainer");
    if (!container) return;

    const id = new URLSearchParams(window.location.search).get("id");
    const user = requireUser();

    if (!id || !user) return;

    try {
        const data = await apiRequest(`/api/communities/${id}`);
        const c = data.community;

        const myCommunitiesData = await apiRequest(
            `/api/users/${user.user_id}/communities`
        );

        const joinedCommunities = myCommunitiesData.communities || [];

        const isMember = joinedCommunities.some(
            community => Number(community.community_id) === Number(c.community_id)
        );

        container.innerHTML = `
            <div class="card">
                <span class="tag">${escapeHtml(c.category_name || "General")}</span>
                <h2>${escapeHtml(c.name)}</h2>
                <p>${escapeHtml(c.description)}</p>
                <p>${escapeHtml(c.about || "")}</p>

                ${
                    isMember
                        ? `
                            <a class="btn btn-primary"
                               href="community-feed.html?community=${c.community_id}">
                                View Community
                            </a>

                            <a class="btn btn-secondary"
                               href="create-post.html?community=${c.community_id}">
                                Create Post
                            </a>
                        `
                        : `
                            <button class="btn btn-primary"
                                    onclick="joinCommunity(${c.community_id})">
                                Join Community
                            </button>

                            <a class="btn btn-secondary"
                               href="create-post.html?community=${c.community_id}">
                                Create Post
                            </a>
                        `
                }
            </div>
        `;
    } catch (error) {
        container.innerHTML = `
            <div class="card error">${escapeHtml(error.message)}</div>
        `;
    }
}

async function loadPosts(containerId = "postsContainer") {
    const container = document.getElementById(containerId);
    if (!container) return;

    try {
        const data = await apiRequest("/api/posts");
        const posts = data.posts || [];

        container.innerHTML = posts.map(post => `
            <article class="card post-card">
                <div class="post-meta">
                    <span>${escapeHtml(post.community_name)}</span>
                    <span>${escapeHtml(post.created_at)}</span>
                </div>
                <h3>${escapeHtml(post.title)}</h3>
                <p>${escapeHtml(post.content)}</p>
                <p class="muted">By ${escapeHtml(post.author_name)}</p>
                <div class="post-actions">
                    <button class="btn btn-secondary" onclick="toggleLike(${post.post_id})">
                        ♥ ${post.total_likes}
                    </button>
                    <a class="btn btn-primary" href="post-details.html?id=${post.post_id}">
                        View Post
                    </a>
                </div>
            </article>
        `).join("") || `<div class="card"><h3>No posts yet.</h3></div>`;
    } catch (error) {
        container.innerHTML = `<div class="card error">${escapeHtml(error.message)}</div>`;
    }
}

async function toggleLike(postId) {
    const user = requireUser();
    if (!user) return;

    try {
        const data = await apiRequest(`/api/posts/${postId}/like`, {
            method: "POST",
            body: JSON.stringify({ user_id: user.user_id })
        });

        if (document.getElementById("postDetailsContainer")) {
            loadPostDetails();
        } else {
            loadPosts();
        }

    } catch (error) {
        alert(error.message);
    }
}

async function loadPostDetails() {
    const container = document.getElementById("postDetailsContainer");
    if (!container) return;

    const id = new URLSearchParams(window.location.search).get("id");
    const user = requireUser();
    if (!id || !user) return;

    try {
        const data = await apiRequest(`/api/posts/${id}`);
        const post = data.post;

        const comments = await apiRequest(`/api/posts/${id}/comments`);

        container.innerHTML = `
            <article class="card">
                <span class="tag">${escapeHtml(post.community_name)}</span>
                <h2>${escapeHtml(post.title)}</h2>
                <p>${escapeHtml(post.content)}</p>
                <p class="muted">By ${escapeHtml(post.author_name)} · ${escapeHtml(post.created_at)}</p>
                <button class="btn btn-secondary" onclick="toggleLike(${post.post_id})">
                    ♥ ${post.total_likes}
                </button>
            </article>

            <div class="card">
                <h3>Comments</h3>
                <div id="commentsList">
                    ${(comments.comments || []).map(c => `
                        <div class="comment">
                            <strong>${escapeHtml(c.author_name)}</strong>
                            <p>${escapeHtml(c.comment_text)}</p>
                            <small>${escapeHtml(c.created_at)}</small>
                        </div>
                    `).join("") || "<p>No comments yet.</p>"}
                </div>

                <form id="commentForm">
                    <textarea id="commentText" required placeholder="Write a comment..."></textarea>
                    <button class="btn btn-primary" type="submit">Comment</button>
                </form>
            </div>
        `;

        document.getElementById("commentForm").onsubmit = async event => {
            event.preventDefault();
            const text = document.getElementById("commentText").value.trim();

            try {
                await apiRequest(`/api/posts/${id}/comments`, {
                    method: "POST",
                    body: JSON.stringify({
                        user_id: user.user_id,
                        comment_text: text
                    })
                });
                loadPostDetails();
            } catch (error) {
                alert(error.message);
            }
        };
    } catch (error) {
        container.innerHTML = `<div class="card error">${escapeHtml(error.message)}</div>`;
    }
}

async function initCreatePost() {
    const form = document.getElementById("createPostForm");
    if (!form) return;

    const user = requireUser();
    if (!user) return;

    const select = document.getElementById("communityId");

    try {
        const data = await apiRequest("/api/communities");
        select.innerHTML = data.communities.map(c =>
            `<option value="${c.community_id}">${escapeHtml(c.name)}</option>`
        ).join("");

        const queryCommunity = new URLSearchParams(window.location.search).get("community");
        if (queryCommunity) select.value = queryCommunity;
    } catch (error) {
        select.innerHTML = `<option value="">Unable to load communities</option>`;
    }

    form.onsubmit = async event => {
        event.preventDefault();

        try {
            const data = await apiRequest("/api/posts", {
                method: "POST",
                body: JSON.stringify({
                    user_id: user.user_id,
                    community: select.options[select.selectedIndex].text,
                    title: document.getElementById("postTitle").value.trim(),
                    content: document.getElementById("postContent").value.trim()
                })
            });

            alert(`${data.message}\nAI Risk: ${data.moderation.risk_level} (${data.moderation.ai_score})`);
            form.reset();
        } catch (error) {
            alert(error.message);
        }
    };
}

async function initAIChat() {
    const form = document.getElementById("chatForm");
    const messages = document.getElementById("chatMessages");
    if (!form || !messages) return;

    const user = requireUser();
    if (!user) return;

    function addMessage(text, type) {
        const item = document.createElement("div");
        item.className = `chat-message ${type}`;
        item.textContent = text;
        messages.appendChild(item);
        messages.scrollTop = messages.scrollHeight;
    }

    addMessage("Hello! I am ModSense AI Assistant. How can I help you?", "bot");

    form.onsubmit = async event => {
        event.preventDefault();

        const input = document.getElementById("chatInput");
        const message = input.value.trim();
        if (!message) return;

        addMessage(message, "user");
        input.value = "";

        try {
            const data = await apiRequest("/api/assistant/chat", {
                method: "POST",
                body: JSON.stringify({
                    user_id: user.user_id,
                    message
                })
            });
            addMessage(data.reply, "bot");
        } catch (error) {
            addMessage(`Error: ${error.message}`, "bot");
        }
    };

    document.getElementById("clearChat")?.addEventListener("click", () => {
        messages.innerHTML = "";
        addMessage("Chat cleared. How can I help?", "bot");
    });
}

document.addEventListener("DOMContentLoaded", () => {
    setUserHeader();

    document.querySelectorAll(".logout-btn").forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();
            logoutUser();
        });
    });

    loadExploreCommunities();
    loadMyCommunities();
    loadCommunityDetails();
    loadPosts();
    loadPostDetails();
    initCreatePost();
    initAIChat();
});
