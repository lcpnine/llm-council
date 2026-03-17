import { useState } from 'react';
import { api } from '../api';

export default function PromptsTab({ promptVersions, onRefresh }) {
  const versionKeys = Object.keys(promptVersions);
  const [viewPromptVersion, setViewPromptVersion] = useState('');
  const [newPromptVersion, setNewPromptVersion] = useState('');
  const [newGenerator, setNewGenerator] = useState('');
  const [newSkeptic, setNewSkeptic] = useState('');
  const [newJudge, setNewJudge] = useState('');

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
      onRefresh();
    } catch (err) {
      console.error('Failed to save prompt:', err);
    }
  };

  return (
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
  );
}
