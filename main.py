# SkillSync/main.py

# --- Core FastAPI & Python Imports ---
from fastapi import (
    FastAPI, 
    Request, 
    Form, 
    Depends, 
    HTTPException, 
    UploadFile, 
    File
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
import shutil
import os
from pydantic import BaseModel
from typing import List
# --- AI Utility Module Imports ---
from utils import speech_to_text
from utils import nlp_feedback

# --- App Initialization ---
app = FastAPI(title="SKILLSYNC")

# --- Setup Templates and Static Files ---

# Mount the 'static' directory to serve CSS, JS, images
app.mount("/static", StaticFiles(directory="static"), name="static")

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Define a directory to store audio files temporarily
TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


# === 1. PAGE-SERVING ENDPOINTS ===

@app.get("/", response_class=HTMLResponse)
async def get_login_page(request: Request):
    """Serves the main login page (login.html)."""
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Serves the main dashboard page (dashboard.html)."""
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
    # This is the page we will build next
    return templates.TemplateResponse("aptitude.html", {"request": request})
    
@app.get("/aptitude/quiz", response_class=HTMLResponse)
async def get_aptitude_quiz_page(request: Request):
    """Serves the main quiz interface page."""
    return templates.TemplateResponse("aptitude_quiz.html", {"request": request})
    
@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    """Serves the analytics page."""
    return templates.TemplateResponse("analytics.html", {"request": request})

# --- ADD MOCK QUIZ DATA AND ENDPOINT ---

# Define data models for our quiz
class QuizQuestion(BaseModel):
    category: str
    question: str
    options: List[str]
    answer: str

# Create a mock database of questions
mock_quiz_db = [
    {
        "category": "Quantitative Reasoning",
        "question": "If a train travels 300 km in 4 hours, what is its average speed in km/h?",
        "options": ["60 km/h", "75 km/h", "80 km/h", "90 km/h"],
        "answer": "75 km/h"
    },
    {
        "category": "Logical Reasoning",
        "question": "Which number should come next in the series? 1, 4, 9, 16, ___",
        "options": ["20", "25", "30", "36"],
        "answer": "25"
    },
    {
        "category": "Verbal Reasoning",
        "question": "Choose the word that is the best antonym for 'Ephemeral'.",
        "options": ["Transient", "Short-lived", "Permanent", "Weak"],
        "answer": "Permanent"
    },
    # Add 17 more questions to make 20
    # For now, we'll just add a few more for testing
    {
        "category": "Data Interpretation",
        "question": "If a pie chart shows 25% for 'Category A', what angle does it represent in degrees?",
        "options": ["45°", "90°", "180°", "25°"],
        "answer": "90°"
    },
    {
        "category": "Quantitative Reasoning",
        "question": "What is 5% of 200?",
        "options": ["5", "10", "15", "20"],
        "answer": "10"
    }
]

@app.get("/api/quiz-questions", response_model=List[QuizQuestion])
async def get_quiz_questions():
    """API endpoint to fetch the list of quiz questions."""
    # In a real app, this would query a database
    # We remove the 'answer' field before sending to the client
    questions_for_client = []
    for q in mock_quiz_db:
        # Create a copy and remove the answer
        q_copy = q.copy()
        q_copy.pop("answer", None) 
        questions_for_client.append(q_copy)
        
    # For this demo, we'll send a truncated list of 5
    return questions_for_client[:5] # Send all 20 in your final version


# --- ADD QUIZ SUBMISSION ENDPOINT ---
class UserAnswers(BaseModel):
    answers: dict # Will look like {"0": "75 km/h", "1": "25", ...}

@app.post("/api/submit-quiz")
async def submit_quiz(user_answers: UserAnswers):
    """API endpoint to score the quiz."""
    score = 0
    total = len(mock_quiz_db[:5]) # Match the number of questions sent
    
    for index, selected_option in user_answers.answers.items():
        try:
            q_index = int(index)
            correct_answer = mock_quiz_db[q_index]["answer"]
            if selected_option == correct_answer:
                score += 1
        except Exception as e:
            print(f"Error scoring question {index}: {e}")

    print(f"Quiz submitted. Final Score: {score} / {total}")
    return {"score": score, "total": total}    

# === 2. MOCK AUTHENTICATION ENDPOINTS ===

@app.post("/login")
async def handle_login(email: str = Form(...), password: str = Form(...)):
    """Handles the login form submission (mock)."""
    print(f"Login attempt: Email={email}, Password={'*' * len(password)}")
    # In a real app, validate credentials and create a session
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/signup")
async def handle_signup(email: str = Form(...), password: str = Form(...)):
    """Handles the sign-up form submission (mock)."""
    print(f"Signup attempt: Email={email}")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/demo")
async def handle_demo_login():
    """Handles the 'Try Demo Account' button click (mock)."""
    return RedirectResponse(url="/dashboard", status_code=303)


# === 3. AI PROCESSING ENDPOINTS ===

@app.post("/process-interview-audio")
async def process_interview_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    context: str = Form(...) # "interview"
):
    """
    Receives audio for the Mock Interview module.
    """
    print(f"Received audio for question: {question}")
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    
    try:
        # 1. Save audio
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # 2. Transcribe
        transcript = speech_to_text.transcribe_audio(file_path)
        print(f"Transcript: {transcript}")

        # 3. Get Feedback
        if not transcript or "[Transcription Error" in transcript:
            feedback = {
                "overall_score": 0, "transcript": transcript, "analysis": {},
                "strengths": ["Transcription failed. Please try recording again."],
                "improvements": ["Ensure your microphone is working and you speak clearly."],
                "suggestions": []
            }
        else:
            feedback = nlp_feedback.get_nlp_feedback(
                transcript, 
                question, 
                context=context
            )
        
        # 4. Clean up
        os.remove(file_path)

        # 5. Return Feedback
        return feedback

    except Exception as e:
        print(f"Error processing audio: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Error processing audio file.")


@app.post("/process-competition-audio")
async def process_competition_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),      # Debate topic
    context: str = Form(...)        # "competition"
):
    """
    Receives audio for the Competition Practice module.
    """
    print(f"Received audio for topic: {question}")
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    
    try:
        # 1. Save audio
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # 2. Transcribe
        transcript = speech_to_text.transcribe_audio(file_path)
        print(f"Transcript: {transcript}")

        # 3. Get Feedback
        if not transcript or "[Transcription Error" in transcript:
            feedback = {
                "overall_score": 0, "transcript": transcript, "analysis": {},
                "strengths": ["Transcription failed. Please try recording again."],
                "improvements": ["Ensure your microphone is working and you speak clearly."],
                "suggestions": []
            }
        else:
            feedback = nlp_feedback.get_nlp_feedback(
                transcript, 
                question, 
                context=context
            )
        
        # 4. Clean up
        os.remove(file_path)

        # 5. Return Feedback
        return feedback

    except Exception as e:
        print(f"Error processing audio: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Error processing audio file.")


@app.post("/process-soft-skills-audio")
async def process_soft_skills_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),      # Soft skill prompt
    context: str = Form(...)        # "soft-skills"
):
    """
    Receives audio for the Soft Skills module.
    """
    print(f"Received audio for prompt: {question}")
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    
    try:
        # 1. Save audio
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        # 2. Transcribe
        transcript = speech_to_text.transcribe_audio(file_path)
        print(f"Transcript: {transcript}")

        # 3. Get Feedback
        if not transcript or "[Transcription Error" in transcript:
            feedback = {
                "overall_score": 0, "transcript": transcript, "analysis": {},
                "strengths": ["Transcription failed. Please try recording again."],
                "improvements": ["Ensure your microphone is working and you speak clearly."],
                "suggestions": []
            }
        else:
            feedback = nlp_feedback.get_nlp_feedback(
                transcript, 
                question, 
                context=context
            )
        
        # 4. Clean up
        os.remove(file_path)

        # 5. Return Feedback
        return feedback

    except Exception as e:
        print(f"Error processing audio: {e}")
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail="Error processing audio file.")


# --- Main entry point for running the app ---
if __name__ == "__main__":
    # Use this for local development
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)