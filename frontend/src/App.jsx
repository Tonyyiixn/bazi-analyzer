import { useState , useEffect } from 'react'
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom'
import Auth from './Auth'
import Dashboard from './Dashboard';
import ChartDetail from './ChartDetail';
import Results from './Results';
import Chat from './Chat';
import WheelPicker from './WheelPicker';

const YEAR_OPTIONS = Array.from({ length: 2100 - 1900 + 1 }, (_, i) => 1900 + i);
const MONTH_OPTIONS = Array.from({ length: 12 }, (_, i) => i + 1);
const HOUR_OPTIONS = Array.from({ length: 24 }, (_, i) => i);
const MINUTE_OPTIONS = Array.from({ length: 60 }, (_, i) => i);
const daysInMonth = (year, month) => new Date(year, month, 0).getDate();
const pad2 = (n) => String(n).padStart(2, '0');

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
  const location = useLocation();

  const token = localStorage.getItem('bazi_token');

  const isAuthenticated = !!token;

  useEffect(() => {
    if (!token && location.pathname !== '/login') {
      navigate('/login');
    }
  }, [token, location.pathname, navigate]);

  const handleLogout = () => {
    localStorage.removeItem('bazi_token');
    navigate('/login');
  }

  // 2. Network State
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState(null);

  // AI Time Test State
  const [showRectifier, setShowRectifier] = useState(false);
  const [userTraits, setUserTraits] = useState("");
  const [isRectifying, setIsRectifying] = useState(false);
  const [rectifierResult, setRectifierResult] = useState(null);
  // Whether to apply the True Solar Time correction. User-controlled via a
  // checkbox; the rectifier flips it off as a smart default since its hour
  // is only a ~2hr block estimate, but the user has final say.
  const [useTrueSolarTime, setUseTrueSolarTime] = useState(true);
  // Whether the date/time wheels are expanded for picking, vs. collapsed to
  // a compact YYYY/MM/DD or HH:MM display.
  const [isDatePickerOpen, setIsDatePickerOpen] = useState(false);
  const [isTimePickerOpen, setIsTimePickerOpen] = useState(false);

  // Only Name/Gender/City go through this now - Year/Month/Day/Hour/Minute
  // are set directly by the wheel pickers via setYear/setMonth/setDay/setHour/setMinute.
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  // Year/Month/Day are picked via scrollable wheels; Day's option list
  // depends on Year+Month, so clamp it whenever either changes.
  const dayOptions = Array.from({ length: daysInMonth(formData.year || 2000, formData.month || 1) }, (_, i) => i + 1);
  const setHour = (hour) => setFormData((prev) => ({ ...prev, hour }));
  const setMinute = (minute) => setFormData((prev) => ({ ...prev, minute }));

  const setYear = (year) => {
    setFormData((prev) => ({ ...prev, year, day: Math.min(prev.day, daysInMonth(year, prev.month)) }));
  };
  const setMonth = (month) => {
    setFormData((prev) => ({ ...prev, month, day: Math.min(prev.day, daysInMonth(prev.year, month)) }));
  };
  const setDay = (day) => setFormData((prev) => ({ ...prev, day }));

  // 3. The API Call to FastAPI
  const handleCalculate = async (e) => {
    e.preventDefault();
    setIsCalculating(true);
    setError(null);

    try {
      // Send the JSON payload to our Python backend
      const response = await fetch("http://127.0.0.1:8000/api/v1/calculate", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` // Include the VIP Wristband for authentication
        },
        body: JSON.stringify({ ...formData, skip_true_solar_time: !useTrueSolarTime }),
      });

      if (!response.ok) {
        throw new Error("Server failed to calculate the chart.");
      }

      // Parse the JSON response
      const data = await response.json();
      navigate ('/results', { state: { chartData: data, formData: formData } }); // Send them to the results page with the data
    } catch (err) {
      setError(err.message);
    } finally {
      setIsCalculating(false);
    }
  };

  // 4. The AI Time Rectification Call
  const handleRectifyTime = async (e) => {
    e.preventDefault(); // Stop form submission
    setIsRectifying(true);
    setError(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/v1/rectify-time", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ answers: userTraits }),
      });

      if (!response.ok) throw new Error("Failed to deduce birth time.");

      const data = await response.json();
      setRectifierResult(data.data);

      // Pro-move: Automatically extract the first number from the time block (e.g., "11" from "11:00-13:00")
      // and update the main form data!
      const timeString = data.data.inferred_time_block;
      const inferredHour = parseInt(timeString.split(':')[0]);

      setFormData(prev => ({ ...prev, hour: inferredHour }));
      setUseTrueSolarTime(false); // it's a ~2hr block estimate, not a precise time - user can re-enable below

    } catch (err) {
      setError(err.message);
    } finally {
      setIsRectifying(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink-950 flex flex-col items-center py-10 px-4">

      {/* 1. THE TOP NAVIGATION BAR */}
      <div className="w-full max-w-4xl flex justify-between items-center mb-8 bg-ink-900 p-4 rounded border border-ink-700">
        <Link to="/" className="text-xl font-serif-display text-gold-500 flex items-baseline gap-2">
          <span>命</span> <span className="text-parchment-200">Bazi</span>
        </Link>
        <div>
          {isAuthenticated ? (
            <div className="flex items-center gap-6 text-sm">
              <Link to="/chat" className="text-parchment-400 hover:text-gold-400 font-medium transition">
                Agent
              </Link>
              <Link to="/dashboard" className="text-parchment-400 hover:text-gold-400 font-medium transition">
                Vault
              </Link>
            <button onClick={handleLogout} className="text-parchment-600 hover:text-el-fire font-medium transition">
                Log Out
            </button>
        </div>
          ) : (
            <Link to="/login" className="bg-gold-500 text-ink-950 px-5 py-2 rounded font-semibold hover:bg-gold-400 transition">
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
          {/* Route D: The Detail View for a Single Chart */}
        <Route path="/chart/:id" element={<ChartDetail />} />
        <Route path="/results" element={<Results />} />
        <Route path="/chat" element={<Chat />} />
        {/* Route B: The Main Calculator (Your existing code goes here!) */}
        <Route path="/" element={
          <div className="w-full flex flex-col items-center">

            {/* >>> PASTE ALL YOUR EXISTING CALCULATOR UI HERE <<< */}
            <h1 className="text-4xl font-serif-display font-medium text-parchment-100 mb-8 tracking-tight">Bazi Calculator</h1>

      {/* THE INPUT FORM */}
      <div className="bg-ink-900 border border-ink-700 p-8 rounded w-full max-w-3xl mb-8">
        <h2 className="text-xl font-serif-display text-parchment-100 mb-6 border-b border-ink-700 pb-3">Enter Birth Details</h2>

        <form onSubmit={handleCalculate} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-parchment-400 mb-1">Name</label>
              <input type="text" name="name" value={formData.name} onChange={handleChange} className="w-full bg-ink-950 border border-ink-700 text-parchment-200 rounded p-2 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none" required />
            </div>
            <div>
              <label className="block text-sm font-medium text-parchment-400 mb-1">Gender</label>
              <select name="gender" value={formData.gender} onChange={handleChange} className="w-full bg-ink-950 border border-ink-700 text-parchment-200 rounded p-2 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none">
                <option value="M">Male</option>
                <option value="F">Female</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-parchment-400 mb-1">Birth City</label>
              <input type="text" name="city" value={formData.city} onChange={handleChange} className="w-full bg-ink-950 border border-ink-700 text-parchment-200 rounded p-2 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none" required />
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-parchment-400 mb-2">Birth Date(YYYY-MM-DD)</label>

              {!isDatePickerOpen ? (
                <button
                  type="button"
                  onClick={() => setIsDatePickerOpen(true)}
                  className="w-full max-w-md text-left bg-ink-950 border border-ink-700 text-parchment-200 rounded p-2 hover:border-gold-500 transition font-serif-display tracking-wide"
                >
                  {formData.year}/{String(formData.month).padStart(2, '0')}/{String(formData.day).padStart(2, '0')}
                </button>
              ) : (
                <div className="max-w-md">
                  <div className="grid grid-cols-3 gap-4">
                    <WheelPicker options={YEAR_OPTIONS} value={formData.year} onChange={setYear} itemHeight={48} visibleItems={5} fontSize="text-lg" />
                    <WheelPicker options={MONTH_OPTIONS} value={formData.month} onChange={setMonth} itemHeight={48} visibleItems={5} fontSize="text-lg" />
                    <WheelPicker options={dayOptions} value={formData.day} onChange={setDay} itemHeight={48} visibleItems={5} fontSize="text-lg" />
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsDatePickerOpen(false)}
                    className="mt-3 w-full bg-gold-500 text-ink-950 font-semibold py-2 rounded hover:bg-gold-400 transition"
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
            <div className="max-w-[220px]">
              <div className="flex justify-between items-end mb-1">
                <label className="block text-sm font-medium text-parchment-400">Time</label>
                <button
                  type="button"
                  onClick={() => setShowRectifier(!showRectifier)}
                  className="text-xs text-gold-500 hover:text-gold-400 font-semibold"
                >
                  Don't know?
                </button>
              </div>
              {!isTimePickerOpen ? (
                <button
                  type="button"
                  onClick={() => setIsTimePickerOpen(true)}
                  className="w-full text-left bg-ink-950 border border-ink-700 text-parchment-200 rounded p-2 hover:border-gold-500 transition font-serif-display tracking-wide"
                >
                  {pad2(formData.hour)}:{pad2(formData.minute)}
                </button>
              ) : (
                <div>
                  <div className="grid grid-cols-2 gap-4">
                    <WheelPicker options={HOUR_OPTIONS} value={formData.hour} onChange={setHour} formatOption={pad2} itemHeight={48} visibleItems={5} fontSize="text-lg" />
                    <WheelPicker options={MINUTE_OPTIONS} value={formData.minute} onChange={setMinute} formatOption={pad2} itemHeight={48} visibleItems={5} fontSize="text-lg" />
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsTimePickerOpen(false)}
                    className="mt-3 w-full bg-gold-500 text-ink-950 font-semibold py-2 rounded hover:bg-gold-400 transition"
                  >
                    Done
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* True Solar Time toggle */}
          <div className="flex items-center gap-2 text-sm text-parchment-400 select-none w-fit">
            <input
              type="checkbox"
              checked={useTrueSolarTime}
              onChange={(e) => setUseTrueSolarTime(e.target.checked)}
              className="w-4 h-4 accent-gold-500 cursor-pointer"
            />
            <span>Apply True Solar Time correction</span>
            <span
              title="Adjusts your birth time based on your city's longitude vs. its timezone's standard meridian, for a more precise Hour Pillar. Turn this off if your time above is only an estimate (e.g. from the AI Time Rectifier below) - the correction just adds false precision to a value that isn't precise to begin with."
              className="inline-flex items-center justify-center w-5 h-5 rounded-full border border-parchment-600 text-parchment-600 hover:text-gold-400 hover:border-gold-400 text-xs font-bold cursor-help transition"
            >
              ⓘ
            </span>
          </div>
          

          {/* Dynamic Button State */}
          <button
            type="submit"
            disabled={isCalculating}
            className={`w-full font-semibold py-3 rounded transition ${isCalculating ? 'bg-ink-700 cursor-not-allowed text-parchment-600' : 'bg-gold-500 text-ink-950 hover:bg-gold-400'}`}
          >
            {isCalculating ? 'Calculating...' : 'Calculate Natal Chart'}
          </button>

          {/* Error Message Display */}
          {error && <div className="text-el-fire text-sm text-center font-semibold mt-2">{error}</div>}
        </form>
        {/* --- AI TIME RECTIFICATION PANEL --- */}
        {showRectifier && (
          <div className="mt-8 bg-ink-950 border border-ink-700 p-6 rounded">
            <h3 className="text-base font-serif-display text-parchment-100 mb-2">
              AI Time Rectification
            </h3>
            <p className="text-sm text-parchment-400 mb-4">
              Describe your personality, how you handle stress, and your career style. Claude will analyze your Ten Gods (Shishen) to deduce your likely birth hour.
            </p>

            <textarea
              value={userTraits}
              onChange={(e) => setUserTraits(e.target.value)}
              placeholder="e.g., I am very rebellious, creative, and I hate strict rules. Under stress, I take charge...Please write as much as possible for accuracy"
              className="w-full h-24 bg-ink-900 border border-ink-700 text-parchment-200 rounded p-3 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none mb-3 placeholder:text-parchment-600"
            />

            <button
              type="button"
              onClick={handleRectifyTime}
              disabled={isRectifying || userTraits.length < 10}
              className={`w-full py-2 rounded font-semibold transition ${isRectifying ? 'bg-ink-700 text-parchment-600 cursor-not-allowed' : 'bg-gold-500 text-ink-950 hover:bg-gold-400'}`}
            >
              {isRectifying ? 'Analyzing Personality...' : 'Deduce My Birth Hour'}
            </button>

            {/* Results Output */}
            {rectifierResult && (
              <div className="mt-4 bg-ink-900 p-4 rounded border-l-2 border-jade-500">
                <p className="font-semibold text-parchment-100 text-sm mb-1">
                  Dominant Energy: <span className="text-jade-400">{rectifierResult.inferred_shishen}</span>
                </p>
                <p className="text-sm text-parchment-400 mb-2">
                  <span className="font-semibold text-parchment-200">Reasoning:</span> {rectifierResult.ai_reasoning}
                </p>
                <p className="text-xs font-semibold text-parchment-600 uppercase tracking-wide">
                  Time auto-filled to: {rectifierResult.inferred_time_block}
                </p>
              </div>
            )}
          </div>
        )}
        {/* --- END AI PANEL --- */}
      </div>

          </div>
        } />

      </Routes>


    </div>
  )
}

export default App
