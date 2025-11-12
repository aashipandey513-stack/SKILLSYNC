# SkillSync/main.py

# --- Core FastAPI & Python Imports ---
from fastapi import (
    FastAPI, 
    Request, 
    Form, 
    Depends, 
    HTTPException, 
    UploadFile, 
    File,
    Cookie, # New
    status  # New
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response # New
from pydantic import BaseModel, EmailStr
from typing import List, Optional # Optional is new
import uvicorn
import shutil
import os
import datetime
from datetime import timedelta, timezone # New

# --- AI Utility Module Imports ---
from utils import speech_to_text
from utils import nlp_feedback

# --- DB & Auth Imports ---
from utils.database import db
from utils.auth import (
    hash_password, 
    verify_password, 
    create_access_token, 
    ALGORITHM, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from jose import JWTError, jwt # New

# --- App Initialization ---
app = FastAPI(title="SKILLSYNC")

# --- Setup Templates and Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

# --- NEW: Load JWT Secret ---
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")


# === 1. PAGE-SERVING ENDPOINTS ===
# (This section is unchanged)
@app.get("/", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, current_user_email: EmailStr = Depends(get_current_user_email)):
   
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")

    # Fetch the user's data from the database
    user_data = await db["users"].find_one({"email": current_user_email})

    if not user_data:
        # This shouldn't happen if the JWT is valid, but good to check
        raise HTTPException(status_code=404, detail="User not found")

    # Format the user's name (e.g., "test@example.com" -> "test")
    user_name = user_data.get("email").split("@")[0]
    
    # Format the join date
    created_at_date = user_data.get("created_at")
    formatted_date = created_at_date.strftime("%m/%d/%Y") # Formats as MM/DD/YYYY

    # TODO: We can make "level" and "streak" real later
    user = {
        "name": user_name.capitalize(),
        "level": "Beginner", # This is still mock
        "streak": 0,         # This is still mock
        "member_since": formatted_date # This is now REAL
    }
    
    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
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


# === 2. REAL AUTHENTICATION ENDPOINTS (UPDATED) ===

# --- NEW: JWT Dependency Function ---
async def get_current_user_email(access_token: Optional[str] = Cookie(None)) -> EmailStr:
    """
    This "dependency" reads the cookie, verifies the JWT, 
    and returns the user's email.
    It will be run automatically for every endpoint that needs auth.
    """
    if not JWT_SECRET_KEY:
        raise HTTPException(status_code=500, detail="JWT Secret not configured")
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated, no token found",
        )
    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub") # "sub" (subject) is our email
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


@app.post("/login")
async def handle_login(response: Response, email: str = Form(...), password: str = Form(...)):
    """
    Handles a real user login.
    UPDATED: Now creates a JWT and sets it as an HttpOnly cookie.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    user_in_db = await db["users"].find_one({"email": email.lower()})

    if not user_in_db or not verify_password(password, user_in_db["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    # Create the access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_in_db["email"]}, expires_delta=access_token_expires
    )
    
    # Create a redirect response and set the cookie
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True, # JavaScript can't access it
        max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES * 60), # in seconds
        samesite="lax", # Good for most cases
        secure=True # Only send over HTTPS (Hugging Face provides this)
    )
    print("Successful login for:", email)
    return redirect_response


@app.post("/signup")
async def handle_signup(email: str = Form(...), password: str = Form(...)):
    """
    Handles a new user signing up.
    UPDATED: Now logs the user in immediately by setting the cookie.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    existing_user = await db["users"].find_one({"email": email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = hash_password(password)
    new_user = { "email": email.lower(), "hashed_password": hashed_pwd, "created_at": datetime.datetime.now(timezone.utc) }
    
    try:
        await db["users"].insert_one(new_user)
        print(f"New user created: {email.lower()}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {e}")
    
    # --- NEW: Log user in immediately ---
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user["email"]}, expires_delta=access_token_expires
    )
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        samesite="lax",
        secure=True
    )
    return redirect_response


@app.get("/demo")
async def handle_demo_login():
    """Handles the 'Try Demo Account' button click (no change)."""
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/logout")
async def handle_logout():
    """
    Logs the user out by clearing the cookie.
    """
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token")
    print("User logged out.")
    return response


# === 3. AI PROCESSING ENDPOINTS (UPDATED) ===
# All 3 endpoints now use: Depends(get_current_user_email)

@app.post("/process-interview-audio")
async def process_interview_audio(
    current_user_email: EmailStr = Depends(get_current_user_email), # NEW
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    context: str = Form(...)
):
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    try:
        # ... (save file, get transcript, get feedback... same as before) ...
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        transcript = speech_to_text.transcribe_audio(file_path)
        if not transcript or "[Transcription Error" in transcript:
            feedback = { "overall_score": 0, "transcript": transcript, "analysis": {}, "strengths": ["Transcription failed."], "improvements": ["Please try again."], "suggestions": [] }
        else:
            feedback = nlp_feedback.get_nlp_feedback(transcript, question, context=context)
        
        # --- UPDATED DATABASE CODE ---
        if db is not None and "Transcription Error" not in transcript:
            # mock_user_email = "demo@example.com" # (REMOVED)
            
            session_document = {
                "user_email": current_user_email, # NEW: Use real user
                "module": "Mock Interview",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "created_at": datetime.datetime.now(timezone.utc)
                # You can add more fields from 'feedback' if you want
            }
            await db["practice_sessions"].insert_one(session_document)
            print(f"Saved session for {current_user_email} to database.")
        # --- END UPDATED DATABASE CODE ---
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-competition-audio")
async def process_competition_audio(
    current_user_email: EmailStr = Depends(get_current_user_email), # NEW
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    context: str = Form(...)
):
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        transcript = speech_to_text.transcribe_audio(file_path)
        if not transcript or "[Transcription Error" in transcript:
             feedback = { "overall_score": 0, "transcript": transcript, "analysis": {}, "strengths": ["Transcription failed."], "improvements": ["Please try again."], "suggestions": [] }
        else:
            feedback = nlp_feedback.get_nlp_feedback(transcript, question, context=context)
        
        # --- UPDATED DATABASE CODE ---
        if db is not None and "Transcription Error" not in transcript:
            session_document = {
                "user_email": current_user_email, # NEW: Use real user
                "module": "Competition",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "created_at": datetime.datetime.now(timezone.utc)
            }
            await db["practice_sessions"].insert_one(session_document)
            print(f"Saved session for {current_user_email} to database.")
        # --- END UPDATED DATABASE CODE ---
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-soft-skills-audio")
async def process_soft_skills_audio(
    current_user_email: EmailStr = Depends(get_current_user_email), # NEW
    audio_file: UploadFile = File(...),
    question: str = Form(...),
    context: str = Form(...)
):
    file_path = os.path.join(TEMP_AUDIO_DIR, audio_file.filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(audio_file.file, buffer)
        transcript = speech_to_text.transcribe_audio(file_path)
        if not transcript or "[Transcription Error" in transcript:
             feedback = { "overall_score": 0, "transcript": transcript, "analysis": {}, "strengths": ["Transcription failed."], "improvements": ["Please try again."], "suggestions": [] }
        else:
            feedback = nlp_feedback.get_nlp_feedback(transcript, question, context=context)
        
        # --- UPDATED DATABASE CODE ---
        if db is not None and "Transcription Error" not in transcript:
            session_document = {
                "user_email": current_user_email, # NEW: Use real user
                "module": "Soft Skills",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "created_at": datetime.datetime.now(timezone.utc)
            }
            await db["practice_sessions"].insert_one(session_document)
            print(f"Saved session for {current_user_email} to database.")
        # --- END UPDATED DATABASE CODE ---
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


# === 4. APTITUDE QUIZ API (UPDATED) ===
# (This section is unchanged, except for api/submit-quiz)
class QuizQuestion(BaseModel):
    category: str; question: str; options: List[str]; answer: str
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
        q_copy = q.copy(); q_copy.pop("answer", None); questions_for_client.append(q_copy)
    return questions_for_client
class UserAnswers(BaseModel):
    answers: dict
@app.post("/api/submit-quiz")
async def submit_quiz(
    user_answers: UserAnswers,
    current_user_email: EmailStr = Depends(get_current_user_email) # NEW
):
    score = 0
    total = len(mock_quiz_db)
    for index, selected_option in user_answers.answers.items():
        try:
            q_index = int(index); correct_answer = mock_quiz_db[q_index]["answer"]
            if selected_option == correct_answer: score += 1
        except Exception as e: print(f"Error scoring question {index}: {e}")
    
    # --- UPDATED DATABASE CODE ---
    if db is not None:
        quiz_result_doc = {
            "user_email": current_user_email, # NEW: Use real user
            "module": "Aptitude Test",
            "score": score,
            "total_questions": total,
            "answers": user_answers.answers,
            "created_at": datetime.datetime.now(timezone.utc)
        }
        await db["quiz_results"].insert_one(quiz_result_doc)
        print(f"Saved quiz result for {current_user_email} to database.")
    # --- END UPDATED DATABASE CODE ---
    return {"score": score, "total": total}


# === 5. ANALYTICS API (UPDATED) ===
# This endpoint now fetches REAL data from the DB

@app.get("/api/analytics-data")
async def get_analytics_data(
    current_user_email: EmailStr = Depends(get_current_user_email) # NEW
):
    """
    API endpoint to fetch all data for the analytics page.
    UPDATED: Now queries the database for the logged-in user.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    # --- Tab 3: Session History (Fetch Real Data) ---
    session_history = []
    cursor = db["practice_sessions"].find(
        {"user_email": current_user_email}
    ).sort("created_at", -1).limit(20) # Get last 20 sessions
    
    async for session in cursor:
        session_history.append({
            "date": session["created_at"].strftime("%Y-%m-%d"),
            "module": session["module"],
            "type": session.get("question", "N/A")[:30] + "...", # Truncate question
            "score": f"{session['score']}%",
            "duration": "N/A", # We don't store this yet
            "details": session.get("transcript", "N/A")[:40] + "..." # Truncate transcript
        })
    
    # --- Tab 1: Recent Activity & Summary (Derived from History) ---
    recent_activity = []
    total_score = 0
    for session in session_history[:3]: # Get last 3 sessions
        recent_activity.append({
            "module": session["module"],
            "type": session["type"],
            "score": session["score"],
            "date": session["date"]
        })
        total_score += int(session["score"].replace("%", ""))

    week_summary = {
        "sessions": len(session_history),
        "avg_score": int(total_score / len(recent_activity)) if recent_activity else 0
    }
    
    # --- Tab 1: Performance Trends (Still mock, this is complex) ---
    performance_trends = {
        "labels": ["Nov 1", "Nov 2", "Nov 3", "Nov 4", "Nov 5"],
        "datasets": [
            {"label": "Mock Interview", "data": [65, 69, 70, 78, 75], "borderColor": "#000000", "backgroundColor": "#000000", "tension": 0.1},
            {"label": "Competition", "data": [0, 0, 45, 0, 68], "borderColor": "#3B82F6", "backgroundColor": "#3B82F6", "tension": 0.4},
        ]
    }

    # --- Tab 2: Skills Analysis (Still mock) ---
    skills_analysis = {
        "radar": {"labels": ["Communication", "Articulation", "Confidence", "Critical Thinking", "Grammar", "Problem Solving"], "data": [84, 81, 79, 86, 89, 84]},
        "breakdown": [
            {"name": "Communication", "score": 84, "rating": "Good"}, {"name": "Articulation", "score": 81, "rating": "Good"},
            {"name": "Confidence", "score": 79, "rating": "Good"}, {"name": "Critical Thinking", "score": 86, "rating": "Excellent"},
        ]
    }

    # --- Tab 4: Achievements (Still mock) ---
    achievements = [
        {"name": "First Interview", "desc": "Completed first mock interview", "icon": "fa-check", "status": "Completed", "progress": 100},
        {"name": "Consistent Performer", "desc": "Complete 20 practice sessions", "icon": "fa-medal", "status": f"{len(session_history)}/20", "progress": (len(session_history)/20)*100},
    ]
    
    return {
        "performanceTrends": performance_trends, 
        "recentActivity": recent_activity, 
        "weekSummary": week_summary,
        "skillsAnalysis": skills_analysis, 
        "sessionHistory": session_history, 
        "achievements": achievements
    }

# --- Main entry point ---
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)