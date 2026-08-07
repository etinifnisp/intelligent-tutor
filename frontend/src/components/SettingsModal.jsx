/**
 * SettingsModal — choose an allowed OpenRouter model.
 * API key is server-side only (backend/.env).
 */
import { useEffect, useState } from 'react';
import { apiFetch } from '../utils.jsx';
import {
  FALLBACK_MODELS,
  STORAGE_KEY_MODEL,
  getSelectedModelId,
} from '../modelSettings.js';

export { STORAGE_KEY_MODEL, FALLBACK_MODELS, getSelectedModelId };
export { getSelectedModelLabel } from '../modelSettings.js';

export default function SettingsModal({ open, onClose }) {
  const [models, setModels] = useState(FALLBACK_MODELS);
  const [defaultModel, setDefaultModel] = useState(FALLBACK_MODELS[1].id);
  const [model, setModel] = useState(getSelectedModelId());
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setSaved(false);
    setError('');
    setModel(getSelectedModelId());
    setLoading(true);
    apiFetch('/tutor/models')
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not load model list');
        return response.json();
      })
      .then((data) => {
        if (Array.isArray(data.models) && data.models.length > 0) {
          setModels(data.models);
        }
        if (data.default_model) setDefaultModel(data.default_model);
        const stored = localStorage.getItem(STORAGE_KEY_MODEL);
        setModel(stored || data.default_model || FALLBACK_MODELS[1].id);
      })
      .catch((loadError) => setError(loadError.message))
      .finally(() => setLoading(false));
  }, [open]);

  if (!open) return null;

  function save() {
    localStorage.setItem(STORAGE_KEY_MODEL, model);
    localStorage.removeItem('jee_openrouter_key');
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function useDefault() {
    setModel(defaultModel);
  }

  const selected = models.find((entry) => entry.id === model);

  return (
    <div className="settings-overlay" role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div className="settings-modal">
        <div className="settings-modal-header">
          <div className="settings-modal-title-group">
            <span className="settings-modal-icon">⚙️</span>
            <div>
              <h2 id="settings-title">AI Model</h2>
              <p>Choose a free or low-cost tutor model</p>
            </div>
          </div>
          <button className="settings-modal-close" onClick={onClose} aria-label="Close settings">✕</button>
        </div>

        <div className="settings-status-banner active">
          <span className="settings-status-dot" />
          Using <strong>OpenRouter</strong>
          {selected ? <> — {selected.label}</> : null}
        </div>

        <div className="settings-modal-body">
          <section className="settings-section">
            <div className="settings-section-header">
              <div className="settings-section-icon" style={{ background: 'linear-gradient(135deg, #7c3aed, #4f46e5)' }}>OR</div>
              <div>
                <h3>Model</h3>
                <p>Only approved free and cheap models are available.</p>
              </div>
            </div>

            {error && <div className="settings-test-result fail">{error}</div>}

            <div className="settings-field">
              <label htmlFor="or-model">Tutor model</label>
              <select
                id="or-model"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="settings-select"
                disabled={loading}
              >
                {models.map((entry) => (
                  <option key={entry.id} value={entry.id}>
                    {entry.tier === 'free' ? 'Free' : 'Cheap'} · {entry.provider} — {entry.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="settings-actions">
              <button className="btn btn-ghost" onClick={useDefault} type="button" disabled={loading}>
                Use default
              </button>
              <button
                className={`btn btn-primary settings-save-btn ${saved ? 'saved' : ''}`}
                onClick={save}
                type="button"
                disabled={loading}
              >
                {saved ? '✓ Saved!' : 'Save model'}
              </button>
            </div>
          </section>

          <div className="settings-info-box">
            <strong>Hosted API key</strong>
            <p>The OpenRouter API key is configured on the server. Students can only switch between approved models.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
