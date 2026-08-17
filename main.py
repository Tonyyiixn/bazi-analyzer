from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# --- IMPORT OUR EXISTING ENGINES ---
from core.time_engine import get_true_solar_time
from core.bazi_math import calculate_bazi_chart, get_element_counts, calculate_chart_ten_gods, calculate_chart_hidden_stems
from core.bazi_interactions import find_branch_interactions, find_stem_combinations, get_current_period
from core.bazi_strength import analyze_day_master_strength
from core.ai_engine import rectify_birth_hour
from core.agent.orchestrator import BaziAgent
from core.skills.registry import SKILLS, DEFAULT_SKILL_ID

from core.schemas import BaziRequest, UserCreate, UserResponse, Token, UserLogin, TimeTestAnswers, ChatRequest, PillarsRequest
from core import models, security, schemas
from core.database import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.bazi_agent = BaziAgent()
    await app.state.bazi_agent.start()
    yield
    await app.state.bazi_agent.stop()


# Initialize the API
app = FastAPI(title="Bazi Analyzer API", version="2.0", lifespan=lifespan)

# This line tells SQLAlchemy to create the database file and tables!
models.Base.metadata.create_all(bind=engine)

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.post("/api/v1/signup", response_model=UserResponse)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """Registers a new user and saves them to the database."""
    # 1. Check if the email is already in use
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Hash the password
    hashed_pw = security.get_password_hash(user.password)
    
    # 3. Save the new user to the vault
    new_user = models.User(email=user.email, name=user.name, hashed_password=hashed_pw)
    db.add(new_user)
    db.commit()
    db.refresh(new_user) # Refreshes to get the auto-generated ID
    
    return new_user


@app.post("/api/v1/login", response_model=Token)
def login(user: UserLogin, db: Session = Depends(get_db)):
    """Logs a user in and hands them a VIP Wristband (JWT)."""
    # 1. Find the user by email
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    
    # 2. If user doesn't exist OR password doesn't match the hash, kick them out
    if not db_user or not security.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    # 3. If they pass, print the VIP wristband!
    access_token = security.create_access_token(data={"sub": db_user.email})
    
    return {"access_token": access_token, "token_type": "bearer"}



# CORS config allows your future React app to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    ], # We will lock this down to your React URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    return {"status": "Bazi API is online and waiting for React."}

@app.post("/api/v1/calculate")
def calculate_bazi(request: BaziRequest,
                   current_user: models.User = Depends(security.get_current_user)):
    """Lightning fast: Only runs the math engines to return the chart."""

    try:
        # Step A: Time Engine
        # Skip the correction when the hour is an AI-rectified estimate (a ~2hr
        # block, not a precise clock time) - true solar time math would just
        # add false precision on top of an already-approximate value.
        if request.skip_true_solar_time:
            adj_year, adj_month, adj_day, adj_hour, adj_minute = (
                request.year, request.month, request.day, request.hour, request.minute
            )
        else:
            adj_year, adj_month, adj_day, adj_hour, adj_minute = get_true_solar_time(
                request.year, request.month, request.day, request.hour, request.minute, request.city
            )

        # Step B: Math Engine
        pillars, da_yuns = calculate_bazi_chart(
            adj_year, adj_month, adj_day, adj_hour, adj_minute, request.gender
        )
        elements = get_element_counts(pillars)

        ten_gods = calculate_chart_ten_gods(pillars)
        hidden_stems = calculate_chart_hidden_stems(pillars)
        branch_interactions = find_branch_interactions(pillars)
        stem_combinations = find_stem_combinations(pillars)
        day_master_strength = analyze_day_master_strength(pillars)
        return {
            "success": True,
            "user": request.name,
            "pillars": pillars,
            "ten_gods": ten_gods,
            "hidden_stems": hidden_stems,
            "da_yuns": da_yuns,
            "elements": elements,
            "branch_interactions": branch_interactions,
            "stem_combinations": stem_combinations,
            "day_master_strength": day_master_strength,
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation Error: {str(e)}")


@app.post("/api/v1/current-period")
def current_period(request: PillarsRequest,
                    current_user: models.User = Depends(security.get_current_user)):
    """Today's Liu Nian/Liu Yue against a natal chart. Deliberately NOT part
    of /calculate's response or the saved chart_data blob - it's a live,
    moving fact (today's date), not a static property of the chart, so
    callers should always fetch it fresh (e.g. on every page load) instead
    of trusting a persisted copy that would go stale the day after it was
    saved."""
    try:
        return {"success": True, **get_current_period(request.pillars)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Current Period Error: {str(e)}")


@app.post("/api/v1/rectify-time")
def rectify_time(request: TimeTestAnswers):
    """
    AI Time Rectification: Uses Gemini to deduce the Shishen and birth hour 
    based on the user's personality traits.
    """
    try:
        # Call the AI engine
        result = rectify_birth_hour(request.answers)
        
        return {
            "success": True,
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Rectification Error: {str(e)}")


@app.get("/api/v1/skills")
def list_skills():
    """Returns the skill registry so the frontend can render a picker."""
    return [
        {"id": s.id, "title": s.title, "description": s.description, "icon": s.icon}
        for s in SKILLS.values()
        if s.id != DEFAULT_SKILL_ID
    ]


@app.post("/api/v1/chat")
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Agent chat: Claude picks/uses a skill and calls the Bazi engines over MCP as tools.

    Session-authoritative: the client sends only the new message. Prior
    history is loaded from the database, and both the new user message and
    the assistant's reply are persisted before returning."""
    try:
        if request.session_id is not None:
            session = db.query(models.ChatSession).filter(
                models.ChatSession.id == request.session_id,
                models.ChatSession.user_id == current_user.id,
            ).first()
            if not session:
                raise HTTPException(status_code=404, detail="Chat session not found")
        else:
            session = models.ChatSession(user_id=current_user.id)
            db.add(session)
            db.flush()  # assigns session.id without a full commit

        history = [{"role": m.role, "content": m.content} for m in session.messages]
        history.append({"role": "user", "content": request.message})

        result = await app.state.bazi_agent.run(history, request.skill_id)

        db.add(models.ChatMessage(session_id=session.id, role="user", content=request.message))
        db.add(models.ChatMessage(session_id=session.id, role="assistant", content=result["reply"]))

        if session.title is None:
            session.title = request.message[:60]
        session.skill_id = result.get("skill_used")
        session.updated_at = datetime.utcnow()

        db.commit()

        return {"success": True, "session_id": session.id, **result}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")


@app.get("/api/v1/chat/sessions", response_model=list[schemas.ChatSessionOut])
def list_chat_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Lists the current user's chat sessions, most recently active first."""
    return db.query(models.ChatSession).filter(
        models.ChatSession.user_id == current_user.id
    ).order_by(models.ChatSession.updated_at.desc()).all()


@app.get("/api/v1/chat/sessions/{session_id}", response_model=schemas.ChatSessionDetailOut)
def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Fetches one chat session with its full message history."""
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session


@app.delete("/api/v1/chat/sessions/{session_id}")
def delete_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    """Deletes a chat session and its messages."""
    session = db.query(models.ChatSession).filter(
        models.ChatSession.id == session_id,
        models.ChatSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    db.delete(session)
    db.commit()
    return {"message": "Chat session deleted"}


@app.post("/api/v1/charts/save")
def save_user_chart(
    chart_in: schemas.ChartCreate, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user) # The Bouncer!
):
    """Saves a Bazi chart and AI reading to the user's account."""
    
    # Create the new chart record
    new_chart = models.SavedChart(
        user_id=current_user.id,
        name=chart_in.name,
        chart_data=chart_in.chart_data,
        ai_reading=chart_in.ai_reading
    )
    
    # Add to database and save
    db.add(new_chart)
    db.commit()
    db.refresh(new_chart)
    
    return {"message": "Chart saved successfully!", "chart_id": new_chart.id}

@app.get("/api/v1/charts")
def get_user_charts(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user) # The VIP Bouncer!
):
    """Fetches all saved charts for the currently logged-in user."""
    
    # Query the database for charts where the user_id matches our current user
    charts = db.query(models.SavedChart).filter(models.SavedChart.user_id == current_user.id).all()
    
    return charts


@app.delete("/api/v1/charts/{chart_id}")
def delete_user_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user) # The VIP Bouncer!
):
    """Deletes a specific chart belonging to the logged-in user."""
    
    # 1. Find the exact chart, making sure it belongs to this user
    chart = db.query(models.SavedChart).filter(
        models.SavedChart.id == chart_id,
        models.SavedChart.user_id == current_user.id
    ).first()
    
    # 2. If it doesn't exist (or isn't theirs), throw a 404 error
    if not chart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")
        
    # 3. Delete it and save the changes
    db.delete(chart)
    db.commit()
    
    return {"message": "Chart deleted successfully"}

@app.get("/api/v1/charts/{chart_id}")
def get_single_chart(
    chart_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user) # The VIP Bouncer
):
    """Fetches a single saved chart by its ID."""
    
    chart = db.query(models.SavedChart).filter(
        models.SavedChart.id == chart_id,
        models.SavedChart.user_id == current_user.id
    ).first()
    
    if not chart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chart not found")
        
    return chart