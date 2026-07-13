// Ensure user is logged in
checkAuth();

document.addEventListener("DOMContentLoaded", () => {
    const user = getCurrentUser();
    
    // Set Welcome Header
    if (user) {
        document.getElementById("welcome-title").innerText = `Welcome, ${user.name}!`;
    }
    
    // Fetch stats and history
    loadDashboardData(user.id);
    
    // Wire up Start Interview session launcher
    const btnStart = document.getElementById("btn-start-interview");
    if (btnStart) {
        btnStart.addEventListener("click", () => {
            const category = document.getElementById("question-category").value;
            const limit = document.getElementById("question-limit").value;
            
            // Save options to sessionStorage for the interview page
            sessionStorage.setItem("interview_category", category);
            sessionStorage.setItem("interview_limit", limit);
            
            window.location.href = "interview.html";
        });
    }
    
    // Wire up Resume Drop Zone
    setupResumeAnalyzer();
});

// Load user stats and history table from Flask
async function loadDashboardData(userId) {
    const tableBody = document.getElementById("history-table-body");
    
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/stats/${userId}`);
        if (!response.ok) throw new Error("Failed to fetch statistics.");
        
        const data = await response.json();
        
        // Update Widgets
        document.getElementById("stat-interviews").innerText = data.total_interviews;
        document.getElementById("stat-avg-score").innerText = `${data.average_score}%`;
        
        if (data.averages) {
            document.getElementById("stat-grammar").innerText = `${data.averages.grammar}/20`;
        }
        
        // Build History Table
        if (data.history && data.history.length > 0) {
            tableBody.innerHTML = "";
            data.history.forEach(report => {
                const tr = document.createElement("tr");
                
                // Format score class
                let scoreClass = "score-low";
                if (report.overall_score >= 80) scoreClass = "score-high";
                else if (report.overall_score >= 60) scoreClass = "score-mid";
                
                tr.innerHTML = `
                    <td>${report.date}</td>
                    <td><span class="score-badge ${scoreClass}">${report.overall_score}/100</span></td>
                    <td>${report.confidence_score}/20</td>
                    <td>${report.technical_score}/25</td>
                    <td>
                        <button onclick="window.location.href='result.html?report_id=${report.id}'" class="btn-table-action">View Report</button>
                    </td>
                `;
                tableBody.appendChild(tr);
            });
        } else {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="no-data-msg">No practice sessions finished yet. Start one above!</td>
                </tr>
            `;
        }
        
    } catch (err) {
        console.error("Dashboard Load Error:", err);
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="no-data-msg" style="color: var(--danger-color);">Could not connect to Flask server. Make sure the backend is running.</td>
            </tr>
        `;
    }
}

// Setup Resume drag and drop events
function setupResumeAnalyzer() {
    const dropZone = document.getElementById("resume-drop-zone");
    const fileInput = document.getElementById("resume-file-input");
    const statusBox = document.getElementById("resume-upload-status");
    const resultBox = document.getElementById("resume-results-box");
    
    // Clicks on zone trigger file input click
    dropZone.addEventListener("click", () => fileInput.click());
    
    // Drag effects
    dropZone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "var(--primary-color)";
        dropZone.style.background = "rgba(99, 102, 241, 0.08)";
    });
    
    dropZone.addEventListener("dragleave", () => {
        dropZone.style.borderColor = "rgba(255, 255, 255, 0.15)";
        dropZone.style.background = "transparent";
    });
    
    dropZone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropZone.style.borderColor = "rgba(255, 255, 255, 0.15)";
        dropZone.style.background = "transparent";
        
        if (e.dataTransfer.files.length > 0) {
            handleResumeFile(e.dataTransfer.files[0]);
        }
    });
    
    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleResumeFile(e.target.files[0]);
        }
    });
}

// Upload file to Flask and render results
async function handleResumeFile(file) {
    if (file.type !== "application/pdf") {
        showToast("Please upload a PDF file.", "error");
        return;
    }
    
    const statusBox = document.getElementById("resume-upload-status");
    const resultBox = document.getElementById("resume-results-box");
    
    // Show spinner loader, hide prior values
    statusBox.classList.remove("hidden");
    resultBox.classList.add("hidden");
    
    const formData = new FormData();
    formData.append("resume", file);
    
    try {
        const response = await fetch(`${API_BASE_URL}/resume/analyze`, {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) throw new Error("Resume parsing error.");
        
        const data = await response.json();
        
        // Hide loader, show results
        statusBox.classList.add("hidden");
        resultBox.classList.remove("hidden");
        
        // Update values
        const scoreSpan = document.getElementById("resume-score");
        scoreSpan.innerText = `${data.match_score}%`;
        
        // Match color code
        if (data.match_score >= 80) scoreSpan.style.color = "var(--success-color)";
        else if (data.match_score >= 50) scoreSpan.style.color = "var(--warning-color)";
        else scoreSpan.style.color = "var(--danger-color)";
        
        document.getElementById("resume-experience").innerText = data.experience;
        
        // Render Found Skills
        const matchedContainer = document.getElementById("resume-matched-skills");
        matchedContainer.innerHTML = "";
        if (data.matched_skills && data.matched_skills.length > 0) {
            data.matched_skills.forEach(skill => {
                const span = document.createElement("span");
                span.className = "skill-tag";
                span.innerText = skill;
                matchedContainer.appendChild(span);
            });
        } else {
            matchedContainer.innerHTML = "<span style='font-size:0.8rem; color:var(--text-secondary);'>None identified</span>";
        }
        
        // Render Missing Skills
        const missingContainer = document.getElementById("resume-missing-skills");
        missingContainer.innerHTML = "";
        if (data.missing_skills && data.missing_skills.length > 0) {
            data.missing_skills.forEach(skill => {
                const span = document.createElement("span");
                span.className = "skill-tag missing";
                span.innerText = skill;
                missingContainer.appendChild(span);
            });
        } else {
            missingContainer.innerHTML = "<span style='font-size:0.8rem; color:var(--success-color);'>All requirements matched!</span>";
        }
        
        showToast("Resume analyzed successfully!", "success");
        
    } catch (err) {
        console.error("Resume Upload Error:", err);
        statusBox.classList.add("hidden");
        showToast("Error processing resume. Check backend server.", "error");
    }
}
