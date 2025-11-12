// SkillSync/static/js/app.js

// Check if the script is running on the correct page
if (document.title.includes("Mock Interview")) {
    
    // --- DOM Element References ---
    const startBtn = document.getElementById('start-record-btn');
    const stopBtn = document.getElementById('stop-record-btn');
    const rerecordBtn = document.getElementById('re-record-btn');
    const getFeedbackBtn = document.getElementById('get-feedback-btn');

    const idleStateDiv = document.getElementById('idle-state');
    const recordingStateDiv = document.getElementById('recording-state');
    const timerDisplay = document.getElementById('timer');
    
    const loadingSpinner = document.getElementById('loading-spinner');
    const feedbackSection = document.getElementById('feedback-section');

    // --- Audio Recording Variables ---
    let mediaRecorder;
    let audioChunks = [];
    let audioBlob;
    let timerInterval;
    let seconds = 0;

    // --- Core Functions ---

    /**
     * Starts the audio recording process.
     */
    async function startRecording() {
        try {
            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Initialize MediaRecorder
            mediaRecorder = new MediaRecorder(stream);
            
            // --- Event Handlers for MediaRecorder ---
            mediaRecorder.ondataavailable = (event) => {
                audioChunks.push(event.data);
            };

            mediaRecorder.onstop = () => {
                // Combine audio chunks into a single Blob
                audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                audioChunks = []; // Clear chunks for next recording
                
                // Stop microphone tracks
                stream.getTracks().forEach(track => track.stop());
            };

            // Start recording
            mediaRecorder.start();
            
            // --- UI Updates for "Recording" state ---
            updateUIState('recording');
            startTimer();

        } catch (err) {
            console.error('Error accessing microphone:', err);
            alert('Could not access microphone. Please ensure permission is granted.');
        }
    }

    /**
     * Stops the audio recording.
     */
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
        updateUIState('stopped');
        stopTimer();
    }

    /**
     * Resets the recording interface.
     */
    function reRecord() {
        audioBlob = null;
        updateUIState('idle');
        resetTimer();
    }

    /**
     * Sends the recorded audio to the backend for feedback.
     */
    async function getFeedback() {
        if (!audioBlob) {
            alert('No audio recorded.');
            return;
        }

        // --- UI Update for "Loading" state ---
        updateUIState('loading');

        // Create form data to send
        const formData = new FormData();
        formData.append('audio_file', audioBlob, 'interview_answer.wav');
        
        // You can add more data
        formData.append('question', 'Tell me about yourself...');
        formData.append('type', 'HR');

        try {
            // --- API Call to FastAPI Backend ---
let endpoint = '/process-interview-audio';
let question = 'Tell me about yourself...'; // Default question

if (document.title.includes("Competition Practice")) {
    endpoint = '/process-competition-audio';
    question = document.getElementById('competition-topic').innerText;
    formData.append('context', 'competition');

} else if (document.title.includes("Soft Skills")) {
    endpoint = '/process-soft-skills-audio';
    question = document.getElementById('skill-prompt').innerText;
    formData.append('context', 'soft-skills');

} else { // Default to Mock Interview
    endpoint = '/process-interview-audio';
    // question = document.getElementById('interview-question').innerText; // (If you make it dynamic)
    formData.append('context', 'interview');
}

// Add the question to the form data
formData.append('question', question);

const response = await fetch(endpoint, {
    method: 'POST',
    body: formData,
});

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const feedbackData = await response.json();
            
            // --- UI Update for "Feedback" state ---
            console.log('Feedback received:', feedbackData);
            // We will build the function to display this data next
            displayFeedback(feedbackData); 
            updateUIState('feedback');

        } catch (err) {
            console.error('Error sending audio for feedback:', err);
            alert('Failed to get feedback. Please try again.');
            updateUIState('stopped'); // Revert to stopped state on error
        }
    }

    /**
     * Updates the UI elements based on the current state.
     * @param {'idle' | 'recording' | 'stopped' | 'loading' | 'feedback'} state
     */
    function updateUIState(state) {
        // Default: Hide all conditional elements
        idleStateDiv.classList.add('hidden');
        recordingStateDiv.classList.add('hidden');
        startBtn.classList.add('hidden');
        stopBtn.classList.add('hidden');
        loadingSpinner.classList.add('hidden');
        feedbackSection.classList.add('hidden');

        // Disable buttons by default
        rerecordBtn.disabled = true;
        getFeedbackBtn.disabled = true;

        if (state === 'idle') {
            idleStateDiv.classList.remove('hidden');
            startBtn.classList.remove('hidden');
            rerecordBtn.disabled = true;
            getFeedbackBtn.disabled = true;
        } else if (state === 'recording') {
            recordingStateDiv.classList.remove('hidden');
            stopBtn.classList.remove('hidden');
        } else if (state === 'stopped') {
            idleStateDiv.classList.remove('hidden'); // Show mic icon again
            startBtn.classList.add('hidden'); // Hide Start
            rerecordBtn.disabled = false;
            getFeedbackBtn.disabled = false;
        } else if (state === 'loading') {
            loadingSpinner.classList.remove('hidden');
        } else if (state === 'feedback') {
            feedbackSection.classList.remove('hidden');
            rerecordBtn.disabled = false; // Allow re-recording
        }
    }

    // --- Timer Functions ---
    function startTimer() {
        seconds = 0;
        timerDisplay.textContent = '00:00';
        timerInterval = setInterval(() => {
            seconds++;
            const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
            const secs = (seconds % 60).toString().padStart(2, '0');
            timerDisplay.textContent = `${mins}:${secs}`;
        }, 1000);
    }

    function stopTimer() {
        clearInterval(timerInterval);
    }

    function resetTimer() {
        stopTimer();
        seconds = 0;
        timerDisplay.textContent = '00:00';
    }
    
    /**
     * (Placeholder) Renders feedback data into the DOM.
     */
    @param {object} data - The JSON feedback object from the backend.
     */
    function displayFeedback(data) {
        
        // --- 1. Populate Overall Performance ---
        const scoreEl = document.getElementById('feedback-score');
        const ratingEl = document.getElementById('feedback-rating');
        
        scoreEl.textContent = `${data.overall_score}%`;
        
        // Determine rating text and color
        if (data.overall_score >= 85) {
            ratingEl.textContent = 'Excellent';
            ratingEl.className = 'text-2xl font-semibold text-green-600';
            scoreEl.className = 'text-5xl font-bold text-green-600';
        } else if (data.overall_score >= 70) {
            ratingEl.textContent = 'Good';
            ratingEl.className = 'text-2xl font-semibold text-blue-600';
            scoreEl.className = 'text-5xl font-bold text-blue-600';
        } else {
            ratingEl.textContent = 'Needs Improvement';
            ratingEl.className = 'text-2xl font-semibold text-yellow-600';
            scoreEl.className = 'text-5xl font-bold text-yellow-600';
        }

        // --- 2. Populate Detailed Analysis Table ---
        const tableBody = document.getElementById('feedback-analysis-table').getElementsByTagName('tbody')[0];
        tableBody.innerHTML = ''; // Clear old data
        
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

        // --- 3. Populate Transcript ---
        document.getElementById('feedback-transcript').textContent = data.transcript;

        // --- 4. Populate List Functions (Strengths, Improvements, Suggestions) ---
        
        /** Helper function to populate a <ul> */
        function populateList(listId, items) {
            const ul = document.getElementById(listId);
            ul.innerHTML = ''; // Clear old items
            if (items && items.length > 0) {
                items.forEach(item => {
                    const li = document.createElement('li');
                    li.textContent = item;
                    ul.appendChild(li);
                });
            } else {
                const li = document.createElement('li');
                li.textContent = 'N/A';
                li.className = 'text-gray-400';
                ul.appendChild(li);
            }
        }
        
        populateList('feedback-strengths-list', data.strengths);
        populateList('feedback-improvements-list', data.improvements);
        populateList('feedback-suggestions-list', data.suggestions);
        
        // --- 5. Show the feedback section ---
        // This is handled by updateUIState('feedback') in the getFeedback function
    }

    // --- Event Listeners ---
    startBtn.addEventListener('click', startRecording);
    stopBtn.addEventListener('click', stopRecording);
    rerecordBtn.addEventListener('click', reRecord);
    getFeedbackBtn.addEventListener('click', getFeedback);

    // --- Initial State ---
    updateUIState('idle');
}