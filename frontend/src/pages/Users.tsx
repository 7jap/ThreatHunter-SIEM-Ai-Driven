import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { Users, UserPlus, Edit, Trash2, X, ShieldAlert, CheckCircle, Shield } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function UsersPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  
  // Delete confirmation state
  const [userToDelete, setUserToDelete] = useState<any>(null);
  const [availableRoles, setAvailableRoles] = useState<any[]>([]);

  const [formData, setFormData] = useState({
    username: '',
    password: '',
    display_name: '',
    email: '',
    role_name: 'Admin',
    is_active: true
  });

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const res = await api.get('/api/v1/users/');
      setUsers(res.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const res = await api.get('/api/v1/users/roles');
      if (res.data && Array.isArray(res.data) && res.data.length > 0) {
        setAvailableRoles(res.data);
      }
    } catch (err) {
      console.warn("Could not load roles, using defaults", err);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchRoles();
  }, []);

  const openCreateModal = () => {
    setModalMode('create');
    const defaultRole = availableRoles.length > 0 ? availableRoles[0].name : 'Admin';
    setFormData({ username: '', password: '', display_name: '', email: '', role_name: defaultRole, is_active: true });
    setIsModalOpen(true);
  };

  const openEditModal = (user: any) => {
    setModalMode('edit');
    const currentRole = user.roles && user.roles.length > 0 ? user.roles[0] : (availableRoles[0]?.name || 'Admin');
    setFormData({ 
      username: user.username, 
      password: '', 
      display_name: user.display_name, 
      email: user.email || '', 
      role_name: currentRole,
      is_active: user.is_active 
    });
    setSelectedUserId(user.id);
    setIsModalOpen(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (modalMode === 'create') {
        await api.post('/api/v1/users/', {
          username: formData.username,
          password: formData.password,
          display_name: formData.display_name,
          email: formData.email,
          role_name: formData.role_name
        });
      } else {
        await api.put(`/api/v1/users/${selectedUserId}`, {
          display_name: formData.display_name,
          email: formData.email,
          role_name: formData.role_name,
          is_active: formData.is_active
        });
      }
      setIsModalOpen(false);
      fetchUsers();
    } catch (err: any) {
      console.error("Failed to save user", err);
      alert(err.response?.data?.detail || "Failed to save user. Check inputs.");
    }
  };

  const confirmDelete = async () => {
    if (!userToDelete) return;
    try {
      await api.delete(`/api/v1/users/${userToDelete.id}`);
      setUserToDelete(null);
      fetchUsers();
    } catch (err: any) {
      console.error("Failed to delete user", err);
      alert(err.response?.data?.detail || "Failed to delete user.");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-2">
            <Users className="w-8 h-8 text-blue-500" />
            Users Management
          </h1>
          <p className="text-slate-400 mt-1">Manage system accounts and roles.</p>
        </div>
        <button 
          onClick={openCreateModal}
          className="bg-blue-600 hover:bg-blue-500 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-500/20"
        >
          <UserPlus className="w-4 h-4" />
          Add User
        </button>
      </div>

      <div className="bg-surface rounded-xl border border-slate-700/60 overflow-hidden shadow-lg shadow-black/20">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-800/50 text-slate-400 border-b border-slate-700/60">
              <tr>
                <th className="px-6 py-4 font-medium">Username</th>
                <th className="px-6 py-4 font-medium">Display Name</th>
                <th className="px-6 py-4 font-medium">Email</th>
                <th className="px-6 py-4 font-medium">Role</th>
                <th className="px-6 py-4 font-medium">Status</th>
                <th className="px-6 py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {loading ? (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-500">Loading users...</td></tr>
              ) : users.map(u => (
                <tr key={u.id} className="hover:bg-slate-800/30 transition-colors">
                  <td className="px-6 py-4 font-medium text-slate-200">{u.username}</td>
                  <td className="px-6 py-4">{u.display_name}</td>
                  <td className="px-6 py-4">{u.email || <span className="text-slate-500 italic">No email</span>}</td>
                  <td className="px-6 py-4 capitalize">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-800 border border-slate-700 text-slate-300">
                      <Shield className="w-3 h-3 text-blue-400" />
                      {u.roles?.join(', ') || 'Admin'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                      u.is_active 
                        ? 'bg-success/10 text-success border border-success/20' 
                        : 'bg-slate-800 text-slate-400 border border-slate-700'
                    }`}>
                      {u.is_active ? <CheckCircle className="w-3 h-3" /> : <X className="w-3 h-3" />}
                      {u.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right space-x-2">
                    <button 
                      onClick={() => openEditModal(u)}
                      className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-400/10 rounded transition-colors"
                      title="Edit User"
                    >
                      <Edit className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => setUserToDelete(u)}
                      className="p-1.5 text-slate-400 hover:text-danger hover:bg-danger/10 rounded transition-colors"
                      title="Delete User"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
              {!loading && users.length === 0 && (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-slate-500">No users found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-surface border border-slate-700/60 rounded-xl shadow-2xl w-full max-w-md overflow-hidden"
            >
              <div className="flex justify-between items-center p-5 border-b border-slate-700/60 bg-slate-800/30">
                <h2 className="text-lg font-medium text-white flex items-center gap-2">
                  {modalMode === 'create' ? <UserPlus className="w-5 h-5 text-blue-500" /> : <Edit className="w-5 h-5 text-blue-500" />}
                  {modalMode === 'create' ? 'Create New User' : 'Edit User'}
                </h2>
                <button type="button" onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white transition-colors">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <form onSubmit={handleSubmit} className="p-5 space-y-4">
                
                {modalMode === 'create' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">Username</label>
                      <input 
                        type="text" required 
                        value={formData.username} 
                        onChange={e => setFormData({...formData, username: e.target.value})} 
                        className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors" 
                        placeholder="jdoe"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-slate-400 mb-1">Password</label>
                      <input 
                        type="password" required 
                        value={formData.password} 
                        onChange={e => setFormData({...formData, password: e.target.value})} 
                        className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors" 
                        placeholder="••••••••"
                      />
                    </div>
                  </>
                )}

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Display Name</label>
                  <input 
                    type="text" required 
                    value={formData.display_name} 
                    onChange={e => setFormData({...formData, display_name: e.target.value})} 
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors" 
                    placeholder="John Doe"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Email</label>
                  <input 
                    type="email" 
                    value={formData.email} 
                    onChange={e => setFormData({...formData, email: e.target.value})} 
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors" 
                    placeholder="john@example.com"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">Role</label>
                  <select 
                    value={formData.role_name} 
                    onChange={e => setFormData({...formData, role_name: e.target.value})} 
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 transition-colors"
                  >
                    {availableRoles.length > 0 ? (
                      availableRoles.map(r => (
                        <option key={r.id || r.name} value={r.name}>{r.name}</option>
                      ))
                    ) : (
                      <>
                        <option value="Admin">Admin</option>
                        <option value="SOC Analyst">SOC Analyst</option>
                      </>
                    )}
                  </select>
                </div>

                {modalMode === 'edit' && (
                  <div className="flex items-center mt-2">
                    <input
                      type="checkbox"
                      id="isActive"
                      checked={formData.is_active}
                      onChange={e => setFormData({...formData, is_active: e.target.checked})}
                      className="w-4 h-4 bg-slate-900 border-slate-700 rounded text-blue-600 focus:ring-blue-500 focus:ring-offset-slate-900"
                    />
                    <label htmlFor="isActive" className="ml-2 text-sm text-slate-300 cursor-pointer">
                      Account is active
                    </label>
                  </div>
                )}

                <div className="flex justify-end gap-3 pt-4 border-t border-slate-700/60 mt-6">
                  <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors">
                    Cancel
                  </button>
                  <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg shadow-lg shadow-blue-500/20 transition-colors">
                    {modalMode === 'create' ? 'Create User' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
        
        {userToDelete && (
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              className="bg-surface border border-danger/30 rounded-xl shadow-2xl w-full max-w-sm overflow-hidden"
            >
              <div className="p-6 text-center">
                <div className="w-12 h-12 rounded-full bg-danger/10 flex items-center justify-center mx-auto mb-4">
                  <ShieldAlert className="w-6 h-6 text-danger" />
                </div>
                <h3 className="text-lg font-medium text-white mb-2">Delete User</h3>
                <p className="text-sm text-slate-400 mb-6">
                  Are you sure you want to delete <span className="text-white font-medium">{userToDelete.username}</span>? This action cannot be undone.
                </p>
                <div className="flex justify-center gap-3">
                  <button onClick={() => setUserToDelete(null)} className="px-4 py-2 text-slate-300 hover:text-white hover:bg-slate-800 rounded-lg transition-colors flex-1">
                    Cancel
                  </button>
                  <button onClick={confirmDelete} className="px-4 py-2 bg-danger hover:bg-red-600 text-white rounded-lg shadow-lg shadow-danger/20 transition-colors flex-1">
                    Delete
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
