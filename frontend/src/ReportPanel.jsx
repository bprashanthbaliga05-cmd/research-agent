import ReactMarkdown from 'react-markdown'

export default function ReportPanel({ report, running, usage }) {
  return (
    <div style={{
      width: 340,
      borderLeft: '1px solid #222',
      background: '#0d0d0d',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden'
    }}>
      <div style={{
        padding: '10px 14px',
        borderBottom: '1px solid #222',
        fontSize: 12,
        color: '#666',
        fontWeight: 500,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <span>RESEARCH REPORT</span>
        {running && <span style={{ color: '#3B8BD4', fontSize: 11 }}>● Generating...</span>}
        {report && !running && <span style={{ color: '#3B9E6A', fontSize: 11 }}>● Complete</span>}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {!report && !running && (
          <p style={{ fontSize: 12, color: '#444', textAlign: 'center', marginTop: 40 }}>
            Report will appear here after the agent completes
          </p>
        )}
        {running && !report && (
          <p style={{ fontSize: 12, color: '#555', textAlign: 'center', marginTop: 40 }}>
            ⏳ Agent is working...
          </p>
        )}
        {report && (
          <div style={{ fontSize: 13, lineHeight: 1.7, color: '#ccc' }}>
            <ReactMarkdown
              components={{
                h1: ({ children }) => <h1 style={{ fontSize: 16, fontWeight: 600, color: '#fff', marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid #222' }}>{children}</h1>,
                h2: ({ children }) => <h2 style={{ fontSize: 14, fontWeight: 600, color: '#eee', margin: '16px 0 8px' }}>{children}</h2>,
                h3: ({ children }) => <h3 style={{ fontSize: 13, fontWeight: 600, color: '#ddd', margin: '12px 0 6px' }}>{children}</h3>,
                p:  ({ children }) => <p style={{ marginBottom: 10, color: '#aaa' }}>{children}</p>,
                li: ({ children }) => <li style={{ marginBottom: 6, color: '#aaa', marginLeft: 16 }}>{children}</li>,
                ul: ({ children }) => <ul style={{ marginBottom: 10, paddingLeft: 8 }}>{children}</ul>,
                strong: ({ children }) => <strong style={{ color: '#fff', fontWeight: 600 }}>{children}</strong>,
                code: ({ children }) => <code style={{ background: '#1a1a1a', padding: '2px 6px', borderRadius: 4, fontSize: 12, color: '#3B8BD4' }}>{children}</code>,
              }}
            >
              {report}
            </ReactMarkdown>

            <button
              onClick={() => navigator.clipboard.writeText(report)}
              style={{ marginTop: 20, width: '100%', padding: '8px', borderRadius: 8, border: '1px solid #333', background: 'transparent', color: '#666', fontSize: 12, cursor: 'pointer' }}
            >
              Copy report
            </button>
          </div>
        )}
      </div>

      {/* ─── Cost summary bar ─────────────────────────────── */}
      {usage && (
        <div style={{
          borderTop: '1px solid #222',
          padding: '10px 14px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 8
        }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: '#555', marginBottom: 2 }}>TOKENS</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>
              {usage.total_tokens.toLocaleString()}
            </div>
          </div>
          <div style={{ textAlign: 'center', borderLeft: '1px solid #222', borderRight: '1px solid #222' }}>
            <div style={{ fontSize: 10, color: '#555', marginBottom: 2 }}>COST</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#3B9E6A' }}>
              ${usage.estimated_cost < 0.001 ? '<0.001' : usage.estimated_cost}
            </div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 10, color: '#555', marginBottom: 2 }}>TIME</div>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>
              {usage.elapsed_seconds}s
            </div>
          </div>
        </div>
      )}

    </div>
  )
}