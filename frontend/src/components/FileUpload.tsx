import React, { useState, useRef, useEffect } from 'react';
import {
  Upload, FileText, CheckCircle2,
  ShieldCheck, ScanText, CaseSensitive, BarChart2, Brain, Hospital, BadgeCheck, Zap,
} from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isProcessing: boolean;
}

// Each step: what to show, what % to reach, and how fast (ms per 1%)
// Slower ms = slower bar = step feels heavier
const PIPELINE_STEPS = [
  { label: 'Validating document',          Icon: ShieldCheck,      target: 8,  msPerPercent: 80  },
  { label: 'Reading document structure',   Icon: ScanText,         target: 20, msPerPercent: 150 },
  { label: 'Extracting text content',      Icon: CaseSensitive,    target: 42, msPerPercent: 220 },
  { label: 'Assessing content quality',    Icon: BarChart2,        target: 52, msPerPercent: 130 },
  { label: 'NLP + LLM clinical analysis',  Icon: Brain,            target: 78, msPerPercent: 380 },
  { label: 'Mapping to FHIR R4 standard',  Icon: Hospital,         target: 90, msPerPercent: 260 },
  { label: 'Running billing validation',   Icon: BadgeCheck,       target: 97, msPerPercent: 200 },
  { label: 'Finalising results',           Icon: Zap,              target: 99, msPerPercent: 1800 },
];

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, isProcessing }) => {
  const [dragActive, setDragActive]     = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress]         = useState(0);
  const [stepIndex, setStepIndex]       = useState(0);
  const [done, setDone]                 = useState(false);

  const fileInputRef  = useRef<HTMLInputElement>(null);
  const intervalRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const progressRef   = useRef(0);
  const stepIndexRef  = useRef(0);

  // Clear the running interval helper
  const clearTick = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  // Advance progress one tick at a time, respecting current step's target and speed
  const startTicking = () => {
    clearTick();

    const tick = () => {
      const step = PIPELINE_STEPS[stepIndexRef.current];
      if (!step) return;

      const next = progressRef.current + 1;

      if (next >= step.target) {
        // Reached this step's ceiling — move to next step if available
        progressRef.current = step.target;
        setProgress(step.target);

        if (stepIndexRef.current < PIPELINE_STEPS.length - 1) {
          stepIndexRef.current += 1;
          setStepIndex(stepIndexRef.current);
          // Reschedule with next step's speed
          clearTick();
          intervalRef.current = setInterval(tick, PIPELINE_STEPS[stepIndexRef.current].msPerPercent);
        } else {
          // At 99% — stop ticking, wait for API to return
          clearTick();
        }
      } else {
        progressRef.current = next;
        setProgress(next);
      }
    };

    intervalRef.current = setInterval(tick, PIPELINE_STEPS[stepIndexRef.current].msPerPercent);
  };

  // Watch isProcessing: when it flips false → API returned → complete the bar
  const wasProcessing = useRef(false);
  useEffect(() => {
    if (wasProcessing.current && !isProcessing) {
      // API just finished
      clearTick();
      setProgress(100);
      setDone(true);
    }
    wasProcessing.current = isProcessing;
  }, [isProcessing]);

  // Reset everything when not processing and not done
  useEffect(() => {
    if (!isProcessing && !done) {
      clearTick();
      progressRef.current  = 0;
      stepIndexRef.current = 0;
      setProgress(0);
      setStepIndex(0);
    }
  }, [isProcessing, done]);

  // Cleanup on unmount
  useEffect(() => () => clearTick(), []);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files?.[0]) handleFile(e.target.files[0]);
  };

  const handleFile = (file: File) => {
    if (file.type === 'application/pdf') {
      setSelectedFile(file);
    } else {
      alert('Please select a PDF file');
    }
  };

  const handleSubmit = () => {
    if (!selectedFile) return;
    // Reset state
    setDone(false);
    progressRef.current  = 0;
    stepIndexRef.current = 0;
    setProgress(0);
    setStepIndex(0);
    // Kick off API call in parent
    onFileSelect(selectedFile);
    // Start simulated progress
    startTicking();
  };

  // ── Processing view ──────────────────────────────────────────────────────
  if (isProcessing || done) {
    const currentStep = PIPELINE_STEPS[Math.min(stepIndex, PIPELINE_STEPS.length - 1)];
    const completedSteps = PIPELINE_STEPS.slice(0, stepIndex);

    return (
      <div className="bg-white dark:bg-slate-800 rounded-3xl p-10 shadow-xl border border-slate-100 dark:border-slate-700 transition-colors">

        {/* Header */}
        <div className="text-center mb-8">
          {done ? (
            <CheckCircle2 className="mx-auto text-emerald-500 mb-4" size={48} />
          ) : (
            <div className="mx-auto w-12 h-12 mb-4 flex items-center justify-center text-emerald-500 animate-pulse">
              <currentStep.Icon size={48} />
            </div>
          )}
          <h3 className="text-2xl font-bold text-slate-900 dark:text-white">
            {done ? 'Processing Complete' : 'Analysing Document'}
          </h3>
          <p className="text-slate-500 dark:text-slate-400 text-sm mt-1 truncate">
            {selectedFile?.name}
          </p>
        </div>

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex justify-between text-xs text-slate-400 dark:text-slate-500 mb-1.5">
            <span>{done ? 'Complete' : currentStep.label}</span>
            <span>{progress}%</span>
          </div>
          <div className="w-full bg-slate-100 dark:bg-slate-700 h-2.5 rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-300 ease-linear ${
                done
                  ? 'bg-emerald-500'
                  : 'bg-gradient-to-r from-emerald-500 to-emerald-400'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Step list */}
        <div className="mt-6 space-y-2">
          {PIPELINE_STEPS.map((step, i) => {
            const isActive    = !done && i === stepIndex;
            const isCompleted = done ? true : i < stepIndex;
            const isPending   = !done && i > stepIndex;

            return (
              <div
                key={i}
                className={`flex items-center gap-3 px-3 py-2 rounded-xl text-sm transition-all duration-300 ${
                  isActive
                    ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300'
                    : isCompleted
                    ? 'text-slate-400 dark:text-slate-500'
                    : 'text-slate-300 dark:text-slate-600'
                }`}
              >
                {/* Status icon */}
                <span className="shrink-0 w-5 text-center">
                  {isCompleted ? (
                    <CheckCircle2 size={14} className="text-emerald-500 inline" />
                  ) : isActive ? (
                    <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                  ) : (
                    <span className="inline-block w-2 h-2 rounded-full bg-slate-200 dark:bg-slate-700" />
                  )}
                </span>

                <span className={`flex items-center gap-2 ${isActive ? 'font-semibold' : ''}`}>
                  <step.Icon size={14} className="shrink-0" />
                  {step.label}
                </span>

                {isActive && (
                  <span className="ml-auto text-xs text-emerald-500 animate-pulse font-mono">
                    running...
                  </span>
                )}
                {isCompleted && !done && (
                  <span className="ml-auto text-xs text-slate-300 dark:text-slate-600 font-mono">
                    done
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  // ── Upload view ──────────────────────────────────────────────────────────
  return (
    <div>
      {!selectedFile ? (
        <label
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-3xl p-20 flex flex-col items-center justify-center bg-white dark:bg-slate-800 transition-all cursor-pointer group w-full ${
            dragActive
              ? 'border-emerald-500 bg-emerald-50/30 dark:bg-emerald-900/10'
              : 'border-slate-300 dark:border-slate-700 hover:border-emerald-500 dark:hover:border-emerald-500 hover:bg-emerald-50/30 dark:hover:bg-emerald-900/10'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            onChange={handleChange}
            accept=".pdf"
          />
          <div className="bg-emerald-100 dark:bg-emerald-900/50 p-6 rounded-full text-emerald-600 dark:text-emerald-400 group-hover:scale-110 transition-transform mb-6">
            <Upload size={48} />
          </div>
          <h3 className="text-xl font-semibold mb-2 text-slate-900 dark:text-white">
            Drop Clinical Document Here
          </h3>
          <p className="text-slate-400 dark:text-slate-500">
            Accepts PDF lab reports and prescriptions
          </p>
          <div className="mt-8 px-6 py-2 bg-slate-900 dark:bg-slate-700 text-white rounded-full font-medium transition-colors hover:bg-slate-800 dark:hover:bg-slate-600">
            Select File
          </div>
        </label>
      ) : (
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-800 rounded-2xl p-6 border border-slate-200 dark:border-slate-700 shadow-sm transition-colors">
            <div className="flex items-start gap-4">
              <div className="bg-emerald-100 dark:bg-emerald-900/50 p-3 rounded-lg text-emerald-600 dark:text-emerald-400">
                <FileText size={32} />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-1 truncate">
                  {selectedFile.name}
                </h3>
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  {(selectedFile.size / 1024).toFixed(2)} KB
                </p>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors text-sm font-medium"
              >
                Remove
              </button>
            </div>
          </div>

          <button
            onClick={handleSubmit}
            disabled={isProcessing}
            className="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-400 text-white px-6 py-4 rounded-xl font-bold text-lg transition-all shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 hover:scale-[1.02] active:scale-95 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {isProcessing ? 'Processing...' : 'Process Document'}
          </button>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
