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

  async runBatch(configs) {
    const res = await fetch(`${API_BASE}/api/benchmark/batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ configs }),
    });
    if (!res.ok) throw new Error('Failed to start batch');
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

  async getProgress(id) {
    const res = await fetch(`${API_BASE}/api/experiments/${id}/progress`);
    if (!res.ok) throw new Error('Failed to fetch progress');
    return res.json();
  },

  async updateNotes(id, notes) {
    const res = await fetch(`${API_BASE}/api/experiments/${id}/notes`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    });
    if (!res.ok) throw new Error('Failed to update notes');
    return res.json();
  },

  async updateTags(id, tags) {
    const res = await fetch(`${API_BASE}/api/experiments/${id}/tags`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tags }),
    });
    if (!res.ok) throw new Error('Failed to update tags');
    return res.json();
  },

  async deleteExperiment(id) {
    const res = await fetch(`${API_BASE}/api/experiments/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete experiment');
    return res.json();
  },

  async compareExperiments(experimentIds) {
    const res = await fetch(`${API_BASE}/api/experiments/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ experiment_ids: experimentIds }),
    });
    if (!res.ok) throw new Error('Failed to compare experiments');
    return res.json();
  },

  async exportExperiments(ids = null) {
    const query = ids && ids.length > 0 ? `?ids=${ids.join(',')}` : '';
    const res = await fetch(`${API_BASE}/api/experiments/export${query}`);
    if (!res.ok) throw new Error('Failed to export experiments');
    return res.json();
  },

  async importExperiments(data, skipExisting = true) {
    const res = await fetch(`${API_BASE}/api/experiments/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data, skip_existing: skipExisting }),
    });
    if (!res.ok) throw new Error('Failed to import experiments');
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
