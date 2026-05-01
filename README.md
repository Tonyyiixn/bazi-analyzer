# ☯️ AI-Driven Bazi Astrology Assistant

An intelligent, full-stack web application that modernizes traditional Chinese metaphysics (Bazi) using Generative AI. 

Instead of relying solely on static mathematical chart calculations, this application utilizes **Google Gemini** and advanced prompt engineering to perform "Time Rectification"—analyzing a user's unstructured personality traits to deduce missing birth hour data through LLM reasoning.

## ✨ Key Features
* **AI Time Rectification:** Integrates Google Gemini to process MBTI-style user inputs and output highly structured JSON data to determine the most statistically likely birth hour.
* **Decoupled Architecture:** Built with a clean separation of concerns, featuring a modern REST API backend and a state-driven client interface.
* **Cloud-Native Deployment:** Containerized with Docker and deployed across serverless cloud infrastructure (AWS ECS Fargate & Vercel).
* **Real-Time Insights:** Calculates complex astrological pillars and translates them into digestible, user-friendly readings.

## 🛠️ Tech Stack
* **Frontend:** React.js, Vite, Tailwind CSS, JavaScript/HTML
* **Backend:** Python, FastAPI, Uvicorn, Pydantic
* **AI / LLM:** Google Gemini API (Generative AI)
* **DevOps & Cloud:** Docker, AWS ECR, AWS ECS (Fargate), Vercel

---

## 🚀 Local Installation & Setup

If you want to run this project locally, you will need two separate terminal windows (one for the frontend, one for the backend).

### 1. Clone the Repository
```bash
git clone https://github.com/Tonyyiixn/bazi-analyzer.git
cd bazi-analyzer
```

### 2. Backend Setup (FastAPI)
Navigate to the backend directory and set up your Python environment:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

**Environment Variables:**
Create a `.env` file in the `backend` directory and add your Google Gemini API key:

```env
GEMINI_API_KEY=your_api_key_here
```

Start the backend server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*The API will be running at `http://localhost:8000/docs`*

### 3. Frontend Setup (React/Vite)
Open a new terminal, navigate to the frontend directory, and start the development server:

```bash
cd frontend
npm install
npm run dev
```
*The UI will be running at `http://localhost:5173`*