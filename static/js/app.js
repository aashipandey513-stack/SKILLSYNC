
// ===================================================
// === AUDIO RECORDER LOGIC (ALL PAGES) ===
// ===================================================

// This block runs on the Interview, Competition, and Soft Skills pages
if (document.title.includes("Mock Interview") || document.title.includes("Competition Practice") || document.title.includes("Soft Skills")) {
    
    console.log("Audio Recorder JS loaded."); // Check F12 Console

    // --- DOM Element References ---
    const startBtn = document.getElementById('start-record-btn');
    const stopBtn = document.getElementById('stop-record-btn');
    const rerecordBtn = document.getElementById('re-record-btn');
    const playbackBtn = document.getElementById('playback-btn');
    const getFeedbackBtn = document.getElementById('get-feedback-btn');

    const idleStateDiv = document.getElementById('idle-state');
    const recordingStateDiv = document.getElementById('recording-state');
    const timerDisplay = document.getElementById('timer');
    
    const loadingSpinner = document.getElementById('loading-spinner');
    const feedbackSection = document.getElementById('feedback-section');
    const audioPlayer = document.getElementById('audio-playback'); // The new <audio> element

    // --- Audio Recording Variables ---
    let mediaRecorder;
    let audioChunks = [];
    let audioBlob;
    let audioUrl; // URL for playback
    let timerInterval;
    let seconds = 0;

    // --- Core Functions ---

    /**
     * Starts the audio recording process.
     */
    async function startRecording() {
        console.log("Attempting to start recording...");
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log("Microphone access granted.");
            
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = []; // Clear old chunks

            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                console.log("Recording stopped. Audio chunks:", audioChunks.length);
                audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                
                if (audioUrl) {
                    URL.revokeObjectURL(audioUrl);
                }
                
                audioUrl = URL.createObjectURL(audioBlob);
                audioPlayer.src = audioUrl;
                console.log("Audio blob and playback URL created.");

                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorder.start();
            console.log("Recorder state:", mediaRecorder.state);
            updateUIState('recording');
            startTimer();

        } catch (err) {
            console.error('Error accessing microphone:', err);
            alert('Could not access microphone. Please ensure permission is granted in your browser (check the lock icon in the URL bar).');
        }
    }

    /**
     * Stops the audio recording.
     */
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
        updateUIState('stopped'); // Go to the new 'stopped' state
        stopTimer();
    }
    
    /**
     * Plays the recorded audio.
     */
    function playRecording() {
        if (audioPlayer && audioPlayer.src) {
            console.log("Playing audio...");
            audioPlayer.play();
        } else {
            console.error("No audio source to play.");
        }
    }

    /**
     * Resets the recording interface.
     */
    function reRecord() {
        if (audioUrl) {
            URL.revokeObjectURL(audioUrl); // Clean up memory
            audioUrl = null;
            audioPlayer.src = '';
        }
        audioBlob = null;
        updateUIState('idle'); // Go back to idle state
        resetTimer();
        feedbackSection.innerHTML = ''; // Clear old feedback
    }

    /**
     * Sends the recorded audio to the backend for feedback.
     */
    async function getFeedback() {
        if (!audioBlob) {
            alert('No audio recorded.');
            return;
        }

        console.log("Getting AI feedback...");
        updateUIState('loading'); // Show loading spinner

        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'interview_answer.wav');
        
        let endpoint = '';
        let question = '';
        let context = 'interview'; // Default context

        if (document.title.includes("Competition Practice")) {
            endpoint = '/process-competition-audio';
            question = document.getElementById('competition-topic').innerText;
            context = 'competition';
        
        } else if (document.title.includes("Soft Skills")) {
            endpoint = '/process-soft-skills-audio';
            question = document.getElementById('skill-prompt').innerText;
            context = 'soft-skills';

        } else { // Default to Mock Interview
            endpoint = '/process-interview-audio';
            question = document.querySelector('h3.text-xl').innerText;
        }
        
        formData.append('question', question);
        formData.append('context', context);
        
        console.log(`Sending audio to ${endpoint}... THIS WILL TAKE A LONG TIME.`);

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                body: formData,
            });

            console.log("Server responded.");
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }

            const feedbackData = await response.json();
            
            console.log('Feedback received:', feedbackData);
            displayFeedback(feedbackData); 
            updateUIState('feedback'); // Show feedback

        } catch (err) {
            console.error('Error getting feedback:', err);
            alert(`Failed to get AI feedback. The server might be busy or an error occurred. Check the F12 console. Error: ${err.message}`);
            updateUIState('stopped'); // Go back to 'stopped' state on error
        }
    }

    /**
     * Updates the UI elements based on the current state.
     */
    function updateUIState(state) {
        console.log("Updating UI state to:", state);
        
        // Hide all conditional elements
        idleStateDiv.classList.add('hidden');
        recordingStateDiv.classList.add('hidden');
        loadingSpinner.classList.add('hidden');
        feedbackSection.classList.add('hidden');
        
        startBtn.classList.add('hidden');
        stopBtn.classList.add('hidden');
        rerecordBtn.classList.add('hidden');
        playbackBtn.classList.add('hidden');
        getFeedbackBtn.classList.add('hidden');

        if (state === 'idle') {
            idleStateDiv.classList.remove('hidden');
            startBtn.classList.remove('hidden');
        } 
        else if (state === 'recording') {
            recordingStateDiv.classList.remove('hidden');
            stopBtn.classList.remove('hidden');
        } 
        else if (state === 'stopped') {
            idleStateDiv.classList.remove('hidden'); // Show mic icon again
            rerecordBtn.classList.remove('hidden');
            playbackBtn.classList.remove('hidden');
            getFeedbackBtn.classList.remove('hidden');
        } 
        else if (state === 'loading') {
            loadingSpinner.classList.remove('hidden');
        } 
        else if (state === 'feedback') {
            feedbackSection.classList.remove('hidden');
            rerecordBtn.classList.remove('hidden');
            playbackBtn.classList.remove('hidden');
            getFeedbackBtn.classList.remove('hidden');
        }
    }

    // --- Timer Functions ---
    function startTimer() {
        if(timerInterval) clearInterval(timerInterval); // Clear old timer
        seconds = 0;
        timerDisplay.textContent = '00:00';
        timerInterval = setInterval(() => {
            seconds++;
            const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
            const secs = (seconds % 60).toString().padStart(2, '0');
            timerDisplay.textContent = `${mins}:${secs}`;
        }, 1000);
        console.log("Timer started.");
    }

    function stopTimer() {
        clearInterval(timerInterval);
        console.log("Timer stopped.");
    }

    function resetTimer() {
        stopTimer();
        seconds = 0;
        timerDisplay.textContent = '00:00';
    }
    
    /**
     * Renders feedback data into the DOM.
     */
    function displayFeedback(data) {
        if (!feedbackSection.innerHTML.trim()) {
            feedbackSection.innerHTML = `
            <div class="bg-white p-8 rounded-lg shadow-sm">
                <div class="mb-6 pb-6 border-b">
                    <h3 class="text-xl font-semibold text-gray-800 mb-2">Overall Performance</h3>
                    <div class="flex items-center space-x-3">
                        <span id="feedback-score" class="text-5xl font-bold text-blue-600">0%</span>
                        <span id="feedback-rating" class="text-2xl font-semibold text-gray-600"></span>
                    </div>
                </div>
                <div class="flex flex-col lg:flex-row gap-8">
                    <div class="flex-grow">
                        <h4 class="text-lg font-semibold text-gray-800 mb-3">Detailed Analysis</h4>
                        <table id="feedback-analysis-table" class="w-full"><tbody class="text-sm"></tbody></table>
                        <h4 class="text-lg font-semibold text-gray-800 mt-6 mb-3">Your Response (Transcribed)</h4>
                        <p id="feedback-transcript" class="p-4 bg-gray-50 rounded-md text-gray-700 leading-relaxed"></p>
                    </div>
                    <div class="w-full lg:w-2/5 flex-shrink-0">
                        <h4 class="text-lg font-semibold text-green-600 mb-3"><i class="fas fa-check-circle"></i> Strengths</h4>
                        <ul id="feedback-strengths-list" class="list-disc list-inside space-y-1 text-gray-700"></ul>
                        <h4 class="text-lg font-semibold text-yellow-600 mt-6 mb-3"><i class="fas fa-exclamation-triangle"></i> Areas to Improve</h4>
                        <ul id="feedback-improvements-list" class="list-disc list-inside space-y-1 text-gray-700"></ul>
                        <h4 class="text-lg font-semibold text-blue-600 mt-6 mb-3"><i class="fas fa-magic"></i> AI-Powered Suggestions</h4>
                        <ul id="feedback-suggestions-list" class="list-disc list-inside space-y-1 text-gray-700"></ul>
                    </div>
                </div>
            </div>`;
        }

        const scoreEl = document.getElementById('feedback-score');
        const ratingEl = document.getElementById('feedback-rating');
        if (scoreEl) scoreEl.textContent = `${data.overall_score}%`;
        
        if (ratingEl) {
            if (data.overall_score >= 85) {
                ratingEl.textContent = 'Excellent';
                ratingEl.className = 'text-2xl font-semibold text-green-600';
            } else if (data.overall_score >= 70) {
                ratingEl.textContent = 'Good';
                ratingEl.className = 'text-2xl font-semibold text-blue-600';
            } else {
                ratingEl.textContent = 'Needs Improvement';
                ratingEl.className = 'text-2xl font-semibold text-yellow-600';
            }
        }

        const tableBody = document.getElementById('feedback-analysis-table')?.getElementsByTagName('tbody')[0];
        if (tableBody) {
            tableBody.innerHTML = '';
            for (const [key, value] of Object.entries(data.analysis)) {
                const row = tableBody.insertRow();
                row.innerHTML = `
                    <td class="py-2 pr-4 font-medium text-gray-700">${key}</td>
                    <td class="py-2 w-full">
                        <div class="w-full bg-gray-200 rounded-full h-2.5">
                            <div class="bg-blue-600 h-2.5 rounded-full" style="width: ${value}%"></div>
                        </div>
                    </td>
                    <td class="py-2 pl-4 font-medium text-gray-900">${value}%</td>
                `;
            }
        }

        const transcriptEl = document.getElementById('feedback-transcript');
        if (transcriptEl) transcriptEl.textContent = data.transcript;

        function populateList(listId, items) {
            const ul = document.getElementById(listId);
            if (!ul) return;
            ul.innerHTML = '';
            if (items && items.length > 0) {
                items.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item;
                    ul.appendChild(li);
                });
            } else {
                ul.innerHTML = '<li class="text-gray-400">N/A</li>';
            }
        }
        
        populateList('feedback-strengths-list', data.strengths);
        populateList('feedback-improvements-list', data.improvements);
        populateList('feedback-suggestions-list', data.suggestions);
    }

    // --- Event Listeners ---
    if(startBtn) startBtn.addEventListener('click', startRecording);
    if(stopBtn) stopBtn.addEventListener('click', stopRecording);
    if(rerecordBtn) rerecordBtn.addEventListener('click', reRecord);
    if(playbackBtn) playbackBtn.addEventListener('click', playRecording); // New listener
    if(getFeedbackBtn) getFeedbackBtn.addEventListener('click', getFeedback);

    // --- Initial State ---
    if (startBtn) { // Only run if we are on a recorder page
        updateUIState('idle'); // Set the initial state
    }
}


// ===================================================
// === APTITUDE QUIZ LOGIC ===
// ===================================================

if (document.title.includes("Aptitude Test") && window.location.pathname.includes("/aptitude/quiz")) {
    
    console.log("Aptitude Quiz JS loaded.");

    // --- Global Quiz Variables ---
    let allQuestions = [];
    let userAnswers = {};
    let currentQuestionIndex = 0;
    let timerInterval;
    let totalTime = 1800; // 30 minutes * 60 seconds

    // --- DOM Elements ---
    const questionCounterEl = document.getElementById('question-counter');
    const timerEl = document.getElementById('quiz-timer');
    const categoryEl = document.getElementById('question-category');
    const questionEl = document.getElementById('question-text');
    const optionsEl = document.getElementById('options-container');
    const quizContainerEl = document.getElementById('quiz-container');
    
    const loadingEl = document.getElementById('loading-state');
    const endEl = document.getElementById('end-state');
    const quizScoreEl = document.getElementById('quiz-score');

    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');
    const submitBtn = document.getElementById('submit-btn');

    // --- Core Functions ---

    async function loadQuestions() {
        try {
            const response = await fetch('/api/quiz-questions');
            if (!response.ok) throw new Error('Failed to load questions');
            
            allQuestions = await response.json();
            if (allQuestions.length === 0) throw new Error('No questions received');
            
            allQuestions.forEach((_, index) => {
                userAnswers[index] = null;
            });
            
            renderQuestion(currentQuestionIndex);
            startTimer(); // Start the timer *after* questions are loaded
        } catch (err) {
            console.error(err);
            questionEl.textContent = 'Error loading quiz. Please try again.';
            optionsEl.innerHTML = '';
        }
    }

    function renderQuestion(index) {
        if (index < 0 || index >= allQuestions.length) return;
        
        const q = allQuestions[index];
        
        questionCounterEl.textContent = `Question ${index + 1} of ${allQuestions.length}`;
        categoryEl.textContent = q.category;
        questionEl.textContent = q.question;
        optionsEl.innerHTML = ''; // Clear old options

        q.options.forEach(option => {
            const label = document.createElement('label');
            label.className = 'block w-full p-4 border rounded-lg hover:bg-gray-50 cursor-pointer';
            
            const radio = document.createElement('input');
            radio.type = 'radio';
            radio.name = 'option';
            radio.value = option;
            radio.className = 'mr-3';
            
            if (userAnswers[index] === option) {
                radio.checked = true;
            }

            radio.addEventListener('change', () => {
                userAnswers[index] = option;
            });

            label.appendChild(radio);
            label.appendChild(document.createTextNode(option));
            optionsEl.appendChild(label);
        });

        updateNavButtons(index);
    }

    function updateNavButtons(index) {
        prevBtn.disabled = (index === 0);
        
        if (index === allQuestions.length - 1) {
            nextBtn.classList.add('hidden');
            submitBtn.classList.remove('hidden');
        } else {
            nextBtn.classList.remove('hidden');
            submitBtn.classList.add('hidden');
        }
    }

    function startTimer() {
        if(timerInterval) clearInterval(timerInterval); // Clear any existing timer

        timerInterval = setInterval(() => {
            totalTime--;
            
            const minutes = Math.floor(totalTime / 60).toString().padStart(2, '0');
            const seconds = (totalTime % 60).toString().padStart(2, '0');
            timerEl.textContent = `${minutes}:${seconds}`;

            if (totalTime <= 0) {
                clearInterval(timerInterval);
                timerEl.textContent = '00:00';
                submitTest();
            }
        }, 1000);
    }

    async function submitTest() {
        clearInterval(timerInterval);
        
        quizContainerEl.classList.add('hidden');
        loadingEl.classList.remove('hidden');
        prevBtn.parentElement.classList.add('hidden');

        try {
            const response = await fetch('/api/submit-quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ answers: userAnswers })
            });
            
            if (!response.ok) throw new Error('Failed to submit test');
            
            const result = await response.json();
            
            loadingEl.classList.add('hidden');
            endEl.classList.remove('hidden');
            quizScoreEl.textContent = `${result.score} / ${result.total}`;

        } catch (err) {
            console.error(err);
            loadingEl.classList.add('hidden');
            quizContainerEl.classList.remove('hidden');
            prevBtn.parentElement.classList.remove('hidden');
            alert('Error submitting test. Please try again.');
        }
    }

    // --- Event Listeners ---
    prevBtn.addEventListener('click', () => {
        if (currentQuestionIndex > 0) {
            currentQuestionIndex--;
            renderQuestion(currentQuestionIndex);
        }
    });

    nextBtn.addEventListener('click', () => {
        if (currentQuestionIndex < allQuestions.length - 1) {
            currentQuestionIndex++;
            renderQuestion(currentQuestionIndex);
        }
    });

    submitBtn.addEventListener('click', submitTest);

    // --- Initialize ---
    loadQuestions();
}


// ===================================================
// === ANALYTICS PAGE LOGIC ===
// ===================================================

if (document.title.includes("Analytics")) {

    console.log("Analytics JS loaded.");

    // --- Tab Handling ---
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;

            tabButtons.forEach(btn => btn.classList.remove('tab-btn-active'));
            button.classList.add('tab-btn-active');

            tabContents.forEach(content => content.classList.remove('tab-content-active'));
            document.getElementById(`tab-${tabName}`).classList.add('tab-content-active');
        });
    });

    // --- DOM Elements ---
    const chartCanvas = document.getElementById('performanceChart');
    const activityListEl = document.getElementById('recent-activity-list');
    const summarySessionsEl = document.getElementById('summary-sessions');
    const summaryScoreEl = document.getElementById('summary-score');
    
    const radarCanvas = document.getElementById('skillsRadarChart');
    const skillBreakdownEl = document.getElementById('skill-breakdown-list');
    const historyTableEl = document.getElementById('session-history-table')?.getElementsByTagName('tbody')[0];
    const achievementsGridEl = document.getElementById('achievements-grid');


    async function loadAnalytics() {
        try {
            const response = await fetch('/api/analytics-data');
            if (!response.ok) throw new Error('Failed to load analytics');
            
            const data = await response.json();
            
            renderPerformanceChart(data.performanceTrends);
            renderRecentActivity(data.recentActivity);
            renderWeekSummary(data.weekSummary);
            
            renderSkillsRadar(data.skillsAnalysis.radar);
            renderSkillBreakdown(data.skillsAnalysis.breakdown);

            renderSessionHistory(data.sessionHistory);

            renderAchievements(data.achievements);

        } catch (err) {
            console.error(err);
            if(chartCanvas) chartCanvas.parentElement.innerHTML = '<p class="text-red-500">Could not load chart data.</p>';
        }
    }

    // --- TAB 1: PROGRESS ---
    function renderPerformanceChart(chartData) {
        if (!chartCanvas) return;
        new Chart(chartCanvas.getContext('2d'), {
            type: 'line', data: chartData,
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { y: { beginAtZero: true, max: 100 } },
                plugins: { legend: { position: 'bottom' } },
                interaction: { mode: 'index', intersect: false },
            }
        });
    }
    function renderRecentActivity(activity) {
        if (!activity || activity.length === 0 || !activityListEl) return;
        activityListEl.innerHTML = '';
        activity.forEach(item => {
            let iconClass = item.module === 'Mock Interview' ? 'fa-microphone-alt text-blue-500' : 'fa-users text-purple-500';
            activityListEl.innerHTML += `
                <div class="flex justify-between items-center">
                    <div class="flex items-center space-x-3">
                        <i class="fas ${iconClass}"></i>
                        <div>
                            <p class="font-semibold text-gray-800">${item.module}</p>
                            <p class="text-xs text-gray-500">${item.type}</p>
                        </div>
                    </div>
                    <div class="text-right">
                        <p class="font-bold text-gray-900">${item.score}</p>
                        <p class="text-xs text-gray-500">${item.date}</p>
                    </div>
                </div>`;
        });
    }
    function renderWeekSummary(summary) {
        if (summarySessionsEl) summarySessionsEl.textContent = summary.sessions;
        if (summaryScoreEl) summaryScoreEl.textContent = `${summary.avg_score}%`;
    }

    // --- TAB 2: SKILLS ANALYSIS ---
    function renderSkillsRadar(radarData) {
        if (!radarCanvas) return;
        new Chart(radarCanvas.getContext('2d'), {
            type: 'radar',
            data: {
                labels: radarData.labels,
                datasets: [{
                    label: 'Your Skills',
                    data: radarData.data,
                    fill: true,
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    borderColor: 'rgb(59, 130, 246)',
                    pointBackgroundColor: 'rgb(59, 130, 246)',
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                scales: { r: { beginAtZero: true, max: 100, ticks: { display: false } } }
            }
        });
    }
    function renderSkillBreakdown(breakdown) {
        if (!skillBreakdownEl) return;
        skillBreakdownEl.innerHTML = '';
        breakdown.forEach(skill => {
            let color = skill.rating === 'Excellent' ? 'bg-green-500' : 'bg-blue-500';
            skillBreakdownEl.innerHTML += `
                <div>
                    <div class="flex justify-between mb-1">
                        <span class="text-base font-medium text-gray-700">${skill.name}</span>
                        <span class="text-sm font-medium text-gray-700">${skill.score}% - ${skill.rating}</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2.5">
                        <div class="${color} h-2.5 rounded-full" style="width: ${skill.score}%"></div>
                    </div>
                </div>`;
        });
    }

    // --- TAB 3: SESSION HISTORY ---
    function renderSessionHistory(history) {
        if (!historyTableEl) return;
        historyTableEl.innerHTML = '';
        history.forEach(session => {
            historyTableEl.innerHTML += `
                <tr class="text-sm">
                    <td class="px-6 py-4 whitespace-nowrap">${session.date}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${session.module}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${session.type}</td>
                    <td class="px-6 py-4 whitespace-nowrap font-medium">${session.score}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${session.duration}</td>
                    <td class="px-6 py-4 whitespace-nowrap">${session.details}</td>
                </tr>`;
        });
    }

    // --- TAB 4: ACHIEVEMENTS ---
    function renderAchievements(achievements) {
        if (!achievementsGridEl) return;
        achievementsGridEl.innerHTML = '';
        achievements.forEach(ach => {
            let color = ach.status === 'Completed' ? 'green' : 'gray';
            let progressHtml = ach.status === 'Completed'
                ? `<p class="text-sm font-medium text-${color}-600">${ach.status}</p>`
                : `<p class="text-sm font-medium text-yellow-600">${ach.status}</p>
                   <div class="w-full bg-gray-200 rounded-full h-1.5 mt-2">
                       <div class="bg-yellow-500 h-1.5 rounded-full" style="width: ${ach.progress}%"></div>
                   </div>`;
            
            achievementsGridEl.innerHTML += `
                <div class="bg-gray-50 rounded-lg p-5 flex items-center space-x-4">
                    <div class="flex-shrink-0 w-16 h-16 rounded-full bg-${color}-100 flex items-center justify-center">
                        <i class="fas ${ach.icon} text-3xl text-${color}-600"></i>
                    </div>
                    <div class="flex-grow">
                        <h4 class="text-lg font-semibold text-gray-800">${ach.name}</h4>
                        <p class="text-sm text-gray-500">${ach.desc}</p>
                        <div class="mt-2">${progressHtml}</div>
                    </div>
                </div>`;
        });
    }

    // --- Initialize ---
    loadAnalytics();
}
