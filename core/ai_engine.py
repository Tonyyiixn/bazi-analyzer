import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables and configure the AI
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_reading(name, gender, city, birth_year, pillars):
    """Constructs the prompt and fetches the AI reading."""
    current_age = datetime.now().year - birth_year
    
    prompt = f"""
    You are a master of Bazi (Four Pillars of Destiny). 
    A {gender} named {name} born in {city} has the following pillars:
    Year: {pillars['year']}, Month: {pillars['month']}, Day: {pillars['day']}, Hour: {pillars['hour']}. 
    They are currently {current_age} years old.
    
    Provide a 3-paragraph reading:
    Paragraph 1: Analyze their primary elements and day master.
    Paragraph 2: Provide insights into their optimal career path.
    Paragraph 3: Look at their current age and provide life advice based on Bazi philosophy.
    """
    
    response = model.generate_content(prompt)
    return response.text

def generate_yearly_prediction(name, gender, pillars, current_year=2026):
    """Generates a specific fortune reading for the current year."""
    prompt = f"""
    You are a master of Bazi (Four Pillars of Destiny). 
    A {gender} named {name} has the following natal chart:
    Year: {pillars['year']}, Month: {pillars['month']}, Day: {pillars['day']}, Hour: {pillars['hour']}. 
    
    The current year is {current_year} (Year of the Fire Horse / Bing Wu). 
    Analyze how the energy of {current_year} interacts with their specific chart.
    
    Provide a 2-paragraph forecast:
    Paragraph 1: Career, Wealth, and Opportunities this year.
    Paragraph 2: Relationships, Health, and Personal Growth this year.
    
    Keep the tone professional, insightful, and encouraging.
    """
    
    response = model.generate_content(prompt)
    return response.text

def rectify_birth_hour(user_answers: str):
    """
    Analyzes MBTI-style user answers to deduce their Bazi birth hour (Shishen).
    Forces the AI to return a structured JSON response.
    """
    prompt = f"""
    You are an expert in traditional Bazi (Four Pillars of Destiny) and the Shishen (Ten Gods) system. 
    The user does not know their exact birth hour. Based on the following personality traits and situational reactions, 
    determine the most likely dominant Shishen in their Hour Pillar. 
    
    User Traits: {user_answers}
    
    Calculate the corresponding 2-hour Chinese time block (e.g., Zi hour 23:00-01:00, Chou hour 01:00-03:00).
    
    You must output a JSON object with EXACTLY these four keys:
    "inferred_shishen": (String - The name of the Ten God)
    "inferred_time_block": (String - e.g., "11:00-13:00")
    "earthly_branch": (String - e.g., "Wu")
    "ai_reasoning": (String - 1-2 sentences explaining why)
    """
    
    # Force Gemini to return strictly formatted JSON
    response = model.generate_content(
        prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
        )
    )
    
    # Convert the JSON string from Gemini into a usable Python dictionary
    return json.loads(response.text)