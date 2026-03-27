import React, { useState } from 'react';
import JsonViewer from './JsonViewer';
import type { ProcessResponse } from '../types/api';
import { CheckCircle2, Download, ChevronLeft, Database, FileText, Activity } from 'lucide-react';

interface ResultsViewProps {
  result: ProcessResponse;
  onReset: () => void;
}

const ResultsView: React.FC<ResultsViewProps> = ({ result, onReset }) => {
  const [activeTab, setActiveTab] = useState<'fhir' | 'text' | 'summary'>('summary');

  const downloadJson = () => {
    const dataStr = JSON.stringify(result.fhir_bundle, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `fhir-bundle-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const renderSummary = () => {
    if (!result.fhir_bundle || !result.fhir_bundle.entry) {
      return <p className="text-slate-500 dark:text-slate-400">No data available</p>;
    }

    const entries = result.fhir_bundle.entry;
    const resourceCounts: Record<string, number> = {};

    entries.forEach((entry: any) => {
      const resourceType = entry.resource?.resourceType;
      if (resourceType) {
        resourceCounts[resourceType] = (resourceCounts[resourceType] || 0) + 1;
      }
    });

    return (
      <div className="space-y-6">
        {/* Success Banner */}
        <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-2xl p-6 transition-colors">
          <div className="flex items-start gap-4">
            <div className="bg-emerald-600 dark:bg-emerald-500 p-2 rounded-lg">
              <CheckCircle2 className="text-white" size={24} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-emerald-900 dark:text-emerald-100 mb-1">
                Successfully Processed {result.document_type?.replace('_', ' ').toUpperCase()}
              </h3>
              <p className="text-emerald-700 dark:text-emerald-300 text-sm">
                {result.message}
              </p>
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
            <Database size={20} className="text-emerald-600 dark:text-emerald-400" />
            FHIR Resources Generated
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(resourceCounts).map(([resourceType, count]) => (
              <div
                key={resourceType}
                className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl p-5 transition-all hover:shadow-md hover:scale-[1.02]"
              >
                <div className="flex justify-between items-center">
                  <div>
                    <div className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-1">
                      Resource Type
                    </div>
                    <div className="text-lg font-bold text-slate-900 dark:text-white">
                      {resourceType}
                    </div>
                  </div>
                  <div className="bg-emerald-600 dark:bg-emerald-500 text-white px-4 py-2 rounded-full font-bold text-lg shadow-lg shadow-emerald-500/20">
                    {count}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-100 dark:bg-slate-800 rounded-xl p-5 border border-slate-200 dark:border-slate-700 transition-colors">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={18} className="text-emerald-600 dark:text-emerald-400" />
              <span className="font-semibold text-slate-700 dark:text-slate-300">Total Resources</span>
            </div>
            <span className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
              {entries.length}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div>
      {/* Header with Actions */}
      <div className="flex flex-col md:flex-row md:justify-between md:items-center gap-4 mb-8">
        <h2 className="text-3xl font-bold text-slate-900 dark:text-white transition-colors">
          Extraction Results
        </h2>
        <div className="flex gap-3">
          <button
            onClick={downloadJson}
            className="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 flex items-center gap-2 hover:scale-105 active:scale-95"
          >
            <Download size={16} />
            Download FHIR
          </button>
          <button
            onClick={onReset}
            className="bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 px-5 py-2.5 rounded-xl font-semibold text-sm transition-all flex items-center gap-2 hover:scale-105 active:scale-95"
          >
            <ChevronLeft size={16} />
            New Document
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-slate-200 dark:border-slate-700">
        <button
          onClick={() => setActiveTab('summary')}
          className={`px-6 py-3 font-semibold text-sm transition-all relative ${
            activeTab === 'summary'
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          Summary
          {activeTab === 'summary' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600 dark:bg-emerald-400"></div>
          )}
        </button>
        <button
          onClick={() => setActiveTab('fhir')}
          className={`px-6 py-3 font-semibold text-sm transition-all relative ${
            activeTab === 'fhir'
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          FHIR Bundle
          {activeTab === 'fhir' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600 dark:bg-emerald-400"></div>
          )}
        </button>
        <button
          onClick={() => setActiveTab('text')}
          className={`px-6 py-3 font-semibold text-sm transition-all relative ${
            activeTab === 'text'
              ? 'text-emerald-600 dark:text-emerald-400'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300'
          }`}
        >
          Extracted Text
          {activeTab === 'text' && (
            <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-emerald-600 dark:bg-emerald-400"></div>
          )}
        </button>
      </div>

      {/* Tab Content */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-slate-700 p-8 transition-colors shadow-sm">
        {activeTab === 'summary' && renderSummary()}
        {activeTab === 'fhir' && result.fhir_bundle && (
          <JsonViewer data={result.fhir_bundle} />
        )}
        {activeTab === 'text' && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <FileText size={18} className="text-slate-500 dark:text-slate-400" />
              <h4 className="font-semibold text-slate-700 dark:text-slate-300">Raw Extracted Text</h4>
            </div>
            <pre className="bg-slate-50 dark:bg-slate-900 p-6 rounded-xl overflow-auto max-h-[600px] text-sm font-mono text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 whitespace-pre-wrap break-words transition-colors">
              {result.extracted_text || 'No text extracted'}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultsView;
