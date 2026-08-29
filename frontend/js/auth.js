// Dynamically resolve API Base URL across mobile, LAN, Cloud, and local environments
function getApiBaseUrl() {
    const origin = window.location.origin || "";
    const hostname = window.location.hostname || "";
    const protocol = window.location.protocol || "http:";

    // If hosted on Cloud (Vercel, Render, Heroku) or running on Flask port 5000 directly
    if (origin.includes('.vercel.app') || origin.includes('.onrender.com') || origin.includes(':5000')) {
        return `${origin}/api`;
    }

    // If accessed over LAN/Wi-Fi from mobile or another device (e.g. http://10.94.195.67:8000 or http://192.168.x.x)
    if (hostname && hostname !== 'localhost' && hostname !== '127.0.0.1') {
        return `${protocol}//${hostname}:5000/api`;
    }

    // Default local fallback
    return "http://127.0.0.1:5000/api";
}

const API_BASE_URL = getApiBaseUrl();

// Fetch stored user data from local storage
function getCurrentUser() {
    const userStr = localStorage.getItem("user");
    if (!userStr) return null;
    try {
        return JSON.parse(userStr);
    } catch (e) {
        localStorage.removeItem("user");
        return null;
    }
}

// Save user data to local storage
function setCurrentUser(user) {
    localStorage.setItem("user", JSON.stringify(user));
}

// Check if user is authenticated
function isAuthenticated() {
    return getCurrentUser() !== null;
}

// Log out and redirect
function logout() {
    localStorage.removeItem("user");
    showToast("Logged out successfully.", "success");
    setTimeout(() => {
        window.location.href = "index.html";
    }, 1000);
}

// Route protector for private pages
function checkAuth() {
    if (!isAuthenticated()) {
        window.location.href = "login.html";
    }
}

// Route protector for guest-only pages (login/register)
function checkGuest() {
    if (isAuthenticated()) {
        window.location.href = "dashboard.html";
    }
}

// Toast notification helper
function showToast(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }
    
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    
    let icon = "💡";
    if (type === "success") icon = "✨";
    if (type === "error") icon = "⚠️";
    
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = "toastIn 0.3s reverse forwards";
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 3500);
}

// Check real-time connection status to Flask backend
async function checkBackendConnection() {
    let badge = document.getElementById("backend-status-badge");
    if (!badge) {
        badge = document.createElement("div");
        badge.id = "backend-status-badge";
        badge.className = "backend-status-badge";
        document.body.appendChild(badge);
    }
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);
        
        const res = await fetch(`${API_BASE_URL}/health`, { 
            method: 'GET', 
            signal: controller.signal 
        });
        clearTimeout(timeoutId);
        
        if (res.ok) {
            badge.className = "backend-status-badge connected";
            badge.innerHTML = `<span class="dot green"></span> Connected`;
            badge.title = `Flask Backend is live at ${API_BASE_URL}`;
        } else {
            badge.className = "backend-status-badge disconnected";
            badge.innerHTML = `<span class="dot red"></span> Backend Error`;
        }
    } catch (e) {
        badge.className = "backend-status-badge disconnected";
        badge.innerHTML = `<span class="dot red"></span> Backend Offline`;
        badge.title = "Could not reach Flask backend. Start server with: python backend/app.py";
    }
}

// Dynamically update the header navigation based on login status
function updateNavigation() {
    const nav = document.getElementById("main-nav");
    if (!nav) return;
    
    const user = getCurrentUser();
    if (user) {
        nav.innerHTML = `
            <a href="dashboard.html" class="nav-link">Dashboard</a>
            <a href="profile.html" class="nav-link">Profile</a>
            <button onclick="logout()" class="btn-nav-outline">Log Out</button>
        `;
        const currentPath = window.location.pathname;
        const links = nav.querySelectorAll(".nav-link");
        links.forEach(link => {
            if (currentPath.includes(link.getAttribute("href"))) {
                link.classList.add("active");
            }
        });
    } else {
        nav.innerHTML = `
            <a href="index.html" class="nav-link">Home</a>
            <a href="login.html" class="nav-link">Login</a>
            <a href="register.html" class="btn-nav">Register</a>
        `;
    }
}

// Setup form handlers & health monitor once DOM loads
document.addEventListener("DOMContentLoaded", () => {
    updateNavigation();
    
    // Check initial connection & schedule polling every 10 seconds
    checkBackendConnection();
    setInterval(checkBackendConnection, 10000);
    
    // Login form logic
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
        checkGuest();
        loginForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            
            const btn = loginForm.querySelector("button[type='submit']");
            const originalText = btn.innerText;
            btn.disabled = true;
            btn.innerText = "Signing in...";
            
            try {
                const response = await fetch(`${API_BASE_URL}/login`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email, password })
                });
                const result = await response.json();
                
                if (response.ok) {
                    setCurrentUser(result.user);
                    showToast("Login successful! Redirecting...", "success");
                    setTimeout(() => {
                        window.location.href = "dashboard.html";
                    }, 1200);
                } else {
                    showToast(result.error || "Login failed.", "error");
                    btn.disabled = false;
                    btn.innerText = originalText;
                }
            } catch (err) {
                console.error("Login Error:", err);
                showToast("Connection to server failed. Start Flask backend.", "error");
                btn.disabled = false;
                btn.innerText = originalText;
            }
        });
    }
    
    // Registration form logic
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        checkGuest();
        registerForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const name = document.getElementById("name").value;
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;
            const confirmPassword = document.getElementById("confirm-password").value;
            
            if (password !== confirmPassword) {
                showToast("Passwords do not match.", "error");
                return;
            }
            
            const btn = registerForm.querySelector("button[type='submit']");
            const originalText = btn.innerText;
            btn.disabled = true;
            btn.innerText = "Creating account...";
            
            try {
                const response = await fetch(`${API_BASE_URL}/register`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ name, email, password })
                });
                const result = await response.json();
                
                if (response.ok) {
                    showToast("Registration successful! Redirecting to login...", "success");
                    setTimeout(() => {
                        window.location.href = "login.html";
                    }, 1500);
                } else {
                    showToast(result.error || "Registration failed.", "error");
                    btn.disabled = false;
                    btn.innerText = originalText;
                }
            } catch (err) {
                console.error("Registration Error:", err);
                showToast("Connection to server failed. Start Flask backend.", "error");
                btn.disabled = false;
                btn.innerText = originalText;
            }
        });
    }
});
