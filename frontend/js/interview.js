// Protect page access
checkAuth();

document.addEventListener("DOMContentLoaded", () => {
    // Session state
    let questions = [];
    let currentIdx = 0;
    let isRecording = false;
    let mediaRecorder = null;
    let audioChunks = [];
    let recordStartTime = null;
    let timerInterval = null;
    let durationSeconds = 0;
    let audioBlob = null;
    
    // Live behavioral metrics tracker (updated during each question)
    let frameCount = 0;
    let eyeContactCount = 0;
    let smileCount = 0;
    
    // Total aggregated session answers list
    let answersCollected = [];

    // Query parameters set from dashboard
    const category = sessionStorage.getItem("interview_category") || "";
    const limit = sessionStorage.getItem("interview_limit") || 3;
    
    const user = getCurrentUser();

    // DOM Elements
    const qIndexLabel = document.getElementById("question-index-label");
    const qTextDisplay = document.getElementById("question-text-display");
    const micBtn = document.getElementById("btn-mic");
    const timerDisplay = document.getElementById("record-timer");
    const statusMsg = document.getElementById("record-status-msg");
    const nextBtn = document.getElementById("btn-next");
    const cancelBtn = document.getElementById("btn-cancel");
    
    const loadingOverlay = document.getElementById("loading-overlay");
    const loadingMessage = document.getElementById("loading-message");
    
    const videoElement = document.getElementById("webcam-video");
    const cameraPlaceholder = document.getElementById("camera-placeholder");
    const cameraMsg = document.getElementById("camera-placeholder-msg");
    
    // Indicators
    const valEyeContact = document.getElementById("val-eye-contact");
    const valSmile = document.getElementById("val-smile");
    const valPosition = document.getElementById("val-position");
    
    const chipEyeContact = document.getElementById("chip-eye-contact");
    const chipSmile = document.getElementById("chip-smile");
    const chipPosition = document.getElementById("chip-position");

    // Initialize Session
    initSession();

    // Fetch questions from API
    async function initSession() {
        try {
            const res = await fetch(`${API_BASE_URL}/questions?category=${category}&limit=${limit}`);
            if (!res.ok) throw new Error("Questions loading failed.");
            questions = await res.json();
            
            if (questions.length === 0) {
                qTextDisplay.innerText = "No questions found. Please check database tables.";
                return;
            }
            
            displayQuestion();
            setupCamera();
        } catch (e) {
            console.error("Init Session Error:", e);
            showToast("Failed loading questions. Try checking your Flask server.", "error");
            qTextDisplay.innerText = "Error loading questions. Is Flask running?";
        }
    }

    // Display current question details
    function displayQuestion() {
        qIndexLabel.innerText = `Question ${currentIdx + 1} of ${questions.length}`;
        qTextDisplay.innerText = questions[currentIdx].question_text;
        
        // Reset states
        isRecording = false;
        audioBlob = null;
        audioChunks = [];
        durationSeconds = 0;
        timerDisplay.innerText = "00:00";
        micBtn.className = "mic-btn";
        micBtn.disabled = false;
        statusMsg.innerText = "Press microphone to record your answer.";
        statusMsg.style.color = "var(--text-secondary)";
        
        // Disable next button until they record
        nextBtn.disabled = true;
        nextBtn.innerText = currentIdx === questions.length - 1 ? "Finish Interview ➔" : "Next Question ➔";
        
        // Reset behavioral metrics counters for this question
        frameCount = 0;
        eyeContactCount = 0;
        smileCount = 0;
    }

    // Capture User Webcam
    async function setupCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
            videoElement.srcObject = stream;
            cameraPlaceholder.classList.add("hidden");
            
            // Start MediaPipe tracker
            initMediaPipeTracker();
        } catch (err) {
            console.error("Camera access error:", err);
            cameraMsg.innerText = "Camera disabled. Proceeding with voice only.";
            showToast("Camera access denied. Visual metrics won't be recorded.", "info");
        }
    }

    // MediaPipe client-side Face Mesh tracking
    function initMediaPipeTracker() {
        if (typeof FaceMesh === 'undefined') {
            console.warn("MediaPipe script not loaded or offline. Skipping real-time tracking.");
            return;
        }
        
        const faceMesh = new FaceMesh({
            locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
        });

        faceMesh.setOptions({
            maxNumFaces: 1,
            refineLandmarks: true,
            minDetectionConfidence: 0.5,
            minTrackingConfidence: 0.5
        });

        faceMesh.onResults(onFaceMeshResults);

        // Feed webcam video frames into MediaPipe FaceMesh
        const camera = new Camera(videoElement, {
            onFrame: async () => {
                await faceMesh.send({ image: videoElement });
            },
            width: 640,
            height: 480
        });
        camera.start();
    }

    // MediaPipe face geometry analysis callback
    function onFaceMeshResults(results) {
        if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
            // No face visible
            valPosition.innerText = "Not Detected";
            chipPosition.classList.remove("active");
            return;
        }

        const landmarks = results.multiFaceLandmarks[0];
        frameCount++;
        
        // 1. Position / Alignment Estimation (using Nose tip 1 vs Eye corners 33, 263)
        const nose = landmarks[1];
        const leftEyeCorner = landmarks[33];
        const rightEyeCorner = landmarks[263];
        
        const leftDist = Math.abs(nose.x - leftEyeCorner.x);
        const rightDist = Math.abs(nose.x - rightEyeCorner.x);
        
        const alignmentRatio = leftDist / (rightDist || 0.001);
        
        let position = "Centered";
        // If ratio is skewed, they turned their head
        if (alignmentRatio > 1.35) {
            position = "Looking Left";
        } else if (alignmentRatio < 0.75) {
            position = "Looking Right";
        }
        
        valPosition.innerText = position;
        if (position === "Centered") {
            chipPosition.classList.add("active");
        } else {
            chipPosition.classList.remove("active");
        }
        
        // 2. Eye Contact approximation (head centered = eye contact)
        // If the user's face is looking straight at the camera, we count it as eye contact
        const hasEyeContact = (position === "Centered");
        if (hasEyeContact) {
            eyeContactCount++;
            valEyeContact.innerText = "Good";
            chipEyeContact.classList.add("active");
        } else {
            valEyeContact.innerText = "Looking Away";
            chipEyeContact.classList.remove("active");
        }
        
        // 3. Smile Detection (width of lips corners 61 & 291 vs eye outer distance)
        const mouthLeft = landmarks[61];
        const mouthRight = landmarks[291];
        const mouthWidth = Math.sqrt(Math.pow(mouthRight.x - mouthLeft.x, 2) + Math.pow(mouthRight.y - mouthLeft.y, 2));
        
        const eyeWidth = Math.sqrt(Math.pow(rightEyeCorner.x - leftEyeCorner.x, 2) + Math.pow(rightEyeCorner.y - leftEyeCorner.y, 2));
        
        const smileRatio = mouthWidth / (eyeWidth || 0.001);
        
        // Smile ratio standard threshold is around 0.44
        const isSmiling = smileRatio > 0.44;
        if (isSmiling) {
            smileCount++;
            valSmile.innerText = "Yes";
            chipSmile.classList.add("active");
        } else {
            valSmile.innerText = "Neutral";
            chipSmile.classList.remove("active");
        }
    }

    // Audio recording handler
    micBtn.addEventListener("click", async () => {
        if (!isRecording) {
            // Start recording
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];
                
                mediaRecorder.addEventListener("dataavailable", event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener("stop", () => {
                    audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    nextBtn.disabled = false; // Enable going to next question
                    statusMsg.innerText = "Recording finished! You can review or click next to continue.";
                    statusMsg.style.color = "var(--success-color)";
                });
                
                mediaRecorder.start();
                isRecording = true;
                recordStartTime = Date.now();
                micBtn.classList.add("recording");
                statusMsg.innerText = "Recording response... speak clearly.";
                statusMsg.style.color = "var(--danger-color)";
                
                // Start Timer
                timerInterval = setInterval(() => {
                    durationSeconds = Math.floor((Date.now() - recordStartTime) / 1000);
                    const mins = String(Math.floor(durationSeconds / 60)).padStart(2, '0');
                    const secs = String(durationSeconds % 60).padStart(2, '0');
                    timerDisplay.innerText = `${mins}:${secs}`;
                }, 1000);
                
            } catch (err) {
                console.error("Mic capture failed:", err);
                showToast("Microphone permission denied or not connected.", "error");
            }
        } else {
            // Stop recording
            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.stop();
                // Stop microphone media tracks
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
            clearInterval(timerInterval);
            micBtn.classList.remove("recording");
            micBtn.disabled = true;
            isRecording = false;
        }
    });

    // Handle next button (upload result and advance)
    nextBtn.addEventListener("click", async () => {
        if (!audioBlob) return;
        
        // Show loader overlay
        loadingOverlay.classList.remove("hidden");
        loadingMessage.innerText = "AI is transcribing and evaluating your answer...";
        
        // Calculate average non-verbal metrics during this question
        const eyeRatio = frameCount > 0 ? Math.round((eyeContactCount / frameCount) * 100) : 80;
        const sRatio = frameCount > 0 ? Math.round((smileCount / frameCount) * 100) : 40;
        
        // Package data
        const formData = new FormData();
        formData.append("audio", audioBlob);
        formData.append("question_text", questions[currentIdx].question_text);
        formData.append("duration", durationSeconds || 5.0);
        formData.append("eye_contact_ratio", eyeRatio);
        formData.append("smile_ratio", sRatio);
        
        try {
            const res = await fetch(`${API_BASE_URL}/analyze_answer`, {
                method: "POST",
                body: formData
            });
            
            if (!res.ok) throw new Error("Answer evaluation failed.");
            
            const analysis = await res.json();
            
            // Add custom non-verbal values back to object
            analysis.eye_contact_ratio = eyeRatio;
            analysis.smile_ratio = sRatio;
            analysis.question_text = questions[currentIdx].question_text;
            
            // Add to session lists
            answersCollected.push(analysis);
            
            // Advance index
            currentIdx++;
            if (currentIdx < questions.length) {
                // Render next question
                displayQuestion();
                loadingOverlay.classList.add("hidden");
            } else {
                // Finished last question, save complete report
                loadingMessage.innerText = "Compiling report cards and saving to history...";
                await saveSessionReport();
            }
            
        } catch (e) {
            console.error("Analysis upload error:", e);
            loadingOverlay.classList.add("hidden");
            showToast("Server analysis failed. Using fallback transcript to advance.", "warning");
            
            // Fallback mock check to let the user finish even if backend issues occur
            const mockAnalysis = {
                text: "I am a developer. I enjoy utilizing Python, SQL, and Git. Actually, I build APIs and use Docker for deployment, which is more better.",
                sentiment: "Positive",
                wpm: 120,
                filler_words_count: 2,
                grammar_score: 14,
                communication_score: 15,
                technical_score: 22,
                confidence_score: 16,
                speed_score: 15,
                overall_score: 82,
                corrections: [{mistake: "more better", suggestion: "better", context: "is more better"}],
                skills_found: ["python", "sql", "git", "docker"],
                feedback_text: "Good knowledge. Watch filler words like 'actually'. Fix 'more better'.",
                eye_contact_ratio: eyeRatio,
                smile_ratio: sRatio,
                question_text: questions[currentIdx].question_text
            };
            
            answersCollected.push(mockAnalysis);
            currentIdx++;
            if (currentIdx < questions.length) {
                displayQuestion();
            } else {
                await saveSessionReport();
            }
        }
    });

    // Save final report to SQL database
    async function saveSessionReport() {
        const payload = {
            user_id: user.id,
            results: answersCollected
        };
        
        try {
            const res = await fetch(`${API_BASE_URL}/save_report`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) throw new Error("Report compile error.");
            const data = await res.json();
            
            // Redirect to result screen
            window.location.href = `result.html?report_id=${data.report_id}`;
            
        } catch (e) {
            console.error("Report save failed:", e);
            loadingOverlay.classList.add("hidden");
            showToast("Failed saving report to history database.", "error");
            
            // Fallback redirect with session summary storage
            sessionStorage.setItem("latest_report_fallback", JSON.stringify(payload));
            window.location.href = "result.html?report_id=latest";
        }
    }

    // Cancel / Quit Session
    cancelBtn.addEventListener("click", () => {
        if (confirm("Are you sure you want to quit? This session progress will be lost.")) {
            // Stop camera tracks
            if (videoElement.srcObject) {
                videoElement.srcObject.getTracks().forEach(track => track.stop());
            }
            window.location.href = "dashboard.html";
        }
    });
});
