import { useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';

// Helper function to colorize Chinese characters based on their Bazi Element
const getElementColor = (char) => {
  const wood = ['甲', '乙', '寅', '卯'];
  const fire = ['丙', '丁', '巳', '午'];
  const earth = ['戊', '己', '辰', '戌', '丑', '未'];
  const metal = ['庚', '辛', '申', '酉'];
  const water = ['壬', '癸', '亥', '子'];

  if (wood.includes(char)) return 'text-green-500';
  if (fire.includes(char)) return 'text-red-500';
  if (earth.includes(char)) return 'text-amber-700';
  if (metal.includes(char)) return 'text-yellow-500'; // Gold/Metal
  if (water.includes(char)) return 'text-blue-500';
  
  return 'text-slate-800'; // Default fallback
};

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Open the backpack to get the data
  const { chartData, formData } = location.state || {};

  // State for our AI and Saving features
  const [aiReading, setAiReading] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  
  const token = localStorage.getItem('bazi_token');

  // Kick them out if they refresh the page and lose the data
  if (!chartData) {
    return (
      <div className="text-center py-20">
        <p className="text-slate-500 mb-4">No chart data found!</p>
        <button onClick={() => navigate('/')} className="text-indigo-600 font-bold">Go back to Calculator</button>
      </div>
    );
  }

  // --- THE AI FUNCTION ---
  const handleAskAI = async () => {
    setIsGenerating(true);
    try {
      // Note: Adjust this URL if your AI route is named something else!
      const response = await fetch("http://127.0.0.1:8000/api/v1/analyze", { 
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) throw new Error("Failed to get AI reading.");
      
      const data = await response.json();
      setAiReading(data.reading || data.ai_reading || data); // Adjust based on your FastAPI return dictionary
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  // --- THE SAVE FUNCTION ---
  const handleSaveChart = async () => {
    setIsSaving(true);
    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/charts/save", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          name: formData.name,
          chart_data: chartData,
          ai_reading: aiReading
        }),
      });

      if (!response.ok) throw new Error("Failed to save the chart.");

      alert("✨ Chart saved successfully to your Vault!");
      navigate('/dashboard'); // Auto-redirect them to the vault!

    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-12">
      {/* Back Button */}
      <div className="mb-6">
        <Link to="/" className="text-indigo-500 hover:text-indigo-700 font-bold flex items-center gap-2 transition">
          <span>←</span> Calculate Another Chart
        </Link>
      </div>

      <div className="bg-white p-8 rounded-2xl shadow-xl border-t-4 border-indigo-500 mb-8">
        <h2 className="text-2xl font-bold text-slate-700 mb-6 text-center">
          Natal Chart for {formData.name}
        </h2>
        
        {/* 1. The 4 Pillars */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {['Year', 'Month', 'Day', 'Hour'].map((pillar) => {
            const pKey = pillar.toLowerCase();
            return (
              <div key={pillar} className="text-center">
                <p className="text-xs text-slate-400 uppercase font-bold mb-2">{pillar}</p>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 shadow-sm">
                  {/* <p className="text-3xl font-medium text-slate-800">{chartData.pillars[pKey]}</p> */}
                  <p className="flex flex-col items-center text-3xl font-medium drop-shadow-sm space-y-1">
  {String(chartData.pillars[pKey]).split('').map((char, index) => (
    <span key={index} className={getElementColor(char)}>
      {char}
    </span>
  ))}
</p>
                  <p className="text-sm font-bold text-indigo-500 mt-2">{chartData.ten_gods[pKey]}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* 2. Elemental Progress Bars */}
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
                 <div className="flex flex-col items-center text-lg font-medium drop-shadow-sm space-y-1 mt-1">
  {String(yun.pillar).split('').map((char, index) => (
    <span key={index} className={getElementColor(char)}>
      {char}
    </span>
  ))}
</div>
            </div>
            ))}
          </div>
        </div>
    </div>
      {/* ACTION BUTTONS */}
      <div className="flex flex-col sm:flex-row justify-center gap-4 mb-8">
        <button 
          onClick={handleAskAI}
          disabled={isGenerating}
          className={`px-8 py-3 rounded-xl font-bold shadow-sm transition-transform flex items-center justify-center gap-2 ${
            isGenerating 
              ? 'bg-slate-200 cursor-not-allowed text-slate-400' 
              : 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white hover:scale-105'
          }`}
        >
          {isGenerating ? '🔮 Consulting the Stars...' : '🔮 Ask AI Astrologer'}
        </button>

        <button 
          onClick={handleSaveChart}
          disabled={isSaving}
          className={`px-8 py-3 rounded-xl font-bold shadow-sm transition-transform flex items-center justify-center gap-2 ${
            isSaving 
              ? 'bg-slate-200 cursor-not-allowed text-slate-400' 
              : 'bg-emerald-500 text-white hover:bg-emerald-600 hover:scale-105'
          }`}
        >
          {isSaving ? '💾 Saving...' : '💾 Save Chart to Vault'}
        </button>
      </div>

      {/* AI READING DISPLAY */}
      {aiReading && (
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-8 rounded-2xl shadow-inner border border-indigo-100">
          <h2 className="text-2xl font-bold text-indigo-900 mb-6 flex items-center gap-2">
            <span>✨</span> Your Cosmic Reading
          </h2>
          <div className="prose prose-indigo max-w-none text-slate-700 leading-relaxed whitespace-pre-wrap font-serif">
            {aiReading}
          </div>
        </div>
      )}
    </div>
  );
}