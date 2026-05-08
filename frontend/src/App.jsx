import { useState, useEffect } from 'react'

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
  const [health, setHealth] = useState(null)
  const [usage, setUsage] = useState(null)   // ← add this
  const [framework, setFramework] = useState('langgraph')

  // HITL state
  const [awaitingApproval, setAwaitingApproval] = useState(false)
  const [pendingQueries, setPendingQueries] = useState('')

  // Check health every 30 seconds
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${API_URL}/health`)
        const data = await res.json()
        setHealth(data.status)
      } catch {
        setHealth('error')
      }
    }
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  const dotColor = {
    ok: '#3B9E6A',
    degraded: '#f59e0b',
    error: '#ef4444',
    null: '#555'
  }[health]

  const validateTopic = (topic) => {
    if (!topic.trim()) 
        return "Please enter a research topic"
    if (topic.trim().length < 3) 
        return "Topic too short — minimum 3 characters"
    if (topic.length > 200) 
        return `Topic too long — ${topic.length}/200 characters`
    if (topic.trim().split(' ').length < 2) 
        return "Please be more specific — at least 2 words"
    return null
  }

  const runAgent = async () => {
    // Client side validation first — no network call needed
    const validationError = validateTopic(topic)
    if (validationError) {
        setLogs([{
            node: 'validation',
            log: validationError,
            time: new Date().toLocaleTimeString()
        }])
        return
    }

    setNodeStatuses({})
    setLogs([])
    setReport('')
    setUsage(null)                             // ← add to reset block
    setRunning(true)
    setAwaitingApproval(false)
    setPendingQueries('')

    const es = new EventSource(
      `${API_URL}/run?topic=${encodeURIComponent(topic)}&framework=${framework}`
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
      if (data.usage) setUsage(data.usage)       // ← add this

      // Agent finished
      if (node === 'report' && status === 'done') {
        setRunning(false)
        es.close()
      }
    }

    es.onerror = async () => {
        setRunning(false)

        // Check if it was a rate limit error
        try {
            const res = await fetch(`${API_URL}/run?topic=ping`)
            if (res.status === 429) {
                setLogs(prev => [...prev, {
                    node: 'rate_limit',
                    log: 'Too many requests — please wait a minute before trying again',
                    time: new Date().toLocaleTimeString()
                }])
                return
            }
        } catch {}

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
      <select
          value={framework}
          onChange={e => setFramework(e.target.value)}
          style={{
              padding: '7px 12px',
              borderRadius: 8,
              border: '1px solid #333',
              background: '#1a1a1a',
              color: '#fff',
              fontSize: 13,
              cursor: 'pointer'
          }}
      >
          <option value="langgraph">LangGraph</option>
          <option value="crewai">CrewAI</option>
          <option value="groq">Groq</option>
      </select>
      <div style={{ padding: '12px 20px', borderBottom: '1px solid #222', display: 'flex', gap: 12, alignItems: 'center', background: '#111' }}>
        <span style={{ fontWeight: 600, fontSize: 14 }}>🤖 Research Agent</span>

        {/* Health indicator */}
        <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: '#555' }}>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: dotColor, display: 'inline-block' }}/>
          {health === 'ok' ? 'All systems operational' : health === 'degraded' ? 'Degraded' : health === 'error' ? 'Backend unreachable' : 'Checking...'}
        </span>

        <div style={{ flex: 1, position: 'relative' }}>
          <input
              value={topic}
              onChange={e => setTopic(e.target.value)}
              placeholder="Enter research topic..."
              maxLength={200}
              style={{
                  width: '100%',
                  padding: '7px 12px',
                  borderRadius: 8,
                  border: `1px solid ${topic.length > 180 ? '#f59e0b' : '#333'}`,
                  background: '#1a1a1a',
                  color: '#fff',
                  fontSize: 13
              }}
          />
          {topic.length > 150 && (
              <span style={{
                  position: 'absolute',
                  right: 8,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  fontSize: 11,
                  color: topic.length > 180 ? '#f59e0b' : '#555'
              }}>
                  {topic.length}/200
              </span>
          )}
      </div>
        <button
          onClick={runAgent}
          disabled={running || health === 'error'}  // ← disable if backend is down
          style={{ padding: '7px 18px', borderRadius: 8, background: running || health === 'error' ? '#333' : '#3B8BD4', color: '#fff', border: 'none', cursor: running ? 'not-allowed' : 'pointer', fontSize: 13, fontWeight: 500 }}
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
        <ReportPanel report={report} running={running} usage={usage} />
      </div>

    </div>
  )

}