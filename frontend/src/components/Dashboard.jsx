import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import RunTab from './RunTab';
import ResultsTab from './ResultsTab';
import DetailTab from './DetailTab';
import CompareTab from './CompareTab';
import ChartsTab from './ChartsTab';
import PromptsTab from './PromptsTab';
import './Dashboard.css';

export default function Dashboard() {
  const [tab, setTab] = useState('run');
  const [models, setModels] = useState([]);
  const [promptVersions, setPromptVersions] = useState({});
  const [experiments, setExperiments] = useState([]);
  const [baselines, setBaselines] = useState([]);

  // Detail view
  const [detailExperiment, setDetailExperiment] = useState(null);
  const [detailResults, setDetailResults] = useState([]);

  // Compare
  const [compareIds, setCompareIds] = useState([]);

  const loadData = useCallback(async () => {
    try {
      const [m, p, e, b] = await Promise.all([
        api.getModels(),
        api.getPrompts(),
        api.getExperiments(),
        api.getBaselines(),
      ]);
      setModels(m);
      setPromptVersions(p);
      setExperiments(e);
      setBaselines(b);
    } catch (err) {
      console.error('Failed to load data:', err);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  // Poll for running experiments
  useEffect(() => {
    const hasRunning = experiments.some(e => e.status === 'running');
    if (!hasRunning) return;
    const interval = setInterval(async () => {
      const exps = await api.getExperiments();
      setExperiments(exps);
      if (!exps.some(e => e.status === 'running')) clearInterval(interval);
    }, 5000);
    return () => clearInterval(interval);
  }, [experiments]);

  const handleViewDetail = async (expId) => {
    try {
      const [exp, results] = await Promise.all([
        api.getExperiment(expId),
        api.getResults(expId),
      ]);
      setDetailExperiment(exp);
      setDetailResults(results);
      setTab('detail');
    } catch (err) {
      console.error('Failed to load detail:', err);
    }
  };

  const handleSelectForCompare = (ids) => {
    setCompareIds(ids);
    setTab('compare');
  };

  const tabs = [
    { id: 'run', label: 'Run Experiment' },
    { id: 'results', label: `Results (${experiments.length})` },
    { id: 'compare', label: 'Compare' },
    { id: 'charts', label: 'Charts' },
    { id: 'prompts', label: 'Prompts' },
  ];
  if (detailExperiment) {
    tabs.push({ id: 'detail', label: `Detail: ${detailExperiment.id}` });
  }

  return (
    <div className="dashboard">
      <header className="dash-header">
        <h1>Medical QA Benchmark</h1>
        <nav className="dash-tabs">
          {tabs.map(t => (
            <button key={t.id} className={tab === t.id ? 'active' : ''}
              onClick={() => setTab(t.id)}>
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="dash-content">
        {tab === 'run' && (
          <RunTab models={models} promptVersions={promptVersions}
            baselines={baselines} onRefresh={loadData} />
        )}
        {tab === 'results' && (
          <ResultsTab experiments={experiments} onViewDetail={handleViewDetail}
            onRefresh={loadData} onSelectForCompare={handleSelectForCompare} />
        )}
        {tab === 'detail' && detailExperiment && (
          <DetailTab experiment={detailExperiment} results={detailResults}
            onBack={() => { setTab('results'); setDetailExperiment(null); }} onRefresh={loadData} />
        )}
        {tab === 'compare' && (
          <CompareTab experiments={experiments} initialIds={compareIds} />
        )}
        {tab === 'charts' && (
          <ChartsTab experiments={experiments} />
        )}
        {tab === 'prompts' && (
          <PromptsTab promptVersions={promptVersions} onRefresh={loadData} />
        )}
      </main>
    </div>
  );
}
