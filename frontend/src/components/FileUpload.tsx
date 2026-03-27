import React, { useState, useRef } from 'react';
import { Upload, Cpu, FileText } from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  isProcessing: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({ onFileSelect, isProcessing }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const handleFile = (file: File) => {
    if (file.type === 'application/pdf') {
      setSelectedFile(file);
    } else {
      alert('Please select a PDF file');
    }
  };

  const handleSubmit = () => {
    if (selectedFile) {
      onFileSelect(selectedFile);
      // Simulate progress
      let p = 0;
      const interval = setInterval(() => {
        p += 5;
        setProgress(p);
        if (p >= 100) {
          clearInterval(interval);
        }
      }, 100);
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current?.click();
  };

  if (isProcessing) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-3xl p-12 shadow-xl border border-slate-100 dark:border-slate-700 text-center transition-colors">
        <Cpu className="mx-auto text-emerald-600 dark:text-emerald-400 animate-pulse mb-6" size={48} />
        <h3 className="text-2xl font-bold mb-2 text-slate-900 dark:text-white">AI Processing...</h3>
        <p className="text-slate-500 dark:text-slate-400 mb-8">Extracting clinical data and generating FHIR bundle</p>
        <div className="w-full bg-slate-100 dark:bg-slate-700 h-3 rounded-full overflow-hidden">
          <div 
            className="bg-gradient-to-r from-emerald-500 to-emerald-600 h-full transition-all duration-300 ease-out" 
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="mt-4 text-sm font-mono text-slate-400 dark:text-slate-500">
          Processing: {selectedFile?.name || 'document'}
        </div>
      </div>
    );
  }

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
