import { useState, useEffect, useRef } from 'react';
import { api } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell
} from 'recharts';

const COLORS = ['#4a90e2', '#e24a4a', '#4ae24a', '#e2c94a', '#9b59b6', '#e67e22', '#1abc9c', '#34495e'];

export default function ChartsTab({ experiments }) {
  const completed = experiments.filter(e => e.status === 'completed');

  // Accuracy bar chart data
  const accuracyData = completed.map(e => ({
    name: `${e.prompt_version} (${e.n_stages}stg)`,
    id: e.id,
    accuracy: e.accuracy != null ? +(e.accuracy * 100).toFixed(1) : 0,
    model: e.model,
  }));

  // Per-class F1 data
  const perClassData = [];
  const classes = new Set();
  completed.forEach(e => {
    if (e.full_metrics?.per_class) {
      Object.keys(e.full_metrics.per_class).forEach(c => classes.add(c));
    }
  });
  for (const cls of classes) {
    const row = { class: cls };
    completed.forEach(e => {
      const pc = e.full_metrics?.per_class?.[cls];
      row[e.id] = pc ? +(pc.f1 * 100).toFixed(1) : 0;
    });
    perClassData.push(row);
  }

  // Token usage data
  const tokenData = completed.map(e => ({
    name: `${e.prompt_version} (${e.n_stages}stg)`,
    tokens: e.total_tokens || 0,
  }));

  const exportChart = async (chartRef, filename) => {
    const container = chartRef.current;
    if (!container) return;

    // Recharts legends can include small icon SVGs; always target the chart surface.
    let svg = container.querySelector('svg.recharts-surface');
    if (!svg) {
      const svgs = Array.from(container.querySelectorAll('svg'));
      svg = svgs.sort((a, b) => {
        const ar = a.getBoundingClientRect();
        const br = b.getBoundingClientRect();
        return (br.width * br.height) - (ar.width * ar.height);
      })[0] || null;
    }
    if (!svg) return;

    const rect = svg.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));

    const cloned = svg.cloneNode(true);
    cloned.setAttribute('width', String(width));
    cloned.setAttribute('height', String(height));
    cloned.setAttribute('viewBox', `0 0 ${width} ${height}`);

    const svgData = new XMLSerializer().serializeToString(cloned);
    const blob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      URL.revokeObjectURL(url);
      return;
    }

    const scale = 2;
    canvas.width = width * scale;
    canvas.height = height * scale;
    ctx.scale(scale, scale);
    ctx.fillStyle = '#fff';
    ctx.fillRect(0, 0, width, height);

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, width, height);
      URL.revokeObjectURL(url);

      const a = document.createElement('a');
      a.download = filename;
      a.href = canvas.toDataURL('image/png');
      a.click();
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      // Keep failure silent in UI but visible in dev tools.
      console.error('Failed to export chart PNG');
    };

    img.src = url;
  };

  const accRef = useRef(null);
  const f1Ref = useRef(null);
  const tokenRef = useRef(null);

  if (completed.length === 0) {
    return (
      <section className="dash-section">
        <h2>Charts</h2>
        <p className="muted">No completed experiments to visualize.</p>
      </section>
    );
  }

  return (
    <section className="dash-section">
      <h2>Charts</h2>

      {/* Accuracy Bar Chart */}
      <div className="chart-container" ref={accRef}>
        <h3>
          Accuracy by Experiment
          <button type="button" className="btn-small" style={{ marginLeft: 12 }}
            onClick={() => exportChart(accRef, 'accuracy.png')}>Export PNG</button>
        </h3>
        <ResponsiveContainer width="100%" height={350}>
          <BarChart data={accuracyData} margin={{ top: 5, right: 20, bottom: 60, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-30} textAnchor="end" fontSize={11} height={80} />
            <YAxis domain={[0, 100]} label={{ value: 'Accuracy (%)', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Bar dataKey="accuracy" name="Accuracy (%)">
              {accuracyData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Per-Class F1 Chart */}
      {perClassData.length > 0 && (
        <div className="chart-container" ref={f1Ref}>
          <h3>
            Per-Class F1 Score
            <button type="button" className="btn-small" style={{ marginLeft: 12 }}
              onClick={() => exportChart(f1Ref, 'per_class_f1.png')}>Export PNG</button>
          </h3>
          <ResponsiveContainer width="100%" height={350}>
            <BarChart data={perClassData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="class" />
              <YAxis domain={[0, 100]} label={{ value: 'F1 (%)', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              {completed.map((e, i) => (
                <Bar key={e.id} dataKey={e.id} name={`${e.prompt_version} (${e.n_stages}stg)`}
                  fill={COLORS[i % COLORS.length]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Token Usage Chart */}
      <div className="chart-container" ref={tokenRef}>
        <h3>
          Token Usage by Experiment
          <button type="button" className="btn-small" style={{ marginLeft: 12 }}
            onClick={() => exportChart(tokenRef, 'token_usage.png')}>Export PNG</button>
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={tokenData} margin={{ top: 5, right: 20, bottom: 60, left: 20 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-30} textAnchor="end" fontSize={11} height={80} />
            <YAxis label={{ value: 'Tokens', angle: -90, position: 'insideLeft' }} />
            <Tooltip />
            <Bar dataKey="tokens" name="Total Tokens" fill="#e67e22" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
