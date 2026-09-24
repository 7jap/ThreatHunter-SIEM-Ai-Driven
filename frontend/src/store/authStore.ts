import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface AuthState {
  token: string | null;
  serverUrl: string;
  user: any | null;
  setToken: (token: string) => void;
  setServerUrl: (url: string) => void;
  setUser: (user: any) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      serverUrl: 'http://localhost:8443',
      user: null,
      setToken: (token) => set({ token }),
      setServerUrl: (serverUrl) => set({ serverUrl }),
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'siem-auth-storage',
    }
  )
);
