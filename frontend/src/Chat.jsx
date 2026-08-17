import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';

// Maps markdown elements to theme-matched styling for chat bubbles.
// `dark` is true for the assistant's ink-background bubble, false for the
// user's gold bubble, so bold/heading text stays legible on either.
const markdownComponents = (dark) => ({
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  strong: ({ children }) => (
    <strong className={`font-semibold ${dark ? 'text-gold-400' : 'text-ink-950'}`}>{children}</strong>
  ),
  em: ({ children }) => <em className="italic">{children}</em>,
  ul: ({ children }) => <ul className="list-disc list-outside pl-5 mb-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal list-outside pl-5 mb-2 space-y-1">{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  h1: ({ children }) => <h1 className="font-serif-display text-base mb-1.5 mt-2 first:mt-0">{children}</h1>,
  h2: ({ children }) => <h2 className="font-serif-display text-base mb-1.5 mt-2 first:mt-0">{children}</h2>,
  h3: ({ children }) => <h3 className="font-serif-display text-sm mb-1 mt-2 first:mt-0">{children}</h3>,
  code: ({ children }) => (
    <code className={`px-1 py-0.5 rounded text-xs ${dark ? 'bg-ink-800 text-jade-400' : 'bg-gold-600/20 text-ink-950'}`}>{children}</code>
  ),
  a: ({ children, href }) => (
    <a href={href} target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:opacity-80">{children}</a>
  ),
});

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

    // Older saved charts may predate branch_interactions/stem_combinations/
    // day_master_strength, so only include them when present.
    const extraFields = [
      chartData.hidden_stems && `Hidden Stems (藏干, full breakdown per branch): ${JSON.stringify(chartData.hidden_stems)}`,
      chartData.branch_interactions && `Branch Interactions: ${JSON.stringify(chartData.branch_interactions)}`,
      chartData.stem_combinations && `Stem Combinations: ${JSON.stringify(chartData.stem_combinations)}`,
      chartData.day_master_strength && `Day Master Strength: ${JSON.stringify(chartData.day_master_strength)}`,
      chartData.current_period && `Current Period (Liu Nian/Liu Yue, already computed for today - no need to call get_current_period again unless asked about a different year/month): ${JSON.stringify(chartData.current_period)}`,
    ].filter(Boolean).join('\n');

    const seedMessage = `Here is my already-computed natal chart, no need to recalculate unless I ask about a different date/person:\n${identityLine}\nPillars: ${JSON.stringify(chartData.pillars)}\nTen Gods: ${JSON.stringify(chartData.ten_gods)}\nElements: ${JSON.stringify(chartData.elements)}\nDa Yun: ${JSON.stringify(chartData.da_yuns)}${extraFields ? `\n${extraFields}` : ''}`;

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
          className="mb-4 px-4 py-2 rounded font-semibold text-sm bg-gold-500 text-ink-950 hover:bg-gold-400 transition"
        >
          + New Chat
        </button>
        <div className="bg-ink-900 rounded border border-ink-700 flex-1 overflow-y-auto max-h-[70vh]">
          {sessions.length === 0 && (
            <p className="text-parchment-600 text-xs text-center p-4">No past conversations yet.</p>
          )}
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => openSession(s.id)}
              className={`group px-4 py-3 border-b border-ink-800 cursor-pointer hover:bg-ink-800 transition flex justify-between items-start gap-2 ${
                sessionId === s.id ? 'bg-ink-800' : ''
              }`}
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-parchment-200 truncate">{s.title || 'New conversation'}</p>
                <p className="text-[10px] text-parchment-600">{new Date(s.updated_at).toLocaleDateString()}</p>
              </div>
              <button
                onClick={(e) => deleteSession(s.id, e)}
                className="opacity-0 group-hover:opacity-100 text-parchment-600 hover:text-el-fire transition text-xs shrink-0"
                title="Delete"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* MAIN CHAT PANEL */}
      <div className="flex-1 min-w-0 flex flex-col">
        <h1 className="text-2xl font-serif-display text-parchment-100 mb-2 text-center">Bazi Agent</h1>
        <p className="text-parchment-400 text-sm text-center mb-6">Pick a lens, or just ask — the agent computes your real chart via its tools.</p>

        {/* SKILL PICKER */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
          <button
            onClick={() => setSkillId(null)}
            className={`p-3 rounded border text-center transition ${
              skillId === null ? 'border-gold-500 bg-ink-800' : 'border-ink-700 bg-ink-900 hover:border-ink-600'
            }`}
          >
            <div className="text-xs font-semibold text-parchment-200">Ask Anything</div>
          </button>
          {skills.map((s) => (
            <button
              key={s.id}
              onClick={() => setSkillId(s.id)}
              title={s.description}
              className={`p-3 rounded border text-center transition ${
                skillId === s.id ? 'border-gold-500 bg-ink-800' : 'border-ink-700 bg-ink-900 hover:border-ink-600'
              }`}
            >
              <div className="text-xs font-semibold text-parchment-200">{s.title}</div>
            </button>
          ))}
        </div>

        {/* MESSAGE LIST */}
        <div className="bg-ink-900 rounded border border-ink-700 flex-1 min-h-[400px] max-h-[55vh] overflow-y-auto p-6 mb-4 space-y-4">
          {isLoadingSession && (
            <p className="text-parchment-600 text-sm text-center mt-10 animate-pulse">Loading conversation…</p>
          )}
          {!isLoadingSession && messages.length === 0 && (
            <p className="text-parchment-600 text-sm text-center mt-10">
              Try: "I was born August 24, 1995, 4:45pm in New York, female — what career fits me?"
            </p>
          )}
          {!isLoadingSession && messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[80%] rounded px-4 py-3 text-sm leading-relaxed ${
                  m.role === 'user' ? 'bg-gold-500 text-ink-950 whitespace-pre-wrap' : 'bg-ink-950 text-parchment-200 border border-ink-700'
                }`}
              >
                {m.role === 'assistant' ? (
                  <ReactMarkdown components={markdownComponents(true)}>{m.content}</ReactMarkdown>
                ) : (
                  m.content
                )}
                {m.skillUsed && (
                  <div className="mt-2 text-[10px] uppercase tracking-widest font-semibold text-jade-500">
                    via {m.skillUsed} skill
                  </div>
                )}
              </div>
            </div>
          ))}
          {isSending && <p className="text-parchment-600 text-sm italic">Consulting the charts…</p>}
          <div ref={bottomRef} />
        </div>

        {error && <div className="text-el-fire text-sm text-center font-semibold mb-2">{error}</div>}

        {/* INPUT */}
        <form onSubmit={handleSend} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the agent about your chart…"
            className="flex-1 bg-ink-900 border border-ink-700 text-parchment-200 rounded p-3 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none placeholder:text-parchment-600"
          />
          <button
            type="submit"
            disabled={isSending || !input.trim()}
            className={`px-6 py-3 rounded font-semibold transition ${
              isSending || !input.trim() ? 'bg-ink-700 text-parchment-600 cursor-not-allowed' : 'bg-gold-500 text-ink-950 hover:bg-gold-400'
            }`}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
