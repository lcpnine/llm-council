import { useRef, useState, useMemo } from 'react';
import { api } from '../api';

const PRESET_TAGS = ['Phase 1', 'Phase 2', 'Final', 'Ablation', 'Debug'];

export default function ResultsTab({ experiments, onViewDetail, onRefresh, onSelectForCompare }) {
  const [sortField, setSortField] = useState('timestamp');
  const [sortDir, setSortDir] = useState('desc');
  const [importStatus, setImportStatus] = useState(null);
  const importInputRef = useRef(null);

  // Filters
  const [filterModel, setFilterModel] = useState('');
  const [filterPrompt, setFilterPrompt] = useState('');
  const [filterDataset, setFilterDataset] = useState('');
  const [filterStages, setFilterStages] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterTag, setFilterTag] = useState('');

  // Compare selection
  const [compareIds, setCompareIds] = useState([]);

  const handleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('desc'); }
  };

  const uniqueVals = (field) => [...new Set(experiments.map(e => e[field]).filter(Boolean))];

  const filtered = useMemo(() => {
    return experiments.filter(e => {
      if (filterModel && e.model !== filterModel) return false;
      if (filterPrompt && e.prompt_version !== filterPrompt) return false;
      if (filterDataset && e.dataset !== filterDataset) return false;
      if (filterStages && e.n_stages !== Number(filterStages)) return false;
      if (filterStatus && e.status !== filterStatus) return false;
      if (filterTag && !(e.tags || []).includes(filterTag)) return false;
      return true;
    });
  }, [experiments, filterModel, filterPrompt, filterDataset, filterStages, filterStatus, filterTag]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let va = a[sortField], vb = b[sortField];
      if (va == null) va = '';
      if (vb == null) vb = '';
      if (typeof va === 'number') return sortDir === 'asc' ? va - vb : vb - va;
      return sortDir === 'asc' ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
    });
  }, [filtered, sortField, sortDir]);

  const toggleCompare = (id) => {
    setCompareIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  };

  const handleDelete = async (id) => {
    if (!confirm(`Delete experiment ${id}?`)) return;
    try {
      await api.deleteExperiment(id);
      onRefresh();
    } catch (err) {
      console.error('Delete failed:', err);
    }
  };

  const handleExport = async () => {
    try {
      const exportIds = compareIds.length > 0 ? compareIds : null;
      const data = await api.exportExperiments(exportIds);
      const label = exportIds ? `${exportIds.length}_selected` : 'all';
      const ts = new Date().toISOString().slice(0, 10);
      const filename = `experiments_${label}_${ts}.json`;
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Export failed: ${err.message}`);
    }
  };

  const handleImportFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    e.target.value = '';
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      setImportStatus('importing');
      const result = await api.importExperiments(data, true);
      setImportStatus(`Imported ${result.imported}, skipped ${result.skipped} (already existed)`);
      onRefresh();
      setTimeout(() => setImportStatus(null), 5000);
    } catch (err) {
      setImportStatus(`Import failed: ${err.message}`);
      setTimeout(() => setImportStatus(null), 5000);
    }
  };

  return (
    <section className="dash-section">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Experiment Results</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            className="btn-secondary"
            onClick={handleExport}
            title={compareIds.length > 0 ? `Export ${compareIds.length} selected experiments` : 'Export all experiments'}
          >
            Export JSON{compareIds.length > 0 ? ` (${compareIds.length})` : ' (all)'}
          </button>
          <button
            className="btn-secondary"
            onClick={() => importInputRef.current?.click()}
            title="Import experiments from a JSON file"
          >
            Import JSON
          </button>
          <input
            ref={importInputRef}
            type="file"
            accept=".json"
            style={{ display: 'none' }}
            onChange={handleImportFile}
          />
        </div>
      </div>
      {importStatus && (
        <div style={{
          padding: '6px 12px',
          marginBottom: 8,
          borderRadius: 4,
          background: importStatus.startsWith('Import failed') ? '#fdecea' : '#e8f5e9',
          color: importStatus.startsWith('Import failed') ? '#c62828' : '#2e7d32',
          fontSize: 13,
        }}>
          {importStatus === 'importing' ? 'Importing...' : importStatus}
        </div>
      )}

      {/* Filters */}
      <div className="filter-bar">
        <select value={filterModel} onChange={e => setFilterModel(e.target.value)}>
          <option value="">All Models</option>
          {uniqueVals('model').map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={filterPrompt} onChange={e => setFilterPrompt(e.target.value)}>
          <option value="">All Prompts</option>
          {uniqueVals('prompt_version').map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={filterDataset} onChange={e => setFilterDataset(e.target.value)}>
          <option value="">All Datasets</option>
          {uniqueVals('dataset').map(v => <option key={v} value={v}>{v}</option>)}
        </select>
        <select value={filterStages} onChange={e => setFilterStages(e.target.value)}>
          <option value="">All Stages</option>
          <option value="1">1 stage</option>
          <option value="3">3 stages</option>
        </select>
        <select value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
          <option value="">All Status</option>
          <option value="completed">Completed</option>
          <option value="running">Running</option>
          <option value="failed">Failed</option>
        </select>
        <select value={filterTag} onChange={e => setFilterTag(e.target.value)}>
          <option value="">All Tags</option>
          {PRESET_TAGS.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {compareIds.length > 0 && (
        <div className="compare-bar">
          <span>{compareIds.length} selected for comparison</span>
          <button className="btn-primary" onClick={() => { onSelectForCompare(compareIds); setCompareIds([]); }}>
            Compare Selected
          </button>
          <button className="btn-secondary" onClick={() => setCompareIds([])}>Clear</button>
        </div>
      )}

      {filtered.length === 0 ? (
        <p className="muted">No experiments match filters.</p>
      ) : (
        <table className="data-table sortable">
          <thead>
            <tr>
              <th style={{ width: 30 }}></th>
              {[
                ['id', 'ID'],
                ['model', 'Model'],
                ['prompt_version', 'Prompt'],
                ['dataset', 'Dataset'],
                ['n_stages', 'Stg'],
                ['status', 'Status'],
                ['accuracy', 'Accuracy'],
                ['f1_macro', 'F1'],
                ['maybe_recall', 'Maybe R'],
                ['total_tokens', 'Tokens'],
              ].map(([field, label]) => (
                <th key={field} onClick={() => handleSort(field)} className="sortable-th">
                  {label} {sortField === field ? (sortDir === 'asc' ? '\u25B2' : '\u25BC') : ''}
                </th>
              ))}
              <th>Tags</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(exp => (
              <tr key={exp.id} className={exp.status === 'running' ? 'row-running' : ''}>
                <td>
                  <input type="checkbox" checked={compareIds.includes(exp.id)}
                    onChange={() => toggleCompare(exp.id)} />
                </td>
                <td className="mono" style={{ fontSize: 11, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}
                  title={exp.id}>{exp.id}</td>
                <td className="mono">{exp.model}</td>
                <td className="mono">{exp.prompt_version}</td>
                <td>{exp.dataset}</td>
                <td>{exp.n_stages}</td>
                <td>
                  <span className={`status-badge status-${exp.status}`}>{exp.status}</span>
                  {exp.status === 'running' && exp.progress && (
                    <span style={{ fontSize: 11, marginLeft: 4 }}>
                      {exp.progress.current}/{exp.progress.total}
                    </span>
                  )}
                </td>
                <td>{exp.accuracy != null ? (exp.accuracy * 100).toFixed(1) + '%' : '-'}</td>
                <td>{exp.f1_macro != null ? exp.f1_macro.toFixed(3) : '-'}</td>
                <td>{exp.maybe_recall != null ? exp.maybe_recall.toFixed(3) : '-'}</td>
                <td>{exp.total_tokens != null ? exp.total_tokens.toLocaleString() : '-'}</td>
                <td>
                  {(exp.tags || []).map(t => (
                    <span key={t} className="tag-pill">{t}</span>
                  ))}
                </td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  {exp.status === 'completed' && (
                    <button className="btn-small" onClick={() => onViewDetail(exp.id)}>View</button>
                  )}
                  <button className="btn-small btn-danger" onClick={() => handleDelete(exp.id)}
                    style={{ marginLeft: 4 }}>Del</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
