import { useState } from 'react';
import { Activity, Eye, EyeOff, Moon, Sun } from 'lucide-react';

const CREDENTIALS: Record<string, { password: string; role: 'staff' | 'finance' }> = {
  // Hospital Staff
  'staff':         { password: 'staff123',    role: 'staff' },
  'dr.sharma':     { password: 'sharma@321',  role: 'staff' },
  'dr.mehta':      { password: 'mehta@456',   role: 'staff' },
  'nurse.priya':   { password: 'priya@789',   role: 'staff' },
  'admission':     { password: 'admit@2024',  role: 'staff' },
  // Finance Manager
  'finance':       { password: 'finance123',  role: 'finance' },
  'accounts':      { password: 'accounts@99', role: 'finance' },
  'tpa.manager':   { password: 'tpa@2024',    role: 'finance' },
};

interface LoginPageProps {
  onLogin: (role: 'staff' | 'finance', username: string) => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
}

export default function LoginPage({ onLogin, theme, toggleTheme }: LoginPageProps) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole]         = useState<'staff' | 'finance'>('staff');
  const [showPw, setShowPw]     = useState(false);
  const [error, setError]       = useState('');
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    await new Promise(r => setTimeout(r, 500));

    const cred = CREDENTIALS[username.trim().toLowerCase()];
    if (!cred || cred.password !== password || cred.role !== role) {
      setError('Invalid username, password, or role.');
      setLoading(false);
      return;
    }
    onLogin(cred.role, username.trim().toLowerCase());
  };

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950 flex items-center justify-center px-4 transition-colors">

      {/* Theme toggle */}
      <button
        onClick={toggleTheme}
        className="fixed top-4 right-4 p-2 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-white dark:hover:bg-slate-800 transition-all"
      >
        {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
      </button>

      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="bg-blue-600 p-3 rounded-2xl shadow-lg shadow-blue-500/20 mb-3">
            <Activity className="text-white" size={26} />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white">
            Clinical<span className="text-blue-600 dark:text-blue-400">FHIR</span>
          </h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">Healthcare RCM Platform</p>
        </div>

        {/* Card */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-700 shadow-sm p-8">
          <h2 className="text-base font-bold text-slate-800 dark:text-white mb-6">Sign in to your account</h2>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Role */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">Role</label>
              <div className="grid grid-cols-2 gap-2">
                {([
                  { value: 'staff',   label: 'Hospital Staff' },
                  { value: 'finance', label: 'Finance Manager' },
                ] as const).map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => { setRole(opt.value); setError(''); }}
                    className={`py-2 rounded-xl text-sm font-semibold border transition-all ${
                      role === opt.value
                        ? 'bg-blue-600 border-blue-600 text-white shadow-sm'
                        : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 hover:border-blue-400 dark:hover:border-blue-600'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Username */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">Username</label>
              <input
                type="text"
                value={username}
                onChange={e => { setUsername(e.target.value); setError(''); }}
                placeholder="Enter username"
                autoComplete="username"
                className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-300 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  value={password}
                  onChange={e => { setPassword(e.target.value); setError(''); }}
                  placeholder="Enter password"
                  autoComplete="current-password"
                  className="w-full px-3.5 py-2.5 pr-10 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-sm text-slate-900 dark:text-white placeholder:text-slate-300 dark:placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <p className="text-xs text-red-500 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full py-2.5 mt-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center gap-2"
            >
              {loading && <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
