import { useState, useEffect, useCallback } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, Cell,
} from 'recharts';
import {
  fetchGoldPrices, fetchLatestPrice, fetchGoldSummary,
  fetchAllPredictions, fetchAdvice, fetchVNGold, fetchVNPredict,
  fetchExplanation, fetchFearGreed, fetchSentiment, fetchModelCompare,
} from './api';
import './App.css';

function App() {
  const [prices, setPrices] = useState([]);
  const [latest, setLatest] = useState(null);
  const [summary, setSummary] = useState(null);
  const [predictions, setPredictions] = useState(null);
  const [advice, setAdvice] = useState(null);
  const [vnGold, setVnGold] = useState(null);
  const [vnPredict, setVnPredict] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [fearGreed, setFearGreed] = useState(null);
  const [sentiment, setSentiment] = useState(null);
  const [modelCompare, setModelCompare] = useState(null);
  const [loading, setLoading] = useState(true);
  const [predLoading, setPredLoading] = useState(false);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [priceData, latestData, summaryData, vnData, fgData] = await Promise.all([
        fetchGoldPrices('xau_usd', 365).catch(() => ({ data: [] })),
        fetchLatestPrice('xau_usd').catch(() => null),
        fetchGoldSummary().catch(() => null),
        fetchVNGold().catch(() => null),
        fetchFearGreed(30).catch(() => null),
      ]);
      setPrices(priceData.data || []);
      setLatest(latestData);
      setSummary(summaryData);
      setVnGold(vnData);
      setFearGreed(fgData);
    } catch (e) {
      setError('Không thể tải dữ liệu. Hãy đảm bảo backend đang chạy.');
      console.error(e);
    }
    setLoading(false);
  }, []);

  const loadPredictions = useCallback(async () => {
    setPredLoading(true);
    try {
      const [predData, adviceData, vnPredData, explainData, sentData, compareData] = await Promise.all([
        fetchAllPredictions(),
        fetchAdvice('7d'),
        fetchVNPredict('7d').catch(() => null),
        fetchExplanation('7d').catch(() => null),
        fetchSentiment(7).catch(() => null),
        fetchModelCompare('7d').catch(() => null),
      ]);
      setPredictions(predData);
      setAdvice(adviceData);
      setVnPredict(vnPredData);
      setExplanation(explainData);
      setSentiment(sentData);
      setModelCompare(compareData);
    } catch (e) {
      console.error('Prediction error:', e);
    }
    setPredLoading(false);
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) return <LoadingScreen />;
  if (error) return <ErrorScreen error={error} onRetry={loadData} />;

  const priceChange = prices.length >= 2
    ? ((prices[prices.length - 1]?.close - prices[prices.length - 2]?.close) / prices[prices.length - 2]?.close * 100)
    : 0;

  return (
    <div className="app">
      <Header />
      <main className="main">
        {/* ===== Overview Stats ===== */}
        <div className="overview-grid">
          <StatCard
            label="XAU/USD"
            value={latest ? `$${Number(latest.close).toLocaleString()}` : '--'}
            change={priceChange}
            type="gold"
          />
          <StatCard
            label="SJC Bán"
            value={vnGold?.sjc_actual ? `${(vnGold.sjc_actual.sell / 1e6).toFixed(1)}M` : '--'}
            subtitle={vnGold?.sjc_actual ? `Mua: ${(vnGold.sjc_actual.buy / 1e6).toFixed(1)}M` : ''}
            type="green"
          />
          <StatCard
            label="Premium SJC"
            value={vnGold?.premium_analysis ? `${vnGold.premium_analysis.premium_pct}%` : '--'}
            subtitle={vnGold?.premium_analysis ? `${(vnGold.premium_analysis.actual_premium / 1e6).toFixed(1)}M VND` : ''}
            type={vnGold?.premium_analysis?.premium_pct > 10 ? 'red' : 'blue'}
          />
          <StatCard
            label="Dữ liệu trong DB"
            value={summary ? `${summary.xau_usd_records?.toLocaleString()}` : '--'}
            subtitle={`SJC: ${summary?.sjc_records || 0} | Macro: ${summary?.macro_records || 0}`}
            type="blue"
          />
        </div>

        {/* ===== Price Chart + Predictions ===== */}
        <div className="chart-section">
          <div className="card">
            <div className="card-header">
              <span className="card-title">📈 Biểu đồ giá vàng XAU/USD (1 năm)</span>
              <button className="btn btn-outline" onClick={loadData}>Làm mới</button>
            </div>
            <div className="chart-container">
              <PriceChart data={prices} />
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">🔮 Dự đoán</span>
              <button className="btn btn-gold" onClick={loadPredictions} disabled={predLoading}>
                {predLoading ? 'Đang chạy...' : predictions ? 'Cập nhật' : 'Chạy dự đoán'}
              </button>
            </div>
            {predLoading ? (
              <div className="loading"><div className="spinner" /><p>Đang huấn luyện ML models...</p></div>
            ) : predictions ? (
              <PredictionPanel predictions={predictions} />
            ) : (
              <div className="loading">
                <p style={{ color: '#94a3b8', fontSize: '0.9rem', textAlign: 'center' }}>
                   Bấm "Chạy dự đoán" để khởi chạy ML models<br />
                   (lần đầu mất ~30 giây)
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ===== VN Gold Section ===== */}
        {(vnGold || vnPredict) && (
          <>
            <div className="section-title">🇻🇳 Vàng Việt Nam (SJC)</div>
            <div className="vn-gold-section">
              <div className="card">
                <div className="card-header">
                  <span className="card-title">💰 Phân tích Premium SJC</span>
                </div>
                <PremiumPanel vnGold={vnGold} />
              </div>
              <div className="card">
                <div className="card-header">
                  <span className="card-title">🔮 Dự đoán giá SJC</span>
                </div>
                {vnPredict ? (
                  <VNPredictPanel data={vnPredict} />
                ) : (
                  <div className="loading" style={{ minHeight: 120 }}>
                    <p style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Bấm "Chạy dự đoán" ở trên</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* ===== SHAP Explanation ===== */}
        {explanation?.price_explanation?.drivers?.length > 0 && (
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-header">
              <span className="card-title">🧠 Tại sao model dự đoán như vậy? (SHAP)</span>
            </div>
            <SHAPPanel explanation={explanation.price_explanation} />
          </div>
        )}

        {/* ===== Advisor Section ===== */}
        {advice && (
          <div className="advisor-section">
            <div className="card">
              <div className="card-header">
                <span className="card-title">💡 Lời khuyên đầu tư</span>
                <span className={`risk-badge risk-${advice.risk_level}`}>{advice.risk_level}</span>
              </div>
              <AdvisorPanel advice={advice} />
            </div>
            <div className="card">
              <div className="card-header">
                <span className="card-title">📊 Chỉ báo kỹ thuật</span>
              </div>
              <TechnicalPanel snapshot={advice.technical_snapshot} />
            </div>
          </div>
        )}

        {/* ===== Analysis ===== */}
        {advice?.analysis && (
          <div className="card" style={{ marginBottom: '1.5rem' }}>
            <div className="card-header">
              <span className="card-title">🔍 Phân tích thị trường</span>
              <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                Powered by: {advice.analysis.ai_provider === 'gemini' ? 'Google Gemini AI' : 'Rule-based Engine'}
              </span>
            </div>
            <div className="analysis-text">{advice.analysis.analysis_text}</div>
          </div>
        )}

        {/* ===== V2: Market Sentiment Section ===== */}
        {(fearGreed || sentiment || modelCompare) && (
          <>
            <div className="section-title">📊 Bảng điều khiển V2</div>
            <div className="v2-grid">
              {fearGreed && <FearGreedPanel data={fearGreed} />}
              {sentiment && <SentimentPanel data={sentiment} />}
              {modelCompare && <ModelComparePanel data={modelCompare} />}
            </div>
          </>
        )}
      </main>
    </div>
  );
}

/* ==========================================
   COMPONENTS
   ========================================== */

function Header() {
  return (
    <header className="header">
      <div className="header-title">
        <span className="emoji">🥇</span>
        <h1>Gold Predictor</h1>
      </div>
      <div className="header-status">
        <div className="status-dot" />
        <span>Hệ thống hoạt động</span>
      </div>
    </header>
  );
}

function LoadingScreen() {
  return (
    <div className="app"><Header /><main className="main">
      <div className="loading"><div className="spinner" /><p>Đang tải dữ liệu...</p></div>
    </main></div>
  );
}

function ErrorScreen({ error, onRetry }) {
  return (
    <div className="app"><Header /><main className="main">
      <div className="error-msg">{error}</div>
      <div style={{ textAlign: 'center', marginTop: '1rem' }}>
        <button className="btn btn-gold" onClick={onRetry}>Thử lại</button>
      </div>
    </main></div>
  );
}

function StatCard({ label, value, change, subtitle, type = 'gold' }) {
  return (
    <div className={`stat-card ${type}`}>
      <div className="stat-label">{label}</div>
      <div className={`stat-value ${type}`}>{value}</div>
      {change !== undefined && (
        <div className={`stat-change ${change >= 0 ? 'up' : 'down'}`}>
          {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
        </div>
      )}
      {subtitle && <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginTop: '0.25rem' }}>{subtitle}</div>}
    </div>
  );
}

function PriceChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="goldGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#2a3a4f" />
        <XAxis dataKey="date" stroke="#64748b" tick={{ fontSize: 11 }}
          tickFormatter={(d) => new Date(d).toLocaleDateString('vi', { month: 'short', day: 'numeric' })}
          interval={Math.floor(data.length / 8)} />
        <YAxis stroke="#64748b" tick={{ fontSize: 11 }}
          tickFormatter={(v) => `$${v.toLocaleString()}`} domain={['auto', 'auto']} />
        <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid #2a3a4f', borderRadius: 12, color: '#f0f4f8' }}
          formatter={(v) => [`$${Number(v).toLocaleString()}`, 'Close']}
          labelFormatter={(d) => new Date(d).toLocaleDateString('vi', { day: 'numeric', month: 'long', year: 'numeric' })} />
        <Area type="monotone" dataKey="close" stroke="#fbbf24" strokeWidth={2} fill="url(#goldGradient)" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function PredictionPanel({ predictions }) {
  const items = predictions?.predictions || {};
  const trendClass = { 0: 'trend-giam', 1: 'trend-sideway', 2: 'trend-tang' };
  const trendEmoji = { 0: '📉', 1: '⏸️', 2: '📈' };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {Object.entries(items).map(([horizon, pred]) => (
        <div key={horizon} style={{
          padding: '0.75rem', background: '#0a0e17', borderRadius: 12, border: '1px solid #2a3a4f',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: '#64748b', fontSize: '0.8rem', textTransform: 'uppercase', fontWeight: 600 }}>{horizon}</span>
            {pred.trend_label && (
              <span className={`prediction-trend ${trendClass[pred.predicted_trend] || 'trend-sideway'}`}>
                {trendEmoji[pred.predicted_trend] || ''} {pred.trend_label}
              </span>
            )}
          </div>
          {pred.predicted_price && (
            <div className="prediction-price" style={{ fontSize: '1.2rem', marginTop: '0.25rem' }}>
              ${Number(pred.predicted_price).toLocaleString()}
            </div>
          )}
          {pred.trend_probabilities && (
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
              {Object.entries(pred.trend_probabilities).map(([k, v]) => (
                <span key={k} style={{ fontSize: '0.7rem', color: '#64748b' }}>
                  {k === 'giam' ? '📉' : k === 'tang' ? '📈' : '⏸️'} {(v * 100).toFixed(0)}%
                </span>
              ))}
            </div>
          )}
          {pred.error && <div style={{ color: '#ef4444', fontSize: '0.8rem' }}>{pred.error}</div>}
        </div>
      ))}
    </div>
  );
}

function PremiumPanel({ vnGold }) {
  if (!vnGold) return <div className="loading" style={{ minHeight: 120 }}><p style={{ color: '#94a3b8' }}>Không có dữ liệu SJC</p></div>;

  const xau = vnGold.xau_usd || {};
  const conv = vnGold.sjc_converted || {};
  const actual = vnGold.sjc_actual || {};
  const prem = vnGold.premium_analysis || {};
  const isHighPremium = prem.premium_pct > 10;

  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
        <div style={{ padding: '0.75rem', background: '#0a0e17', borderRadius: 12, border: '1px solid #2a3a4f' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>Giá thế giới quy đổi</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#94a3b8' }}>
            {conv.world_price_vnd ? `${(conv.world_price_vnd / 1e6).toFixed(1)}M` : '--'}
          </div>
        </div>
        <div style={{ padding: '0.75rem', background: '#0a0e17', borderRadius: 12, border: '1px solid #2a3a4f' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>SJC thực tế (Bán)</div>
          <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fbbf24' }}>
            {actual.sell ? `${(actual.sell / 1e6).toFixed(1)}M` : '--'}
          </div>
        </div>
      </div>

      {prem.actual_premium && (
        <div style={{
          padding: '0.75rem', borderRadius: 12,
          background: isHighPremium ? 'rgba(239,68,68,0.08)' : 'rgba(34,197,94,0.08)',
          border: `1px solid ${isHighPremium ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)'}`,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>Premium SJC</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: isHighPremium ? '#ef4444' : '#22c55e' }}>
            {(prem.actual_premium / 1e6).toFixed(1)}M VND ({prem.premium_pct}%)
          </div>
          {isHighPremium && (
            <div style={{ fontSize: '0.75rem', color: '#ef4444', marginTop: '0.25rem' }}>
              ⚠️ Premium cao bất thường (bình thường 3-8%)
            </div>
          )}
        </div>
      )}

      {conv.formula && (
        <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.75rem', fontFamily: 'monospace' }}>
          {conv.formula}
        </div>
      )}
    </div>
  );
}

function VNPredictPanel({ data }) {
  if (!data) return null;
  const sjc = data.sjc || {};
  const xau = data.xau_usd || {};

  return (
    <div>
      <div style={{ marginBottom: '0.75rem' }}>
        <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.25rem' }}>
          Dự đoán {data.horizon} - XAU/USD: ${xau.predicted_price?.toLocaleString()} ({xau.predicted_trend})
        </div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
        <div style={{ padding: '0.75rem', background: '#0a0e17', borderRadius: 12, border: '1px solid #2a3a4f', textAlign: 'center' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>SJC Mua (dự đoán)</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#22c55e' }}>
            {sjc.buy_predicted ? `${(sjc.buy_predicted / 1e6).toFixed(1)}M` : '--'}
          </div>
        </div>
        <div style={{ padding: '0.75rem', background: '#0a0e17', borderRadius: 12, border: '1px solid #2a3a4f', textAlign: 'center' }}>
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>SJC Bán (dự đoán)</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#fbbf24' }}>
            {sjc.sell_predicted ? `${(sjc.sell_predicted / 1e6).toFixed(1)}M` : '--'}
          </div>
        </div>
      </div>
      {sjc.formula && (
        <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.5rem', fontFamily: 'monospace' }}>
          {sjc.formula}
        </div>
      )}
    </div>
  );
}

function SHAPPanel({ explanation }) {
  const drivers = explanation?.drivers || [];
  if (drivers.length === 0) return null;

  const chartData = drivers.map((d) => ({
    name: d.display_name,
    value: d.shap_value,
    fill: d.direction === 'tang' ? '#22c55e' : '#ef4444',
  }));

  return (
    <div>
      <div style={{ height: 260, marginBottom: '1rem' }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} layout="vertical" margin={{ top: 5, right: 20, left: 120, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a3a4f" horizontal={false} />
            <XAxis type="number" stroke="#64748b" tick={{ fontSize: 10 }} />
            <YAxis type="category" dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} width={110} />
            <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid #2a3a4f', borderRadius: 8, color: '#f0f4f8' }}
              formatter={(v) => [v.toFixed(4), 'SHAP']} />
            <Bar dataKey="value" radius={[0, 4, 4, 0]}>
              {chartData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
        {drivers.map((d, i) => (
          <div key={i} style={{
            padding: '0.5rem', background: '#0a0e17', borderRadius: 8,
            border: `1px solid ${d.direction === 'tang' ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f0f4f8' }}>
                {d.direction === 'tang' ? '📈' : '📉'} {d.display_name}
              </span>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: d.direction === 'tang' ? '#22c55e' : '#ef4444' }}>
                {d.impact}
              </span>
            </div>
            {d.context && (
              <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.25rem' }}>{d.context}</div>
            )}
          </div>
        ))}
      </div>

      {explanation.summary && (
        <div className="analysis-text" style={{ marginTop: '0.75rem', fontSize: '0.8rem' }}>
          {explanation.summary}
        </div>
      )}
    </div>
  );
}

function AdvisorPanel({ advice }) {
  const recClass = advice.recommendation?.includes('BUY') ? 'rec-buy'
    : advice.recommendation?.includes('SELL') ? 'rec-sell' : 'rec-hold';
  const recEmoji = advice.recommendation?.includes('BUY') ? '📈'
    : advice.recommendation?.includes('SELL') ? '📉' : '⏸️';
  const confLevel = advice.confidence >= 0.6 ? 'high' : advice.confidence >= 0.3 ? 'medium' : 'low';

  return (
    <div>
      <div className={`recommendation-badge ${recClass}`}>
        <span>{recEmoji}</span><span>{advice.recommendation}</span>
      </div>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
          <span className="tech-label">Độ tin cậy</span>
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

/* ==========================================
   V2 COMPONENTS
   ========================================== */

function FearGreedPanel({ data }) {
  const val = data?.latest?.value || 0;
  const cls = data?.classification || 'N/A';

  const gaugeColor = val <= 25 ? '#ef4444' : val <= 40 ? '#f97316' : val <= 60 ? '#eab308' : val <= 75 ? '#84cc16' : '#22c55e';
  const gaugeWidth = `${val}%`;

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">😱 Fear & Greed Index</span>
      </div>
      <div style={{ padding: '1rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color: gaugeColor }}>{val}</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 600, color: gaugeColor }}>{cls}</div>
        </div>
        <div style={{ background: '#1a2332', borderRadius: 8, height: 12, overflow: 'hidden' }}>
          <div style={{
            width: gaugeWidth,
            height: '100%',
            borderRadius: 8,
            background: `linear-gradient(90deg, #ef4444, #f97316, #eab308, #84cc16, #22c55e)`,
            transition: 'width 0.6s ease',
          }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: '#64748b', marginTop: '0.25rem' }}>
          <span>Extreme Fear</span><span>Extreme Greed</span>
        </div>
        {data?.history?.length > 0 && (
          <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: '#94a3b8' }}>
            7d avg: {(data.history.slice(0, 7).reduce((s, h) => s + h.value, 0) / Math.min(data.history.length, 7)).toFixed(0)}
            {' | '}
            30d avg: {(data.history.reduce((s, h) => s + h.value, 0) / data.history.length).toFixed(0)}
          </div>
        )}
      </div>
    </div>
  );
}

function SentimentPanel({ data }) {
  const score = data?.avg_score || 0;
  const overall = data?.overall_sentiment || 'N/A';
  const sentColor = score > 0.1 ? '#22c55e' : score < -0.1 ? '#ef4444' : '#eab308';
  const sentEmoji = score > 0.1 ? '📈' : score < -0.1 ? '📉' : '⏸️';

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">📰 News Sentiment</span>
      </div>
      <div style={{ padding: '1rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '1rem' }}>
          <div style={{ fontSize: '1.5rem' }}>{sentEmoji}</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: sentColor }}>{overall}</div>
          <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>Score: {score.toFixed(4)}</div>
        </div>
        {data?.daily && Object.keys(data.daily).length > 0 && (
          <div style={{ fontSize: '0.75rem' }}>
            {Object.entries(data.daily).slice(0, 5).map(([date, info]) => (
              <div key={date} style={{
                display: 'flex', justifyContent: 'space-between',
                padding: '0.25rem 0', borderBottom: '1px solid #1a2332',
              }}>
                <span style={{ color: '#64748b' }}>{date}</span>
                <span style={{
                  fontWeight: 600,
                  color: info.avg_score > 0 ? '#22c55e' : info.avg_score < 0 ? '#ef4444' : '#eab308',
                }}>
                  {info.avg_score > 0 ? '📈' : info.avg_score < 0 ? '📉' : '⏸️'} {info.avg_score.toFixed(2)} ({info.count})
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ModelComparePanel({ data }) {
  const models = data?.models || [];
  const returnModels = models.filter(m => m.type === 'regression');
  const trendModels = models.filter(m => m.type === 'classification');

  return (
    <div className="card">
      <div className="card-header">
        <span className="card-title">🏆 Model Comparison ({data?.horizon})</span>
      </div>
      <div style={{ padding: '1rem' }}>
        {returnModels.length > 0 && (
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem', fontWeight: 600 }}>RETURN MODELS</div>
            {returnModels.map((m, i) => {
              const mae = m.metrics?.mae;
              const r2 = m.metrics?.r2;
              return (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '0.4rem 0.5rem', marginBottom: '0.25rem',
                  background: '#0a0e17', borderRadius: 8,
                }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f0f4f8' }}>{m.name.replace(/_/g, ' ')}</span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {mae !== undefined && `MAE: ${mae.toFixed(2)}%`}
                    {r2 !== undefined && ` | R²: ${r2.toFixed(3)}`}
                  </span>
                </div>
              );
            })}
          </div>
        )}
        {trendModels.length > 0 && (
          <div>
            <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem', fontWeight: 600 }}>TREND MODELS</div>
            {trendModels.map((m, i) => {
              const acc = m.metrics?.accuracy;
              const f1 = m.metrics?.f1_weighted;
              return (
                <div key={i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '0.4rem 0.5rem', marginBottom: '0.25rem',
                  background: '#0a0e17', borderRadius: 8,
                }}>
                  <span style={{ fontSize: '0.8rem', fontWeight: 600, color: '#f0f4f8' }}>{m.name.replace(/_/g, ' ')}</span>
                  <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                    {acc !== undefined && `Acc: ${(acc * 100).toFixed(1)}%`}
                    {f1 !== undefined && ` | F1: ${f1.toFixed(3)}`}
                  </span>
                </div>
              );
            })}
          </div>
        )}
        <div style={{ fontSize: '0.7rem', color: '#64748b', marginTop: '0.75rem', textAlign: 'center' }}>
          Total: {models.length} models
        </div>
      </div>
    </div>
  );
}

export default App;
