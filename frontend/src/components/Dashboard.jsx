import { useState, useEffect, useCallback } from 'react';
import { api } from '../api';
import './Dashboard.css';

const DATASETS = ['pubmedqa', 'medqa', 'mmlu'];

export default function Dashboard() {
  const [tab, setTab] = useState('run');       // run | results | detail | prompts
  const [models, setModels] = useState([]);
  const [promptVersions, setPromptVersions] = useState({});
  const [experiments, setExperiments] = useState([]);
  const [baselines, setBaselines] = useState([]);

  // Run form
  const [runModel, setRunModel] = useState('');
  const [runPrompt, setRunPrompt] = useState('');
  const [runDataset, setRunDataset] = useState('pubmedqa');
  const [runSamples, setRunSamples] = useState(100);
  const [runStages, setRunStages] = useState(3);
  const [runLoading, setRunLoading] = useState(false);
  const [runMessage, setRunMessage] = useState('');

  // Detail view
  const [detailExperiment, setDetailExperiment] = useState(null);
  const [detailResults, setDetailResults] = useState([]);
  const [expandedRow, setExpandedRow] = useState(null);

  // Prompt editor
  const [newPromptVersion, setNewPromptVersion] = useState('');
  const [newGenerator, setNewGenerator] = useState('');
  const [newSkeptic, setNewSkeptic] = useState('');
  const [newJudge, setNewJudge] = useState('');
  const [viewPromptVersion, setViewPromptVersion] = useState('');

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
      if (m.length && !runModel) setRunModel(m[0]);
      const versions = Object.keys(p);
      if (versions.length && !runPrompt) setRunPrompt(versions[0]);
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

  const handleRunBenchmark = async () => {
    setRunLoading(true);
    setRunMessage('');
    try {
      const res = await api.runBenchmark({
        model: runModel,
        prompt_version: runPrompt,
        dataset: runDataset,
        n_samples: runSamples,
        n_stages: runStages,
      });
      setRunMessage(`Started: ${res.experiment_id}`);
      const exps = await api.getExperiments();
      setExperiments(exps);
    } catch (err) {
      setRunMessage(`Error: ${err.message}`);
    }
    setRunLoading(false);
  };

  const handleRunBaselines = async () => {
    setRunLoading(true);
    setRunMessage('');
    try {
      const res = await api.runAllBaselines(runDataset, runSamples);
      setRunMessage(`Started ${res.experiment_ids.length} baselines`);
      const exps = await api.getExperiments();
      setExperiments(exps);
    } catch (err) {
      setRunMessage(`Error: ${err.message}`);
    }
    setRunLoading(false);
  };

  const handleViewDetail = async (expId) => {
    try {
      const [exp, results] = await Promise.all([
        api.getExperiment(expId),
        api.getResults(expId),
      ]);
      setDetailExperiment(exp);
      setDetailResults(results);
      setExpandedRow(null);
      setTab('detail');
    } catch (err) {
      console.error('Failed to load detail:', err);
    }
  };

  const handleExportCSV = () => {
    if (!detailResults.length) return;
    const headers = ['question_id', 'gold', 'predicted', 'correct'];
    const rows = detailResults.map(r =>
      [r.question_id, r.gold, r.predicted, r.correct].join(',')
    );
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${detailExperiment?.id || 'results'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleSavePrompt = async () => {
    if (!newPromptVersion || !newGenerator || !newSkeptic || !newJudge) return;
    try {
      await api.savePrompt({
        version: newPromptVersion,
        generator: newGenerator,
        skeptic: newSkeptic,
        judge: newJudge,
      });
      setNewPromptVersion('');
      setNewGenerator('');
      setNewSkeptic('');
      setNewJudge('');
      const p = await api.getPrompts();
      setPromptVersions(p);
    } catch (err) {
      console.error('Failed to save prompt:', err);
    }
  };

  // Sort helpers
  const [sortField, setSortField] = useState('timestamp');
  const [sortDir, setSortDir] = useState('desc');
  const handleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('desc'); }
  };
  const sortedExperiments = [...experiments].sort((a, b) => {
    let va = a[sortField], vb = b[sortField];
    if (va == null) va = '';
    if (vb == null) vb = '';
    if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
    return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
  });

  const versionKeys = Object.keys(promptVersions);

  return (
    <div className="dashboard">
      <header className="dash-header">
        <h1>Medical QA Benchmark</h1>
        <nav className="dash-tabs">
          <button className={tab === 'run' ? 'active' : ''} onClick={() => setTab('run')}>
            Run Experiment
          </button>
          <button className={tab === 'results' ? 'active' : ''} onClick={() => setTab('results')}>
            Results ({experiments.length})
          </button>
          <button className={tab === 'prompts' ? 'active' : ''} onClick={() => setTab('prompts')}>
            Prompts
          </button>
          {detailExperiment && (
            <button className={tab === 'detail' ? 'active' : ''} onClick={() => setTab('detail')}>
              Detail: {detailExperiment.id}
            </button>
          )}
        </nav>
      </header>

      <main className="dash-content">
        {/* ========== RUN TAB ========== */}
        {tab === 'run' && (
          <section className="dash-section">
            <h2>Run New Experiment</h2>
            <div className="form-grid">
              <label>
                Model
                <select value={runModel} onChange={e => setRunModel(e.target.value)}>
                  {models.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </label>
              <label>
                Prompt Version
                <select value={runPrompt} onChange={e => setRunPrompt(e.target.value)}>
                  {versionKeys.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
              </label>
              <label>
                Dataset
                <select value={runDataset} onChange={e => setRunDataset(e.target.value)}>
                  {DATASETS.map(d => <option key={d} value={d}>{d}</option>)}
                </select>
              </label>
              <label>
                Samples
                <input type="number" min={1} max={1000} value={runSamples}
                  onChange={e => setRunSamples(Number(e.target.value))} />
              </label>
              <label>
                Stages
                <select value={runStages} onChange={e => setRunStages(Number(e.target.value))}>
                  <option value={1}>1 (Generator only)</option>
                  <option value={3}>3 (Full debate)</option>
                </select>
              </label>
            </div>
            <div className="form-actions">
              <button className="btn-primary" onClick={handleRunBenchmark} disabled={runLoading}>
                {runLoading ? 'Starting...' : 'Run Experiment'}
              </button>
              <button className="btn-secondary" onClick={handleRunBaselines} disabled={runLoading}>
                Run All Baselines
              </button>
            </div>
            {runMessage && <div className="run-message">{runMessage}</div>}

            <h3>Baseline Configurations</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Model</th>
                  <th>Prompt</th>
                  <th>Stages</th>
                </tr>
              </thead>
              <tbody>
                {baselines.map((b, i) => (
                  <tr key={i}>
                    <td>{b.name}</td>
                    <td>{b.description}</td>
                    <td className="mono">{b.model}</td>
                    <td className="mono">{b.prompt_version}</td>
                    <td>{b.n_stages}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {/* ========== RESULTS TAB ========== */}
        {tab === 'results' && (
          <section className="dash-section">
            <h2>Experiment Results</h2>
            {experiments.length === 0 ? (
              <p className="muted">No experiments yet. Run one from the "Run Experiment" tab.</p>
            ) : (
              <table className="data-table sortable">
                <thead>
                  <tr>
                    {[
                      ['id', 'Experiment ID'],
                      ['timestamp', 'Timestamp'],
                      ['model', 'Model'],
                      ['prompt_version', 'Prompt Ver'],
                      ['dataset', 'Dataset'],
                      ['n_samples', 'Samples'],
                      ['status', 'Status'],
                      ['accuracy', 'Accuracy'],
                      ['f1_macro', 'F1 Macro'],
                      ['maybe_recall', 'Maybe Recall'],
                    ].map(([field, label]) => (
                      <th key={field} onClick={() => handleSort(field)} className="sortable-th">
                        {label} {sortField === field ? (sortDir === 'asc' ? '▲' : '▼') : ''}
                      </th>
                    ))}
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedExperiments.map(exp => (
                    <tr key={exp.id} className={exp.status === 'running' ? 'row-running' : ''}>
                      <td className="mono">{exp.id}</td>
                      <td>{exp.timestamp ? new Date(exp.timestamp).toLocaleString() : ''}</td>
                      <td className="mono">{exp.model}</td>
                      <td className="mono">{exp.prompt_version}</td>
                      <td>{exp.dataset}</td>
                      <td>{exp.n_samples}</td>
                      <td>
                        <span className={`status-badge status-${exp.status}`}>{exp.status}</span>
                      </td>
                      <td>{exp.accuracy != null ? (exp.accuracy * 100).toFixed(1) + '%' : '-'}</td>
                      <td>{exp.f1_macro != null ? exp.f1_macro.toFixed(3) : '-'}</td>
                      <td>{exp.maybe_recall != null ? exp.maybe_recall.toFixed(3) : '-'}</td>
                      <td>
                        {exp.status === 'completed' && (
                          <button className="btn-small" onClick={() => handleViewDetail(exp.id)}>
                            View Details
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        )}

        {/* ========== DETAIL TAB ========== */}
        {tab === 'detail' && detailExperiment && (
          <section className="dash-section">
            <button className="btn-back" onClick={() => setTab('results')}>
              ← Back to Results
            </button>
            <h2>Experiment: {detailExperiment.id}</h2>

            <div className="detail-meta">
              <div><strong>Model:</strong> {detailExperiment.model}</div>
              <div><strong>Prompt:</strong> {detailExperiment.prompt_version}</div>
              <div><strong>Dataset:</strong> {detailExperiment.dataset}</div>
              <div><strong>Samples:</strong> {detailExperiment.n_samples}</div>
              <div><strong>Stages:</strong> {detailExperiment.n_stages}</div>
              <div><strong>Status:</strong> {detailExperiment.status}</div>
            </div>

            {detailExperiment.full_metrics && (
              <>
                <h3>Metrics</h3>
                <div className="metrics-grid">
                  <div className="metric-card">
                    <div className="metric-value">
                      {(detailExperiment.full_metrics.accuracy * 100).toFixed(1)}%
                    </div>
                    <div className="metric-label">Accuracy</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-value">
                      {detailExperiment.full_metrics.f1_macro?.toFixed(3) || '-'}
                    </div>
                    <div className="metric-label">F1 Macro</div>
                  </div>
                  {detailExperiment.full_metrics.maybe_recall != null && (
                    <div className="metric-card">
                      <div className="metric-value">
                        {detailExperiment.full_metrics.maybe_recall.toFixed(3)}
                      </div>
                      <div className="metric-label">Maybe Recall</div>
                    </div>
                  )}
                  <div className="metric-card">
                    <div className="metric-value">
                      {detailExperiment.full_metrics.correct}/{detailExperiment.full_metrics.total}
                    </div>
                    <div className="metric-label">Correct / Total</div>
                  </div>
                </div>

                {/* Per-class metrics */}
                {detailExperiment.full_metrics.per_class && (
                  <>
                    <h3>Per-Class Metrics</h3>
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(detailExperiment.full_metrics.per_class).map(([cls, m]) => (
                          <tr key={cls}>
                            <td className="mono">{cls}</td>
                            <td>{m.precision.toFixed(3)}</td>
                            <td>{m.recall.toFixed(3)}</td>
                            <td>{m.f1.toFixed(3)}</td>
                            <td>{m.support}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </>
                )}

                {/* Confusion Matrix */}
                {detailExperiment.full_metrics.confusion_matrix && (
                  <>
                    <h3>Confusion Matrix (rows = gold, cols = predicted)</h3>
                    <ConfusionMatrix data={detailExperiment.full_metrics.confusion_matrix}
                      dataset={detailExperiment.dataset} />
                  </>
                )}
              </>
            )}

            {/* Per-question results */}
            <h3>
              Per-Question Results
              <button className="btn-small" style={{ marginLeft: 12 }} onClick={handleExportCSV}>
                Export CSV
              </button>
            </h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Question ID</th><th>Gold</th><th>Predicted</th><th>Correct</th><th>Debate Log</th>
                </tr>
              </thead>
              <tbody>
                {detailResults.map((r, i) => (
                  <>
                    <tr key={i} className={r.correct ? '' : 'row-wrong'}>
                      <td className="mono">{r.question_id}</td>
                      <td className="mono">{r.gold}</td>
                      <td className="mono">{r.predicted}</td>
                      <td>{r.correct ? '✓' : '✗'}</td>
                      <td>
                        <button className="btn-small"
                          onClick={() => setExpandedRow(expandedRow === i ? null : i)}>
                          {expandedRow === i ? 'Hide' : 'Show'}
                        </button>
                      </td>
                    </tr>
                    {expandedRow === i && (
                      <tr key={`${i}-log`} className="debate-log-row">
                        <td colSpan={5}>
                          <DebateLog log={r.debate_log} />
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {/* ========== PROMPTS TAB ========== */}
        {tab === 'prompts' && (
          <section className="dash-section">
            <h2>Prompt Versions</h2>

            <label>
              View existing version:
              <select value={viewPromptVersion} onChange={e => setViewPromptVersion(e.target.value)}>
                <option value="">-- select --</option>
                {versionKeys.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </label>

            {viewPromptVersion && promptVersions[viewPromptVersion] && (
              <div className="prompt-view">
                {['generator', 'skeptic', 'judge'].map(role => (
                  <div key={role} className="prompt-block">
                    <h4>{role}</h4>
                    <pre>{promptVersions[viewPromptVersion][role]}</pre>
                  </div>
                ))}
              </div>
            )}

            <h3>Create New Prompt Version</h3>
            <div className="prompt-form">
              <label>
                Version Name
                <input type="text" value={newPromptVersion}
                  onChange={e => setNewPromptVersion(e.target.value)}
                  placeholder="e.g. v4_custom" />
              </label>
              <label>
                Generator Prompt
                <textarea rows={6} value={newGenerator}
                  onChange={e => setNewGenerator(e.target.value)}
                  placeholder="Use {question} as placeholder" />
              </label>
              <label>
                Skeptic Prompt
                <textarea rows={6} value={newSkeptic}
                  onChange={e => setNewSkeptic(e.target.value)}
                  placeholder="Use {question} and {answer} as placeholders" />
              </label>
              <label>
                Judge Prompt
                <textarea rows={6} value={newJudge}
                  onChange={e => setNewJudge(e.target.value)}
                  placeholder="Use {question}, {answer}, and {critique} as placeholders" />
              </label>
              <button className="btn-primary" onClick={handleSavePrompt}
                disabled={!newPromptVersion || !newGenerator || !newSkeptic || !newJudge}>
                Save Prompt Version
              </button>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}


function ConfusionMatrix({ data, dataset }) {
  const labels = dataset === 'pubmedqa'
    ? ['yes', 'no', 'maybe']
    : ['A', 'B', 'C', 'D'];
  // Include 'unknown' if present
  const allPredicted = new Set();
  Object.values(data).forEach(preds => Object.keys(preds).forEach(k => allPredicted.add(k)));
  const cols = [...labels];
  if (allPredicted.has('unknown')) cols.push('unknown');

  return (
    <table className="data-table confusion-matrix">
      <thead>
        <tr>
          <th>Gold \ Pred</th>
          {cols.map(c => <th key={c}>{c}</th>)}
        </tr>
      </thead>
      <tbody>
        {labels.map(gold => (
          <tr key={gold}>
            <td className="mono"><strong>{gold}</strong></td>
            {cols.map(pred => (
              <td key={pred} className={gold === pred ? 'cm-diag' : ''}>
                {data[gold]?.[pred] || 0}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}


function DebateLog({ log }) {
  if (!log || Object.keys(log).length === 0) return <p className="muted">No log data</p>;
  return (
    <div className="debate-log">
      {log.generator_output && (
        <div className="log-section">
          <h5>Generator</h5>
          <pre>{log.generator_output}</pre>
        </div>
      )}
      {log.skeptic_output && (
        <div className="log-section">
          <h5>Skeptic</h5>
          <pre>{log.skeptic_output}</pre>
        </div>
      )}
      {log.judge_output && (
        <div className="log-section">
          <h5>Judge</h5>
          <pre>{log.judge_output}</pre>
        </div>
      )}
      {log.error && (
        <div className="log-section log-error">
          <h5>Error</h5>
          <pre>{log.error}</pre>
        </div>
      )}
    </div>
  );
}
