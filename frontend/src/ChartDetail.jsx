import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';

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

  if (loading) return <div className="text-center py-20 font-bold animate-pulse">Loading Chart...</div>;
  if (error) return <div className="text-center py-20 text-red-500 font-bold">{error}</div>;

  const { chart_data: chartData, ai_reading: aiReading, name } = chartRecord;

  return (
    <div className="w-full max-w-4xl mx-auto px-4">
      {/* Back Button */}
      <div className="mb-6">
        <Link to="/dashboard" className="text-indigo-500 hover:text-indigo-700 font-bold flex items-center gap-2 transition">
          <span>←</span> Back to Vault
        </Link>
      </div>

      <div className="bg-white p-8 rounded-2xl shadow-xl border-t-4 border-indigo-500">
        <h2 className="text-2xl font-bold text-slate-700 mb-6 text-center">Natal Chart for {name}</h2>
        
        {/* 1. The 4 Pillars */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          {['Year', 'Month', 'Day', 'Hour'].map((pillar) => {
            const pKey = pillar.toLowerCase();
            return (
              <div key={pillar} className="text-center">
                <p className="text-xs text-slate-400 uppercase font-bold mb-2">{pillar}</p>
                <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 shadow-sm">
                  <p className="text-3xl font-medium text-slate-800">{chartData.pillars[pKey]}</p>
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
      </div>

      {/* AI READING DISPLAY */}
      {aiReading && (
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 p-8 rounded-2xl shadow-inner mt-8 border border-indigo-100">
          <h2 className="text-2xl font-bold text-indigo-900 mb-6 flex items-center gap-2">
            <span>🔮</span> AI Astrologer Reading
          </h2>
          <div className="prose prose-indigo max-w-none text-slate-700 leading-relaxed whitespace-pre-wrap font-serif">
            {aiReading}
          </div>
        </div>
      )}
    </div>
  );
}