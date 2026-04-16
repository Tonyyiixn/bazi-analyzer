import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';

export default function Dashboard() {
  const [charts, setCharts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // We moved the token up here so we can use it in multiple functions!
  const token = localStorage.getItem('bazi_token');

  useEffect(() => {
    const fetchCharts = async () => {
      if (!token) {
        navigate('/login');
        return;
      }

      try {
        const response = await fetch("http://127.0.0.1:8000/api/v1/charts", {
          method: "GET",
          headers: { "Authorization": `Bearer ${token}` }
        });

        if (!response.ok) throw new Error("Failed to load your vault.");
        const data = await response.json();
        setCharts(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCharts();
  }, [navigate, token]);

  // --- NEW: THE DELETE FUNCTION ---
  const handleDelete = async (chartId) => {
    // Add a quick confirmation popup so they don't delete by accident!
    if (!window.confirm("Are you sure you want to delete this chart?")) return;

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/v1/charts/${chartId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });

      if (!response.ok) throw new Error("Failed to delete the chart.");

      // If successful, instantly remove it from the screen without refreshing the page!
      setCharts(charts.filter(chart => chart.id !== chartId));
      
    } catch (err) {
      alert("Error: " + err.message);
    }
  };
  // --------------------------------

  if (loading) return <div className="text-center py-20 text-slate-500 font-bold animate-pulse">Unlocking your vault...</div>;
  if (error) return <div className="text-center py-20 text-red-500 font-bold">Error: {error}</div>;

  return (
    <div className="w-full max-w-4xl mx-auto px-4">
      
      {/* NEW: THE BACK BUTTON */}
      <div className="mb-6">
        <Link to="/" className="text-indigo-500 hover:text-indigo-700 font-bold flex items-center gap-2 transition">
          <span>←</span> Back to Calculator
        </Link>
      </div>

      <h2 className="text-3xl font-extrabold text-slate-800 mb-8 flex items-center gap-3">
        <span>🗄️</span> My Saved Charts
      </h2>

      {charts.length === 0 ? (
        <div className="bg-white p-10 rounded-2xl shadow-sm text-center border-2 border-dashed border-slate-200">
          <p className="text-slate-500 mb-6 text-lg">Your vault is currently empty!</p>
          <Link to="/" className="bg-gradient-to-r from-purple-600 to-indigo-600 text-white px-8 py-3 rounded-full font-bold hover:scale-105 transition-transform shadow-md inline-block">
            Calculate a Chart
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {charts.map((chart) => (
            <div key={chart.id} className="bg-white p-6 rounded-2xl shadow-md border-t-4 border-indigo-500 hover:shadow-lg transition relative">
              
              {/* NEW: THE DELETE BUTTON (Trash Can Icon) */}
              <button 
                onClick={() => handleDelete(chart.id)}
                className="absolute top-4 right-4 text-slate-300 hover:text-red-500 transition text-xl"
                title="Delete Chart"
              >
                🗑️
              </button>

              <div className="mb-4 pr-8">
                <h3 className="text-xl font-bold text-indigo-900">{chart.name}</h3>
                <span className="text-xs text-slate-400 font-medium">
                  {new Date(chart.created_at).toLocaleDateString()}
                </span>
              </div>
              
              {/* Quick preview of the pillars */}
              <div className="bg-slate-50 rounded-lg p-3 flex justify-between text-center border border-slate-100 mb-4">
                {['year', 'month', 'day', 'hour'].map(pillar => (
                  <div key={pillar}>
                    <p className="text-[10px] text-slate-400 uppercase font-bold">{pillar}</p>
                    <p className="font-medium text-slate-700">{chart.chart_data.pillars[pillar]}</p>
                  </div>
                ))}
              </div>
              
              <div className="text-sm text-slate-500 line-clamp-2 italic mb-4">
                {chart.ai_reading ? "AI Analysis attached ✨" : "No AI Analysis attached"}
              </div>

              {/* NEW: VIEW FULL CHART BUTTON (Placeholder for now) */}
              <button 
                className="w-full bg-indigo-50 text-indigo-600 hover:bg-indigo-100 font-bold py-2 rounded-lg transition"
                onClick={() => alert("Full Chart View coming soon!")}
              >
                View Full Chart
              </button>

            </div>
          ))}
        </div>
      )}
    </div>
  );
}