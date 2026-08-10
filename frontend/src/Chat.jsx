import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';

const ICONS = {
  briefcase: '💼',
  heart: '💞',
  calendar: '📅',
  'heart-pulse': '🩺',
  sparkles: '✨',
};

const API = 'http://127.0.0.1:8000/api/v1';

export default function Chat() {
  const location = useLocation();
  const token = localStorage.getItem('bazi_token');

  const [skills, setSkills] = useState([]);
  const [skillId, setSkillId] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isLoadingSession, setIsLoadingSession] = useState(false);
  const [error, setError] = useState(null);

  const bottomRef = useRef(null);
  const seededLocationKey = useRef(null);

  const authHeaders = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };

  const refreshSessions = () => {
    fetch(`${API}/chat/sessions`, { headers: authHeaders })
      .then((res) => res.json())
      .then(setSessions)
      .catch(() => {});
  };

  // Fetch the skill registry + this user's past sessions
  useEffect(() => {
    fetch(`${API}/skills`)
      .then((res) => res.json())
      .then(setSkills)
      .catch(() => setError('Could not load skills.'));
    refreshSessions();
  }, []);

  // Arrived from Results/ChartDetail with chart context - kick off a real
  // first turn (grounded by the actual agent) in a brand new session,
  // instead of faking a canned local exchange.
  useEffect(() => {
    const { chartData, formData } = location.state || {};
    if (!chartData || !formData) return;
    if (seededLocationKey.current === location.key) return; // already handled this navigation
    seededLocationKey.current = location.key;

    const identityLine = [
      `Name: ${formData.name}`,
      formData.gender && `Gender: ${formData.gender}`,
      formData.city && `City: ${formData.city}`,
    ].filter(Boolean).join(', ');

    const seedMessage = `Here is my already-computed natal chart, no need to recalculate unless I ask about a different date/person:\n${identityLine}\nPillars: ${JSON.stringify(chartData.pillars)}\nTen Gods: ${JSON.stringify(chartData.ten_gods)}\nElements: ${JSON.stringify(chartData.elements)}\nDa Yun: ${JSON.stringify(chartData.da_yuns)}`;

    startNewChat();
    sendMessage(seedMessage, null);
  }, [location.key]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startNewChat = () => {
    setSessionId(null);
    setMessages([]);
    setSkillId(null);
    setError(null);
  };

  const openSession = async (id) => {
    setIsLoadingSession(true);
    setError(null);
    try {
      const response = await fetch(`${API}/chat/sessions/${id}`, { headers: authHeaders });
      if (!response.ok) throw new Error('Could not load that conversation.');
      const data = await response.json();
      setSessionId(data.id);
      setSkillId(data.skill_id || null);
      setMessages(
        data.messages.map((m) => ({ role: m.role, content: m.content }))
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingSession(false);
    }
  };

  const deleteSession = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation?')) return;
    try {
      await fetch(`${API}/chat/sessions/${id}`, { method: 'DELETE', headers: authHeaders });
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (sessionId === id) startNewChat();
    } catch {
      alert('Failed to delete conversation.');
    }
  };

  // Sends one message against `forSessionId` (null = start a new session).
  // Used both by the normal input box and the chart-context seed above.
  const sendMessage = async (text, forSessionId) => {
    setMessages((prev) => [...prev, { role: 'user', content: text }]);
    setIsSending(true);
    setError(null);

    try {
      const response = await fetch(`${API}/chat`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ message: text, session_id: forSessionId, skill_id: skillId }),
      });

      if (!response.ok) throw new Error('The agent failed to respond.');

      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'assistant', content: data.reply, skillUsed: data.skill_used }]);
      setSessionId(data.session_id);
      refreshSessions();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSending(false);
    }
  };

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim() || isSending) return;
    const text = input;
    setInput('');
    sendMessage(text, sessionId);
  };

  return (
    <div className="w-full max-w-6xl mx-auto px-4 pb-12 flex gap-6">
      {/* SESSION SIDEBAR */}
      <div className="w-64 shrink-0 hidden md:flex flex-col">
        <button
          onClick={startNewChat}
          className="mb-4 px-4 py-2 rounded-xl font-bold text-sm bg-indigo-600 text-white hover:bg-indigo-700 transition"
        >
          + New Chat
        </button>
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 flex-1 overflow-y-auto max-h-[70vh]">
          {sessions.length === 0 && (
            <p className="text-slate-400 text-xs text-center p-4">No past conversations yet.</p>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => openSession(s.id)}
              className={`group px-4 py-3 border-b border-slate-50 cursor-pointer hover:bg-slate-50 transition flex justify-between items-start gap-2 ${
                sessionId === s.id ? 'bg-indigo-50' : ''
              }`}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-700 truncate">{s.title || 'New conversation'}</p>
                <p className="text-[10px] text-slate-400">{new Date(s.updated_at).toLocaleDateString()}</p>
              </div>
              <button
                onClick={(e) => deleteSession(s.id, e)}
                className="opacity-0 group-hover:opacity-100 text-slate-300 hover:text-red-500 transition text-sm"
                title="Delete"
              >
                🗑️
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CHAT PANEL */}
      <div className="flex-1 min-w-0 flex flex-col">
        <h1 className="text-3xl font-extrabold text-slate-800 mb-2 tracking-tight text-center">🤖 Bazi Agent</h1>
        <p className="text-slate-500 text-center mb-6">Pick a lens, or just ask — the agent computes your real chart via its tools.</p>

        {/* SKILL PICKER */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <button
            onClick={() => setSkillId(null)}
            className={`p-3 rounded-xl border text-center transition ${
              skillId === null ? 'border-indigo-500 bg-indigo-50 shadow-sm' : 'border-slate-200 bg-white hover:border-indigo-300'
            }`}
          >
            <div className="text-2xl mb-1">✨</div>
            <div className="text-xs font-bold text-slate-700">Ask Anything</div>
          </button>
          {skills.map((s) => (
            <button
              key={s.id}
              onClick={() => setSkillId(s.id)}
              title={s.description}
              className={`p-3 rounded-xl border text-center transition ${
                skillId === s.id ? 'border-indigo-500 bg-indigo-50 shadow-sm' : 'border-slate-200 bg-white hover:border-indigo-300'
              }`}
            >
              <div className="text-2xl mb-1">{ICONS[s.icon] || '🔮'}</div>
              <div className="text-xs font-bold text-slate-700">{s.title}</div>
            </button>
          ))}
        </div>

        {/* MESSAGE LIST */}
        <div className="bg-white rounded-2xl shadow-xl border border-slate-100 flex-1 min-h-[400px] max-h-[55vh] overflow-y-auto p-6 mb-4 space-y-4">
          {isLoadingSession && (
            <p className="text-slate-400 text-sm text-center mt-10 animate-pulse">Loading conversation…</p>
          )}
          {!isLoadingSession && messages.length === 0 && (
            <p className="text-slate-400 text-sm text-center mt-10">
              Try: "I was born August 24, 1995, 4:45pm in New York, female — what career fits me?"
            </p>
          )}
          {!isLoadingSession && messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 whitespace-pre-wrap text-sm leading-relaxed ${
                  m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-50 text-slate-800 border border-slate-100'
                }`}
              >
                {m.content}
                {m.skillUsed && (
                  <div className="mt-2 text-[10px] uppercase tracking-widest font-bold text-indigo-400">
                    via {m.skillUsed} skill
                  </div>
                )}
              </div>
            </div>
          ))}
          {isSending && <p className="text-slate-400 text-sm italic">Consulting the charts…</p>}
          <div ref={bottomRef} />
        </div>

        {error && <div className="text-red-500 text-sm text-center font-semibold mb-2">{error}</div>}

        {/* INPUT */}
        <form onSubmit={handleSend} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the agent about your chart…"
            className="flex-1 border border-slate-300 rounded-xl p-3 focus:ring-2 focus:ring-indigo-500 outline-none"
          />
          <button
            type="submit"
            disabled={isSending || !input.trim()}
            className={`px-6 py-3 rounded-xl font-bold shadow-sm transition ${
              isSending || !input.trim() ? 'bg-slate-200 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-700'
            }`}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
