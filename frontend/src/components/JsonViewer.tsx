import React, { useState } from 'react';
import { Copy, CheckCircle2 } from 'lucide-react';

interface JsonViewerProps {
  data: any;
}

const JsonViewer: React.FC<JsonViewerProps> = ({ data }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    const jsonString = JSON.stringify(data, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h4 className="font-semibold text-slate-700 dark:text-slate-300 flex items-center gap-2">
          <span className="text-emerald-600 dark:text-emerald-400">{'{ }'}</span>
          FHIR Bundle JSON
        </h4>
        <button
          onClick={copyToClipboard}
          className="flex items-center gap-2 px-4 py-2 bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-lg font-medium text-sm transition-all hover:scale-105 active:scale-95"
        >
          {copied ? (
            <>
              <CheckCircle2 size={16} className="text-emerald-600 dark:text-emerald-400" />
              Copied!
            </>
          ) : (
            <>
              <Copy size={16} />
              Copy JSON
            </>
          )}
        </button>
      </div>

      <div className="relative">
        <pre className="bg-slate-900 dark:bg-slate-950 p-6 rounded-xl overflow-auto max-h-[600px] text-sm font-mono border-2 border-slate-700 dark:border-slate-800 transition-colors">
          <code className="text-emerald-400 dark:text-emerald-300">
            {JSON.stringify(data, null, 2)}
          </code>
        </pre>
      </div>
    </div>
  );
};

export default JsonViewer;
