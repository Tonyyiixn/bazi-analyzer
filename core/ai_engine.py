import os
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