from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

# --- IMPORT OUR EXISTING ENGINES ---
from core import database
from database.models import SessionLocal, Base, engine
from database.crud import create_reading
from core.time_engine import get_true_solar_time
from core.bazi_math import calculate_bazi_chart, get_element_counts ,calculate_chart_ten_gods
from core.ai_engine import generate_reading

from core.schemas import BaziRequest, UserCreate, UserResponse, Token, UserLogin
from core import models, security , schemas
from core.database import engine, get_db

# Initialize the API
app = FastAPI(title="Bazi Analyzer API", version="2.0")

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

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        adj_year, adj_month, adj_day, adj_hour, adj_minute = get_true_solar_time(
            request.year, request.month, request.day, request.hour, request.minute, request.city
        )
        
        # Step B: Math Engine
        pillars, da_yuns = calculate_bazi_chart(
            adj_year, adj_month, adj_day, adj_hour, adj_minute, request.gender
        )
        elements = get_element_counts(pillars)
        
        ten_gods = calculate_chart_ten_gods(pillars)
        return {
            "success": True,
            "user": request.name,
            "pillars": pillars,
            "ten_gods": ten_gods,
            "da_yuns": da_yuns,
            "elements": elements
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Calculation Error: {str(e)}")


@app.post("/api/v1/analyze")
def analyze_bazi(request: BaziRequest, db: Session = Depends(get_db)):
    """Heavy lifting: Runs the AI generation and saves to the database."""
    try:
        # Re-run the fast math locally to get the pillars for the AI
        adj_year, adj_month, adj_day, adj_hour, adj_minute = get_true_solar_time(
            request.year, request.month, request.day, request.hour, request.minute, request.city
        )
        pillars, _ = calculate_bazi_chart(adj_year, adj_month, adj_day, adj_hour, adj_minute, request.gender)
        
        # Step C: AI Engine
        ai_text = generate_reading(request.name, request.gender, request.city, request.year, pillars)
        
        # Step D: Save to DB
        pillars_str = f"{pillars['year']} {pillars['month']} {pillars['day']} {pillars['hour']}"
        birth_date_str = f"{request.year}-{request.month:02d}-{request.day:02d} {request.hour:02d}:{request.minute:02d}"
        create_reading(db, request.name, request.gender, request.city, birth_date_str, pillars_str, ai_text)
        
        return {
            "success": True,
            "ai_reading": ai_text
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Engine Error: {str(e)}")
    

@app.post("/api/v1/charts/save")
def save_user_chart(
    chart_in: schemas.ChartCreate, 
    db: Session = Depends(database.get_db),
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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(security.get_current_user) # The VIP Bouncer!
):
    """Fetches all saved charts for the currently logged-in user."""
    
    # Query the database for charts where the user_id matches our current user
    charts = db.query(models.SavedChart).filter(models.SavedChart.user_id == current_user.id).all()
    
    return charts


@app.delete("/api/v1/charts/{chart_id}")
def delete_user_chart(
    chart_id: int,
    db: Session = Depends(database.get_db),
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