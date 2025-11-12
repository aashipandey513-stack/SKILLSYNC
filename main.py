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
from pydantic import BaseModel, EmailStr
from typing import List
import uvicorn
import shutil
import os
import datetime # Make sure this is imported

# --- AI Utility Module Imports ---
from utils import speech_to_text
from utils import nlp_feedback

# --- DB & Auth Imports ---
from utils.database import db  # Import our database connection
from utils.auth import hash_password, verify_password

# --- App Initialization ---
app = FastAPI(title="SKILLSYNC")

# --- Setup Templates and Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)


# === 1. PAGE-SERVING ENDPOINTS ===
# (This section is unchanged)
@app.get("/", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    demo_user = {"name": "Demo", "level": "Beginner", "streak": 0, "member_since": "10/11/2025"}
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": demo_user})

@app.get("/mock-interview", response_class=HTMLResponse)
async def get_mock_interview(request: Request):
    return templates.TemplateResponse("mock_interview.html", {"request": request})

@app.get("/competition", response_class=HTMLResponse)
async def get_competition_practice(request: Request):
    return templates.TemplateResponse("competition.html", {"request": request})

@app.get("/soft-skills", response_class=HTMLResponse)
async def get_soft_skills(request: Request):
    return templates.TemplateResponse("soft_skills.html", {"request": request})

@app.get("/aptitude", response_class=HTMLResponse)
async def get_aptitude_test(request: Request):
    return templates.TemplateResponse("aptitude.html", {"request": request})

@app.get("/aptitude/quiz", response_class=HTMLResponse)
async def get_aptitude_quiz_page(request: Request):
    return templates.TemplateResponse("aptitude_quiz.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    return templates.TemplateResponse("analytics.html", {"request": request})


# === 2. REAL AUTHENTICATION ENDPOINTS ===
# (This section is unchanged)
@app.post("/login")
async def handle_login(email: str = Form(...), password: str = Form(...)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    user_in_db = await db["users"].find_one({"email": email.lower()})
    if not user_in_db or not verify_password(password, user_in_db["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    print("Successful login for:", email)
    return RedirectResponse(url="/dashboard", status_code=303)

@app.post("/signup")
async def handle_signup(email: str = Form(...), password: str = Form(...)):
    if not db:
        raise HTTPException(status_code=500, detail="Database not connected")
    existing_user = await db["users"].find_one({"email": email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_pwd = hash_password(password)
    new_user = {
        "email": email.lower(),
        "hashed_password": hashed_pwd,
        "created_at": datetime.datetime.now(datetime.UTC)
    }
    try:
        result = await db["users"].insert_one(new_user)
        print(f"New user created: {result.inserted_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {e}")
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/demo")
async def handle_demo_login():
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/logout")
async def handle_logout():
    return RedirectResponse(url="/", status_code=303)


# === 3. AI PROCESSING ENDPOINTS ===
# (This section is UPDATED)

@app.post("/process-interview-audio")
async def process_interview_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    context: str = Form(...) # "interview"
):
    """
    Receives audio for the Mock Interview module.
    UPDATED: Now saves results to the database.
    """
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        transcript = speech_to_text.transcribe_audio(file_path)
        
        if not transcript or "[Transcription Error" in transcript:
            feedback = { "overall_score": 0, "transcript": transcript, "analysis": {}, "strengths": ["Transcription failed."], "improvements": ["Please try again."], "suggestions": [] }
        else:
            feedback = nlp_feedback.get_nlp_feedback(transcript, question, context=context)
        
        # --- NEW DATABASE CODE ---
        if db and "Transcription Error" not in transcript:
            # TODO: Replace "demo@example.com" with a real user ID from a session
            mock_user_email = "demo@example.com"
            
            session_document = {
                "user_email": mock_user_email,
                "module": "Mock Interview",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "analysis": feedback["analysis"],
                "strengths": feedback["strengths"],
                "improvements": feedback["improvements"],
                "created_at": datetime.datetime.now(datetime.UTC)
            }
            await db["practice_sessions"].insert_one(session_document)
            print(f"Saved session for {mock_user_email} to database.")
        # --- END NEW DATABASE CODE ---
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-competition-audio")
async def process_competition_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    context: str = Form(...) # "competition"
):
    """
    Receives audio for the Competition Practice module.
    UPDATED: Now saves results to the database.
    """
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)

        transcript = speech_to_text.transcribe_audio(file_path)
        
        if not transcript or "[Transcription Error" in transcript:
             feedback = { "overall_score": 0, "transcript": transcript, "analysis": {}, "strengths": ["Transcription failed."], "improvements": ["Please try again."], "suggestions": [] }
        else:
            feedback = nlp_feedback.get_nlp_feedback(transcript, question, context=context)
        
        # --- NEW DATABASE CODE ---
        if db and "Transcription Error" not in transcript:
            mock_user_email = "demo@example.com"
            
            session_document = {
                "user_email": mock_user_email,
                "module": "Competition",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "analysis": feedback["analysis"],
                "strengths": feedback["strengths"],
                "improvements": feedback["improvements"],
                "created_at": datetime.datetime.now(datetime.UTC)
            }
            await db["practice_sessions"].insert_one(session_document)
            print(f"Saved session for {mock_user_email} to database.")
        # --- END NEW DATABASE CODE ---
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-soft-skills-audio")
async def process_soft_skills_audio(
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    context: str = Form(...) # "soft-skills"
):
    """
    Receives audio for the Soft Skills module.
    UPDATED: Now saves results to the database.
    """
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        
        transcript = speech_to_text.transcribe_audio(file_path)
        
        if not transcript or "[Transcription Error" in transcript:
             feedback = { "overall_score": 0, "transcript": transcript, "analysis": {}, "strengths": ["Transcription failed."], "improvements": ["Please try again."], "suggestions": [] }
        else:
            feedback = nlp_feedback.get_nlp_feedback(transcript, question, context=context)
        
        # --- NEW DATABASE CODE ---
        if db and "Transcription Error" not in transcript:
            mock_user_email = "demo@example.com"
            
            session_document = {
                "user_email": mock_user_email,
                "module": "Soft Skills",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "analysis": feedback["analysis"],
                "strengths": feedback["strengths"],
                "improvements": feedback["improvements"],
                "created_at": datetime.datetime.now(datetime.UTC)
            }
            await db["practice_sessions"].insert_one(session_document)
            print(f"Saved session for {mock_user_email} to database.")
        # --- END NEW DATABASE CODE ---
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


# === 4. APTITUDE QUIZ API ===
# (This section is unchanged)
class QuizQuestion(BaseModel):
    category: str
    question: str
    options: List[str]
    answer: str
mock_quiz_db = [
    {"category": "Quantitative Reasoning", "question": "If a train travels 300 km in 4 hours, what is its average speed in km/h?", "options": ["60 km/h", "75 km/h", "80 km/h", "90 km/h"], "answer": "75 km/h"},
    {"category": "Logical Reasoning", "question": "Which number should come next in the series? 1, 4, 9, 16, ___", "options": ["20", "25", "30", "36"], "answer": "25"},
    {"category": "Verbal Reasoning", "question": "Choose the word that is the best antonym for 'Ephemeral'.", "options": ["Transient", "Short-lived", "Permanent", "Weak"], "answer": "Permanent"},
    {"category": "Data Interpretation", "question": "If a pie chart shows 25% for 'Category A', what angle does it represent in degrees?", "options": ["45°", "90°", "180°", "25°"], "answer": "90°"},
    {"category": "Quantitative Reasoning", "question": "What is 5% of 200?", "options": ["5", "10", "15", "20"], "answer": "10"}
]
@app.get("/api/quiz-questions")
async def get_quiz_questions():
    questions_for_client = []
    for q in mock_quiz_db:
        q_copy = q.copy()
        q_copy.pop("answer", None) 
        questions_for_client.append(q_copy)
    return questions_for_client
class UserAnswers(BaseModel):
    answers: dict
@app.post("/api/submit-quiz")
async def submit_quiz(user_answers: UserAnswers):
    score = 0
    total = len(mock_quiz_db)
    for index, selected_option in user_answers.answers.items():
        try:
            q_index = int(index)
            correct_answer = mock_quiz_db[q_index]["answer"]
            if selected_option == correct_answer:
                score += 1
        except Exception as e:
            print(f"Error scoring question {index}: {e}")
    
    # --- NEW DATABASE CODE ---
    if db:
        mock_user_email = "demo@example.com"
        quiz_result_doc = {
            "user_email": mock_user_email,
            "module": "Aptitude Test",
            "score": score,
            "total_questions": total,
            "answers": user_answers.answers,
            "created_at": datetime.datetime.now(datetime.UTC)
        }
        await db["quiz_results"].insert_one(quiz_result_doc)
        print(f"Saved quiz result for {mock_user_email} to database.")
    # --- END NEW DATABASE CODE ---

    return {"score": score, "total": total}


# === 5. ANALYTICS API ===
# (This section is unchanged)
@app.get("/api/analytics-data")
async def get_analytics_data():
    # ... (This function is unchanged, it still returns mock data) ...
    performance_trends = {
        "labels": ["Nov 1", "Nov 2", "Nov 3", "Nov 4", "Nov 5"],
        "datasets": [
            {"label": "Mock Interview", "data": [65, 69, 70, 78, 75], "borderColor": "#000000", "backgroundColor": "#000000", "tension": 0.1},
            {"label": "Competition", "data": [0, 0, 45, 0, 68], "borderColor": "#3B82F6", "backgroundColor": "#3B82F6", "tension": 0.4},
            {"label": "Soft Skills", "data": [0, 0, 0, 0, 80], "borderColor": "#F59E0B", "backgroundColor": "#F59E0B", "tension": 0.4}
        ]
    }
    recent_activity = [
        {"module": "Mock Interview", "type": "Behavioral - 'Tell me about yourself'", "score": "75%", "date": "11/05"},
        {"module": "Competition", "type": "Public Speaking - 'Future of AI'", "score": "68%", "date": "11/04"},
        {"module": "Mock Interview", "type": "Technical - 'React hooks explanation'", "score": "82%", "date": "11/03"}
    ]
    week_summary = {"sessions": 3, "avg_score": 75}
    skills_analysis = {
        "radar": {"labels": ["Communication", "Articulation", "Confidence", "Critical Thinking", "Grammar", "Problem Solving"], "data": [84, 81, 79, 86, 89, 84]},
        "breakdown": [
            {"name": "Communication", "score": 84, "rating": "Good"}, {"name": "Articulation", "score": 81, "rating": "Good"},
            {"name": "Confidence", "score": 79, "rating": "Good"}, {"name": "Critical Thinking", "score": 86, "rating": "Excellent"},
            {"name": "Grammar", "score": 89, "rating": "Excellent"}, {"name": "Problem Solving", "score": 84, "rating": "Good"}
        ]
    }
    session_history = [
        {"date": "2024-11-05", "module": "Mock Interview", "type": "Behavioral", "score": "75%", "duration": "2:30", "details": "Tell me about yourself question"},
        {"date": "2024-11-04", "module": "Competition", "type": "Public Speaking", "score": "68%", "duration": "4:15", "details": "Future of AI in education"},
        {"date": "2024-11-03", "module": "Mock Interview", "type": "Technical", "score": "82%", "duration": "3:45", "details": "React hooks explanation"}
    ]
    achievements = [
        {"name": "Practice Streak", "desc": "5 days in a row", "icon": "fa-fire", "status": "Completed", "progress": 100},
        {"name": "Quick Learner", "desc": "Improved by 15% this week", "icon": "fa-star", "status": "Completed", "progress": 100},
        {"name": "First Interview", "desc": "Completed first mock interview", "icon": "fa-check", "status": "Completed", "progress": 100},
        {"name": "Perfect Score", "desc": "Get 100% on any practice", "icon": "fa-bullseye", "status": "In Progress", "progress": 0},
        {"name": "Consistent Performer", "desc": "Complete 20 practice sessions", "icon": "fa-medal", "status": "12/20", "progress": 60},
        {"name": "Master Communicator", "desc": "Reach 90% in all skills", "icon": "fa-brain", "status": "4/6", "progress": 66}
    ]
    return {
        "performanceTrends": performance_trends, "recentActivity": recent_activity, "weekSummary": week_summary,
        "skillsAnalysis": skills_analysis, "sessionHistory": session_history, "achievements": achievements
    }

# --- Main entry point ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)