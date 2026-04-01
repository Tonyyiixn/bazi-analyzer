import { useState } from 'react'

function App() {
  // 1. Form State
  const [formData, setFormData] = useState({
    name: 'Alex',
    gender: 'M',
    city: 'Chengdu',
    year: 1995,
    month: 8,
    day: 15,
    hour: 14,
    minute: 30
  });

  // 2. Network State
  const [isCalculating, setIsCalculating] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [error, setError] = useState(null);

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

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center py-10 px-4">
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
      {chartData && (
        <div className="space-y-8 w-full max-w-4xl animate-fade-in-up">
          
          {/* MAIN CHART CARD */}
          <div className="bg-white p-8 rounded-2xl shadow-xl border-t-4 border-indigo-500">
            <h2 className="text-2xl font-bold text-slate-700 mb-6 text-center">Natal Chart (Four Pillars)</h2>
            
            <div className="grid grid-cols-4 gap-4 mb-8">
              {['Year', 'Month', 'Day', 'Hour'].map((pillar) => (
                <div key={pillar} className="text-center">
                  <p className="text-xs text-slate-400 uppercase font-bold mb-2">{pillar}</p>
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 shadow-sm">
                    {/* The Pillar (e.g., 甲子) */}
                    <p className="text-3xl font-medium text-slate-800">{chartData.pillars[pillar.toLowerCase()]}</p>
                    {/* Placeholder for Shishen (e.g., Eating God) */}
                    <p className="text-sm font-bold text-indigo-500 mt-2">Eating God</p>
                  </div>
                </div>
              ))}
            </div>

            {/* ELEMENTAL PROGRESS BARS */}
            <h3 className="text-sm font-bold text-slate-400 uppercase tracking-widest mb-4 text-center">Element Strength</h3>
            <div className="grid grid-cols-5 gap-2">
              {Object.entries(chartData.elements).map(([el, val]) => (
                <div key={el} className="text-center">
                  <div className="h-24 bg-slate-100 rounded-full relative overflow-hidden flex flex-col justify-end">
                    <div 
                      className={`w-full transition-all duration-1000 ${el === 'Wood' ? 'bg-green-500' : el === 'Fire' ? 'bg-red-500' : el === 'Earth' ? 'bg-amber-700' : el === 'Metal' ? 'bg-yellow-400' : 'bg-blue-500'}`} 
                      style={{ height: `${(val / 8) * 100}%` }}
                    ></div>
                  </div>
                  <p className="text-xs font-bold mt-2 text-slate-600">{el}</p>
                </div>
              ))}
            </div>
          </div>

          {/* THE AI TRIGGER BUTTON (The "Small Button" you requested) */}
          <div className="flex flex-col items-center py-6">
            <p className="text-slate-500 text-sm mb-4 italic">Want a deeper look into your destiny?</p>
            <button className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-10 py-4 rounded-full font-bold shadow-lg hover:scale-105 transition-transform flex items-center gap-2">
              ✨ Ask Gemini AI for Detailed Analysis
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default App