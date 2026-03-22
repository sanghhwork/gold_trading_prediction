import { useState, useEffect, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import {
  fetchGoldPrices, fetchLatestPrice, fetchGoldSummary,
  fetchAllPredictions, fetchAdvice,
} from './api';
import './App.css';

function App() {
  const [prices, setPrices] = useState([]);
  const [latest, setLatest] = useState(null);
  const [summary, setSummary] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const [advice, setAdvice] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('7d');

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [priceData, latestData, summaryData] = await Promise.all([
        fetchGoldPrices('xau_usd', 365),
        fetchLatestPrice('xau_usd'),
        fetchGoldSummary(),
      ]);
      setPrices(priceData.data || []);
      setLatest(latestData);
      setSummary(summaryData);
    } catch (e) {
      setError('Khong the tai du lieu. Hay chay backend truoc (uvicorn).');
      console.error(e);
    }
    setLoading(false);
  }, []);

  const loadPredictions = useCallback(async () => {
    try {
      const [predData, adviceData] = await Promise.all([
        fetchAllPredictions(),
        fetchAdvice(activeTab),
      ]);
      setPredictions(predData);
      setAdvice(adviceData);
    } catch (e) {
      console.error('Prediction error:', e);
    }
  }, [activeTab]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="app">
        <Header />
        <main className="main">
          <div className="loading">
            <div className="spinner" />
            <p>Dang tai du lieu...</p>
          </div>
        </main>
      </div>
    );
  }

  if (error) {
    return (
      <div className="app">
        <Header />
        <main className="main">
          <div className="error-msg">{error}</div>
          <div style={{ textAlign: 'center', marginTop: '1rem' }}>
            <button className="btn btn-gold" onClick={loadData}>Thu lai</button>
          </div>
        </main>
      </div>
    );
  }

  const priceChange = prices.length >= 2
    ? ((prices[prices.length - 1]?.close - prices[prices.length - 2]?.close) / prices[prices.length - 2]?.close * 100)
    : 0;

  return (
    <div className="app">
      <Header />
      <main className="main">
        {/* Overview Stats */}
        <div className="overview-grid">
          <StatCard
            label="Gia Vang XAU/USD"
            value={latest ? `$${Number(latest.close).toLocaleString()}` : '--'}
            change={priceChange}
            type="gold"
          />
          <StatCard
            label="Gia cao nhat (1Y)"
            value={latest ? `$${Math.max(...prices.map(p => p.high || 0)).toLocaleString()}` : '--'}
            type="green"
          />
          <StatCard
            label="Gia thap nhat (1Y)"
            value={latest ? `$${Math.min(...prices.filter(p => p.low > 0).map(p => p.low)).toLocaleString()}` : '--'}
            type="red"
          />
          <StatCard
            label="Du lieu trong DB"
            value={summary ? `${summary.xau_usd_records?.toLocaleString()} rows` : '--'}
            type="blue"
          />
        </div>

        {/* Price Chart */}
        <div className="chart-section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">📈 Bieu do gia vang XAU/USD (1 nam)</span>
              <button className="btn btn-outline" onClick={loadData}>Lam moi</button>
            </div>
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={prices} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a3a4f" />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(d) => new Date(d).toLocaleDateString('vi', { month: 'short', day: 'numeric' })}
                    interval={Math.floor(prices.length / 8)}
                  />
                  <YAxis
                    stroke="#64748b"
                    tick={{ fontSize: 11 }}
                    tickFormatter={(v) => `$${v.toLocaleString()}`}
                    domain={['auto', 'auto']}
                  />
                  <Tooltip
                    contentStyle={{ background: '#1a2332', border: '1px solid #2a3a4f', borderRadius: '12px', color: '#f0f4f8' }}
                    formatter={(value) => [`$${Number(value).toLocaleString()}`, 'Close']}
                    labelFormatter={(d) => new Date(d).toLocaleDateString('vi', { day: 'numeric', month: 'long', year: 'numeric' })}
                  />
                  <Area type="monotone" dataKey="close" stroke="#fbbf24" strokeWidth={2} fill="url(#goldGradient)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">🔮 Du doan</span>
              <button className="btn btn-gold" onClick={loadPredictions}>
                {predictions ? 'Cap nhat' : 'Tai du doan'}
              </button>
            </div>
            {predictions ? (
              <PredictionPanel predictions={predictions} />
            ) : (
              <div className="loading">
                <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                  Bam "Tai du doan" de chay ML models<br />
                  (lan dau mat ~30 giay de train)
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Advisor Section */}
        {advice && (
          <div className="advisor-section">
            <div className="card">
              <div className="card-header">
                <span className="card-title">💡 Loi khuyen dau tu</span>
                <span className="risk-badge risk-{advice.risk_level}">
                  {advice.risk_level}
                </span>
              </div>
              <AdvisorPanel advice={advice} />
            </div>
            <div className="card">
              <div className="card-header">
                <span className="card-title">📊 Chi bao ky thuat</span>
              </div>
              <TechnicalPanel snapshot={advice.technical_snapshot} />
            </div>
          </div>
        )}

        {/* Analysis */}
        {advice?.analysis && (
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-header">
              <span className="card-title">🔍 Phan tich thi truong</span>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                Powered by: {advice.analysis.ai_provider === 'gemini' ? 'Google Gemini AI' : 'Rule-based Engine'}
              </span>
            </div>
            <div className="analysis-text">{advice.analysis.analysis_text}</div>
          </div>
        )}
      </main>
    </div>
  );
}

function Header() {
  return (
    <header className="header">
      <div className="header-title">
        <span className="emoji">🥇</span>
        <h1>Gold Predictor</h1>
      </div>
      <div className="header-status">
        <div className="status-dot" />
        <span>System Online</span>
      </div>
    </header>
  );
}

function StatCard({ label, value, change, type = 'gold' }) {
  return (
    <div className={`stat-card ${type}`}>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${type}`}>{value}</div>
      {change !== undefined && (
        <div className={`stat-change ${change >= 0 ? 'up' : 'down'}`}>
          {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
        </div>
      )}
    </div>
  );
}

function PredictionPanel({ predictions }) {
  const items = predictions?.predictions || {};
  const trendMap = { 0: 'GIAM', 1: 'SIDEWAY', 2: 'TANG' };
  const trendClass = { 0: 'trend-giam', 1: 'trend-sideway', 2: 'trend-tang' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {Object.entries(items).map(([horizon, pred]) => (
        <div key={horizon} style={{
          padding: '0.75rem',
          background: '#0a0e17',
          borderRadius: '12px',
          border: '1px solid #2a3a4f',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#64748b', fontSize: '0.8rem', textTransform: 'uppercase' }}>{horizon}</span>
            {pred.trend_label && (
              <span className={`prediction-trend ${trendClass[pred.predicted_trend] || 'trend-sideway'}`}>
                {pred.trend_label}
              </span>
            )}
          </div>
          {pred.predicted_price && (
            <div className="prediction-price" style={{ fontSize: '1.2rem', marginTop: '0.25rem' }}>
              ${Number(pred.predicted_price).toLocaleString()}
            </div>
          )}
          {pred.error && <div style={{ color: '#ef4444', fontSize: '0.8rem' }}>{pred.error}</div>}
        </div>
      ))}
    </div>
  );
}

function AdvisorPanel({ advice }) {
  const recClass = advice.recommendation?.includes('BUY') ? 'rec-buy'
    : advice.recommendation?.includes('SELL') ? 'rec-sell'
    : 'rec-hold';

  const recEmoji = advice.recommendation?.includes('BUY') ? '📈'
    : advice.recommendation?.includes('SELL') ? '📉'
    : '⏸️';

  const confLevel = advice.confidence >= 0.6 ? 'high' : advice.confidence >= 0.3 ? 'medium' : 'low';

  return (
    <div>
      <div className={`recommendation-badge ${recClass}`}>
        <span>{recEmoji}</span>
        <span>{advice.recommendation}</span>
      </div>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
          <span className="tech-label">Do tin cay</span>
          <span style={{ fontWeight: 600 }}>{(advice.confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="confidence-bar">
          <div className={`confidence-fill ${confLevel}`} style={{ width: `${advice.confidence * 100}%` }} />
        </div>
      </div>
      <div className="analysis-text" style={{ fontSize: '0.85rem', lineHeight: '1.7' }}>
        {advice.summary}
      </div>
    </div>
  );
}

function TechnicalPanel({ snapshot }) {
  if (!snapshot) return null;

  const items = [
    { label: 'RSI (14)', value: snapshot.rsi?.toFixed(1), color: snapshot.rsi > 70 ? '#ef4444' : snapshot.rsi < 30 ? '#22c55e' : '#f0f4f8' },
    { label: 'MACD', value: snapshot.macd?.toFixed(2), color: snapshot.macd > snapshot.macd_signal ? '#22c55e' : '#ef4444' },
    { label: 'BB Position', value: `${(snapshot.bb_position * 100).toFixed(0)}%`, color: '#f0f4f8' },
    { label: 'ATR %', value: `${snapshot.atr_pct?.toFixed(2)}%`, color: snapshot.atr_pct > 3 ? '#ef4444' : '#f0f4f8' },
    { label: 'SMA 50/200', value: snapshot.sma_50_above_200 ? 'Golden Cross' : 'Death Cross', color: snapshot.sma_50_above_200 ? '#22c55e' : '#ef4444' },
    { label: 'vs SMA 200', value: `${snapshot.price_to_sma_200?.toFixed(1)}%`, color: snapshot.price_to_sma_200 > 10 ? '#fbbf24' : '#f0f4f8' },
  ];

  return (
    <div className="tech-grid">
      {items.map((item, i) => (
        <div key={i} className="tech-item">
          <span className="tech-label">{item.label}</span>
          <span className="tech-value" style={{ color: item.color }}>{item.value}</span>
        </div>
      ))}
    </div>
  );
}

export default App;
