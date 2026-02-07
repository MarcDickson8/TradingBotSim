import React, { useState } from 'react';
import TradingChart from './components/TradingChart';

function App() {
  const [chartData, setChartData] = useState([]);
  const [trades, setTrades] = useState([]);
  const [summary, setSummary] = useState(null);
  
  const fetchData = async () => {
    try {
      const response = await fetch('http://localhost:8000/backtest');
      
      // Safety 1: Check if the server actually responded
      if (!response.ok) {
        console.error("Server error:", response.status);
        return;
      }

      const json = await response.json();
      console.log("Full JSON from backend:", json);

      // Safety 2: Check if 'json' exists and has the key we want
      // Change 'chartData' to 'data' if that's what your Python returns
      if (json && json.chartData) {
        setChartData(json.chartData);
        setTrades(json.trades || []);
        setSummary(json.summary || null);
      } else {
        console.error("JSON received, but 'chartData' key is missing:", json);
      }

    } catch (err) {
      // Safety 3: This catches network errors (server down, CORS, etc.)
      console.error("Fetch failed entirely:", err);
    }
  };

  console.log("DEBUG: App is rendering. current chartData:");

  return (
    <div style={{ backgroundColor: '#131722', minHeight: '100vh', color: 'white', padding: '20px' }}>
      <h1>Trading Algo Dashboard</h1>
      <button 
        onClick={fetchData} 
        style={{ padding: '10px 20px', marginBottom: '20px', cursor: 'pointer' }}
      >
        Historical Data Test
      </button>

      <div style={{ border: '1px solid #2b2b43', borderRadius: '8px', overflow: 'hidden' }}>
        {/* Only render the chart if we have data, preventing crashes on empty/undefined */}
        {chartData && chartData.length > 0 ? (
          <TradingChart data={chartData} trades={trades} />
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: '#888' }}>
            No data loaded. Click "Historical Data Test" to fetch.
          </div>
        )}
      </div>
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
            <strong>Trades:</strong> {summary.trade_count}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
