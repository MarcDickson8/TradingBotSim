import React from 'react';

const thStyle = {
  padding: '8px 10px',
  textAlign: 'left',
  color: '#888',
  fontWeight: 'normal',
  borderBottom: '1px solid #2b2b43',
  whiteSpace: 'nowrap',
};

const tdStyle = {
  padding: '7px 10px',
  borderBottom: '1px solid #1a1e2a',
  whiteSpace: 'nowrap',
};

function Leaderboard({ entries, onDelete, onClearAll }) {
  return (
    <div style={{ backgroundColor: '#1e222d', borderRadius: '8px', border: '1px solid #2b2b43', marginTop: '20px', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderBottom: '1px solid #2b2b43' }}>
        <span style={{ fontSize: '13px', color: '#ccc', fontWeight: 'bold' }}>Strategy Leaderboard</span>
        <button
          onClick={onClearAll}
          disabled={entries.length === 0}
          style={{ padding: '5px 12px', cursor: entries.length === 0 ? 'default' : 'pointer', backgroundColor: '#2b2b43', color: '#e57373', border: '1px solid #e57373', borderRadius: '4px', fontSize: '12px', opacity: entries.length === 0 ? 0.4 : 1 }}
        >
          Clear All
        </button>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', color: '#ccc' }}>
          <thead>
            <tr style={{ backgroundColor: '#161a25' }}>
              <th style={thStyle}>#</th>
              <th style={thStyle}>Strategy</th>
              <th style={thStyle}>Net Profit</th>
              <th style={thStyle}>Gross Profit</th>
              <th style={thStyle}>Fees</th>
              <th style={thStyle}>Profit/Fee</th>
              <th style={thStyle}>Trades</th>
              <th style={thStyle}>Candles</th>
              <th style={thStyle}>Date</th>
              <th style={thStyle}></th>
            </tr>
          </thead>
          <tbody>
            {entries.length === 0 ? (
              <tr>
                <td colSpan={10} style={{ ...tdStyle, textAlign: 'center', color: '#555', padding: '24px' }}>
                  No results yet. Run a backtest to populate the leaderboard.
                </td>
              </tr>
            ) : (
              entries.map((e) => {
                const netColor = e.net_profit >= 0 ? '#26a69a' : '#e57373';
                const date = e.timestamp ? e.timestamp.slice(0, 10) : '—';
                return (
                  <tr key={e.id} style={{ backgroundColor: e.rank % 2 === 0 ? '#181c27' : 'transparent' }}>
                    <td style={{ ...tdStyle, color: '#555' }}>{e.rank}</td>
                    <td style={{ ...tdStyle, color: '#ddd', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{e.name}</td>
                    <td style={{ ...tdStyle, color: netColor }}>${e.net_profit?.toFixed(2)}</td>
                    <td style={{ ...tdStyle, color: '#aaa' }}>${e.total_profit?.toFixed(2)}</td>
                    <td style={{ ...tdStyle, color: '#e57373' }}>-${e.total_fees?.toFixed(2)}</td>
                    <td style={{ ...tdStyle, color: '#aaa' }}>{e.score?.toFixed(2)}</td>
                    <td style={{ ...tdStyle, color: '#aaa' }}>{e.trade_count}</td>
                    <td style={{ ...tdStyle, color: '#aaa' }}>{e.actual_candles?.toLocaleString()}</td>
                    <td style={{ ...tdStyle, color: '#555' }}>{date}</td>
                    <td style={tdStyle}>
                      <button
                        onClick={() => onDelete(e.id)}
                        title="Remove entry"
                        style={{ background: 'none', border: 'none', color: '#555', cursor: 'pointer', fontSize: '14px', padding: '0 4px', lineHeight: 1 }}
                        onMouseEnter={ev => ev.target.style.color = '#e57373'}
                        onMouseLeave={ev => ev.target.style.color = '#555'}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Leaderboard;
