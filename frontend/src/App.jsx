import { useState , useEffect, use } from 'react'
import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import Auth from './Auth'
import Dashboard from './Dashboard';

function App() {
  // 1. Form State
  const [formData, setFormData] = useState({
    name: 'Alice',
    gender: 'M',
    city: 'Beijing',
    year: 1990,
    month: 1,
    day: 1,
    hour: 1,
    minute: 1
  });

  const navigate = useNavigate();
  
  const token = localStorage.getItem('bazi_token');

  const isAuthenticated = !!token;

  useEffect(() => {
    if (!token && window.location.pathname !== '/login') {
      navigate('/login');
    }
  }, [token, navigate]);

  const handleLogout = () => {
    localStorage.removeItem('bazi_token');
    navigate('/login');
  }

  // 2. Network State
  const [isCalculating, setIsCalculating] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [error, setError] = useState(null);

  // AI Analysis State
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiReading, setAiReading] = useState(null);

  // Save chart state
  const [isSaving, setIsSaving] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    const parsedValue = ['year', 'month', 'day', 'hour', 'minute'].includes(name) 
      ? parseInt(value) || '' 
      : value;
    setFormData({ ...formData, [name]: parsedValue });
  };

  // 3. The API Call to FastAPI
  const handleCalculate = async (e) => {
    e.preventDefault();
    setIsCalculating(true);
    setError(null);
    setChartData(null); // Clear old chart if recalculating

    try {
      // Send the JSON payload to our Python backend
      const response = await fetch("http://127.0.0.1:8000/api/v1/calculate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` // Include the VIP Wristband for authentication
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error("Server failed to calculate the chart.");
      }

      // Parse the JSON response
      const data = await response.json();
      setChartData(data); // Save the pillars and elements into React state!

    } catch (err) {
      setError(err.message);
    } finally {
      setIsCalculating(false);
    }
  };

  // 4. The AI Analysis Call
  const handleAnalyze = async () => {
    setIsAnalyzing(true);
    setAiReading(null); // Clear old reading if asking again
    setError(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` // Include the VIP Wristband for authentication
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error("Failed to connect to the AI engine.");
      }

      const data = await response.json();
      setAiReading(data.ai_reading);

    } catch (err) {
      setError(err.message);
    } finally {
      setIsAnalyzing(false);
    }
  };


  const handleSaveChart = async () => {
    setIsSaving(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/charts/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` // Show the VIP wristband!
        },
        body: JSON.stringify({
          name: formData.name, // The person's name from the input form
          chart_data: chartData, // The calculated 4 pillars data
          ai_reading: aiReading // The Gemini text (will be null if they haven't asked AI yet)
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to save the chart.");
      }

      alert("✨ Chart saved successfully to your Vault!");

    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center py-10 px-4">

      {/* 1. THE TOP NAVIGATION BAR */}
      <div className="w-full max-w-4xl flex justify-between items-center mb-8 bg-white p-4 rounded-xl shadow-sm border-b-2 border-indigo-100">
        <Link to="/" className="text-xl font-bold text-indigo-900 flex items-center gap-2">
          <span>🌌</span> Bazi AI
        </Link>
        <div>
          {isAuthenticated ? (
            <div className="flex items-center gap-6">
              <Link to="/dashboard" className="text-indigo-600 font-bold hover:text-indigo-800 transition">
                My Vault
              </Link>
            <button onClick={handleLogout} className="text-slate-500 hover:text-red-500 font-bold transition">
                Log Out
            </button>
        </div>
          ) : (
            <Link to="/login" className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-5 py-2 rounded-full font-bold hover:scale-105 transition-transform shadow-md">
              Log In
            </Link>
          )}
        </div>
      </div>

      {/* 2. THE TRAFFIC COP (ROUTER) */}
      <Routes>
        
        {/* Route A: The Login Page */}
        <Route path="/login" element={<Auth />} />
          {/* Route C: The Dashboard for Saved Charts */}
        <Route path="/dashboard" element={<Dashboard />} />
        {/* Route B: The Main Calculator (Your existing code goes here!) */}
        <Route path="/" element={
          <div className="w-full flex flex-col items-center">
            
            {/* >>> PASTE ALL YOUR EXISTING CALCULATOR UI HERE <<< */}
            <h1 className="text-4xl font-extrabold text-slate-800 mb-8 tracking-tight">☯️ Bazi Calculator Pro</h1>
      
      {/* THE INPUT FORM */}
      <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-3xl mb-8">
        <h2 className="text-2xl font-bold text-slate-700 mb-6 border-b pb-2">Enter Birth Details</h2>
        
        <form onSubmit={handleCalculate} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Name</label>
              <input type="text" name="name" value={formData.name} onChange={handleChange} className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Gender</label>
              <select name="gender" value={formData.gender} onChange={handleChange} className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none">
                <option value="M">Male</option>
                <option value="F">Female</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Birth City</label>
              <input type="text" name="city" value={formData.city} onChange={handleChange} className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Year</label>
              <input type="number" name="year" value={formData.year} onChange={handleChange} min="1900" max="2100" className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Month</label>
              <input type="number" name="month" value={formData.month} onChange={handleChange} min="1" max="12" className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Day</label>
              <input type="number" name="day" value={formData.day} onChange={handleChange} min="1" max="31" className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Hour</label>
              <input type="number" name="hour" value={formData.hour} onChange={handleChange} min="0" max="23" className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1">Minute</label>
              <input type="number" name="minute" value={formData.minute} onChange={handleChange} min="0" max="59" className="w-full border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none" required />
            </div>
          </div>

          {/* Dynamic Button State */}
          <button 
            type="submit" 
            disabled={isCalculating}
            className={`w-full font-bold py-3 rounded-lg transition shadow-md ${isCalculating ? 'bg-indigo-400 cursor-not-allowed text-indigo-100' : 'bg-indigo-600 text-white hover:bg-indigo-700'}`}
          >
            {isCalculating ? 'Calculating Astrometry...' : 'Calculate Natal Chart'}
          </button>

          {/* Error Message Display */}
          {error && <div className="text-red-500 text-sm text-center font-semibold mt-2">{error}</div>}
        </form>
      </div>

      {/* THE RESULTS DASHBOARD (Only shows if chartData exists) */}
      {/* THE RESULTS DASHBOARD */}
      {chartData && (
        <div className="space-y-8 w-full max-w-4xl animate-fade-in-up">
          
          {/* MAIN CHART CARD */}
          <div className="bg-white p-8 rounded-2xl shadow-xl border-t-4 border-indigo-500">
            <h2 className="text-2xl font-bold text-slate-700 mb-6 text-center">Natal Chart (Four Pillars)</h2>
            
            {/* 1. The 4 Pillars & Ten Gods */}
            <div className="grid grid-cols-4 gap-4 mb-8">
              {['Year', 'Month', 'Day', 'Hour'].map((pillar) => {
                const pKey = pillar.toLowerCase();
                return (
                  <div key={pillar} className="text-center">
                    <p className="text-xs text-slate-400 uppercase font-bold mb-2">{pillar}</p>
                    <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 shadow-sm hover:shadow-md transition">
                      <p className="text-3xl font-medium text-slate-800">{chartData.pillars[pKey]}</p>
                      {/* Dynamic Ten Gods Injection */}
                      <p className="text-sm font-bold text-indigo-500 mt-2">{chartData.ten_gods[pKey]}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* 2. Elemental Progress Bars */}
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 text-center">Element Strength</h3>
            <div className="grid grid-cols-5 gap-2 mb-8">
              {Object.entries(chartData.elements).map(([el, val]) => (
                <div key={el} className="text-center">
                  <div className="h-24 bg-slate-100 rounded-full relative overflow-hidden flex flex-col justify-end">
                    <div 
                      className={`w-full transition-all duration-1000 ${el === 'Wood' ? 'bg-green-500' : el === 'Fire' ? 'bg-red-500' : el === 'Earth' ? 'bg-amber-700' : el === 'Metal' ? 'bg-yellow-400' : 'bg-blue-500'}`} 
                      style={{ height: `${(val / 8) * 100}%` }}
                    ></div>
                  </div>
                  <p className="text-xs font-bold mt-2 text-slate-600">{el} ({val})</p>
                </div>
              ))}
            </div>

            {/* 3. The Da Yun (10-Year Luck Pillars) */}
            <div className="pt-6 border-t border-slate-100">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 text-center">10-Year Luck Pillars (Da Yun)</h3>
              <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
                {chartData.da_yuns.map((yun, index) => (
                  <div key={index} className="bg-slate-50 border border-slate-200 rounded-lg p-2 text-center shadow-sm hover:bg-indigo-50 transition cursor-default">
                    <p className="text-xs font-bold text-slate-500 mb-1">{yun.start_age}y</p>
                    <p className="text-[10px] text-slate-400 mb-1">{yun.start_year}</p>
                    <p className="text-base font-medium text-slate-800">{yun.pillar}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* THE AI TRIGGER BUTTON */}
          <div className="flex flex-col items-center py-6">
            <p className="text-slate-500 text-sm mb-4 italic">Want a deeper look into your destiny?</p>
            <button 
              onClick={handleAnalyze}
              disabled={isAnalyzing}
              className={`px-10 py-4 rounded-full font-bold shadow-lg transition-transform flex items-center gap-2 ${
                isAnalyzing 
                  ? 'bg-slate-300 cursor-not-allowed text-slate-500 animate-pulse' 
                  : 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:scale-105'
              }`}
            >
              {isAnalyzing ? '✨ Consulting the Stars...' : '✨ Ask Gemini AI for Detailed Analysis'}
            </button>
          </div>
          
          {/* THE SAVE BUTTON */}
          <div className="flex justify-center mt-6">
            <button 
              onClick={handleSaveChart}
              disabled={isSaving}
              className={`px-8 py-3 rounded-xl font-bold shadow-sm transition-transform flex items-center gap-2 ${
                isSaving 
                  ? 'bg-slate-200 cursor-not-allowed text-slate-400' 
                  : 'bg-emerald-500 text-white hover:bg-emerald-600 hover:scale-105'
              }`}
            >
              {isSaving ? '💾 Saving...' : '💾 Save Chart to Profile'}
            </button>
          </div>
          {/* AI READING DISPLAY */}
          {aiReading && (
            <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-8 rounded-2xl shadow-inner mt-8 animate-fade-in-up border border-indigo-100">
              <h2 className="text-2xl font-bold text-indigo-900 mb-6 flex items-center gap-2">
                <span>🔮</span> AI Astrologer Reading
              </h2>
              <div className="prose prose-indigo max-w-none text-slate-700 leading-relaxed whitespace-pre-wrap font-serif">
                {aiReading}
              </div>
            </div>
          )}
        </div>
      )}
            {/* (The title, the input form, the chartData cards, the Gemini AI button, etc.) */}
            
          </div>
        } />

      </Routes>

      
    </div>
  )
}

export default App