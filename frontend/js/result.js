// Protect page access
checkAuth();

document.addEventListener("DOMContentLoaded", () => {
    // Parse URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    const reportId = urlParams.get("report_id");
    
    if (!reportId) {
        showToast("No report ID specified. Returning to dashboard.", "error");
        setTimeout(() => window.location.href = "dashboard.html", 1500);
        return;
    }
    
    loadReportDetails(reportId);
});

// Load report from API or fallback storage
async function loadReportDetails(reportId) {
    let reportData = null;
    
    // Check if redirect was due to database save error (use session fallback)
    if (reportId === "latest") {
        const fallbackStr = sessionStorage.getItem("latest_report_fallback");
        if (fallbackStr) {
            try {
                const parsedFallback = JSON.parse(fallbackStr);
                // Convert payload structure to mock API report structure
                reportData = compileMockReport(parsedFallback);
                showToast("Displaying offline report.", "info");
            } catch (e) {
                console.error("Parse fallback error:", e);
            }
        }
    }
    
    // Fetch from Flask server
    if (!reportData) {
        try {
            const res = await fetch(`${API_BASE_URL}/report/${reportId}`);
            if (!res.ok) throw new Error("Report fetch failed.");
            reportData = await res.json();
        } catch (e) {
            console.error("Report Fetch Error:", e);
            document.getElementById("qa-cards-container").innerHTML = `
                <div class="glass-container qa-card text-center">
                    <p style="color: var(--danger-color); font-weight:600;">Could not load report details from Flask server.</p>
                </div>
            `;
            return;
        }
    }
    
    // Display Report Overview
    renderReportOverview(reportData);
}

// Convert unsaved results array to matching report layout
function compileMockReport(payload) {
    const results = payload.results;
    const total = results.length;
    const avg = (key) => Math.round(results.reduce((acc, r) => acc + r[key], 0) / total);
    
    return {
        id: "offline",
        date: new Date().toISOString(),
        overall_score: avg("overall_score"),
        grammar_score: avg("grammar_score"),
        communication_score: avg("communication_score"),
        technical_score: avg("technical_score"),
        confidence_score: avg("confidence_score"),
        speed_score: avg("speed_score"),
        non_verbal_score: Math.round(results.reduce((acc, r) => acc + (r.eye_contact_ratio + r.smile_ratio)/2, 0) / total),
        strengths: ["Offline session finished successfully."],
        improvements: ["Connect to MySQL/SQLite backend to persist results."],
        answers: results
    };
}

// Update UI text and dials
function renderReportOverview(report) {
    // Title & Date
    document.getElementById("report-title").innerText = `Interview Performance Report #${report.id}`;
    
    const formattedDate = new Date(report.date).toLocaleDateString("en-US", {
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    document.getElementById("report-date").innerText = `Session Date: ${formattedDate}`;
    
    // Overall Score Dial
    const score = report.overall_score;
    document.getElementById("overall-score-val").innerText = score;
    const scoreWheel = document.getElementById("overall-score-wheel");
    scoreWheel.style.background = `conic-gradient(var(--primary-color) 0%, var(--secondary-color) ${score}%, rgba(255,255,255,0.05) ${score}% 100%)`;
    
    // Strengths Lists
    const strengthsContainer = document.getElementById("strengths-list");
    strengthsContainer.innerHTML = "";
    if (report.strengths && report.strengths.length > 0) {
        report.strengths.forEach(str => {
            const li = document.createElement("li");
            li.innerText = str;
            strengthsContainer.appendChild(li);
        });
    } else {
        strengthsContainer.innerHTML = "<li>No specific strengths recorded. Keep practicing!</li>";
    }
    
    // Improvements Lists
    const improvementsContainer = document.getElementById("improvements-list");
    improvementsContainer.innerHTML = "";
    if (report.improvements && report.improvements.length > 0) {
        report.improvements.forEach(imp => {
            const li = document.createElement("li");
            li.innerText = imp;
            improvementsContainer.appendChild(li);
        });
    } else {
        improvementsContainer.innerHTML = "<li>No serious issues detected. Great work!</li>";
    }
    
    // Render Charts
    renderRadarChart(report);
    
    // Render Question Cards
    renderQuestionCards(report.answers);
}

// Chart.js Radar Chart setup
function renderRadarChart(report) {
    const ctx = document.getElementById("scores-chart").getContext("2d");
    
    // Normalize dimensions into percentage scores (out of 100)
    const grammarPct = Math.round((report.grammar_score / 20) * 100);
    const commPct = Math.round((report.communication_score / 20) * 100);
    const techPct = Math.round((report.technical_score / 25) * 100);
    const confPct = Math.round((report.confidence_score / 20) * 100);
    const speedPct = Math.round((report.speed_score / 15) * 100);
    const nonVerbalPct = report.non_verbal_score;
    
    new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Grammar', 'Communication', 'Technical', 'Confidence', 'Pacing Rate', 'Body Language'],
            datasets: [{
                label: 'Performance %',
                data: [grammarPct, commPct, techPct, confPct, speedPct, nonVerbalPct],
                backgroundColor: 'rgba(99, 102, 241, 0.2)',
                borderColor: '#6366f1',
                borderWidth: 2,
                pointBackgroundColor: '#a855f7',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#6366f1'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    pointLabels: {
                        color: '#9ca3af',
                        font: {
                            family: 'Outfit',
                            size: 11,
                            weight: '600'
                        }
                    },
                    ticks: {
                        backdropColor: 'transparent',
                        color: '#6b7280',
                        font: {
                            size: 9
                        },
                        stepSize: 20
                    },
                    min: 0,
                    max: 100
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Generate dynamic question detail HTML blocks
function renderQuestionCards(answers) {
    const container = document.getElementById("qa-cards-container");
    container.innerHTML = "";
    
    answers.forEach((ans, index) => {
        const card = document.createElement("div");
        card.className = "glass-container qa-card";
        
        let scoreClass = "score-low";
        if (ans.overall_score >= 80) scoreClass = "score-high";
        else if (ans.overall_score >= 60) scoreClass = "score-mid";
        
        // Render detailed stats checklist
        let correctionsHtml = "";
        if (ans.corrections && ans.corrections.length > 0) {
            correctionsHtml = `
                <div style="margin-top: 15px;">
                    <div class="qa-lbl-heading">Grammar & Phrasing Corrections</div>
                    <div class="corrections-wrapper">
                        ${ans.corrections.map(c => `
                            <div class="correction-item">
                                <span class="correction-mistake">"${c.mistake}"</span>
                                <span class="correction-arrow">➔</span>
                                <span class="correction-suggest">"${c.suggestion}"</span>
                                <p style="color:var(--text-secondary); font-size:0.75rem; margin-top:4px;">Context: ...${c.context}...</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="qa-question-header">
                <h4>Question ${index + 1}: ${ans.question_text}</h4>
                <span class="score-badge ${scoreClass}">Score: ${ans.overall_score}/100</span>
            </div>
            
            <div class="qa-metrics-grid">
                <div class="qa-metric-box">
                    <div class="qa-metric-val">${ans.wpm} WPM</div>
                    <div class="qa-metric-lbl">Speed</div>
                </div>
                <div class="qa-metric-box">
                    <div class="qa-metric-val" style="color: ${ans.sentiment === 'Positive' ? 'var(--success-color)' : ans.sentiment === 'Negative' ? 'var(--danger-color)' : 'var(--warning-color)'};">${ans.sentiment}</div>
                    <div class="qa-metric-lbl">Sentiment Tone</div>
                </div>
                <div class="qa-metric-box">
                    <div class="qa-metric-val">${ans.filler_words_count}</div>
                    <div class="qa-metric-lbl">Filler Words</div>
                </div>
                <div class="qa-metric-box">
                    <div class="qa-metric-val">${ans.eye_contact_ratio}%</div>
                    <div class="qa-metric-lbl">Eye Contact</div>
                </div>
                <div class="qa-metric-box">
                    <div class="qa-metric-val">${ans.smile_ratio}%</div>
                    <div class="qa-metric-lbl">Smiling Face</div>
                </div>
            </div>
            
            <div class="qa-answer-block">
                <div class="qa-lbl-heading">Answer Transcript</div>
                <div class="qa-answer-text">"${ans.text}"</div>
            </div>
            
            ${correctionsHtml}
            
            <div style="margin-top: 20px;">
                <div class="qa-lbl-heading">AI Delivery Suggestions</div>
                <div class="qa-feedback-block">
                    ${ans.feedback_text}
                </div>
            </div>
        `;
        
        container.appendChild(card);
    });
}
