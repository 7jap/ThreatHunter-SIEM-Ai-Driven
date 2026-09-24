import { useEffect, useState, useRef } from 'react';
import { api } from '../lib/api';
import { Search, Filter, MessageSquareText, ShieldAlert, X, Terminal, Send, Activity, Download } from 'lucide-react';
import { format } from 'date-fns';
import { useAuthStore } from '../store/authStore';
import { motion, AnimatePresence } from 'framer-motion';
import { jsPDF } from 'jspdf';

export default function Alerts() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filtering state
  const [searchTerm, setSearchTerm] = useState('');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  // Details Panel State
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [alertDetails, setAlertDetails] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<'details' | 'chat'>('details');
  
  // Chat State
  const [chatMessages, setChatMessages] = useState<{role: 'ai' | 'user', text: string}[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  
  const { serverUrl } = useAuthStore();

  useEffect(() => {
    fetchAlerts();
    
    // Connect to WebSocket for live updates with auto-reconnect
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
              setAlerts(prev => {
                if (prev.some(a => a.id === msg.data.id)) return prev;
                return [msg.data, ...prev];
              });
            } else if (msg.event === 'alert.ai_completed') {
              setAlerts(prev => prev.map(a => 
                a.id === msg.data.alert_id 
                  ? { ...a, status: 'ANALYZED', ai_verdict: msg.data.verdict, ai_confidence: msg.data.confidence } 
                  : a
              ));
              if (selectedAlertId === msg.data.alert_id) {
                 fetchAlertDetails(msg.data.alert_id);
              }
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

    // Background polling fallback every 3 seconds
    const pollInterval = setInterval(() => {
      fetchAlerts(true);
    }, 3000);
    
    return () => {
      isUnmounted = true;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      clearInterval(pollInterval);
      if (ws) {
        ws.onclose = null;
        ws.close();
      }
    };
  }, [serverUrl, selectedAlertId]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(() => { fetchAlerts(); }, 300);
    return () => clearTimeout(delayDebounceFn);
  }, [searchTerm, filterSeverity, filterStatus]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const fetchAlerts = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      let url = '/api/v1/alerts?limit=100';
      if (searchTerm) url += `&search=${encodeURIComponent(searchTerm)}`;
      if (filterSeverity !== 'all') url += `&severity=${filterSeverity}`;
      if (filterStatus !== 'all') url += `&status=${filterStatus}`;
      
      const { data } = await api.get(url);
      setAlerts(data);
    } catch (err) {
      console.error(err);
    } finally {
      if (!silent) setLoading(false);
    }
  };

  const fetchAlertDetails = async (id: string) => {
    try {
      const { data } = await api.get(`/api/v1/alerts/${id}`);
      setAlertDetails(data);
    } catch (err) {
      console.error(err);
    }
  };

  // Save to localStorage when chatMessages change for the selected alert
  useEffect(() => {
    if (selectedAlertId && chatMessages.length > 0) {
      localStorage.setItem(`alert_chat_${selectedAlertId}`, JSON.stringify(chatMessages));
    }
  }, [chatMessages, selectedAlertId]);

  const viewAlertDetails = (id: string) => {
    setSelectedAlertId(id);
    setAlertDetails(null);
    setActiveTab('details');
    
    // Load history or set default
    const saved = localStorage.getItem(`alert_chat_${id}`);
    if (saved) {
      try {
        setChatMessages(JSON.parse(saved));
      } catch (e) {
        setChatMessages([{ role: 'ai', text: `I am ready to help you investigate alert ${id}. What would you like to know?` }]);
      }
    } else {
      setChatMessages([{ role: 'ai', text: `I am ready to help you investigate alert ${id}. What would you like to know?` }]);
    }
    
    fetchAlertDetails(id);
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || !selectedAlertId) return;
    
    const userMsg = chatInput;
    setChatMessages(prev => [...prev, { role: 'user', text: userMsg }]);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await api.post(`/api/v1/chat/alert/${selectedAlertId}`, { 
        message: userMsg,
        history: chatMessages.slice(-5)
      });
      setChatMessages(prev => [...prev, { role: 'ai', text: res.data.response }]);
    } catch (err: any) {
      const errMsg = err.response?.data?.detail || err.message || 'Error: Could not reach AI service.';
      setChatMessages(prev => [...prev, { role: 'ai', text: String(errMsg) }]);
    } finally {
      setChatLoading(false);
    }
  };

  const getSeverityColor = (sev: number) => {
    if (sev === 1) return 'text-red-500 bg-red-500/10 border-red-500/30';
    if (sev === 2) return 'text-orange-400 bg-orange-400/10 border-orange-400/30';
    return 'text-blue-400 bg-blue-400/10 border-blue-400/30';
  };

  const generatePDF = () => {
    if (!alertDetails) return;
    
    const doc = new jsPDF();
    const user = useAuthStore.getState().user;
    
    // Header
    doc.setFontSize(22);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(30, 58, 138); // Dark blue
    doc.text('ThreatHunter SIEM — Security Operations Center', 20, 25);
    
    doc.setLineWidth(0.5);
    doc.setDrawColor(200, 200, 200);
    doc.line(20, 32, 190, 32);

    doc.setFontSize(16);
    doc.setTextColor(40, 40, 40);
    doc.text('INCIDENT REPORT', 20, 45);
    
    // Details
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 0, 0);
    const refId = alertDetails.id ? alertDetails.id.toString().substring(0, 8) : '001';
    doc.text(`REF: SOC-${new Date().getFullYear()}${String(new Date().getMonth()+1).padStart(2, '0')}${String(new Date().getDate()).padStart(2, '0')}-${refId}`, 20, 55);
    
    const isCritical = alertDetails.severity === 1;
    doc.setTextColor(isCritical ? 220 : (alertDetails.severity === 2 ? 220 : 50), isCritical ? 38 : 100, isCritical ? 38 : 0);
    doc.text(isCritical ? 'SEVERITY: CRITICAL' : (alertDetails.severity === 2 ? 'SEVERITY: MEDIUM' : 'SEVERITY: LOW'), 20, 65);
    
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(100, 100, 100);
    const incidentTime = alertDetails.timestamp ? format(new Date(alertDetails.timestamp), "dd MMMM yyyy — HH:mm:ss 'UTC'") : 'Unknown';
    doc.text(`Incident Time: ${incidentTime}`, 20, 73);
    
    // Table/Grid section
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(30, 58, 138);
    doc.text('Report Details', 20, 90);
    doc.line(20, 93, 190, 93);
    
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(100, 100, 100);
    doc.text('Report Generated On', 20, 102);
    doc.text('Alert Status', 70, 102);
    doc.text('Analyst on Shift', 120, 102);
    
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(0, 0, 0);
    doc.text(format(new Date(), 'dd MMMM yyyy HH:mm:ss'), 20, 108);
    doc.text(alertDetails.status === 'NEW' ? 'Open — Awaiting Analysis' : 'Closed — Analyzed', 70, 108);
    
    // Use user details
    const analystName = user?.display_name || user?.username || 'System Analyst';
    const analystRole = user?.role_name || 'SOC Analyst';
    doc.text(`${analystRole}, ${analystName}`, 120, 108);
    
    // Network Details Table
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(100, 100, 100);
    doc.text('Source IP', 20, 120);
    doc.text('Destination IP', 70, 120);
    doc.text('Protocol', 120, 120);

    doc.setFont('helvetica', 'normal');
    doc.setTextColor(0, 0, 0);
    doc.text(`${alertDetails.source_ip}:${alertDetails.source_port || 'N/A'}`, 20, 126);
    doc.text(`${alertDetails.destination_ip}:${alertDetails.destination_port || 'N/A'}`, 70, 126);
    doc.text(`${alertDetails.protocol || 'TCP'}`, 120, 126);
    
    // Incident Narrative
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(30, 58, 138);
    doc.text('Incident Narrative', 20, 145);
    doc.line(20, 148, 190, 148);
    
    doc.setFontSize(11);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(40, 40, 40);
    
    let narrativeText = `At ${incidentTime}, the ThreatHunter SIEM automated security monitoring systems detected malicious activity matching the signature:\n"${alertDetails.signature}".\n\n`;
    narrativeText += `The attack originated from external IP address ${alertDetails.source_ip} targeting internal asset ${alertDetails.destination_ip} over ${alertDetails.protocol}.\n\n`;
    
    if (alertDetails.ai_verdict) {
      narrativeText += `--- AI Analyst Verdict ---\nVerdict: ${alertDetails.ai_verdict} (Confidence: ${alertDetails.ai_confidence ? Math.round(alertDetails.ai_confidence) + '%' : 'N/A'})\n\n`;
      if (alertDetails.ai_explanation) {
        narrativeText += `Explanation:\n${alertDetails.ai_explanation}\n\n`;
      }
    } else {
       narrativeText += `--- AI Analyst Verdict ---\nPending manual or automated analysis.\n\n`;
    }
    
    const splitNarrative = doc.splitTextToSize(narrativeText, 170);
    doc.text(splitNarrative, 20, 158);
    
    // Signature
    const finalY = 158 + (splitNarrative.length * 5) + 20;
    doc.line(20, finalY - 5, 80, finalY - 5);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'italic');
    doc.setTextColor(100, 100, 100);
    doc.text(`Electronically Signed By: ${analystName}`, 20, finalY);
    doc.text(`Role: ${analystRole}`, 20, finalY + 5);
    doc.text(`Timestamp: ${format(new Date(), 'yyyy-MM-dd HH:mm:ss')}`, 20, finalY + 10);
    
    doc.save(`ThreatHunter_Incident_Report_${refId}.pdf`);
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center">
             <Activity className="w-6 h-6 mr-2 text-blue-500" />
             Threat Hunter
          </h1>
          <p className="text-slate-400 mt-1 text-sm">Real-time enterprise threat monitoring feed</p>
        </div>
        
        <div className="flex items-center space-x-3 bg-slate-900 p-2 rounded border border-slate-800 shadow-inner w-full md:w-auto">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search signatures, IPs..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-700 rounded text-sm text-slate-200 focus:outline-none focus:border-blue-500 w-64 placeholder-slate-600 transition-colors"
            />
          </div>
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-500" />
            <select 
              value={filterSeverity} 
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-blue-500"
            >
              <option value="all">Severity: All</option>
              <option value="1">High</option>
              <option value="2">Medium</option>
              <option value="3">Low</option>
            </select>
            <select 
              value={filterStatus} 
              onChange={(e) => setFilterStatus(e.target.value)}
              className="bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-blue-500"
            >
              <option value="all">Status: All</option>
              <option value="NEW">New</option>
              <option value="ANALYZED">Analyzed</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </div>
        </div>
      </div>

        {/* Modern Log Data Grid */}
      <div className="flex-1 bg-[#0d1117] border border-slate-700/60 rounded shadow-xl overflow-hidden flex flex-col font-mono">
        {/* Grid Header */}
        <div className="grid grid-cols-12 gap-3 p-3 border-b border-slate-700/60 bg-[#161b22] text-[11px] font-bold text-slate-400 uppercase tracking-widest sticky top-0 z-10">
          <div className="col-span-2">Time</div>
          <div className="col-span-1">Sev</div>
          <div className="col-span-4">Detection Rule</div>
          <div className="col-span-2">Source</div>
          <div className="col-span-2">Destination</div>
          <div className="col-span-1 text-center">AI</div>
        </div>
        
        {/* Grid Body */}
        <div className="flex-1 overflow-y-auto custom-scrollbar">
          {loading && alerts.length === 0 ? (
            <div className="flex justify-center items-center h-48 space-x-3 text-slate-500 font-sans">
               <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
               <span>Loading telemetry...</span>
            </div>
          ) : alerts.length === 0 ? (
            <div className="flex justify-center items-center h-48 text-slate-500 font-sans font-medium">No alerts detected in current filter scope.</div>
          ) : (
            <AnimatePresence>
              {alerts.map((alert) => (
                <motion.div 
                  key={alert.id}
                  initial={{ opacity: 0, backgroundColor: 'rgba(59, 130, 246, 0.1)' }}
                  animate={{ opacity: 1, backgroundColor: 'transparent' }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.5 }}
                  className="grid grid-cols-12 gap-3 px-3 py-2 border-b border-slate-800/60 hover:bg-[#1f2937] cursor-pointer items-center text-[13px] transition-colors group"
                  onClick={() => viewAlertDetails(alert.id)}
                >
                  <div className="col-span-2 text-slate-400 text-xs">
                    {alert.timestamp ? format(new Date(alert.timestamp), 'MM/dd HH:mm:ss') : '-'}
                  </div>
                  
                  <div className="col-span-1 flex items-center">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-sans ${
                      alert.severity === 1 ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 
                      alert.severity === 2 ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30' : 
                      'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    }`}>
                      {alert.severity === 1 ? 'HIGH' : alert.severity === 2 ? 'MED' : 'LOW'}
                    </span>
                  </div>
                  
                  <div className="col-span-4 font-semibold text-slate-200 truncate group-hover:text-blue-400 transition-colors font-sans" title={alert.signature}>
                    {alert.signature}
                  </div>
                  
                  <div className="col-span-2 text-slate-400 truncate">
                    {alert.source_ip}
                  </div>
                  
                  <div className="col-span-2 text-slate-400 truncate">
                    {alert.destination_ip}
                  </div>
                  
                  <div className="col-span-1 flex justify-center items-center">
                    {alert.ai_verdict ? (
                      <div className={`w-2 h-2 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.8)] ${
                        alert.ai_verdict === 'MALICIOUS' ? 'bg-red-500 shadow-red-500' : 
                        alert.ai_verdict === 'BENIGN' ? 'bg-green-500 shadow-green-500' : 
                        'bg-orange-500 shadow-orange-500'
                      }`} title={`${alert.ai_verdict} (${Math.round(alert.ai_confidence || 0)}%)`}></div>
                    ) : (
                      <div className="w-2 h-2 rounded-full bg-slate-600 animate-pulse" title="Analyzing..."></div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
        </div>
      </div>

      {/* Sliding Side Panel */}
      <AnimatePresence>
        {selectedAlertId && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40"
              onClick={() => setSelectedAlertId(null)}
            />
            <motion.div 
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 right-0 w-full max-w-3xl bg-slate-900 border-l border-slate-700 shadow-2xl z-50 flex flex-col"
            >
              {/* Header */}
              <div className="flex justify-between items-center px-6 py-4 border-b border-slate-800 bg-slate-950">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center">
                    <ShieldAlert className="w-5 h-5 mr-2 text-blue-500" />
                    Alert Details
                  </h2>
                  <p className="text-xs text-slate-500 font-mono mt-1">{selectedAlertId}</p>
                </div>
                <div className="flex items-center space-x-3">
                  <button 
                    onClick={generatePDF} 
                    className="flex items-center text-xs bg-blue-600/20 hover:bg-blue-600/40 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded transition-colors shadow"
                  >
                    <Download className="w-4 h-4 mr-1.5" />
                    Export PDF
                  </button>
                  <button onClick={() => setSelectedAlertId(null)} className="text-slate-400 hover:text-white transition-colors bg-slate-800 hover:bg-slate-700 p-2 rounded-full">
                    <X className="w-5 h-5" />
                  </button>
                </div>
              </div>
              
              {/* Tabs */}
              <div className="flex border-b border-slate-800 bg-slate-900 items-center">
                <button 
                  onClick={() => setActiveTab('details')}
                  className={`flex-1 py-3 text-sm font-medium transition-colors ${activeTab === 'details' ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-900/10' : 'text-slate-400 hover:text-slate-200'}`}
                >
                  Investigation Data
                </button>
                <div className={`flex-1 flex justify-center items-center py-3 text-sm font-medium transition-colors relative ${activeTab === 'chat' ? 'text-blue-400 border-b-2 border-blue-400 bg-blue-900/10' : 'text-slate-400'}`}>
                  <button 
                    onClick={() => setActiveTab('chat')}
                    className="flex items-center w-full justify-center"
                  >
                    <MessageSquareText className="w-4 h-4 mr-2" /> AI Assistant
                  </button>
                  {activeTab === 'chat' && (
                    <button 
                      onClick={() => {
                        localStorage.removeItem(`alert_chat_${selectedAlertId}`);
                        setChatMessages([{ role: 'ai', text: `I am ready to help you investigate alert ${selectedAlertId}. What would you like to know?` }]);
                      }}
                      className="absolute right-4 text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2 py-1 rounded"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-6 bg-slate-900">
                {loading || !alertDetails ? (
                  <div className="flex flex-col items-center justify-center h-full space-y-4">
                    <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                    <p className="text-slate-500">Loading contextual data...</p>
                  </div>
                ) : activeTab === 'details' ? (
                  <div className="space-y-8">
                    {/* Basic Info */}
                    <div>
                      <h3 className="text-xl font-bold text-white mb-4">{alertDetails.signature}</h3>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                           <p className="text-xs text-slate-500 font-semibold mb-1">STATUS</p>
                           <p className="text-sm text-slate-200 uppercase">{alertDetails.status}</p>
                        </div>
                        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                           <p className="text-xs text-slate-500 font-semibold mb-1">SEVERITY</p>
                           <p className="text-sm font-bold"><span className={getSeverityColor(alertDetails.severity).split(' ')[0]}>{alertDetails.severity}</span></p>
                        </div>
                        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                           <p className="text-xs text-slate-500 font-semibold mb-1">PROTOCOL</p>
                           <p className="text-sm text-slate-200">{alertDetails.protocol}</p>
                        </div>
                        <div className="bg-slate-950 border border-slate-800 p-4 rounded-lg">
                           <p className="text-xs text-slate-500 font-semibold mb-1">TIMESTAMP</p>
                           <p className="text-xs font-mono text-slate-300 mt-1">{format(new Date(alertDetails.timestamp), 'HH:mm:ss')}</p>
                        </div>
                      </div>
                    </div>

                    {/* IPs */}
                    <div className="flex flex-col md:flex-row gap-4">
                      <div className="flex-1 bg-slate-950 border border-slate-800 p-4 rounded-lg relative overflow-hidden">
                        <div className="absolute top-0 left-0 w-1 h-full bg-blue-500"></div>
                        <p className="text-xs text-slate-500 font-semibold mb-2">SOURCE</p>
                        <p className="font-mono text-lg text-slate-200">{alertDetails.source_ip}</p>
                        <p className="text-xs text-slate-500 mt-1">Port: {alertDetails.source_port}</p>
                      </div>
                      <div className="flex-1 bg-slate-950 border border-slate-800 p-4 rounded-lg relative overflow-hidden">
                         <div className="absolute top-0 left-0 w-1 h-full bg-red-500"></div>
                        <p className="text-xs text-slate-500 font-semibold mb-2">DESTINATION</p>
                        <p className="font-mono text-lg text-slate-200">{alertDetails.destination_ip}</p>
                        <p className="text-xs text-slate-500 mt-1">Port: {alertDetails.destination_port}</p>
                      </div>
                    </div>
                    
                    {/* AI Analysis */}
                    {alertDetails.ai_analysis && (
                      <div className="bg-blue-950/20 border border-blue-900/50 rounded-lg p-5">
                         <h4 className="text-sm font-bold text-blue-400 mb-4 flex items-center"><Terminal className="w-4 h-4 mr-2"/> Automated Analysis</h4>
                         <div className="space-y-4">
                            <div>
                              <span className="text-xs text-slate-500 block mb-1">VERDICT</span>
                              <span className={`text-sm font-bold px-2 py-1 rounded bg-slate-900 border ${
                                alertDetails.ai_analysis.verdict === 'MALICIOUS' ? 'text-red-500 border-red-500/30' :
                                alertDetails.ai_analysis.verdict === 'BENIGN' ? 'text-green-500 border-green-500/30' : 'text-orange-500 border-orange-500/30'
                              }`}>
                                {alertDetails.ai_analysis.verdict} ({alertDetails.ai_analysis.confidence}%)
                              </span>
                            </div>
                            <div>
                              <span className="text-xs text-slate-500 block mb-1">EXPLANATION</span>
                              <p className="text-sm text-slate-300 leading-relaxed bg-slate-950 p-4 rounded-lg border border-slate-800/50">
                                {alertDetails.ai_analysis.explanation}
                              </p>
                            </div>
                            {alertDetails.ai_analysis.recommended_actions && (
                              <div>
                                <span className="text-xs text-slate-500 block mb-2">RECOMMENDED ACTIONS</span>
                                <div className="space-y-2">
                                  {alertDetails.ai_analysis.recommended_actions.map((act: string, i: number) => (
                                    <div key={i} className="flex items-start text-sm text-slate-300 bg-slate-950 px-3 py-2 rounded border border-slate-800/50">
                                      <span className="text-blue-500 mr-2">•</span> {act}
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                         </div>
                      </div>
                    )}

                    {/* Raw Payload */}
                    <div>
                      <h4 className="text-sm font-bold text-slate-400 mb-2">Raw Payload</h4>
                      <div className="bg-[#0d1117] border border-slate-800 rounded-lg p-4 overflow-x-auto">
                        <pre className="text-[11px] font-mono text-emerald-400/90 whitespace-pre-wrap">
                          {JSON.stringify(alertDetails.raw_payload, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col h-full">
                    {/* Chat Messages */}
                    <div className="flex-1 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
                      <AnimatePresence>
                        {chatMessages.map((msg, i) => (
                          <motion.div 
                            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                            key={i} 
                            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                          >
                            <div className={`max-w-[85%] rounded-2xl px-5 py-3 text-sm ${
                              msg.role === 'user' 
                                ? 'bg-blue-600 text-white rounded-tr-sm shadow-lg shadow-blue-900/20' 
                                : 'bg-slate-800 text-slate-200 rounded-tl-sm border border-slate-700 shadow-md'
                            }`}>
                              {String(msg.text).split('\n').map((line, j) => (
                                <span key={j}>{line}<br/></span>
                              ))}
                            </div>
                          </motion.div>
                        ))}
                        {chatLoading && (
                          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex justify-start">
                            <div className="bg-slate-800 rounded-2xl rounded-tl-sm px-5 py-4 border border-slate-700 flex space-x-2 items-center">
                              <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce"></div>
                              <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-75"></div>
                              <div className="w-2 h-2 bg-slate-500 rounded-full animate-bounce delay-150"></div>
                            </div>
                          </motion.div>
                        )}
                        <div ref={chatEndRef} />
                      </AnimatePresence>
                    </div>

                    {/* Chat Input */}
                    <div className="pt-4 mt-4 border-t border-slate-800">
                      <form onSubmit={handleChatSubmit} className="relative">
                        <input 
                          type="text" 
                          placeholder="Ask AI about this specific alert..." 
                          value={chatInput}
                          onChange={e => setChatInput(e.target.value)}
                          className="w-full bg-slate-950 border border-slate-700 rounded-full pl-5 pr-12 py-3 text-sm text-white focus:outline-none focus:border-blue-500 shadow-inner"
                        />
                        <button 
                          type="submit" 
                          disabled={!chatInput.trim() || chatLoading}
                          className="absolute right-2 top-2 p-2 bg-blue-600 hover:bg-blue-500 rounded-full text-white disabled:opacity-50 transition-colors"
                        >
                          <Send className="w-4 h-4 ml-0.5" />
                        </button>
                      </form>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
