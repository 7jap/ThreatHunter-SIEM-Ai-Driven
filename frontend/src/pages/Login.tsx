import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Settings, Server, Lock } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { api } from '../lib/api';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showConfig, setShowConfig] = useState(false);
  const [tempUrl, setTempUrl] = useState(useAuthStore.getState().serverUrl);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  
  const { setToken, setServerUrl, setUser } = useAuthStore();
  const navigate = useNavigate();

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const { data } = await api.post('/api/v1/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      setToken(data.access_token);
      
      const meRes = await api.get('/api/v1/auth/me');
      setUser(meRes.data);
      
      navigate('/');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed. Check server connection or credentials.');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = () => {
    let clean = tempUrl.trim();
    // Fix accidental /:8443 -> :8443
    clean = clean.replace(/\/:(\d+)/, ':$1');
    // Remove trailing slashes
    clean = clean.replace(/\/+$/, '');
    setServerUrl(clean);
    setTempUrl(clean);
    setShowConfig(false);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-surface p-8 rounded-lg shadow-xl border border-slate-700">
        <div className="flex justify-center mb-6">
          <Shield className="w-16 h-16 text-primary" />
        </div>
        <h1 className="text-2xl font-bold text-center text-white mb-2">Dashboard</h1>
        <p className="text-slate-400 text-center mb-8">Sign in to your security dashboard</p>

        {error && (
          <div className="bg-danger/20 border border-danger/50 text-danger p-3 rounded mb-6 text-sm">
            {error}
          </div>
        )}

        {showConfig ? (
          <div className="space-y-4 animate-in fade-in slide-in-from-top-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">SIEM Server URL</label>
              <div className="relative">
                <Server className="absolute left-3 top-2.5 h-5 w-5 text-slate-400" />
                <input
                  type="text"
                  value={tempUrl}
                  onChange={(e) => setTempUrl(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md py-2 pl-10 pr-4 text-white focus:outline-none focus:border-primary"
                  placeholder="https://192.168.1.100:8443"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowConfig(false)}
                className="w-1/3 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-md transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={saveConfig}
                className="w-2/3 py-2 bg-primary hover:bg-blue-600 text-white rounded-md font-medium transition-colors"
              >
                Save Configuration
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-md py-2 px-4 text-white focus:outline-none focus:border-primary"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-2.5 h-5 w-5 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-md py-2 pl-10 pr-4 text-white focus:outline-none focus:border-primary"
                  required
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2 mt-4 bg-primary hover:bg-blue-600 text-white rounded-md font-medium transition-colors flex justify-center items-center"
            >
              {loading ? 'Authenticating...' : 'Sign In'}
            </button>
          </form>
        )}

        <div className="mt-8 flex justify-center">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center text-sm text-slate-400 hover:text-white transition-colors"
          >
            <Settings className="w-4 h-4 mr-2" />
            {showConfig ? 'Back to Login' : 'Configure Server Endpoint'}
          </button>
        </div>
      </div>
    </div>
  );
}
