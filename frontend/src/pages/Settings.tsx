import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useAuthStore } from '../store/authStore';
import { Save, BrainCircuit, Database } from 'lucide-react';

export default function Settings() {
  const { serverUrl } = useAuthStore();
  const [aiContextSize, setAiContextSize] = useState(10);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const { data } = await api.get('/api/v1/system/settings');
      if (data.ai_context_size) {
        setAiContextSize(data.ai_context_size);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put('/api/v1/system/settings/ai_context_size', { value: aiContextSize });
      alert("Settings saved successfully");
    } catch (err) {
      console.error(err);
      alert("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <h1 className="text-2xl font-bold text-white">System Settings</h1>

      <div className="bg-surface rounded-lg border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700 flex items-center">
          <Database className="w-5 h-5 text-primary mr-3" />
          <h2 className="text-lg font-medium text-white">Connection Settings</h2>
        </div>
        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">Backend Server URL</label>
            <input
              type="text"
              value={serverUrl}
              disabled
              className="w-full bg-slate-900 border border-slate-700 rounded-md py-2 px-4 text-slate-500 cursor-not-allowed"
            />
            <p className="text-xs text-slate-500 mt-1">To change this, log out and configure from the login screen.</p>
          </div>
        </div>
      </div>

      <div className="bg-surface rounded-lg border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700 flex items-center">
          <BrainCircuit className="w-5 h-5 text-primary mr-3" />
          <h2 className="text-lg font-medium text-white">AI Engine Tuning</h2>
        </div>
        <div className="p-6 space-y-4">
          {loading ? (
            <p className="text-slate-400">Loading settings...</p>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Context Analysis Depth (Number of past alerts)</label>
                <p className="text-xs text-slate-400 mb-3">
                  Determines how many historical alerts the AI should review to find correlations when analyzing a new alert.
                </p>
                <div className="flex items-center">
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={aiContextSize}
                    onChange={(e) => setAiContextSize(parseInt(e.target.value))}
                    className="flex-1 mr-4 accent-primary"
                  />
                  <span className="text-white font-mono bg-slate-900 px-3 py-1 rounded border border-slate-700">
                    {aiContextSize} alerts
                  </span>
                </div>
              </div>

              <div className="pt-4">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center px-4 py-2 bg-primary hover:bg-blue-600 text-white rounded-md transition-colors"
                >
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Settings'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="bg-surface rounded-lg border border-slate-700 overflow-hidden">
        <div className="p-6 border-b border-slate-700 flex items-center">
          <BrainCircuit className="w-5 h-5 text-purple-400 mr-3" />
          <h2 className="text-lg font-medium text-white">AI Provider Configuration</h2>
        </div>
        <div className="p-6">
           <AIProviderSettings />
        </div>
      </div>
    </div>
  );
}

function AIProviderSettings() {
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  
  const defaultForm = { name: 'Local Ollama', endpoint: 'http://127.0.0.1:11434', model: 'llama3', api_key: '', is_enabled: true, is_default: false };
  const [form, setForm] = useState(defaultForm);

  const fetchProviders = async () => {
    try {
      const { data } = await api.get('/api/v1/system/ai-providers');
      setProviders(data);
    } catch(e) {}
    setLoading(false);
  };

  useEffect(() => { fetchProviders(); }, []);

  const openAddForm = () => {
    setEditingId(null);
    setForm(defaultForm);
    setShowForm(true);
  };

  const applyTemplate = (type: string) => {
    if (type === 'gemini') {
      setForm({ ...form, name: 'Google Gemini', endpoint: 'https://generativelanguage.googleapis.com/v1beta/models', model: 'gemini-1.5-flash', api_key: '' });
    } else if (type === 'ollama') {
      setForm({ ...form, name: 'Local Ollama', endpoint: 'http://127.0.0.1:11434', model: 'llama3', api_key: '' });
    }
  };

  const openEditForm = (p: any) => {
    setEditingId(p.id);
    setForm({
      name: p.name,
      endpoint: p.endpoint,
      model: p.model,
      api_key: '', // Do not load the old key, leave empty means keep old
      is_enabled: p.is_enabled,
      is_default: p.is_default
    });
    setShowForm(true);
  };

  const saveProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.put(`/api/v1/system/ai-providers/${editingId}`, form);
      } else {
        await api.post('/api/v1/system/ai-providers', form);
      }
      setShowForm(false);
      fetchProviders();
    } catch (err) {
      alert('Failed to save provider');
    }
  };

  const deleteProvider = async (id: string) => {
    if (!confirm('Are you sure you want to delete this AI Provider?')) return;
    try {
      await api.delete(`/api/v1/system/ai-providers/${id}`);
      fetchProviders();
    } catch (err) {
      alert('Failed to delete provider');
    }
  };

  const setAsDefault = async (p: any) => {
    try {
      await api.put(`/api/v1/system/ai-providers/${p.id}`, {
        ...p,
        is_default: true,
        api_key: '' // Preserve existing
      });
      fetchProviders();
    } catch (err) {}
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h3 className="text-white font-medium">Configured Integrations</h3>
        <button onClick={openAddForm} className="bg-primary hover:bg-blue-600 text-white px-3 py-1.5 rounded text-sm transition-colors shadow">
          + Add New AI
        </button>
      </div>

      {showForm && (
        <form onSubmit={saveProvider} className="space-y-4 border border-blue-900/50 p-5 rounded-lg bg-slate-900/80 shadow-lg relative">
          <button type="button" onClick={() => setShowForm(false)} className="absolute top-4 right-4 text-slate-400 hover:text-white">✕</button>
          <div className="flex justify-between items-center mb-4">
             <h3 className="text-white font-medium">{editingId ? 'Edit AI Provider' : 'Add New AI Provider'}</h3>
             {!editingId && (
               <div className="flex space-x-2 text-xs">
                 <button type="button" onClick={() => applyTemplate('gemini')} className="bg-blue-900/40 text-blue-300 hover:bg-blue-800/50 px-2 py-1 rounded border border-blue-800">Use Gemini Template</button>
                 <button type="button" onClick={() => applyTemplate('ollama')} className="bg-slate-800 text-slate-300 hover:bg-slate-700 px-2 py-1 rounded border border-slate-700">Use Ollama Template</button>
               </div>
             )}
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-slate-400 mb-1">Provider Type / Name</label>
              <input type="text" placeholder="e.g. Google Gemini" value={form.name} onChange={e => setForm({...form, name: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" required />
            </div>
            <div>
              <label className="block text-sm text-slate-400 mb-1">Model ID</label>
              <input type="text" placeholder="e.g. gemini-flash-latest" value={form.model} onChange={e => setForm({...form, model: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" required />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-slate-400 mb-1">Endpoint URL</label>
              <input type="text" placeholder="https://generativelanguage.googleapis.com/v1beta/models" value={form.endpoint} onChange={e => setForm({...form, endpoint: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white font-mono text-sm" required />
            </div>
            <div className="col-span-2">
              <label className="block text-sm text-slate-400 mb-1">API Key {editingId && '(Leave blank to keep existing)'}</label>
              <input type="password" placeholder="Required for Gemini, leave blank for Ollama" value={form.api_key} onChange={e => setForm({...form, api_key: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
            </div>
            <div className="col-span-2 flex items-center space-x-6">
              <label className="flex items-center space-x-2 text-slate-300">
                <input type="checkbox" checked={form.is_enabled} onChange={e => setForm({...form, is_enabled: e.target.checked})} className="rounded bg-slate-900 border-slate-700 text-primary" />
                <span>Enabled</span>
              </label>
              <label className="flex items-center space-x-2 text-slate-300">
                <input type="checkbox" checked={form.is_default} onChange={e => setForm({...form, is_default: e.target.checked})} className="rounded bg-slate-900 border-slate-700 text-primary" />
                <span>Set as Default AI</span>
              </label>
            </div>
          </div>
          <div className="pt-2 flex justify-end space-x-3">
             <button type="button" onClick={() => setShowForm(false)} className="px-4 py-2 rounded text-slate-400 hover:text-white">Cancel</button>
             <button type="submit" className="bg-success hover:bg-green-600 text-white px-5 py-2 rounded transition-colors font-medium">Save Provider</button>
          </div>
        </form>
      )}

      <div>
        {loading ? <div className="p-8 text-center text-slate-500">Loading AI config...</div> : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {providers.map(p => (
              <div key={p.id} className={`p-4 rounded-xl border flex flex-col justify-between ${p.is_default ? 'bg-blue-900/10 border-blue-500/50 shadow-[0_0_15px_rgba(59,130,246,0.1)]' : 'bg-slate-900 border-slate-700'}`}>
                <div>
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="text-white font-bold text-lg">{p.name}</h4>
                    {p.is_default ? (
                      <span className="px-2.5 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-bold uppercase tracking-wider rounded border border-blue-500/30">Active</span>
                    ) : !p.is_enabled ? (
                      <span className="px-2.5 py-0.5 bg-slate-700/50 text-slate-400 text-[10px] font-bold uppercase tracking-wider rounded border border-slate-600">Disabled</span>
                    ) : null}
                  </div>
                  <div className="space-y-1 mb-4">
                    <p className="text-xs text-slate-400"><span className="text-slate-500 w-16 inline-block">Model:</span> <span className="font-mono text-slate-300">{p.model}</span></p>
                    <p className="text-xs text-slate-400"><span className="text-slate-500 w-16 inline-block">Endpoint:</span> <span className="font-mono text-slate-300">{p.endpoint}</span></p>
                    <p className="text-xs text-slate-400"><span className="text-slate-500 w-16 inline-block">Auth:</span> {p.has_api_key ? 'API Key Set' : 'None'}</p>
                  </div>
                </div>
                <div className="flex justify-between items-center pt-3 border-t border-slate-800">
                  <div className="space-x-2">
                    <button onClick={() => openEditForm(p)} className="text-xs text-slate-400 hover:text-blue-400 px-2 py-1 bg-slate-950 rounded transition-colors">Edit</button>
                    <button onClick={() => deleteProvider(p.id)} className="text-xs text-slate-400 hover:text-red-400 px-2 py-1 bg-slate-950 rounded transition-colors">Delete</button>
                  </div>
                  {!p.is_default && p.is_enabled && (
                    <button onClick={() => setAsDefault(p)} className="text-xs font-medium text-blue-400 hover:text-white px-3 py-1 bg-blue-900/20 rounded border border-blue-900/50 transition-colors">
                      Set Default
                    </button>
                  )}
                </div>
              </div>
            ))}
            {providers.length === 0 && <div className="col-span-2 p-8 text-center text-slate-500 border border-dashed border-slate-700 rounded-lg">No AI providers configured. Add one to enable analysis.</div>}
          </div>
        )}
      </div>
    </div>
  );
}
