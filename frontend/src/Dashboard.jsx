import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { API } from './api';

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
        const response = await fetch(`${API}/charts`, {
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
      const response = await fetch(`${API}/charts/${chartId}`, {
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

  if (loading) return <div className="text-center py-20 text-parchment-400 font-semibold animate-pulse">Unlocking your vault...</div>;
  if (error) return <div className="text-center py-20 text-el-fire font-semibold">Error: {error}</div>;

  return (
    <div className="w-full max-w-4xl mx-auto px-4">

      {/* NEW: THE BACK BUTTON */}
      <div className="mb-6">
        <Link to="/" className="text-gold-500 hover:text-gold-400 font-semibold flex items-center gap-2 transition">
          <span>←</span> Back to Calculator
        </Link>
      </div>

      <h2 className="text-2xl font-serif-display text-parchment-100 mb-8">
        My Saved Charts
      </h2>

      {charts.length === 0 ? (
        <div className="bg-ink-900 p-10 rounded text-center border border-dashed border-ink-700">
          <p className="text-parchment-400 mb-6 text-lg">Your vault is currently empty.</p>
          <Link to="/" className="bg-gold-500 text-ink-950 px-8 py-3 rounded font-semibold hover:bg-gold-400 transition inline-block">
            Calculate a Chart
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {charts.map((chart) => (
            <div key={chart.id} className="bg-ink-900 border border-ink-700 p-6 rounded hover:border-gold-600 transition relative">

              {/* NEW: THE DELETE BUTTON */}
              <button
                onClick={() => handleDelete(chart.id)}
                className="absolute top-4 right-4 text-parchment-600 hover:text-el-fire transition text-sm"
                title="Delete Chart"
              >
                Delete
              </button>

              <div className="mb-4 pr-12">
                <h3 className="text-lg font-serif-display text-parchment-100">{chart.name}</h3>
                <span className="text-xs text-parchment-600 font-medium">
                  {new Date(chart.created_at).toLocaleDateString()}
                </span>
              </div>

              {/* Quick preview of the pillars */}
              <div className="bg-ink-950 rounded p-3 flex justify-between text-center border border-ink-700 mb-4">
                {['year', 'month', 'day', 'hour'].map(pillar => (
                  <div key={pillar}>
                    <p className="text-[10px] text-parchment-600 uppercase font-semibold">{pillar}</p>
                    <p className="font-serif-display text-parchment-200">{chart.chart_data.pillars[pillar]}</p>
                  </div>
                ))}
              </div>

              <div className="text-sm text-parchment-600 italic mb-4">
                {chart.ai_reading ? "AI analysis attached" : "No AI analysis attached"}
              </div>

              <Link
                to={`/chart/${chart.id}`}
                className="w-full bg-ink-950 border border-ink-700 text-gold-500 hover:border-gold-500 font-semibold py-2 rounded transition text-center block"
              >
                View Full Chart
              </Link>

            </div>
          ))}
        </div>
      )}
    </div>
  );
}
