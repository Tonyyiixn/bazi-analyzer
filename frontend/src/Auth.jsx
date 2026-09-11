import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { API_BASE } from './api';

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    // Choose the endpoint based on whether we are logging in or signing up
    const endpoint = isLogin ? '/api/v1/login' : '/api/v1/signup';

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      if (isLogin) {
        // SUCCESS! Save the VIP Wristband and send them to the calculator
        localStorage.setItem('bazi_token', data.access_token);
        navigate('/');
      } else {
        // If they just signed up, switch to login mode so they can enter their new credentials
        setIsLogin(true);
        setError("Account created! Please log in.");
      }

    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-ink-950 flex flex-col justify-center items-center p-4">
      <div className="bg-ink-900 p-8 rounded w-full max-w-md border border-ink-700">
        <h2 className="text-2xl font-serif-display text-parchment-100 mb-6 text-center">
          {isLogin ? 'Welcome Back' : 'Create Account'}
        </h2>

        {error && (
          <div className={`p-3 rounded mb-4 text-sm font-medium border ${error.includes('created') ? 'bg-jade-500/10 border-jade-600 text-jade-400' : 'bg-el-fire/10 border-el-fire text-el-fire'}`}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <div>
              <label className="block text-sm font-medium text-parchment-400 mb-1">Name</label>
              <input
                type="text"
                className="w-full bg-ink-950 border border-ink-700 text-parchment-200 rounded p-3 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-parchment-400 mb-1">Email</label>
            <input
              type="email"
              required
              className="w-full bg-ink-950 border border-ink-700 text-parchment-200 rounded p-3 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-parchment-400 mb-1">Password</label>
            <input
              type="password"
              required
              className="w-full bg-ink-950 border border-ink-700 text-parchment-200 rounded p-3 focus:ring-1 focus:ring-gold-500 focus:border-gold-500 outline-none"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
            />
          </div>

          <button type="submit" className="w-full bg-gold-500 text-ink-950 font-semibold py-3 rounded hover:bg-gold-400 transition">
            {isLogin ? 'Log In' : 'Sign Up'}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-parchment-600">
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <button
            onClick={() => { setIsLogin(!isLogin); setError(null); }}
            className="text-gold-500 font-semibold hover:text-gold-400 hover:underline"
          >
            {isLogin ? 'Sign up' : 'Log in'}
          </button>
        </p>
      </div>
    </div>
  );
}
