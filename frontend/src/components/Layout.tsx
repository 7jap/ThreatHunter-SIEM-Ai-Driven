
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, AlertTriangle, ShieldCheck, Settings, LogOut, Users } from 'lucide-react';
import { useAuthStore } from '../store/authStore';

export default function Layout() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { name: 'Dashboard', path: '/', icon: LayoutDashboard },
    { name: 'Alerts', path: '/alerts', icon: AlertTriangle },
    { name: 'Agents', path: '/agents', icon: ShieldCheck },
    { name: 'Accounts', path: '/users', icon: Users },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="w-64 bg-surface border-r border-slate-700 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-slate-700">
          <ShieldCheck className="w-8 h-8 text-primary mr-3" />
          <span className="text-xl font-bold text-white tracking-wide">Dashboard</span>
        </div>
        
        <div className="flex-1 overflow-y-auto py-4">
          <nav className="space-y-1 px-3">
            {navItems.map((item) => (
              <NavLink
                key={item.name}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                  }`
                }
              >
                <item.icon className="w-5 h-5 mr-3" />
                {item.name}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="p-4 border-t border-slate-700">
          <div className="flex items-center mb-4">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-white font-bold">
              {user?.username?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-white">{user?.display_name || 'User'}</p>
              <p className="text-xs text-slate-400 capitalize">{user?.roles?.[0] || 'Role'}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center w-full px-3 py-2 text-sm font-medium text-danger hover:bg-danger/10 rounded-md transition-colors"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 bg-surface border-b border-slate-700 flex items-center px-6">
          <h2 className="text-xl font-semibold text-white">Security Operations Center</h2>
        </header>
        <div className="flex-1 overflow-auto p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
