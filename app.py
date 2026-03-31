import streamlit as st
from datetime import datetime

# --- IMPORT OUR CUSTOM ENGINES ---
from database.models import SessionLocal
from database.crud import create_reading, get_recent_readings
from core.time_engine import get_true_solar_time
from core.bazi_math import calculate_bazi_chart
from core.ai_engine import generate_reading

# --- UI HELPER FUNCTIONS ---
WUXING_COLORS = {
    "甲": "#4CAF50", "乙": "#4CAF50", "寅": "#4CAF50", "卯": "#4CAF50",
    "丙": "#F44336", "丁": "#F44336", "巳": "#F44336", "午": "#F44336",
    "戊": "#8D6E63", "己": "#8D6E63", "辰": "#8D6E63", "戌": "#8D6E63", "丑": "#8D6E63", "未": "#8D6E63",
    "庚": "#FFC107", "辛": "#FFC107", "申": "#FFC107", "酉": "#FFC107",
    "壬": "#2196F3", "癸": "#2196F3", "亥": "#2196F3", "子": "#2196F3"
}

def color_char(char):
    """Wraps characters in their elemental color for the UI."""
    color = WUXING_COLORS.get(char, "black")
    return f"<span style='color:{color}; font-size: 24px; font-weight: bold;'>{char}</span>"

# --- DATABASE SESSION MANAGEMENT ---
def get_db():
    """Safely opens and closes the database connection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- MAIN APP LAYOUT ---
st.set_page_config(page_title="Pro Bazi Master", page_icon="☯️", layout="wide")
st.title("☯️ Advanced Enterprise Bazi Analyzer")
st.markdown("Powered by True Solar Time, Lunar Math, and Gemini AI.")

# 1. Input Section
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Your Name", "Jackie")
    city = st.text_input("Birth City", "New York")
    gender_input = st.radio("Gender", ["Male", "Female"], horizontal=True)

with col2:
    year = st.number_input("Year", min_value=1900, max_value=2100, value=1995)
    month = st.number_input("Month", min_value=1, max_value=12, value=8)
    day = st.number_input("Day", min_value=1, max_value=31, value=24)
    c1, c2 = st.columns(2)
    with c1: hour = st.number_input("Hour (24h)", min_value=0, max_value=23, value=16)
    with c2: minute = st.number_input("Minute", min_value=0, max_value=59, value=45)

# 2. Execution Section
if st.button("Calculate & Save Bazi Chart", type="primary"):
    with st.spinner("Consulting the engines..."):
        try:
            # Step A: True Solar Time Engine
            adj_year, adj_month, adj_day, adj_hour, adj_minute = get_true_solar_time(year, month, day, hour, minute, city)
            
            # Step B: Bazi Math Engine
            pillars, da_yuns = calculate_bazi_chart(adj_year, adj_month, adj_day, adj_hour, adj_minute, gender_input)
            
            # Step C: AI Reading Engine
            ai_text = generate_reading(name, gender_input, city, year, pillars)
            
            # --- THE NEW MULTI-TAB UI ---
            tab1, tab2, tab3 = st.tabs(["☯️ Natal Chart", "📊 Five Elements", "🔮 Yearly Predictions"])
            
            # --- TAB 1: The Original Bazi Reading ---
            with tab1:
                st.subheader(f"{name}'s Natal Chart")
                pc1, pc2, pc3, pc4 = st.columns(4)
                with pc1: st.markdown("**Year**<br>" + color_char(pillars['year'][0]) + "<br>" + color_char(pillars['year'][1]), unsafe_allow_html=True)
                with pc2: st.markdown("**Month**<br>" + color_char(pillars['month'][0]) + "<br>" + color_char(pillars['month'][1]), unsafe_allow_html=True)
                with pc3: st.markdown("**Day Master**<br>" + color_char(pillars['day'][0]) + "<br>" + color_char(pillars['day'][1]), unsafe_allow_html=True)
                with pc4: st.markdown("**Hour**<br>" + color_char(pillars['hour'][0]) + "<br>" + color_char(pillars['hour'][1]), unsafe_allow_html=True)
                
                st.divider()
                st.subheader("Major Life Cycles (Da Yun)")
                dy_cols = st.columns(8)
                for i in range(1, 9):
                    if i < len(da_yuns):
                        dy = da_yuns[i]
                        with dy_cols[i-1]:
                            st.markdown(f"**Age {dy.getStartAge()}**")
                            st.markdown(color_char(dy.getGanZhi()[0]) + "<br>" + color_char(dy.getGanZhi()[1]), unsafe_allow_html=True)
                
                st.divider()
                st.subheader("AI Astrological Analysis")
                st.write(ai_text)
            
            # --- TAB 2: The Elements Chart (Coming Next) ---
            with tab2:
                st.subheader("The Five Elements Balance (Wu Xing)")
                st.info("We will build the math to count the elements and display a bar chart here next!")
                
            # --- TAB 3: Yearly Predictions (Coming Next) ---
            with tab3:
                st.subheader("2026 Yearly Forecast")
                st.info("We will add a new AI prompt engine to look at the current year's energy and predict the user's fortune here!")

            # Step E: Save to Database Engine
            db = next(get_db())
            pillars_str = f"{pillars['year']} {pillars['month']} {pillars['day']} {pillars['hour']}"
            birth_date_str = f"{year}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"
            create_reading(db, name, gender_input, city, birth_date_str, pillars_str, ai_text)

        except Exception as e:
            st.error(f"System Error: {e}")

# 3. Sidebar History (Admin Locked)
st.sidebar.title("🔒 Admin Access")
st.sidebar.markdown("Enter password to view user history.")

# The type="password" hides the text as they type!
admin_attempt = st.sidebar.text_input("Password", type="password")

# Fetch the real password from our secure environment variables
import os
CORRECT_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Only run the database query IF the password matches
if admin_attempt == CORRECT_PASSWORD:
    st.sidebar.success("Database Unlocked")
    st.sidebar.subheader("📜 Reading History")
    
    db = next(get_db())
    history = get_recent_readings(db)

    if history:
        for record in history:
            with st.sidebar.expander(f"👤 {record.name} ({record.birth_date[:4]})"):
                st.markdown(f"**Pillars:** {record.pillars}")
                st.caption(record.ai_reading[:150] + "...")
    else:
        st.sidebar.info("Database is empty. Generate a reading!")
elif admin_attempt:
    # If they typed something, but it's wrong, show an error.
    st.sidebar.error("Incorrect password.")

