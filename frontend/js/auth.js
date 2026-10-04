const API_BASE_URL = "https://modsense-ai-1.onrender.com";

async function authRequest(path, body) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(body)
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
        throw new Error(data.error || "Request failed.");
    }

    return data;
}

document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("loginForm");
    const signupForm = document.getElementById("signupForm");

    if (loginForm) {
        loginForm.addEventListener("submit", async event => {
            event.preventDefault();

            try {
                const data = await authRequest("/api/login", {
                    email: document.getElementById("email").value.trim(),
                    password: document.getElementById("password").value
                });

                localStorage.setItem("user", JSON.stringify(data.user));

                if (data.user.role === "admin") {
                    window.location.href = "../admin/admin-dashboard.html";
                } else {
                    window.location.href = "../user/community-home.html";
                }
            } catch (error) {
                document.getElementById("formMessage").textContent = error.message;
            }
        });
    }

    if (signupForm) {
        signupForm.addEventListener("submit", async event => {
            event.preventDefault();

            const password = document.getElementById("password").value;
            const confirm = document.getElementById("confirmPassword").value;

            if (password !== confirm) {
                document.getElementById("formMessage").textContent = "Passwords do not match.";
                return;
            }

            try {
                await authRequest("/api/signup", {
                    first_name: document.getElementById("firstName").value.trim(),
                    last_name: document.getElementById("lastName").value.trim(),
                    email: document.getElementById("email").value.trim(),
                    password
                });

                alert("Account created successfully. Please log in.");
                window.location.href = "login.html";
            } catch (error) {
                document.getElementById("formMessage").textContent = error.message;
            }
        });
    }
});
