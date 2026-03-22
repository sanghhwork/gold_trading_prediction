const API_BASE = 'http://127.0.0.1:8001/api/v1';

export async function fetchGoldPrices(source = 'xau_usd', days = 90) {
  const res = await fetch(`${API_BASE}/gold/prices?source=${source}&days=${days}`);
  if (!res.ok) throw new Error('Failed to fetch gold prices');
  return res.json();
}

export async function fetchLatestPrice(source = 'xau_usd') {
  const res = await fetch(`${API_BASE}/gold/latest?source=${source}`);
  if (!res.ok) throw new Error('Failed to fetch latest price');
  return res.json();
}

export async function fetchGoldSummary() {
  const res = await fetch(`${API_BASE}/gold/summary`);
  if (!res.ok) throw new Error('Failed to fetch summary');
  return res.json();
}

export async function fetchPrediction(horizon = '7d') {
  const res = await fetch(`${API_BASE}/predictions/${horizon}`);
  if (!res.ok) throw new Error('Failed to fetch prediction');
  return res.json();
}

export async function fetchAllPredictions() {
  const res = await fetch(`${API_BASE}/predictions`);
  if (!res.ok) throw new Error('Failed to fetch predictions');
  return res.json();
}

export async function fetchAnalysis() {
  const res = await fetch(`${API_BASE}/analysis`);
  if (!res.ok) throw new Error('Failed to fetch analysis');
  return res.json();
}

export async function fetchAdvice(horizon = '7d') {
  const res = await fetch(`${API_BASE}/advisor?horizon=${horizon}`);
  if (!res.ok) throw new Error('Failed to fetch advice');
  return res.json();
}

export async function triggerTraining(horizon = '7d') {
  const res = await fetch(`${API_BASE}/train`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ horizon, source: 'xau_usd' }),
  });
  if (!res.ok) throw new Error('Training failed');
  return res.json();
}

export async function triggerDataCollection() {
  const res = await fetch(`${API_BASE}/collect-data`, { method: 'POST' });
  if (!res.ok) throw new Error('Data collection failed');
  return res.json();
}
