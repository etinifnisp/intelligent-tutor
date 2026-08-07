export const STORAGE_KEY_MODEL = 'jee_openrouter_model';

export const FALLBACK_MODELS = [
  { id: 'openai/gpt-4o-mini', label: 'GPT-4o Mini', provider: 'OpenAI', tier: 'cheap' },
  { id: 'google/gemini-3.5-flash-lite', label: 'Gemini 3.5 Flash Lite', provider: 'Google', tier: 'cheap' },
  { id: 'google/gemma-4-31b-it:free', label: 'Gemma 4 31B IT', provider: 'Google', tier: 'free' },
  {
    id: 'nvidia/nemotron-3-super-120b-a12b:free',
    label: 'Nemotron 3 Super 120B',
    provider: 'NVIDIA',
    tier: 'free',
  },
  { id: 'qwen/qwen3.7-flash', label: 'Qwen 3.7 Flash', provider: 'Qwen', tier: 'cheap' },
];

export function getSelectedModelId() {
  return localStorage.getItem(STORAGE_KEY_MODEL) || FALLBACK_MODELS[1].id;
}

export function getSelectedModelLabel(models = FALLBACK_MODELS) {
  const current = getSelectedModelId();
  return models.find((model) => model.id === current)?.label || current;
}
