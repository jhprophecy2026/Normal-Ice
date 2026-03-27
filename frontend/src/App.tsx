import { useState, useEffect } from 'react';
import FileUpload from './components/FileUpload';
import ResultsView from './components/ResultsView';
import { processPdf, healthCheck } from './services/api';
import type { ProcessResponse } from './types/api';
import { Activity, Sun, Moon, CheckCircle2 } from 'lucide-react';

function App() {
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [theme, setTheme] = useState<'light' | 'dark'>('dark');

  useEffect(() => {
    checkApiHealth();
  }, []);

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const checkApiHealth = async () => {
    try {
      await healthCheck();
      setApiStatus('online');
    } catch (err) {
      setApiStatus('offline');
    }
  };

  const handleFileSelect = async (file: File) => {
    setIsProcessing(true);
    setError(null);

    try {
      const response = await processPdf(file);
      
      if (response.success) {
        setResult(response);
      } else {
        setError(response.error || response.message || 'Processing failed');
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        err.message || 
        'An error occurred while processing the document'
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  const toggleTheme = () => {
    setTheme(t => t === 'light' ? 'dark' : 'light');
  };

  const StepIndicator = ({ currentStep }: { currentStep: number }) => (
    <div className="flex items-center justify-center space-x-4 mb-12">
      {[1, 2].map((s) => (
        <div key={s} className="flex items-center">
          <div className={`flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-500 ${
            currentStep >= s 
              ? 'bg-emerald-600 border-emerald-600 text-white shadow-lg shadow-emerald-500/30' 
              : 'border-slate-300 dark:border-slate-700 text-slate-400 dark:text-slate-500'
          }`}>
            {currentStep > s ? <CheckCircle2 size={20} /> : <span className="font-semibold">{s}</span>}
          </div>
          {s < 2 && <div className={`w-20 h-0.5 transition-colors ${currentStep > s ? 'bg-emerald-600' : 'bg-slate-200 dark:bg-slate-700'}`} />}
        </div>
      ))}
    </div>
  );

  const step = !result ? 1 : 2;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 font-sans antialiased transition-colors duration-300">
      {/* Navbar */}
      <nav className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-8 py-4 flex justify-between items-center sticky top-0 z-50 transition-colors">
        <div className="flex items-center space-x-2">
          <div className="bg-gradient-to-br from-emerald-500 to-emerald-600 p-2 rounded-lg shadow-lg shadow-emerald-500/20">
            <Activity className="text-white" size={24} />
          </div>
          <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
            Clinical<span className="text-emerald-600 dark:text-emerald-400">FHIR</span>
          </span>
        </div>
        
        <div className="flex items-center space-x-4">
          <button 
            onClick={toggleTheme}
            className="p-2 rounded-full text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-all"
            title="Toggle Light/Dark Mode"
          >
            {theme === 'light' ? <Moon size={20} /> : <Sun size={20} />}
          </button>
          
          {/* API Status Badge */}
          <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold transition-colors ${
            apiStatus === 'online' 
              ? 'bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-400' 
              : apiStatus === 'offline'
              ? 'bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-400'
              : 'bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              apiStatus === 'online' ? 'bg-emerald-500' : 
              apiStatus === 'offline' ? 'bg-red-500' : 'bg-amber-500'
            }`}></span>
            {apiStatus === 'online' ? 'API Online' : 
             apiStatus === 'offline' ? 'API Offline' : 'Checking...'}
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto py-12 px-6">
        <StepIndicator currentStep={step} />

        {!result ? (
          <div className="max-w-2xl mx-auto">
            <div className="text-center mb-10 animate-in fade-in duration-500">
              <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white mb-4 transition-colors">
                Clinical Data Extraction
              </h1>
              <p className="text-slate-500 dark:text-slate-400 text-lg transition-colors">
                Upload lab reports or prescriptions for AI-powered FHIR conversion
              </p>
            </div>
            
            <FileUpload 
              onFileSelect={handleFileSelect} 
              isProcessing={isProcessing}
            />
            
            {/* Error Display */}
            {error && (
              <div className="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl text-red-700 dark:text-red-400 transition-colors animate-in fade-in duration-300">
                <strong className="font-semibold">Error:</strong> {error}
              </div>
            )}

            {/* Instructions */}
            {!isProcessing && !error && (
              <div className="mt-10 bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm p-8 transition-colors animate-in fade-in duration-700">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4">
                  How it works
                </h3>
                <ol className="space-y-3 text-slate-600 dark:text-slate-400">
                  <li className="flex items-start gap-3">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 text-sm font-bold shrink-0">1</span>
                    <span>Upload a PDF (lab report or prescription)</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 text-sm font-bold shrink-0">2</span>
                    <span>AI extracts structured clinical data using Gemini</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 text-sm font-bold shrink-0">3</span>
                    <span>System generates FHIR R4 compliant bundle</span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 text-sm font-bold shrink-0">4</span>
                    <span>Download or integrate with your healthcare system</span>
                  </li>
                </ol>
              </div>
            )}
          </div>
        ) : (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <ResultsView result={result} onReset={handleReset} />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center mt-16 py-8 border-t border-slate-200 dark:border-slate-800 text-slate-400 dark:text-slate-500 text-sm transition-colors">
        <p>Healthcare FHIR Converter - Powered by Gemini 1.5 Pro</p>
      </footer>
    </div>
  );
}

export default App;
