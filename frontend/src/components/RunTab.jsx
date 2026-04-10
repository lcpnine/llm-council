import { useState } from 'react';
import { api } from '../api';

const DATASETS = ['pubmedqa', 'medqa', 'mmlu'];


export default function RunTab({ models, promptVersions, baselines, onRefresh }) {
  const versionKeys = Object.keys(promptVersions);

  const [runModel, setRunModel] = useState(models[0] || '');
  const [runGeneratorModel, setRunGeneratorModel] = useState(models[0] || '');
  const [runSkepticModel, setRunSkepticModel] = useState(models[0] || '');
  const [runJudgeModel, setRunJudgeModel] = useState(models[0] || '');
  const [runPrompt, setRunPrompt] = useState(versionKeys[0] || '');
  const [runDataset, setRunDataset] = useState('pubmedqa');
  const [runSamples, setRunSamples] = useState(100);
  const [runStages, setRunStages] = useState(3);
  const isAngelDevil = runPrompt.includes('angel_devil');
  const [runLoading, setRunLoading] = useState(false);
  const [runMessage, setRunMessage] = useState('');

  // Batch mode
  const [batchMode, setBatchMode] = useState(false);
  const [batchModels, setBatchModels] = useState([]);
  const [batchPrompts, setBatchPrompts] = useState([]);
  const [batchDatasets, setBatchDatasets] = useState(['pubmedqa']);
  const [batchStagesList, setBatchStagesList] = useState([3]);

  const handleRunBenchmark = async () => {
    setRunLoading(true);
    setRunMessage('');
    try {
      const config = runStages === 3
        ? {
            model: runGeneratorModel,
            generator_model: runGeneratorModel,
            skeptic_model: runSkepticModel,
            judge_model: runJudgeModel,
            prompt_version: runPrompt,
            dataset: runDataset,
            n_samples: runSamples,
            n_stages: runStages,
          }
        : {
            model: runModel,
            prompt_version: runPrompt,
            dataset: runDataset,
            n_samples: runSamples,
            n_stages: runStages,
          };
      const res = await api.runBenchmark(config);
      setRunMessage(`Started: ${res.experiment_id}`);
      onRefresh();
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
      onRefresh();
    } catch (err) {
      setRunMessage(`Error: ${err.message}`);
    }
    setRunLoading(false);
  };

  const toggleBatchItem = (arr, setArr, item) => {
    setArr(prev => prev.includes(item) ? prev.filter(x => x !== item) : [...prev, item]);
  };

  const batchCount = batchModels.length * batchPrompts.length * batchDatasets.length * batchStagesList.length;

  const handleRunBatch = async () => {
    if (batchCount === 0) return;
    setRunLoading(true);
    setRunMessage('');
    try {
      const configs = [];
      for (const model of batchModels) {
        for (const prompt of batchPrompts) {
          for (const dataset of batchDatasets) {
            for (const stages of batchStagesList) {
              configs.push({
                model,
                prompt_version: prompt,
                dataset,
                n_samples: runSamples,
                n_stages: stages,
              });
            }
          }
        }
      }
      const res = await api.runBatch(configs);
      setRunMessage(`Queued ${res.count} experiments`);
      onRefresh();
    } catch (err) {
      setRunMessage(`Error: ${err.message}`);
    }
    setRunLoading(false);
  };

  return (
    <section className="dash-section">
      <h2>Run New Experiment</h2>

      <div style={{ marginBottom: 16 }}>
        <label style={{ fontSize: 13, cursor: 'pointer' }}>
          <input type="checkbox" checked={batchMode} onChange={e => setBatchMode(e.target.checked)} />
          {' '}Batch Mode (run matrix of experiments)
        </label>
      </div>

      {!batchMode ? (
        <>
          <div className="form-grid">
            {runStages === 3 ? (
              <>
                <label>
                  {isAngelDevil ? 'Angel Model' : 'Generator Model'}
                  <select value={runGeneratorModel} onChange={e => setRunGeneratorModel(e.target.value)}>
                    {models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </label>
                <label>
                  {isAngelDevil ? 'Devil Model' : 'Skeptic Model'}
                  <select value={runSkepticModel} onChange={e => setRunSkepticModel(e.target.value)}>
                    {models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </label>
                <label>
                  Judge Model
                  <select value={runJudgeModel} onChange={e => setRunJudgeModel(e.target.value)}>
                    {models.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </label>
              </>
            ) : (
              <label>
                Model
                <select value={runModel} onChange={e => setRunModel(e.target.value)}>
                  {models.map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </label>
            )}
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
        </>
      ) : (
        <>
          <div className="batch-grid">
            <div className="batch-section">
              <h4>Models</h4>
              {models.map(m => (
                <label key={m} className="batch-check">
                  <input type="checkbox" checked={batchModels.includes(m)}
                    onChange={() => toggleBatchItem(batchModels, setBatchModels, m)} />
                  <span className="mono">{m}</span>
                </label>
              ))}
            </div>
            <div className="batch-section">
              <h4>Prompt Versions</h4>
              {versionKeys.map(v => (
                <label key={v} className="batch-check">
                  <input type="checkbox" checked={batchPrompts.includes(v)}
                    onChange={() => toggleBatchItem(batchPrompts, setBatchPrompts, v)} />
                  <span className="mono">{v}</span>
                </label>
              ))}
            </div>
            <div className="batch-section">
              <h4>Datasets</h4>
              {DATASETS.map(d => (
                <label key={d} className="batch-check">
                  <input type="checkbox" checked={batchDatasets.includes(d)}
                    onChange={() => toggleBatchItem(batchDatasets, setBatchDatasets, d)} />
                  {d}
                </label>
              ))}
            </div>
            <div className="batch-section">
              <h4>Stages</h4>
              {[1, 3].map(s => (
                <label key={s} className="batch-check">
                  <input type="checkbox" checked={batchStagesList.includes(s)}
                    onChange={() => toggleBatchItem(batchStagesList, setBatchStagesList, s)} />
                  {s} stage{s > 1 ? 's' : ''}
                </label>
              ))}
            </div>
          </div>
          <div style={{ margin: '12px 0' }}>
            <label>
              Samples per experiment
              <input type="number" min={1} max={1000} value={runSamples}
                onChange={e => setRunSamples(Number(e.target.value))}
                style={{ marginLeft: 8, width: 80, padding: '4px 8px' }} />
            </label>
          </div>
          <div className="form-actions">
            <button className="btn-primary" onClick={handleRunBatch}
              disabled={runLoading || batchCount === 0}>
              {runLoading ? 'Queuing...' : `Run Batch (${batchCount} experiments)`}
            </button>
          </div>
        </>
      )}

      {runMessage && <div className="run-message">{runMessage}</div>}

      <h3>Baseline Configurations</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Name</th><th>Description</th><th>Model</th><th>Prompt</th><th>Stages</th>
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
  );
}
