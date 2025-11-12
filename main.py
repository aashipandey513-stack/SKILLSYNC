# SkillSync/main.py
from fastapi import UploadFile, File
import shutil
import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from utils import speech_to_text
from utils import nlp_feedback
# from utils import speech_to_text, nlp_feedback, auth

# Initialize the FastAPI app
app = FastAPI(title="SKILLSYNC")

# --- Setup Templates and Static Files ---

# Mount the 'static' directory to serve CSS, JS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# --- Page-Serving Endpoints ---

@app.get("/", response_class=HTMLResponse)
async def get_login_page(request: Request):
    """Serves the main login page (login.html)."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Serves the main dashboard page (dashboard.html)."""
    # In a real app, you'd check for a valid user session here
    demo_user = {
        "name": "Demo",
        "level": "Beginner",
        "streak": 0,
        "member_since": "10/11/2025"
    }
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": demo_user})

@app.get("/mock-interview", response_class=HTMLResponse)
async def get_mock_interview(request: Request):
    """Serves the mock interview page."""
    return templates.TemplateResponse("mock_interview.html", {"request": request})

@app.get("/competition", response_class=HTMLResponse)
async def get_competition_practice(request: Request):
    """Serves the competition practice page."""
    return templates.TemplateResponse("competition.html", {"request": request})

@app.get("/soft-skills", response_class=HTMLResponse)
async def get_soft_skills(request: Request):
    """Serves the soft skills page."""
    return templates.TemplateResponse("soft_skills.html", {"request": request})

@app.get("/aptitude", response_class=HTMLResponse)
async def get_aptitude_test(request: Request):
    """Serves the aptitude test page."""
    return templates.TemplateResponse("aptitude.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    """Serves the analytics page."""
    return templates.TemplateResponse("analytics.html", {"request": request})

# --- Authentication (Mock) ---

@app.post("/login")
async def handle_login(email: str = Form(...), password: str = Form(...)):
    """
    Handles the login form submission.
    TODO: Implement real auth logic using utils/auth.py and a database.
    """
    print(f"Login attempt: Email={email}, Password={'*' * len(password)}")
    
    # --- MOCK LOGIN ---
    # In a real app, you would validate credentials and create a session token.
    # For now, we just redirect to the dashboard.
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/signup")
async def handle_signup(email: str = Form(...), password: str = Form(...)):
    """
    Handles the sign-up form submission.
    TODO: Implement real user creation logic.
    """
    print(f"Signup attempt: Email={email}")
    # --- MOCK SIGNUP ---
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/demo")
async def handle_demo_login():
    """Handles the 'Try Demo Account' button click."""
    # --- MOCK DEMO LOGIN ---
    return RedirectResponse(url="/dashboard", status_code=303)

# --- Main entry point for running the app ---
if __name__ == "__main__":
   TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


@app.post("/process-interview-audio")
async def process_interview_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    type: str = Form(...)
):
    """
    Receives recorded audio, transcribes it, and gets full NLP feedback.
    """
    print(f"Received audio for question: {question} (Type: {type})")
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    
    try:
        # --- 1. Save the audio file ---
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        print(f"Audio file saved to: {file_path}")

        # --- 2. Speech-to-Text (Whisper) ---
        transcript = speech_to_text.transcribe_audio(file_path)
        print(f"Transcript: {transcript}")

        # --- 3. NLP Feedback (REAL) ---
        # This is NO LONGER MOCK!
        # We replace the entire mock_feedback object with this function call.
        if not transcript or "[Transcription Error" in transcript:
            # Handle cases where transcription failed
            feedback = {
                "overall_score": 0,
                "transcript": transcript,
                "analysis": {},
                "strengths": ["Transcription failed. Please try recording again."],
                "improvements": ["Ensure your microphone is working and you speak clearly."],
                "suggestions": []
            }
        else:
            # Call our new nlp_feedback module
            feedback = nlp_feedback.get_nlp_feedback(transcript, question)
        
        # --- 4. Clean up the audio file ---
        os.remove(file_path)

        # --- 5. Return the REAL feedback ---
        return feedback

    except Exception as e:
        print(f"Error processing audio: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Error processing audio file.")
@app.post("/process-competition-audio")
async def process_competition_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),      # This will be the debate topic
    position: str = Form(...)       # This will be "Argue in FAVOR..."
):
    """
    Receives recorded audio for the competition module.
    """
    print(f"Received audio for topic: {question}")
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    
    try:
        # --- 1. Save the audio file ---
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # --- 2. Speech-to-Text (REUSED) ---
        transcript = speech_to_text.transcribe_audio(file_path)
        print(f"Transcript: {transcript}")

        # --- 3. NLP Feedback (REUSED with different prompts) ---
        if not transcript or "[Transcription Error" in transcript:
            feedback = {
                # ... (same error handling as the interview endpoint)
            }
        else:
            # We call the *same* function, but the AI will get
            # a different context (question) and provide different feedback.
            # We'll customize the NLP module for this next.
            
            # For now, we can just call it directly
            feedback = nlp_feedback.get_nlp_feedback(transcript, question)
            
            # --- FUTURE IMPROVEMENT ---
            # We can pass a "context" to our NLP module, e.g.:
            # feedback = nlp_feedback.get_nlp_feedback(
            #    transcript, 
            #    question, 
            #    context="debate"
            # )
            # And that function would use different prompts.
            # For now, it will work well just by changing the question.
        
        # --- 4. Clean up the audio file ---
        os.remove(file_path)

        # --- 5. Return the REAL feedback ---
        return feedback

    except Exception as e:
        # ... (same error handling)
        print(f"Error processing audio: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Error processing audio file.")
# ... (keep your __main__ entry point at the bottom)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)