import React, { useState, useEffect } from 'react';
import TradingChart from './components/TradingChart';
import ProfitChart from './components/ProfitChart';
import Leaderboard from './components/Leaderboard';

function App() {
  const [chartData, setChartData] = useState([]);
  // const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState(1);
  const [activeTradeSpeed, setActiveTradeSpeed] = useState(1);
  const [generalSpeed, setGeneralSpeed] = useState(1);
  const [candles, setCandles] = useState(20000);
  const [bbPeriod, setBbPeriod] = useState(20);
  const [longsEnabled, setLongsEnabled] = useState(true);
  const [shortsEnabled, setShortsEnabled] = useState(false);
  const [trendEnabled, setTrendEnabled] = useState(false);
  const [granularity, setGranularity] = useState('M5');
  const [rsiPeriod, setRsiPeriod] = useState(14);
  const [bbStd, setBbStd] = useState(2);
  const [rvolThreshold, setRvolThreshold] = useState(1.5);
  const [atrChopEnabled, setAtrChopEnabled] = useState(false);
  const [reinvestEnabled, setReinvestEnabled] = useState(false);
  const [initialCapital, setInitialCapital] = useState(10000);
  const [leverage, setLeverage] = useState(1);
  const [tradingStartTime, setTradingStartTime] = useState('05:00');
  const [tradingEndTime, setTradingEndTime] = useState('17:00');
  const [slMultiplier, setSlMultiplier] = useState(1.0);
  const oneYearAgo = new Date();
  oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1);
  const [startDate, setStartDate] = useState(oneYearAgo.toISOString().split('T')[0]);
  const [skipSignal, setSkipSignal] = useState(0);
  const [showAllSignal, setShowAllSignal] = useState(0);
  const [leaderboard, setLeaderboard] = useState([]);

  const fetchLeaderboard = async () => {
    try {
      const res = await fetch('http://localhost:8000/leaderboard');
      if (res.ok) setLeaderboard(await res.json());
    } catch (_) {}
  };

  useEffect(() => { fetchLeaderboard(); }, []);

  const deleteEntry = async (id) => {
    await fetch(`http://localhost:8000/leaderboard/${id}`, { method: 'DELETE' });
    fetchLeaderboard();
  };

  const clearLeaderboard = async () => {
    await fetch('http://localhost:8000/leaderboard', { method: 'DELETE' });
    setLeaderboard([]);
  };

  const fetchData = async () => {
    try {
      const params = new URLSearchParams({
        num_candles: candles,
        bb_period: bbPeriod,
        longs_enabled: longsEnabled,
        shorts_enabled: shortsEnabled,
        trend_enabled: trendEnabled,
        granularity: granularity,
        rsi_period: rsiPeriod,
        bb_std: bbStd,
        rvol_threshold: rvolThreshold,
        atr_chop_enabled: atrChopEnabled,
        start_date: startDate,
        reinvest_enabled: reinvestEnabled,
        initial_capital: initialCapital,
        leverage: leverage,
        trading_start_time: tradingStartTime,
        trading_end_time: tradingEndTime,
        sl_multiplier: slMultiplier,
      });
      const response = await fetch(`http://localhost:8000/backtest?${params}`);

      // Safety 1: Check if the server actually responded
      if (!response.ok) {
        console.error("Server error:", response.status);
        return;
      }

      const json = await response.json();
      console.log("Full JSON from backend:", json);

      if (json && json.chartData) {
        setChartData(json.chartData);
        if (json.actualCandles && json.actualCandles < candles) {
          setCandles(json.actualCandles);
        }
        fetchLeaderboard();
      } else {
        console.error("JSON received, but 'chartData' key is missing:", json);
      }

    } catch (err) {
      // Safety 3: This catches network errors (server down, CORS, etc.)
      console.error("Fetch failed entirely:", err);
    }
  };

  console.log("DEBUG: App is rendering. current chartData:");

  const inputStyle = { padding: '6px', width: '100px', backgroundColor: '#1e222d', color: 'white', border: '1px solid #2b2b43', borderRadius: '4px' };
  const labelStyle = { display: 'block', marginBottom: '6px', fontSize: '12px', color: '#aaa' };
  const fieldStyle = { display: 'flex', flexDirection: 'column' };

  return (
    <div style={{ backgroundColor: '#131722', minHeight: '100vh', color: 'white', padding: '20px' }}>
      <h1>Trading Algo Dashboard</h1>

      <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', marginBottom: '16px', padding: '12px', backgroundColor: '#1e222d', borderRadius: '8px', border: '1px solid #2b2b43' }}>
        <div style={fieldStyle}>
          <label style={labelStyle}>Active Trade Speed</label>
          <input type="number" min="0.1" step="0.1" value={activeTradeSpeed} onChange={(e) => setActiveTradeSpeed(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>General Speed</label>
          <input type="number" min="0.1" step="0.1" value={generalSpeed} onChange={(e) => setGeneralSpeed(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Start Date</label>
          <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Num Candles</label>
          <input type="number" min="200" step="1" value={candles} onChange={(e) => setCandles(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Granularity</label>
          <select value={granularity} onChange={(e) => setGranularity(e.target.value)} style={inputStyle}>
            <option>M1</option>
            <option>M5</option>
            <option>M15</option>
            <option>M30</option>
            <option>H1</option>
            <option>H4</option>
            <option>D</option>
          </select>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>BB Period</label>
          <input type="number" min="1" step="1" value={bbPeriod} onChange={(e) => setBbPeriod(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>BB Std</label>
          <input type="number" min="0.1" step="0.1" value={bbStd} onChange={(e) => setBbStd(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>RSI Period</label>
          <input type="number" min="1" step="1" value={rsiPeriod} onChange={(e) => setRsiPeriod(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>RVOL Threshold</label>
          <input type="number" min="0.1" step="0.1" value={rvolThreshold} onChange={(e) => setRvolThreshold(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', color: '#aaa' }}>
            <input type="checkbox" checked={longsEnabled} onChange={(e) => setLongsEnabled(e.target.checked)} style={{ width: '16px', height: '16px', cursor: 'pointer' }} />
            Longs
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', color: '#aaa' }}>
            <input type="checkbox" checked={shortsEnabled} onChange={(e) => setShortsEnabled(e.target.checked)} style={{ width: '16px', height: '16px', cursor: 'pointer' }} />
            Shorts
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', color: '#aaa' }}>
            <input type="checkbox" checked={trendEnabled} onChange={(e) => setTrendEnabled(e.target.checked)} style={{ width: '16px', height: '16px', cursor: 'pointer' }} />
            Trade on Trends
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', color: '#aaa' }}>
            <input type="checkbox" checked={atrChopEnabled} onChange={(e) => setAtrChopEnabled(e.target.checked)} style={{ width: '16px', height: '16px', cursor: 'pointer' }} />
            ATR Chop Filter
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '12px', color: '#aaa' }}>
            <input type="checkbox" checked={reinvestEnabled} onChange={(e) => setReinvestEnabled(e.target.checked)} style={{ width: '16px', height: '16px', cursor: 'pointer' }} />
            Reinvest Profits
          </label>
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Initial Capital</label>
          <input type="number" min="100" step="100" value={initialCapital} onChange={(e) => setInitialCapital(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Leverage (x)</label>
          <input type="number" min="1" step="1" value={leverage} onChange={(e) => setLeverage(Number(e.target.value))} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Trade Start (UTC)</label>
          <input type="time" value={tradingStartTime} onChange={(e) => setTradingStartTime(e.target.value)} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>Trade End (UTC)</label>
          <input type="time" value={tradingEndTime} onChange={(e) => setTradingEndTime(e.target.value)} style={inputStyle} />
        </div>

        <div style={fieldStyle}>
          <label style={labelStyle}>SL Multiplier</label>
          <input type="number" min="0.1" step="0.1" value={slMultiplier} onChange={(e) => setSlMultiplier(Number(e.target.value))} style={inputStyle} />
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <button onClick={fetchData} style={{ padding: '10px 20px', cursor: 'pointer' }}>
          Historical Data Test
        </button>
        <button onClick={() => setSkipSignal(s => s + 1)} style={{ padding: '10px 20px', cursor: 'pointer' }} disabled={!chartData.length}>
          Skip to End
        </button>
        <button onClick={() => setShowAllSignal(s => s + 1)} style={{ padding: '10px 20px', cursor: 'pointer' }} disabled={!chartData.length}>
          Show Full Timeframe
        </button>
      </div>

      <div style={{ border: '1px solid #2b2b43', borderRadius: '8px', overflow: 'hidden' }}>
        {chartData && chartData.length > 0 ? (
          <TradingChart data={chartData} activeTradeSpeed={activeTradeSpeed} generalSpeed={generalSpeed} onUpdateSummary={setSummary} skipSignal={skipSignal} showAllSignal={showAllSignal} />
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: '#888' }}>
            No data loaded. Click "Historical Data Test" to fetch.
          </div>
        )}
      </div>

      {chartData && chartData.length > 0 && (
        <div style={{ border: '1px solid #2b2b43', borderRadius: '8px', overflow: 'hidden', marginTop: '20px' }}>
          <ProfitChart data={chartData} />
        </div>
      )}
      {summary && (
        <div
          style={{
            display: 'flex',
            gap: '20px',
            marginBottom: '20px',
            padding: '12px',
            backgroundColor: '#1e222d',
            borderRadius: '8px',
            border: '1px solid #2b2b43'
          }}
        >
          <div>
            <strong>Total Profit:</strong> ${summary.total_profit}
          </div>
          <div>
            <strong>Brokerage Fees:</strong> <span style={{ color: '#e57373' }}>-${summary.total_fees ?? '0.00'}</span>
            <span style={{ fontSize: '11px', color: '#666', marginLeft: '6px' }}>(live spread from OANDA)</span>
          </div>
          <div>
            <strong>Net Profit:</strong> <span style={{ color: summary.total_profit - (summary.total_fees ?? 0) >= 0 ? '#26a69a' : '#e57373' }}>${((summary.total_profit ?? 0) - (summary.total_fees ?? 0)).toFixed(2)}</span>
          </div>
          <div>
            <strong>Trades:</strong> {summary.trade_count}
          </div>
        </div>
      )}

      <Leaderboard entries={leaderboard} onDelete={deleteEntry} onClearAll={clearLeaderboard} />
    </div>
  );
}

export default App;
