import { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import FileUpload from './components/FileUpload';
import ResultsView from './components/ResultsView';
import PatientList from './components/PatientList';
import PatientDetail from './components/PatientDetail';
import PreAuthForm from './components/PreAuthForm';
import EnhancementPage from './components/EnhancementPage';
import CaseList from './components/CaseList';
import CasePage from './components/CasePage';
import ConfigPage from './components/ConfigPage';
import LoginPage from './components/LoginPage';
import FinanceManagerPage from './components/FinanceManagerPage';
import { processPdf } from './services/api';
import type { ProcessResponse } from './services/api';
import { Activity, Sun, Moon, Users, Upload, Briefcase, Settings, LogOut } from 'lucide-react';

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------
interface AuthUser { role: 'staff' | 'finance'; username: string }

function getStoredAuth(): AuthUser | null {
  try {
    const raw = localStorage.getItem('auth');
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}

// ---------------------------------------------------------------------------
// Upload page
// ---------------------------------------------------------------------------
function UploadPage() {
  const [lastResult, setLastResult] = useState<ProcessResponse | null>(null);

  const handleFileSelect = async (file: File) => {
    const response = await processPdf(file);
    if (!response.success) {
      throw new Error(response.error || response.message || 'Processing failed');
    }
    setLastResult(response);
  };

  return (
    <main className="max-w-6xl mx-auto py-12 px-6">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-10 animate-in fade-in duration-500">
          <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white mb-4 transition-colors">
            Clinical Data Extraction
          </h1>
          <p className="text-slate-500 dark:text-slate-400 text-lg transition-colors">
            Upload lab reports or prescriptions for AI-powered FHIR conversion
          </p>
        </div>

        <FileUpload onFileSelect={handleFileSelect} />

        {lastResult ? (
          <div className="mt-10 animate-in fade-in duration-500">
            <ResultsView result={lastResult} onReset={() => setLastResult(null)} />
          </div>
        ) : (
          <div className="mt-10 bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm p-8 transition-colors animate-in fade-in duration-700">
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4">How it works</h3>
            <ol className="space-y-3 text-slate-600 dark:text-slate-400">
              <li className="flex items-start gap-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 text-sm font-bold shrink-0">1</span>
                <span>Upload one or more clinical documents (PDF, image, Word, Excel, CSV)</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 text-sm font-bold shrink-0">2</span>
                <span>NLP + LLM engine extracts structured clinical data from each file</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 text-sm font-bold shrink-0">3</span>
                <span>System generates FHIR R4 bundles and saves patient records</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 text-sm font-bold shrink-0">4</span>
                <span>View all processed patients in the Patients section</span>
              </li>
            </ol>
          </div>
        )}
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Root App
// ---------------------------------------------------------------------------
function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (localStorage.getItem('theme') as 'light' | 'dark') || 'light'
  );
  const [auth, setAuth] = useState<AuthUser | null>(getStoredAuth);
  const location = useLocation();

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => setTheme(t => t === 'light' ? 'dark' : 'light');

  const handleLogin = (role: 'staff' | 'finance', username: string) => {
    const user: AuthUser = { role, username };
    localStorage.setItem('auth', JSON.stringify(user));
    setAuth(user);
  };

  const handleLogout = () => {
    localStorage.removeItem('auth');
    setAuth(null);
  };

  // Not logged in → show login
  if (!auth) {
    return <LoginPage onLogin={handleLogin} theme={theme} toggleTheme={toggleTheme} />;
  }

  // Finance Manager → dedicated portal
  if (auth.role === 'finance') {
    return (
      <FinanceManagerPage
        username={auth.username}
        theme={theme}
        toggleTheme={toggleTheme}
        onLogout={handleLogout}
      />
    );
  }

  // Hospital Staff → normal app
  const navLink = (to: string, label: string, Icon: React.ElementType) => {
    const active = location.pathname === to || (to !== '/' && location.pathname.startsWith(to));
    return (
      <Link
        to={to}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
          active
            ? 'bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400'
            : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
        }`}
      >
        <Icon size={15} />
        {label}
      </Link>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans antialiased transition-colors duration-300">
      {/* Navbar */}
      <nav className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-8 py-4 flex justify-between items-center sticky top-0 z-50 transition-colors">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center space-x-2">
            <div className="bg-blue-600 p-2 rounded-lg shadow-sm">
              <Activity className="text-white" size={24} />
            </div>
            <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              Clinical<span className="text-blue-600 dark:text-blue-400">FHIR</span>
            </span>
          </Link>

          <div className="flex items-center gap-1">
            {navLink('/', 'Upload', Upload)}
            {navLink('/cases', 'Cases', Briefcase)}
            {navLink('/patients', 'Patients', Users)}
            {navLink('/configure', 'Configure', Settings)}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 hidden sm:block mr-1">
            {auth.username}
          </span>
          <button
            onClick={toggleTheme}
            className="p-2 rounded-full text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
            title="Toggle Light/Dark Mode"
          >
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
          <button
            onClick={handleLogout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium text-slate-500 dark:text-slate-400 hover:bg-red-50 dark:hover:bg-red-900/20 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            title="Sign out"
          >
            <LogOut size={15} />
            <span className="hidden sm:inline">Sign out</span>
          </button>
        </div>
      </nav>

      {/* Routes */}
      <Routes>
        <Route path="/"                    element={<UploadPage />} />
        <Route path="/patients"            element={<main className="max-w-6xl mx-auto py-12 px-6"><PatientList /></main>} />
        <Route path="/patients/:patientId" element={<main className="max-w-6xl mx-auto py-12 px-6"><PatientDetail /></main>} />
        <Route path="/pre-auth"            element={<main className="max-w-6xl mx-auto py-12 px-6"><PreAuthForm /></main>} />
        <Route path="/enhancement"         element={<main className="max-w-6xl mx-auto py-12 px-6"><EnhancementPage /></main>} />
        <Route path="/cases"               element={<main className="max-w-6xl mx-auto py-12 px-6"><CaseList /></main>} />
        <Route path="/cases/:billNo"       element={<main className="max-w-6xl mx-auto py-12 px-6"><CasePage /></main>} />
        <Route path="/configure"           element={<main className="max-w-4xl mx-auto py-12 px-6"><ConfigPage /></main>} />
      </Routes>

      <footer className="text-center mt-16 py-8 border-t border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 text-sm transition-colors">
        <p>Healthcare FHIR Converter — AI-Powered Clinical Data Normalization</p>
      </footer>
    </div>
  );
}

export default App;
