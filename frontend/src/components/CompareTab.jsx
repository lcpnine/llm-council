import { useState, useEffect, useMemo } from 'react';
import { api } from '../api';

export default function CompareTab({ experiments, initialIds = [] }) {
  const [selectedIds, setSelectedIds] = useState(initialIds);
  const [compareData, setCompareData] = useState(null);
  const [loading, setLoading] = useState(false);

  const completedExps = experiments.filter(e => e.status === 'completed');

  useEffect(() => {
    if (initialIds.length > 0) {
      setSelectedIds(initialIds);
    }
  }, [initialIds]);

  useEffect(() => {
    if (selectedIds.length < 2) { setCompareData(null); return; }
    let cancelled = false;
    setLoading(true);
    api.compareExperiments(selectedIds).then(data => {
      if (!cancelled) setCompareData(data);
    }).catch(console.error).finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [selectedIds]);

  const toggleId = (id) => {
    setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  // Build per-question diff
  const questionDiff = useMemo(() => {
    if (!compareData || compareData.experiments.length < 2) return [];
    const exps = compareData.experiments;
    // Collect all question IDs
    const qids = new Set();
    exps.forEach(e => (e.results || []).forEach(r => qids.add(r.question_id)));

    const diffs = [];
    for (const qid of qids) {
      const row = { question_id: qid };
      let hasDisagreement = false;
      let gold = '';
      for (const e of exps) {
        const r = (e.results || []).find(r => r.question_id === qid);
        if (r) {
          row[e.id] = { predicted: r.predicted, correct: r.correct, gold: r.gold };
          gold = r.gold;
        }
      }
      // Check disagreement
      const preds = exps.map(e => row[e.id]?.predicted).filter(Boolean);
      if (new Set(preds).size > 1) hasDisagreement = true;
      row.gold = gold;
      row.hasDisagreement = hasDisagreement;
      diffs.push(row);
    }
    return diffs;
  }, [compareData]);

  const [showOnlyDiffs, setShowOnlyDiffs] = useState(false);
  const displayDiff = showOnlyDiffs ? questionDiff.filter(d => d.hasDisagreement) : questionDiff;

  // Generate LaTeX table
  const generateLatex = () => {
    if (!compareData) return;
    const exps = compareData.experiments;
    const cols = exps.length + 1;
    let latex = `\\begin{tabular}{l${'c'.repeat(exps.length)}}\n\\hline\n`;
    latex += `Metric & ${exps.map(e => e.id.replace(/_/g, '\\_')).join(' & ')} \\\\\n\\hline\n`;
    const metrics = ['accuracy', 'f1_macro', 'maybe_recall'];
    for (const m of metrics) {
      const vals = exps.map(e => {
        const v = e[m];
        if (v == null) return '-';
        return m === 'accuracy' ? `${(v * 100).toFixed(1)}\\%` : v.toFixed(3);
      });
      latex += `${m.replace(/_/g, ' ')} & ${vals.join(' & ')} \\\\\n`;
    }
    latex += `Total Tokens & ${exps.map(e => (e.total_tokens || 0).toLocaleString()).join(' & ')} \\\\\n`;
    latex += `\\hline\n\\end{tabular}`;
    navigator.clipboard.writeText(latex);
    alert('LaTeX table copied to clipboard!');
  };

  return (
    <section className="dash-section">
      <h2>Compare Experiments</h2>

      <div style={{ marginBottom: 16 }}>
        <h4 style={{ margin: '0 0 8px' }}>Select experiments to compare:</h4>
        <div style={{ maxHeight: 200, overflow: 'auto', border: '1px solid #e0e0e0', borderRadius: 6, padding: 8 }}>
          {completedExps.map(e => (
            <label key={e.id} style={{ display: 'block', fontSize: 13, padding: '2px 0', cursor: 'pointer' }}>
              <input type="checkbox" checked={selectedIds.includes(e.id)}
                onChange={() => toggleId(e.id)} />
              {' '}<span className="mono">{e.id}</span>
              {' '}<span style={{ color: '#888' }}>
                ({e.model}, {e.prompt_version}, {e.n_stages}stg, {e.accuracy != null ? (e.accuracy * 100).toFixed(1) + '%' : '-'})
              </span>
            </label>
          ))}
        </div>
      </div>

      {loading && <p>Loading comparison...</p>}

      {compareData && compareData.experiments.length >= 2 && (
        <>
          {/* Metrics comparison table */}
          <h3>
            Metrics Comparison
            <button className="btn-small" style={{ marginLeft: 12 }} onClick={generateLatex}>
              Copy LaTeX
            </button>
          </h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Metric</th>
                {compareData.experiments.map(e => (
                  <th key={e.id} className="mono" style={{ fontSize: 11 }}>{e.id}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                ['Model', e => e.model],
                ['Prompt', e => e.prompt_version],
                ['Stages', e => e.n_stages],
                ['Accuracy', e => e.accuracy != null ? (e.accuracy * 100).toFixed(1) + '%' : '-'],
                ['F1 Macro', e => e.f1_macro != null ? e.f1_macro.toFixed(3) : '-'],
                ['Maybe Recall', e => e.maybe_recall != null ? e.maybe_recall.toFixed(3) : '-'],
                ['Total Tokens', e => e.total_tokens != null ? e.total_tokens.toLocaleString() : '-'],
              ].map(([label, fn]) => (
                <tr key={label}>
                  <td><strong>{label}</strong></td>
                  {compareData.experiments.map(e => <td key={e.id}>{fn(e)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>

          {/* Per-question diff */}
          <h3>
            Per-Question Comparison
            <label style={{ marginLeft: 12, fontSize: 13, fontWeight: 'normal', cursor: 'pointer' }}>
              <input type="checkbox" checked={showOnlyDiffs}
                onChange={e => setShowOnlyDiffs(e.target.checked)} />
              {' '}Show only disagreements ({questionDiff.filter(d => d.hasDisagreement).length})
            </label>
          </h3>
          <div style={{ maxHeight: 500, overflow: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Question ID</th>
                  <th>Gold</th>
                  {compareData.experiments.map(e => (
                    <th key={e.id} className="mono" style={{ fontSize: 11 }}>{e.id}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {displayDiff.map(row => (
                  <tr key={row.question_id} className={row.hasDisagreement ? 'row-diff' : ''}>
                    <td className="mono">{row.question_id}</td>
                    <td className="mono">{row.gold}</td>
                    {compareData.experiments.map(e => {
                      const cell = row[e.id];
                      if (!cell) return <td key={e.id}>-</td>;
                      return (
                        <td key={e.id} className={cell.correct ? 'cell-correct' : 'cell-wrong'}>
                          {cell.predicted}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
