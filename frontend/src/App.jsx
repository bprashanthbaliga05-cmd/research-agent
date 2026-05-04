import { useState } from 'react'
import FlowChart from './FlowChart'
import LogPanel from './LogPanel'
import ReportPanel from './ReportPanel'

export default function App() {
  const [nodeStatuses, setNodeStatuses] = useState({})
  const [logs, setLogs] = useState([])
  const [running, setRunning] = useState(false)
  const [topic, setTopic] = useState('Agentic AI in 2025')
  const [report, setReport] = useState('')        // ← new

  const runAgent = () => {
    setNodeStatuses({})
    setLogs([])
    setReport('')                                  // ← reset report
    setRunning(true)

    const es = new EventSource(`http://localhost:8000/run?topic=${encodeURIComponent(topic)}`)

    es.onmessage = (e) => {
      const { node, status, log, report: finalReport } = JSON.parse(e.data)
      setNodeStatuses(prev => ({ ...prev, [node]: status }))
      setLogs(prev => [...prev, { node, log, time: new Date().toLocaleTimeString() }])

      if (finalReport) setReport(finalReport)      // ← capture report

      if (node === 'report' && status === 'done') {
        setRunning(false)
        es.close()
      }
    }

    es.onerror = () => {
      setRunning(false)
      es.close()
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh', flexDirection: 'column' }}>
      <div style={{ padding: '12px 20px', borderBottom: '1px solid #222', display: 'flex', gap: 12, alignItems: 'center', background: '#111' }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>🤖 Research Agent</span>
        <input
          value={topic}
          onChange={e => setTopic(e.target.value)}
          placeholder="Enter research topic..."
          style={{ flex: 1, padding: '7px 12px', borderRadius: 8, border: '1px solid #333', background: '#1a1a1a', color: '#fff', fontSize: 13 }}
        />
        <button
          onClick={runAgent}
          disabled={running}
          style={{ padding: '7px 18px', borderRadius: 8, background: running ? '#333' : '#3B8BD4', color: '#fff', border: 'none', cursor: running ? 'not-allowed' : 'pointer', fontSize: 13, fontWeight: 500 }}
        >
          {running ? 'Running...' : 'Run Agent'}
        </button>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <FlowChart nodeStatuses={nodeStatuses} />
        <LogPanel logs={logs} />
        <ReportPanel report={report} running={running} />  {/* ← new */}
      </div>
    </div>
  )
}