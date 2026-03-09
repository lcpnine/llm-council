/**
 * API client for the Medical QA Benchmark backend.
 */

const API_BASE = 'http://localhost:8001';

export const api = {
  // Models
  async getModels() {
    const res = await fetch(`${API_BASE}/api/models`);
    if (!res.ok) throw new Error('Failed to fetch models');
    return res.json();
  },

  // Experiments
  async runBenchmark(config) {
    const res = await fetch(`${API_BASE}/api/benchmark/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error('Failed to start benchmark');
    return res.json();
  },

  async getExperiments() {
    const res = await fetch(`${API_BASE}/api/experiments`);
    if (!res.ok) throw new Error('Failed to fetch experiments');
    return res.json();
  },

  async getExperiment(id) {
    const res = await fetch(`${API_BASE}/api/experiments/${id}`);
    if (!res.ok) throw new Error('Failed to fetch experiment');
    return res.json();
  },

  async getResults(id) {
    const res = await fetch(`${API_BASE}/api/experiments/${id}/results`);
    if (!res.ok) throw new Error('Failed to fetch results');
    return res.json();
  },

  // Prompts
  async getPrompts() {
    const res = await fetch(`${API_BASE}/api/prompts`);
    if (!res.ok) throw new Error('Failed to fetch prompts');
    return res.json();
  },

  async savePrompt(data) {
    const res = await fetch(`${API_BASE}/api/prompts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to save prompt');
    return res.json();
  },

  // Baselines
  async getBaselines() {
    const res = await fetch(`${API_BASE}/api/baselines`);
    if (!res.ok) throw new Error('Failed to fetch baselines');
    return res.json();
  },

  async runAllBaselines(dataset, nSamples) {
    const res = await fetch(
      `${API_BASE}/api/baselines/run?dataset=${dataset}&n_samples=${nSamples}`,
      { method: 'POST' }
    );
    if (!res.ok) throw new Error('Failed to start baselines');
    return res.json();
  },
};
