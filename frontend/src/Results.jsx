import { useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';

// Helper function to colorize Chinese characters based on their Bazi Element
const getElementColor = (char) => {
  const wood = ['甲', '乙', '寅', '卯'];
  const fire = ['丙', '丁', '巳', '午'];
  const earth = ['戊', '己', '辰', '戌', '丑', '未'];
  const metal = ['庚', '辛', '申', '酉'];
  const water = ['壬', '癸', '亥', '子'];

  if (wood.includes(char)) return 'text-el-wood';
  if (fire.includes(char)) return 'text-el-fire';
  if (earth.includes(char)) return 'text-el-earth';
  if (metal.includes(char)) return 'text-el-metal'; // Gold/Metal
  if (water.includes(char)) return 'text-el-water';

  return 'text-parchment-200'; // Default fallback
};

export default function Results() {
  const location = useLocation();
  const navigate = useNavigate();

  // Open the backpack to get the data
  const { chartData, formData } = location.state || {};

  // State for the Saving feature
  const [isSaving, setIsSaving] = useState(false);

  const token = localStorage.getItem('bazi_token');

  // Kick them out if they refresh the page and lose the data
  if (!chartData) {
    return (
      <div className="text-center py-20">
        <p className="text-parchment-400 mb-4">No chart data found!</p>
        <button onClick={() => navigate('/')} className="text-gold-500 font-semibold hover:text-gold-400">Go back to Calculator</button>
      </div>
    );
  }

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
        }),
      });

      if (!response.ok) throw new Error("Failed to save the chart.");

      alert("Chart saved to your Vault.");
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
        <Link to="/" className="text-gold-500 hover:text-gold-400 font-semibold flex items-center gap-2 transition">
          <span>←</span> Calculate Another Chart
        </Link>
      </div>

      <div className="bg-ink-900 border border-ink-700 p-8 rounded mb-8">
        <h2 className="text-xl font-serif-display text-parchment-100 mb-6 text-center">
          Natal Chart for {formData.name}
        </h2>

        {/* 1. The 4 Pillars */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {['Year', 'Month', 'Day', 'Hour'].map((pillar) => {
            const pKey = pillar.toLowerCase();
            return (
              <div key={pillar} className="text-center">
                <p className="text-xs text-parchment-600 uppercase tracking-widest font-semibold mb-2">{pillar}</p>
                <div className="bg-ink-950 border border-ink-700 rounded p-4">
                  {/* Stem (upper) */}
                  <div className="flex flex-col items-center">
                    <span className={`text-3xl font-serif-display ${getElementColor(chartData.pillars[pKey][0])}`}>
                      {chartData.pillars[pKey][0]}
                    </span>
                    <span className="text-xs font-semibold text-gold-500 mt-1">{chartData.ten_gods[pKey].stem}</span>
                  </div>
                  {/* Branch (lower) */}
                  <div className="flex flex-col items-center mt-2 pt-2 border-t border-ink-700">
                    <span className={`text-3xl font-serif-display ${getElementColor(chartData.pillars[pKey][1])}`}>
                      {chartData.pillars[pKey][1]}
                    </span>
                    <span className="text-xs font-semibold text-jade-500 mt-1">{chartData.ten_gods[pKey].branch}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* 2. Elemental Progress Bars */}
        <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">Element Strength</h3>
        <div className="grid grid-cols-5 gap-2">
          {Object.entries(chartData.elements).map(([el, val]) => (
            <div key={el} className="text-center">
              <div className="h-24 bg-ink-950 border border-ink-700 rounded relative overflow-hidden flex flex-col justify-end">
                <div
                  className={`w-full transition-all duration-700 ${el === 'Wood' ? 'bg-el-wood' : el === 'Fire' ? 'bg-el-fire' : el === 'Earth' ? 'bg-el-earth' : el === 'Metal' ? 'bg-el-metal' : 'bg-el-water'}`}
                  style={{ height: `${(val / 8) * 100}%` }}
                ></div>
              </div>
              <p className="text-xs font-semibold mt-2 text-parchment-400">{el} ({val})</p>
            </div>
          ))}
        </div>



        {/* 3. The Da Yun (10-Year Luck Pillars) */}
        <div className="pt-6 border-t border-ink-700 mt-6">
            <h3 className="text-xs font-semibold text-parchment-600 uppercase tracking-widest mb-4 text-center">10-Year Luck Pillars (Da Yun)</h3>
            <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
            {chartData.da_yuns.map((yun, index) => (
                <div key={index} className="bg-ink-950 border border-ink-700 rounded p-2 text-center hover:border-gold-500 transition cursor-default">
                <p className="text-xs font-semibold text-parchment-400 mb-1">{yun.start_age}y</p>
                <p className="text-[10px] text-parchment-600 mb-1">{yun.start_year}</p>
                 <div className="flex flex-col items-center text-lg font-serif-display space-y-1 mt-1">
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
          onClick={handleSaveChart}
          disabled={isSaving}
          className={`px-8 py-3 rounded font-semibold transition flex items-center justify-center gap-2 ${
            isSaving
              ? 'bg-ink-700 cursor-not-allowed text-parchment-600'
              : 'bg-jade-500 text-ink-950 hover:bg-jade-400'
          }`}
        >
          {isSaving ? 'Saving...' : 'Save Chart to Vault'}
        </button>

        <button
          onClick={() => navigate('/chat', { state: { chartData, formData } })}
          className="px-8 py-3 rounded font-semibold transition flex items-center justify-center gap-2 bg-gold-500 text-ink-950 hover:bg-gold-400"
        >
          Discuss with the Agent
        </button>
      </div>
    </div>
  );
}
