import ReactFlow, { Background, Controls } from 'reactflow'
import 'reactflow/dist/style.css'

const STATUS_STYLES = {
  idle:               { background: '#1a1a1a', border: '1px solid #333',    color: '#888' },
  active:             { background: '#1a3a5c', border: '2px solid #3B8BD4', color: '#fff', boxShadow: '0 0 12px #3B8BD466' },
  done:               { background: '#1a3a2a', border: '1px solid #3B9E6A', color: '#aef' },
  awaiting_approval:  { background: '#2a2a1a', border: '2px solid #f59e0b', color: '#fcd34d', boxShadow: '0 0 12px #f59e0b66' }, // ← new
  error:              { background: '#3a1a1a', border: '1px solid #e44',    color: '#faa' },
}

const BASE_NODES = [
  { id: 'input',       position: { x: 175, y: 20  }, data: { label: '📥 Research Topic' } },
  { id: 'planner',     position: { x: 175, y: 110 }, data: { label: '🧠 Planner Agent'  } },
  { id: 'web_search',  position: { x: 50,  y: 210 }, data: { label: '🔍 Web Search'     } },
  { id: 'doc_reader',  position: { x: 300, y: 210 }, data: { label: '📄 Doc Reader'     } },
  { id: 'synthesizer', position: { x: 175, y: 310 }, data: { label: '⚗️ Synthesizer'    } },
  { id: 'report',      position: { x: 175, y: 410 }, data: { label: '📝 Report Writer'  } },
]

const EDGES = [
  { id: 'e1', source: 'input',       target: 'planner',     animated: false },
  { id: 'e2', source: 'planner',     target: 'web_search',  animated: false },
  { id: 'e3', source: 'planner',     target: 'doc_reader',  animated: false },
  { id: 'e4', source: 'web_search',  target: 'synthesizer', animated: false },
  { id: 'e5', source: 'doc_reader',  target: 'synthesizer', animated: false },
  { id: 'e6', source: 'synthesizer', target: 'report',      animated: false },
]

export default function FlowChart({ nodeStatuses }) {
  const nodes = BASE_NODES.map(n => ({
    ...n,
    style: { ...STATUS_STYLES[nodeStatuses[n.id] || 'idle'], borderRadius: 10, padding: '8px 16px', fontSize: 13, fontWeight: 500, minWidth: 150, textAlign: 'center' }
  }))

  const edges = EDGES.map(e => ({
    ...e,
    animated: nodeStatuses[e.source] === 'active',
    style: { stroke: nodeStatuses[e.source] === 'active' ? '#3B8BD4' : '#444' }
  }))

  return (
    <div style={{ flex: 1, height: '100%' }}>
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#222" gap={20} />
        <Controls />
      </ReactFlow>
    </div>
  )
}