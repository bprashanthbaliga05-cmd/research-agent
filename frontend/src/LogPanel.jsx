export default function LogPanel({ logs }) {
    return (
      <div style={{ width: 280, borderLeft: '1px solid #222', background: '#111', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '10px 14px', borderBottom: '1px solid #222', fontSize: 12, color: '#666', fontWeight: 500 }}>
          EXECUTION LOG
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: 10, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {logs.length === 0 && (
            <p style={{ fontSize: 12, color: '#444', textAlign: 'center', marginTop: 20 }}>Run the agent to see logs</p>
          )}
          {logs.map((l, i) => (
            <div key={i} style={{ fontSize: 12, padding: '8px 10px', borderRadius: 8, background: '#1a1a1a', border: '1px solid #2a2a2a' }}>
              <span style={{ color: '#3B8BD4', fontWeight: 600, display: 'block', marginBottom: 2 }}>{l.node}</span>
              <span style={{ color: '#aaa' }}>{l.log}</span>
              <span style={{ color: '#444', fontSize: 10, float: 'right' }}>{l.time}</span>
            </div>
          ))}
        </div>
      </div>
    )
  }