import React, { useState } from 'react';
import { api } from '../api';

const PRESET_TAGS = ['Phase 1', 'Phase 2', 'Final', 'Ablation', 'Debug'];

export default function DetailTab({ experiment, results, onBack, onRefresh }) {
  const [expandedRow, setExpandedRow] = useState(null);
  const [notes, setNotes] = useState(experiment.notes || '');
  const [tags, setTags] = useState(experiment.tags || []);
  const [saving, setSaving] = useState(false);

  const handleSaveNotes = async () => {
    setSaving(true);
    try {
      await api.updateNotes(experiment.id, notes);
    } catch (err) {
      console.error('Failed to save notes:', err);
    }
    setSaving(false);
  };

  const toggleTag = async (tag) => {
    const newTags = tags.includes(tag) ? tags.filter(t => t !== tag) : [...tags, tag];
    setTags(newTags);
    try {
      await api.updateTags(experiment.id, newTags);
    } catch (err) {
      console.error('Failed to update tags:', err);
    }
  };

  const handleExportCSV = () => {
    if (!results.length) return;
    const headers = ['question_id', 'gold', 'predicted', 'correct', 'generator_tokens', 'skeptic_tokens', 'judge_tokens'];
    const rows = results.map(r => {
      const tu = r.token_usage || {};
      return [
        r.question_id, r.gold, r.predicted, r.correct,
        tu.generator?.total_tokens || 0,
        tu.skeptic?.total_tokens || 0,
        tu.judge?.total_tokens || 0,
      ].join(',');
    });
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${experiment.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const m = experiment.full_metrics;

  return (
    <section className="dash-section">
      <button className="btn-back" onClick={onBack}>&larr; Back to Results</button>
      <h2>Experiment: {experiment.id}</h2>

      <div className="detail-meta">
        {experiment.n_stages === 3 && experiment.config?.generator_model ? (
          <>
            <div><strong>Generator:</strong> {experiment.config.generator_model}</div>
            <div><strong>Skeptic:</strong>   {experiment.config.skeptic_model || experiment.model}</div>
            <div><strong>Judge:</strong>     {experiment.config.judge_model   || experiment.model}</div>
          </>
        ) : (
          <div><strong>Model:</strong> {experiment.model}</div>
        )}
        <div><strong>Prompt:</strong> {experiment.prompt_version}</div>
        <div><strong>Dataset:</strong> {experiment.dataset}</div>
        <div><strong>Samples:</strong> {experiment.n_samples}</div>
        <div><strong>Stages:</strong> {experiment.n_stages}</div>
        <div><strong>Status:</strong> {experiment.status}</div>
        <div><strong>Total Tokens:</strong> {experiment.total_tokens?.toLocaleString() || '-'}</div>
      </div>

      {/* Tags */}
      <div style={{ marginBottom: 16 }}>
        <strong style={{ fontSize: 13 }}>Tags: </strong>
        {PRESET_TAGS.map(t => (
          <button key={t} className={`tag-pill ${tags.includes(t) ? 'tag-active' : ''}`}
            onClick={() => toggleTag(t)}>{t}</button>
        ))}
      </div>

      {/* Notes */}
      <div style={{ marginBottom: 16 }}>
        <strong style={{ fontSize: 13 }}>Notes:</strong>
        <textarea rows={3} value={notes} onChange={e => setNotes(e.target.value)}
          style={{ width: '100%', marginTop: 4, padding: 8, fontSize: 13, border: '1px solid #d0d0d0', borderRadius: 6 }}
          placeholder="Add experiment notes..." />
        <button className="btn-small" onClick={handleSaveNotes} disabled={saving}>
          {saving ? 'Saving...' : 'Save Notes'}
        </button>
      </div>

      {m && (
        <>
          <h3>Metrics</h3>
          <div className="metrics-grid">
            <div className="metric-card">
              <div className="metric-value">{(m.accuracy * 100).toFixed(1)}%</div>
              <div className="metric-label">Accuracy</div>
            </div>
            <div className="metric-card">
              <div className="metric-value">{m.f1_macro?.toFixed(3) || '-'}</div>
              <div className="metric-label">F1 Macro</div>
            </div>
            {m.maybe_recall != null && (
              <div className="metric-card">
                <div className="metric-value">{m.maybe_recall.toFixed(3)}</div>
                <div className="metric-label">Maybe Recall</div>
              </div>
            )}
            <div className="metric-card">
              <div className="metric-value">{m.correct}/{m.total}</div>
              <div className="metric-label">Correct / Total</div>
            </div>
          </div>

          {m.per_class && (
            <>
              <h3>Per-Class Metrics</h3>
              <table className="data-table">
                <thead>
                  <tr><th>Class</th><th>Precision</th><th>Recall</th><th>F1</th><th>Support</th></tr>
                </thead>
                <tbody>
                  {Object.entries(m.per_class).map(([cls, v]) => (
                    <tr key={cls}>
                      <td className="mono">{cls}</td>
                      <td>{v.precision.toFixed(3)}</td>
                      <td>{v.recall.toFixed(3)}</td>
                      <td>{v.f1.toFixed(3)}</td>
                      <td>{v.support}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {m.confusion_matrix && (
            <>
              <h3>Confusion Matrix (rows = gold, cols = predicted)</h3>
              <ConfusionMatrix data={m.confusion_matrix} dataset={experiment.dataset} />
            </>
          )}
        </>
      )}

      <h3>
        Per-Question Results
        <button className="btn-small" style={{ marginLeft: 12 }} onClick={handleExportCSV}>Export CSV</button>
      </h3>
      <table className="data-table">
        <thead>
          <tr><th>Question ID</th><th>Gold</th><th>Predicted</th><th>Correct</th><th>Debate Log</th></tr>
        </thead>
        <tbody>
          {results.map((r, i) => (
            <React.Fragment key={i}>
              <tr className={r.correct ? '' : 'row-wrong'}>
                <td className="mono">{r.question_id}</td>
                <td className="mono">{r.gold}</td>
                <td className="mono">{r.predicted}</td>
                <td>{r.correct ? '\u2713' : '\u2717'}</td>
                <td>
                  <button className="btn-small"
                    onClick={() => setExpandedRow(expandedRow === i ? null : i)}>
                    {expandedRow === i ? 'Hide' : 'Show'}
                  </button>
                </td>
              </tr>
              {expandedRow === i && (
                <tr className="debate-log-row">
                  <td colSpan={5}><DebateLog log={r.debate_log} /></td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </section>
  );
}


function ConfusionMatrix({ data, dataset }) {
  const labels = dataset === 'pubmedqa' ? ['yes', 'no', 'maybe'] : ['A', 'B', 'C', 'D'];
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
        <div className="log-section"><h5>Generator</h5><pre>{log.generator_output}</pre></div>
      )}
      {log.skeptic_output && (
        <div className="log-section"><h5>Skeptic</h5><pre>{log.skeptic_output}</pre></div>
      )}
      {log.judge_output && (
        <div className="log-section"><h5>Judge</h5><pre>{log.judge_output}</pre></div>
      )}
      {log.error && (
        <div className="log-section log-error"><h5>Error</h5><pre>{log.error}</pre></div>
      )}
    </div>
  );
}
