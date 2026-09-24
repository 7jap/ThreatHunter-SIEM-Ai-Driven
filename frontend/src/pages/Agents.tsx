import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Server, Edit, Trash2, Check, X, ShieldAlert } from 'lucide-react';
import { format } from 'date-fns';

interface Agent {
  id: string;
  hostname: string;
  ip_address: string | null;
  status: string;
  last_heartbeat: string | null;
  created_at: string;
}

export default function Agents() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [editHostname, setEditHostname] = useState('');
  const [editStatus, setEditStatus] = useState('');

  const [deletingAgent, setDeletingAgent] = useState<Agent | null>(null);

  const fetchAgents = async () => {
    try {
      const res = await api.get('/api/v1/agent/list');
      setAgents(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
    const interval = setInterval(fetchAgents, 10000);
    return () => clearInterval(interval);
  }, []);

  const approveAgent = async (id: string) => {
    try {
      await api.put(`/api/v1/agent/${id}/approve`);
      fetchAgents();
    } catch (err) {
      console.error(err);
    }
  };

  const handleEditSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingAgent) return;
    try {
      await api.put(`/api/v1/agent/${editingAgent.id}`, {
        hostname: editHostname,
        status: editStatus,
      });
      setEditingAgent(null);
      fetchAgents();
    } catch (err) {
      console.error(err);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingAgent) return;
    try {
      await api.delete(`/api/v1/agent/${deletingAgent.id}`);
      setDeletingAgent(null);
      fetchAgents();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-3 mb-8">
        <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
          <Server className="w-6 h-6 text-blue-500" />
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Connected Agents</h1>
          <p className="text-slate-400 mt-1">Manage and monitor your endpoints.</p>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-xl overflow-hidden relative z-0">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-800">
            <thead className="bg-slate-950/50">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Hostname</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Agent ID</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">IP Address</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Last Heartbeat</th>
                <th className="px-6 py-4 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 bg-slate-900/50">
              {loading && agents.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-400">Loading...</td></tr>
              ) : agents.length === 0 ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-400">No agents found</td></tr>
              ) : (
                agents.map(agent => (
                  <tr key={agent.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap font-medium text-slate-200">
                      {agent.hostname}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400 font-mono text-sm">
                      {agent.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400 font-mono text-sm">
                      {agent.ip_address || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${
                        agent.status === 'ACTIVE' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 
                        agent.status === 'PENDING' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 
                        'bg-red-500/10 text-red-400 border-red-500/20'
                      }`}>
                        {agent.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-slate-400 text-sm">
                      {agent.last_heartbeat ? format(new Date(agent.last_heartbeat), 'PPpp') : 'Never'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end space-x-3">
                        {agent.status === 'PENDING' && (
                          <button 
                            onClick={() => approveAgent(agent.id)} 
                            className="text-emerald-400 hover:text-emerald-300 transition-colors"
                            title="Approve"
                          >
                            <Check className="w-4 h-4" />
                          </button>
                        )}
                        <button 
                          onClick={() => {
                            setEditingAgent(agent);
                            setEditHostname(agent.hostname);
                            setEditStatus(agent.status);
                          }} 
                          className="text-blue-400 hover:text-blue-300 transition-colors"
                          title="Edit"
                        >
                          <Edit className="w-4 h-4" />
                        </button>
                        <button 
                          onClick={() => setDeletingAgent(agent)} 
                          className="text-red-400 hover:text-red-300 transition-colors"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Edit Modal */}
      {editingAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-md overflow-hidden">
            <div className="flex justify-between items-center p-4 border-b border-slate-700/60 bg-slate-800/30">
              <h3 className="text-lg font-medium text-white">Edit Agent</h3>
              <button onClick={() => setEditingAgent(null)} className="text-slate-400 hover:text-white transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleEditSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Hostname</label>
                <input
                  type="text"
                  value={editHostname}
                  onChange={(e) => setEditHostname(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Status</label>
                <select
                  value={editStatus}
                  onChange={(e) => setEditStatus(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-colors appearance-none"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="PENDING">PENDING</option>
                  <option value="INACTIVE">INACTIVE</option>
                  <option value="DISCONNECTED">DISCONNECTED</option>
                </select>
              </div>
              <div className="pt-4 flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={() => setEditingAgent(null)}
                  className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-500 rounded-lg transition-colors"
                >
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deletingAgent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-sm overflow-hidden">
            <div className="p-6">
              <div className="flex items-center justify-center w-12 h-12 rounded-full bg-red-500/10 mb-4 mx-auto">
                <ShieldAlert className="w-6 h-6 text-red-500" />
              </div>
              <h3 className="text-xl font-medium text-white text-center mb-2">Delete Agent?</h3>
              <p className="text-slate-400 text-center text-sm mb-6">
                Are you sure you want to delete <span className="font-semibold text-slate-200">{deletingAgent.hostname}</span>? This action cannot be undone.
              </p>
              <div className="flex justify-center space-x-3">
                <button
                  onClick={() => setDeletingAgent(null)}
                  className="flex-1 px-4 py-2 text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors border border-slate-700"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  className="flex-1 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
