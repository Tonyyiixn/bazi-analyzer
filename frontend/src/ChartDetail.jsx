import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';

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
  if (metal.includes(char)) return 'text-el-metal';
  if (water.includes(char)) return 'text-el-water';

  return 'text-parchment-200'; // Default fallback
};

export default function ChartDetail() {
  const { id } = useParams(); // Grabs the ID from the URL!
  const navigate = useNavigate();
  const [chartRecord, setChartRecord] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchChart = async () => {
      const token = localStorage.getItem('bazi_token');
      if (!token) {
        navigate('/login');
        return;
      }

      try {
        const response = await fetch(`http://127.0.0.1:8000/api/v1/charts/${id}`, {
          headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Could not find this chart.");

        const data = await response.json();
        setChartRecord(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchChart();
  }, [id, navigate]);

  if (loading) return <div className="text-center py-20 text-parchment-400 font-semibold animate-pulse">Loading Chart...</div>;
  if (error) return <div className="text-center py-20 text-el-fire font-semibold">{error}</div>;

  const { chart_data: chartData, ai_reading: aiReading, name } = chartRecord;

  return (
    <div className="w-full max-w-4xl mx-auto px-4">
      {/* Back Button */}
      <div className="mb-6">
        <Link to="/dashboard" className="text-gold-500 hover:text-gold-400 font-semibold flex items-center gap-2 transition">
          <span>←</span> Back to Vault
        </Link>
      </div>

      <div className="bg-ink-900 border border-ink-700 p-8 rounded">
        <h2 className="text-xl font-serif-display text-parchment-100 mb-6 text-center">Natal Chart for {name}</h2>

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
        <div className="grid grid-cols-5 gap-2 mb-8">
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
      </div>

      {/* AGENT NAVIGATION */}
      <div className="flex justify-center mt-8 mb-8">
        <button
          onClick={() => navigate('/chat', { state: { chartData, formData: { name } } })}
          className="px-8 py-3 rounded font-semibold transition flex items-center justify-center gap-2 bg-gold-500 text-ink-950 hover:bg-gold-400"
        >
          Discuss with the Agent
        </button>
      </div>

      {/* AI READING DISPLAY */}
      {aiReading && (
        <div className="bg-ink-900 p-8 rounded mt-8 border border-ink-700">
          <h2 className="text-xl font-serif-display text-parchment-100 mb-6">
            AI Astrologer Reading
          </h2>
          <div className="max-w-none text-parchment-200 leading-relaxed whitespace-pre-wrap font-serif-display">
            {aiReading}
          </div>
        </div>
      )}
    </div>
  );
}
