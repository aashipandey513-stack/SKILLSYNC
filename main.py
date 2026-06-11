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
    Cookie,
    status
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import uvicorn
import shutil
import os
import datetime
from datetime import timedelta, timezone

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
from jose import JWTError, jwt

# --- App Initialization ---
app = FastAPI(title="SKILLSYNC")

# --- Setup Templates and Static Files ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
TEMP_AUDIO_DIR = "temp_audio"
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")


# === JWT Dependency Function ===
async def get_current_user_email(access_token: Optional[str] = Cookie(None)) -> EmailStr:
    """
    This "dependency" reads the cookie, verifies the JWT, 
    and returns the user's email.
    """
    if not JWT_SECRET_KEY:
        raise HTTPException(status_code=500, detail="JWT Secret not configured")
    if access_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated, no token found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(access_token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        return email
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


# === 1. PAGE-SERVING ENDPOINTS ===

@app.get("/", response_class=HTMLResponse)
async def get_login_page(request: Request):
    return templates.TemplateResponse(
    request=request, 
    name="login.html", 
    context={} 
)

@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request, current_user_email: EmailStr = Depends(get_current_user_email)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    user_data = await db["users"].find_one({"email": current_user_email})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")

    user_name = user_data.get("email").split("@")[0]
    created_at_date = user_data.get("created_at")
    formatted_date = created_at_date.strftime("%m/%d/%Y")

    user = {
        "name": user_name.capitalize(),
        "level": "Beginner",
        "streak": 0,
        "member_since": formatted_date
    }
    return templates.TemplateResponse(
    request=request, 
    name="dashboard.html", 
    context={"user": user}
)

@app.get("/mock-interview", response_class=HTMLResponse)
async def get_mock_interview(request: Request):
    return templates.TemplateResponse(request=request, name="mock_interview.html")
@app.get("/competition", response_class=HTMLResponse)
async def get_competition_practice(request: Request):
    return templates.TemplateResponse(request=request, name="competition.html")
@app.get("/soft-skills", response_class=HTMLResponse)
async def get_soft_skills(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="soft_skills.html"
    )

@app.get("/aptitude", response_class=HTMLResponse)
async def get_aptitude_test(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="aptitude.html"
    )

@app.get("/aptitude/quiz", response_class=HTMLResponse)
async def get_aptitude_quiz_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="aptitude_quiz.html"
    )

@app.get("/analytics", response_class=HTMLResponse)
async def get_analytics(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="analytics.html"
    )


# === 2. REAL AUTHENTICATION ENDPOINTS ===

@app.post("/login")
async def handle_login(response: Response, email: str = Form(...), password: str = Form(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    user_in_db = await db["users"].find_one({"email": email.lower()})
    if not user_in_db or not verify_password(password, user_in_db["hashed_password"]):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_in_db["email"]}, expires_delta=access_token_expires
    )
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect_response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES * 60), samesite="none", secure=True, path="/"
    )
    return redirect_response

@app.post("/signup")
async def handle_signup(email: str = Form(...), password: str = Form(...)):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    existing_user = await db["users"].find_one({"email": email.lower()})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
        
    hashed_pwd = hash_password(password)
    new_user = { 
        "email": email.lower(), 
        "hashed_password": hashed_pwd, 
        "created_at": datetime.datetime.now(timezone.utc) 
    }
    try:
        await db["users"].insert_one(new_user)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating user: {e}")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user["email"]}, expires_delta=access_token_expires
    )
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect_response.set_cookie(
        key="access_token", value=access_token, httponly=True,
        max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES * 60), samesite="none", secure=True, path="/"
    )
    return redirect_response

@app.get("/demo")
async def handle_demo_login():
    """
    Handles the 'Try Demo Account' button click.
    UPDATED: Now logs in as a pre-defined demo user.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
    
    # --- HANDLING DEMO SIGN IN ---
    DEMO_USER_EMAIL = "demo@skillsync.app"
    
    # 1. Find the demo user in the database
    user_in_db = await db["users"].find_one({"email": DEMO_USER_EMAIL})
    
    if not user_in_db:
        # This will happen if you forgot to create the user from Step 1
        raise HTTPException(status_code=404, detail=f"Demo user '{DEMO_USER_EMAIL}' not found in database. Please sign up as this user first.")
    
    # 2. Create an access token for the demo user
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_in_db["email"]}, expires_delta=access_token_expires
    )
    
    # 3. Create a redirect response and set the cookie
    redirect_response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    redirect_response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=int(ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        samesite="none",
        secure=True,
        path="/"
    )
    print("Successful login for: DEMO USER")
    return redirect_response

@app.get("/logout")
async def handle_logout():
    response = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="access_token", path="/", samesite="none", secure=True)
    return response


# === 3. AI PROCESSING ENDPOINTS ===

@app.post("/process-interview-audio")
async def process_interview_audio(
    current_user_email: EmailStr = Depends(get_current_user_email),
    audio_file: UploadFile = File(...), question: str = Form(...), context: str = Form(...)
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
        
        if db is not None and "Transcription Error" not in transcript:
            session_document = {
                "user_email": current_user_email,
                "module": "Mock Interview",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "analysis": feedback.get("analysis", {}), # Save the analysis block
                "created_at": datetime.datetime.now(timezone.utc)
            }
            await db["practice_sessions"].insert_one(session_document)
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-competition-audio")
async def process_competition_audio(
    current_user_email: EmailStr = Depends(get_current_user_email),
    audio_file: UploadFile = File(...), question: str = Form(...), context: str = Form(...)
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
        
        if db is not None and "Transcription Error" not in transcript:
            session_document = {
                "user_email": current_user_email,
                "module": "Competition",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "analysis": feedback.get("analysis", {}),
                "created_at": datetime.datetime.now(timezone.utc)
            }
            await db["practice_sessions"].insert_one(session_document)
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-soft-skills-audio")
async def process_soft_skills_audio(
    current_user_email: EmailStr = Depends(get_current_user_email),
    audio_file: UploadFile = File(...), question: str = Form(...), context: str = Form(...)
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
        
        if db is not None and "Transcription Error" not in transcript:
            session_document = {
                "user_email": current_user_email,
                "module": "Soft Skills",
                "question": question,
                "transcript": feedback["transcript"],
                "score": feedback["overall_score"],
                "analysis": feedback.get("analysis", {}),
                "created_at": datetime.datetime.now(timezone.utc)
            }
            await db["practice_sessions"].insert_one(session_document)
        
        os.remove(file_path)
        return feedback
    except Exception as e:
        if os.path.exists(file_path): os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))


# === 4. APTITUDE QUIZ API ===
class QuizQuestion(BaseModel):
    category: str; question: str; options: List[str]; answer: str
mock_quiz_db = [
    {"category": "Quantitative Reasoning", "question": "If a train travels 300 km in 4 hours, what is its average speed in km/h?", "options": ["60 km/h", "75 km/h", "80 km/h", "90 km/h"], "answer": "75 km/h"},
    {"category": "Logical Reasoning", "question": "Which number should come next in the series? 1, 4, 9, 16, ___", "options": ["20", "25", "30", "36"], "answer": "25"},
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
    current_user_email: EmailStr = Depends(get_current_user_email)
):
    score = 0
    total = len(mock_quiz_db)
    for index, selected_option in user_answers.answers.items():
        try:
            q_index = int(index); correct_answer = mock_quiz_db[q_index]["answer"]
            if selected_option == correct_answer: score += 1
        except Exception as e: print(f"Error scoring question {index}: {e}")
    
    if db is not None:
        quiz_result_doc = {
            "user_email": current_user_email, "module": "Aptitude Test",
            "score": score, "total_questions": total,
            "answers": user_answers.answers, "created_at": datetime.datetime.now(timezone.utc)
        }
        await db["quiz_results"].insert_one(quiz_result_doc)
    return {"score": score, "total": total}


# === 5. ANALYTICS API (UPDATED WITH REAL DATA) ===

@app.get("/api/analytics-data")
async def get_analytics_data(
    current_user_email: EmailStr = Depends(get_current_user_email)
):
    """
    API endpoint to fetch all data for the analytics page.
    UPDATED: Now queries the database for the logged-in user.
    """
    if db is None:
        raise HTTPException(status_code=500, detail="Database not connected")
        
    # --- Query 1: Session History (Real Data) ---
    session_history = []
    session_cursor = db["practice_sessions"].find(
        {"user_email": current_user_email}
    ).sort("created_at", -1).limit(20)
    
    async for session in session_cursor:
        session_history.append({
            "date": session["created_at"].strftime("%Y-%m-%d"),
            "module": session["module"],
            "type": session.get("question", "N/A")[:30] + "...",
            "score": f"{session['score']}%",
            "duration": "N/A",
            "details": session.get("transcript", "N/A")[:40] + "..."
        })
    
    # --- Tab 1: Recent Activity & Summary (Real Data) ---
    recent_activity = []
    total_score = 0
    for session in session_history[:3]:
        recent_activity.append({
            "module": session["module"], "type": session["type"],
            "score": session["score"], "date": session["date"]
        })
        total_score += int(session["score"].replace("%", ""))

    week_summary = {
        "sessions": len(session_history),
        "avg_score": int(total_score / len(recent_activity)) if recent_activity else 0
    }
    
    # --- Query 2: Performance Trends (Real Data) ---
    # 
    pipeline = [
        { "$match": { "user_email": current_user_email } },
        { "$project": {
            "module": 1,
            "score": 1,
            "date": { "$dateToString": { "format": "%Y-%m-%d", "date": "$created_at" } }
        }},
        { "$group": {
            "_id": { "date": "$date", "module": "$module" },
            "avg_score": { "$avg": "$score" }
        }},
        { "$sort": { "_id.date": 1 } }
    ]
    
    trends_cursor = db["practice_sessions"].aggregate(pipeline)
    
    # Format data for Chart.js
    labels = set()
    module_data = {"Mock Interview": {}, "Competition": {}, "Soft Skills": {}}
    
    async for item in trends_cursor:
        date = item["_id"]["date"]
        module = item["_id"]["module"]
        avg_score = item["avg_score"]
        
        if module in module_data:
            labels.add(date)
            module_data[module][date] = avg_score

    sorted_labels = sorted(list(labels))
    datasets = []
    
    colors = {
        "Mock Interview": "#000000",
        "Competition": "#3B82F6",
        "Soft Skills": "#F59E0B"
    }

    for module, scores in module_data.items():
        data_points = []
        for label in sorted_labels:
            data_points.append(scores.get(label, None)) # Use null for missing days
            
        if any(data_points): # Only add if there is data
            datasets.append({
                "label": module,
                "data": data_points,
                "borderColor": colors.get(module, "#CCCCCC"),
                "backgroundColor": colors.get(module, "#CCCCCC"),
                "tension": 0.1
            })

    performance_trends = {
        "labels": sorted_labels,
        "datasets": datasets
    }

    # --- Query 3: Skills Analysis (Real Data) ---
    # 
    pipeline_skills = [
        { "$match": { "user_email": current_user_email, "analysis": { "$exists": True, "$ne": {} } } },
        { "$project": { "analysis_kv": { "$objectToArray": "$analysis" } } },
        { "$unwind": "$analysis_kv" },
        { "$group": {
            "_id": "$analysis_kv.k", # Group by skill name (e.g., "Clarity")
            "avg_score": { "$avg": "$analysis_kv.v" }
        }},
        { "$project": {
            "name": "$_id",
            "score": { "$round": ["$avg_score", 0] }
        }}
    ]
    
    skills_cursor = db["practice_sessions"].aggregate(pipeline_skills)
    
    radar_labels = []
    radar_data = []
    breakdown_list = []
    
    async for skill in skills_cursor:
        name = skill["name"]
        score = skill["score"]
        
        radar_labels.append(name)
        radar_data.append(score)
        
        rating = "Good"
        if score >= 85:
            rating = "Excellent"
        elif score < 70:
            rating = "Needs Improvement"
            
        breakdown_list.append({
            "name": name,
            "score": score,
            "rating": rating
        })

    skills_analysis = {
        "radar": {"labels": radar_labels, "data": radar_data},
        "breakdown": breakdown_list
    }

    # --- Tab 4: Achievements (Real Data) ---
    achievements = [
        {"name": "First Session", "desc": "Completed first practice session", "icon": "fa-check", "status": "Completed" if len(session_history) > 0 else "In Progress", "progress": 100 if len(session_history) > 0 else 0},
        {"name": "Consistent Performer", "desc": "Complete 10 practice sessions", "icon": "fa-medal", "status": f"{len(session_history)}/10", "progress": (len(session_history)/10)*100},
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
