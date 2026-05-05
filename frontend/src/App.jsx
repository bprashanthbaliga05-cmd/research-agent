import { useState } from 'react'
import FlowChart from './FlowChart'
import LogPanel from './LogPanel'
import ReportPanel from './ReportPanel'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function App() {
  const [nodeStatuses, setNodeStatuses] = useState({})
  const [logs, setLogs] = useState([])
  const [running, setRunning] = useState(false)
  const [topic, setTopic] = useState('Agentic AI in 2025')
  const [report, setReport] = useState('')
  const [sessionId, setSessionId] = useState(null)

  // HITL state
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [pendingQueries, setPendingQueries] = useState('')

  const runAgent = () => {
    setNodeStatuses({})
    setLogs([])
    setReport('')
    setRunning(true)
    setAwaitingApproval(false)
    setPendingQueries('')

    const es = new EventSource(
      `${API_URL}/run?topic=${encodeURIComponent(topic)}`
    )

    es.onmessage = (e) => {
      const data = JSON.parse(e.data)

      // Capture session ID
      if (data.node === 'session') {
        setSessionId(data.session_id)
        return
      }

      const { node, status, log, report: finalReport, data: hitlData } = data

      // Update node status in flowchart
      setNodeStatuses(prev => ({ ...prev, [node]: status }))

      // Add to log panel
      if (log) {
        setLogs(prev => [...prev, {
          node,
          log,
          time: new Date().toLocaleTimeString()
        }])
      }

      // HITL — agent is waiting for approval
      if (status === 'awaiting_approval') {
        setAwaitingApproval(true)
        setPendingQueries(hitlData)
        return
      }

      // Capture final report
      if (finalReport) setReport(finalReport)

      // Agent finished
      if (node === 'report' && status === 'done') {
        setRunning(false)
        es.close()
      }
    }

    es.onerror = () => {
      setRunning(false)
      setLogs(prev => [...prev, {
        node: 'error',
        log: 'Connection dropped — please try again',
        time: new Date().toLocaleTimeString()
      }])
      es.close()
    }
  }

  const handleApprove = async () => {
    if (!sessionId) return
    setAwaitingApproval(false)
    setNodeStatuses(prev => ({ ...prev, planner: 'active' }))

    await fetch(`${API_URL}/approve/${sessionId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ queries: pendingQueries })
    })
  }

  return (
    <div style={{ display: 'flex', height: '100vh', flexDirection: 'column' }}>

      {/* Header */}
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

      {/* HITL Approval Banner */}
      {awaitingApproval && (
        <div style={{ padding: '12px 20px', background: '#1a2a1a', borderBottom: '1px solid #2a4a2a', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16 }}>⏸</span>
            <span style={{ color: '#3B9E6A', fontWeight: 600, fontSize: 13 }}>Agent paused — review search queries before continuing</span>
          </div>
          <textarea
            value={pendingQueries}
            onChange={e => setPendingQueries(e.target.value)}
            rows={3}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid #2a4a2a', background: '#111', color: '#fff', fontSize: 13, fontFamily: 'sans-serif', resize: 'vertical' }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={handleApprove}
              style={{ padding: '7px 20px', borderRadius: 8, background: '#3B9E6A', color: '#fff', border: 'none', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}
            >
              Approve & Continue ✓
            </button>
            <span style={{ fontSize: 12, color: '#555', alignSelf: 'center' }}>
              You can edit the queries above before approving
            </span>
          </div>
        </div>
      )}

      {/* Main panels */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <FlowChart nodeStatuses={nodeStatuses} />
        <LogPanel logs={logs} />
        <ReportPanel report={report} running={running} />
      </div>

    </div>
  )
}