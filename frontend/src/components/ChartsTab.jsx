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

  const exportChart = (chartRef, filename) => {
    const svg = chartRef.current?.querySelector('svg');
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      ctx.scale(2, 2);
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0);
      const a = document.createElement('a');
      a.download = filename;
      a.href = canvas.toDataURL('image/png');
      a.click();
    };
    img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)));
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
          <button className="btn-small" style={{ marginLeft: 12 }}
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
            <button className="btn-small" style={{ marginLeft: 12 }}
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
          <button className="btn-small" style={{ marginLeft: 12 }}
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
