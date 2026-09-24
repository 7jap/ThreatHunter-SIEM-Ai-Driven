import { useEffect, useState, useRef } from 'react';
import { api } from '../lib/api';
import { Activity, ShieldAlert, ShieldCheck, Send, BrainCircuit } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { format } from 'date-fns';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';

export default function Dashboard() {
  const { user, serverUrl } = useAuthStore();
  const [stats, setStats] = useState<any>({ total_alerts: 0, high_severity: 0, active_agents: 0, by_severity: {}, timeline: [] });
  const [recentAlerts, setRecentAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Chat State
  const [chatMessages, setChatMessages] = useState<{role: 'ai' | 'user', text: string}[]>([
    { role: 'ai', text: `Hi ${user?.display_name || 'there'}! I'm your AI SOC Analyst. How can I help you today?` }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDashboardData();
    // Fast 3-second background polling fallback
    const interval = setInterval(fetchDashboardData, 3000);
    
    // Connect to WebSocket with auto-reconnect
    const token = useAuthStore.getState().token;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = serverUrl ? serverUrl.replace(/^https?:\/\//, '').replace(/\/+$/, '') : window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/ws${token ? `?token=${encodeURIComponent(token)}` : ''}`;
    
    let ws: WebSocket | null = null;
    let reconnectTimeout: any = null;
    let isUnmounted = false;

    const connectWs = () => {
      if (isUnmounted) return;
      try {
        ws = new WebSocket(wsUrl);
        
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.event === 'alert.created') {
              setRecentAlerts(prev => {
                if (prev.some(a => a.id === msg.data.id)) return prev;
                return [msg.data, ...prev].slice(0, 5);
              });
              setStats((prev: any) => ({ ...prev, total_alerts: (prev?.total_alerts || 0) + 1 }));
              fetchDashboardData();
            } else if (msg.event === 'alert.ai_completed') {
              setRecentAlerts(prev => prev.map(a => 
                a.id === msg.data.alert_id 
                  ? { ...a, status: 'ANALYZED', ai_verdict: msg.data.verdict, ai_confidence: msg.data.confidence } 
                  : a
              ));
              fetchDashboardData();
            }
          } catch(e) {}
        };

        ws.onclose = () => {
          if (!isUnmounted) {
            reconnectTimeout = setTimeout(connectWs, 2000);
          }
        };

        ws.onerror = () => {
          ws?.close();
        };
      } catch (e) {
        if (!isUnmounted) {
          reconnectTimeout = setTimeout(connectWs, 2000);
        }
      }
    };

    connectWs();

    return () => {
      isUnmounted = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      clearInterval(interval);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [serverUrl]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const fetchDashboardData = async () => {
    try {
      const statsRes = await api.get('/api/v1/alerts/stats');
      setStats({
        total_alerts: statsRes.data.total_alerts,
        high_severity: statsRes.data.by_severity['1'] || 0,
        active_agents: 1, // Mock or fetch actual
        by_severity: statsRes.data.by_severity,
        timeline: statsRes.data.timeline
      });

      const alertsRes = await api.get('/api/v1/alerts?limit=5');
      setRecentAlerts(alertsRes.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Load chat messages from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem('dashboard_chat_history');
    if (saved) {
      try {
        setChatMessages(JSON.parse(saved));
      } catch (e) {}
    }
  }, []);

  // Save to localStorage on change
  useEffect(() => {
    localStorage.setItem('dashboard_chat_history', JSON.stringify(chatMessages));
  }, [chatMessages]);

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    const userMsg = chatInput;
    // Send the last 5 messages to the backend as history context
    const historyPayload = chatMessages.slice(-5);
    
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await api.post('/api/v1/chat', { 
        message: userMsg,
        history: historyPayload
      });
      setChatMessages(prev => [...prev, { role: 'ai', text: res.data.response }]);
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Error: Could not reach AI service.';
      setChatMessages(prev => [...prev, { role: 'ai', text: String(errMsg) }]);
    } finally {
      setChatLoading(false);
    }
  };

  // Process data for graphs
  const timelineData = stats.timeline && stats.timeline.length > 0 
    ? stats.timeline.map((t: any) => ({ time: format(new Date(t.time), 'HH:mm'), alerts: t.alerts })) 
    : [];

  const severityData = stats.by_severity ? [
    { name: 'High', value: stats.by_severity['1'] || 0, color: '#ef4444' }, // Red
    { name: 'Medium', value: stats.by_severity['2'] || 0, color: '#f59e0b' }, // Yellow
    { name: 'Low', value: stats.by_severity['3'] || 0, color: '#3b82f6' } // Blue
  ].filter(d => d.value > 0) : [];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Security Overview</h1>
          <p className="text-slate-400 mt-1">Real-time threat monitoring and AI analysis.</p>
        </div>
      </div>

      {/* Top Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="bg-surface rounded-xl border border-slate-700/60 p-6 flex items-center shadow-lg shadow-black/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <Activity className="w-24 h-24 text-blue-500" />
          </div>
          <div className="p-4 bg-blue-500/10 rounded-lg mr-4 border border-blue-500/20 z-10">
            <Activity className="w-8 h-8 text-blue-400" />
          </div>
          <div className="z-10">
            <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">Total Alerts</p>
            <p className="text-3xl font-bold text-white mt-1">{loading ? '-' : stats.total_alerts}</p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-surface rounded-xl border border-danger/30 p-6 flex items-center shadow-lg shadow-danger/5 relative overflow-hidden">
           <div className="absolute top-0 right-0 p-4 opacity-10">
            <ShieldAlert className="w-24 h-24 text-danger" />
          </div>
          <div className="p-4 bg-danger/10 rounded-lg mr-4 border border-danger/20 z-10">
            <ShieldAlert className="w-8 h-8 text-danger" />
          </div>
          <div className="z-10">
            <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">High Severity</p>
            <p className="text-3xl font-bold text-white mt-1">{loading ? '-' : stats.high_severity}</p>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-surface rounded-xl border border-slate-700/60 p-6 flex items-center shadow-lg shadow-black/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10">
            <ShieldCheck className="w-24 h-24 text-success" />
          </div>
          <div className="p-4 bg-success/10 rounded-lg mr-4 border border-success/20 z-10">
            <ShieldCheck className="w-8 h-8 text-success" />
          </div>
          <div className="z-10">
            <p className="text-sm font-medium text-slate-400 uppercase tracking-wider">Active Agents</p>
            <p className="text-3xl font-bold text-white mt-1">{loading ? '-' : stats.active_agents}</p>
          </div>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Graphs & Recent Alerts */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Charts Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Area Chart */}
            <div className="bg-surface rounded-xl border border-slate-700/60 p-6 shadow-lg shadow-black/20">
              <h3 className="text-lg font-medium text-white mb-4">Alerts Over Time (24h)</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={timelineData}>
                    <defs>
                      <linearGradient id="colorAlerts" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis stroke="#94a3b8" fontSize={12} tickLine={false} axisLine={false} />
                    <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }} />
                    <Area type="monotone" dataKey="alerts" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorAlerts)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Donut Chart */}
            <div className="bg-surface rounded-xl border border-slate-700/60 p-6 shadow-lg shadow-black/20">
              <h3 className="text-lg font-medium text-white mb-4">Severity Distribution</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={severityData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                      {severityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip contentStyle={{ backgroundColor: '#1e293b', borderColor: '#334155', color: '#f8fafc' }} />
                    <Legend verticalAlign="bottom" height={36} iconType="circle" />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Recent Alerts List */}
          <div className="bg-surface rounded-xl border border-slate-700/60 overflow-hidden shadow-lg shadow-black/20">
            <div className="p-5 border-b border-slate-700/60 bg-slate-800/30 flex justify-between items-center">
              <h2 className="text-lg font-medium text-white">Recent Detections</h2>
            </div>
            <div className="divide-y divide-slate-700/50">
              {recentAlerts.map((alert, i) => (
                <motion.div 
                  initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.1 }}
                  key={alert.id} className="p-4 hover:bg-slate-800/40 transition-colors flex justify-between items-center"
                >
                  <div>
                    <div className="flex items-center space-x-3 mb-1">
                      <span className={`w-2 h-2 rounded-full ${alert.severity === 1 ? 'bg-danger' : alert.severity === 2 ? 'bg-warning' : 'bg-primary'}`}></span>
                      <p className="text-white font-medium text-sm">{alert.signature}</p>
                      {alert.ai_verdict && (
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border ${
                          alert.ai_verdict === 'MALICIOUS' ? 'border-danger text-danger bg-danger/10' :
                          alert.ai_verdict === 'BENIGN' ? 'border-success text-success bg-success/10' : 'border-warning text-warning bg-warning/10'
                        }`}>AI: {alert.ai_verdict} {alert.ai_confidence ? `(${alert.ai_confidence}%)` : ''}</span>
                      )}
                    </div>
                    <p className="text-slate-400 text-xs font-mono">{alert.source_ip} → {alert.destination_ip}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-slate-400 text-xs">{format(new Date(alert.timestamp), 'HH:mm:ss')}</p>
                    <p className="text-slate-500 text-[10px] uppercase mt-1">{alert.status}</p>
                  </div>
                </motion.div>
              ))}
              {recentAlerts.length === 0 && !loading && (
                <div className="p-8 text-center text-slate-500">No alerts detected recently.</div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: AI Assistant Chat */}
        <div className="bg-surface rounded-xl border border-slate-700/60 shadow-lg shadow-black/20 flex flex-col h-[800px] overflow-hidden">
          {/* Header */}
          <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-900 shrink-0">
            <div className="flex items-center">
              <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center mr-3">
                <BrainCircuit className="w-4 h-4 text-primary" />
              </div>
              <div>
                <h2 className="text-white font-medium">AI Analyst</h2>
                <p className="text-xs text-slate-400">Powered by SIEM Core</p>
              </div>
            </div>
            <button 
              onClick={() => setChatMessages([{ role: 'ai', text: "Hi SOC Admin! I'm your AI SOC Analyst. How can I help you today?" }])}
              className="text-xs text-slate-500 hover:text-white transition-colors"
            >
              Clear Chat
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar bg-slate-900/30">
            <AnimatePresence>
              {chatMessages.map((msg, i) => (
                <motion.div 
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  key={i} 
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-md ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white rounded-tr-sm' 
                      : 'bg-slate-800 text-slate-200 rounded-tl-sm border border-slate-700'
                  }`}>
                    {/* Basic markdown simulation by splitting newlines */}
                    {String(msg.text).split('\n').map((line, j) => (
                      <span key={j}>{line}<br/></span>
                    ))}
                  </div>
                </motion.div>
              ))}
              {chatLoading && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                  <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-4 py-3 border border-slate-700 flex space-x-2 items-center">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-75"></div>
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-150"></div>
                  </div>
                </motion.div>
              )}
              <div ref={chatEndRef} />
            </AnimatePresence>
          </div>

          <div className="p-4 border-t border-slate-700/60 bg-slate-800/50">
            <form onSubmit={handleChatSubmit} className="relative">
              <input 
                type="text" 
                placeholder="Ask AI to summarize alerts..." 
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                className="w-full bg-slate-900 border border-slate-600 rounded-full pl-4 pr-12 py-3 text-sm text-white focus:outline-none focus:border-blue-500 transition-colors shadow-inner"
              />
              <button 
                type="submit" 
                disabled={!chatInput.trim() || chatLoading}
                className="absolute right-2 top-2 p-1.5 bg-blue-600 hover:bg-blue-500 rounded-full text-white disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
              >
                <Send className="w-4 h-4 ml-0.5" />
              </button>
            </form>
          </div>
        </div>

      </div>
    </div>
  );
}
