import { useEffect, useRef } from 'react';

interface FlowNode {
  id: string;
  type: 'input' | 'orchestrator' | 'agent' | 'parallel';
  label: string;
  detail: string;
  activatesAt: number;
}

// Text pipeline — PIPELINE_STEPS.slice(1) has 6 steps → pipelineStep goes 0..6
const TEXT_NODES: FlowNode[] = [
  { id: 'input',    type: 'input',        label: 'User Input',              detail: 'Text received',            activatesAt: 0 },
  { id: 'orch0',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Routing input',            activatesAt: 0 },
  { id: 'lang',     type: 'agent',        label: 'Language Detector',       detail: 'Detecting language',       activatesAt: 1 },
  { id: 'orch1',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Evaluating language',      activatesAt: 2 },
  { id: 'intent',   type: 'agent',        label: 'Intent Refiner',          detail: 'Refining intent',          activatesAt: 3 },
  { id: 'orch2',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Routing by intent',        activatesAt: 3 },
  { id: 'extract',  type: 'parallel',     label: 'Topic · Decision · Action', detail: 'Parallel extraction',   activatesAt: 4 },
  { id: 'orch3',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Passing to formatter',     activatesAt: 5 },
  { id: 'format',   type: 'agent',        label: 'Formatter',               detail: 'Formatting MOM',           activatesAt: 5 },
  { id: 'orch4',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Generating response',      activatesAt: 6 },
  { id: 'response', type: 'agent',        label: 'Response Generator',      detail: 'Building response',        activatesAt: 6 },
];

// Audio pipeline — PIPELINE_STEPS (full, 7 steps) → pipelineStep goes 0..7
const AUDIO_NODES: FlowNode[] = [
  { id: 'input',    type: 'input',        label: 'Audio Input',             detail: 'Audio file received',      activatesAt: 0 },
  { id: 'orch0',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Routing to STT',           activatesAt: 0 },
  { id: 'stt',      type: 'agent',        label: 'Speech-to-Text',          detail: 'Transcribing audio',       activatesAt: 1 },
  { id: 'orch1',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Passing transcript',       activatesAt: 2 },
  { id: 'lang',     type: 'agent',        label: 'Language Detector',       detail: 'Detecting language',       activatesAt: 2 },
  { id: 'orch2',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Evaluating language',      activatesAt: 3 },
  { id: 'intent',   type: 'agent',        label: 'Intent Refiner',          detail: 'Refining intent',          activatesAt: 4 },
  { id: 'orch3',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Routing by intent',        activatesAt: 4 },
  { id: 'extract',  type: 'parallel',     label: 'Topic · Decision · Action', detail: 'Parallel extraction',   activatesAt: 5 },
  { id: 'orch4',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Passing to formatter',     activatesAt: 6 },
  { id: 'format',   type: 'agent',        label: 'Formatter',               detail: 'Formatting MOM',           activatesAt: 6 },
  { id: 'orch5',    type: 'orchestrator', label: 'Orchestrator',            detail: 'Generating response',      activatesAt: 7 },
  { id: 'response', type: 'agent',        label: 'Response Generator',      detail: 'Building response',        activatesAt: 7 },
];

const TYPE_COLORS: Record<string, { bg: string; border: string; text: string; glow: string }> = {
  input:        { bg: '#0a2420', border: '#10b981', text: '#34d399', glow: 'rgba(16,185,129,0.25)' },
  orchestrator: { bg: '#201800', border: '#f59e0b', text: '#fbbf24', glow: 'rgba(245,158,11,0.25)' },
  agent:        { bg: '#0a1628', border: '#3b82f6', text: '#60a5fa', glow: 'rgba(59,130,246,0.25)'  },
  parallel:     { bg: '#160a28', border: '#8b5cf6', text: '#a78bfa', glow: 'rgba(139,92,246,0.25)' },
};

const TYPE_ICONS: Record<string, string> = {
  input:        '⌨',
  orchestrator: '⚡',
  agent:        '🤖',
  parallel:     '◈',
};

const TYPE_BADGE: Record<string, string> = {
  input:        'INPUT',
  orchestrator: 'ORCH',
  agent:        'AGENT',
  parallel:     'PARALLEL',
};

interface Props {
  /** -1 = idle, 0 = just started, 1..N = step N completed, 99 = all done */
  pipelineStep: number;
  isAudio: boolean;
  loading: boolean;
  inputPreview?: string;
}

type NodeState = 'pending' | 'active' | 'done';

export default function PipelineFlowPanel({ pipelineStep, isAudio, loading, inputPreview }: Props) {
  const nodes = isAudio ? AUDIO_NODES : TEXT_NODES;
  const scrollRef = useRef<HTMLDivElement>(null);

  const isIdle      = pipelineStep < 0;
  const isCompleted = pipelineStep >= 99 && !loading;

  const getState = (node: FlowNode): NodeState => {
    if (isIdle) return 'pending';
    if (isCompleted) return 'done';
    if (pipelineStep > node.activatesAt) return 'done';
    if (pipelineStep === node.activatesAt) return 'active';
    return 'pending';
  };

  // Scroll to first active node
  useEffect(() => {
    if (!scrollRef.current || isIdle) return;
    const el = scrollRef.current.querySelector('[data-active="true"]') as HTMLElement | null;
    el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }, [pipelineStep, isIdle]);

  const statusLabel = isIdle
    ? 'IDLE'
    : isCompleted
    ? 'DONE ✓'
    : 'RUNNING';

  const statusColor = isIdle ? '#475569' : isCompleted ? '#10b981' : '#f59e0b';

  return (
    <div style={styles.panel}>
      {/* ── Header ── */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={{ ...styles.headerDot, background: statusColor, boxShadow: isCompleted || !isIdle ? `0 0 6px ${statusColor}` : 'none' }} />
          <span style={styles.headerTitle}>PIPELINE FLOW</span>
        </div>
        <span style={{ ...styles.headerStatus, color: statusColor }}>{statusLabel}</span>
      </div>

      {/* ── Input preview ── */}
      {inputPreview && !isIdle && (
        <div style={styles.inputPreview}>
          <span style={styles.inputPreviewLabel}>{isAudio ? '🎙 AUDIO' : '💬 INPUT'}</span>
          <span style={styles.inputPreviewText}>
            {inputPreview.length > 55 ? inputPreview.slice(0, 55) + '…' : inputPreview}
          </span>
        </div>
      )}

      {/* ── Nodes ── */}
      <div ref={scrollRef} style={styles.flow}>
        {isIdle ? (
          <div style={styles.idleState}>
            <div style={styles.idleIcon}>▷</div>
            <div style={styles.idleText}>Submit input to watch<br />the live pipeline flow</div>
          </div>
        ) : (
          nodes.map((node, idx) => {
            const state   = getState(node);
            const colors  = TYPE_COLORS[node.type];
            const isActive = state === 'active';
            const isDone   = state === 'done';
            const prevDone = idx === 0 || getState(nodes[idx - 1]) !== 'pending';

            return (
              <div key={node.id} className="flow-node-enter" data-active={isActive} style={{ animationDelay: `${idx * 0.04}s` }}>
                {/* Arrow line */}
                {idx > 0 && (
                  <div style={{
                    ...styles.connector,
                    background: prevDone ? colors.border : '#1e293b',
                    opacity: prevDone ? 0.6 : 0.2,
                  }} />
                )}

                {/* Node card */}
                <div style={{
                  ...styles.node,
                  borderColor: isActive ? colors.border : isDone ? `${colors.border}88` : '#1a2332',
                  background:  isActive ? colors.bg      : isDone ? `${colors.bg}88`    : '#080e18',
                  boxShadow:   isActive ? `0 0 14px ${colors.glow}, 0 2px 8px rgba(0,0,0,0.4)` : 'none',
                  opacity:     state === 'pending' ? 0.3 : 1,
                }}>
                  {/* Icon */}
                  <div style={{
                    ...styles.nodeIcon,
                    color: isActive ? colors.text : isDone ? `${colors.text}99` : '#2d3f52',
                    animation: isActive ? 'pulse-node 1.3s ease-in-out infinite' : 'none',
                  }}>
                    {isDone ? '✓' : TYPE_ICONS[node.type]}
                  </div>

                  {/* Content */}
                  <div style={styles.nodeContent}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{
                        ...styles.nodeLabel,
                        color: isActive ? colors.text : isDone ? '#6b7f95' : '#253242',
                      }}>
                        {node.label}
                      </span>
                      <span style={{
                        ...styles.nodeBadge,
                        borderColor: isActive ? colors.border : '#1e293b',
                        color: isActive ? colors.text : '#2d3f52',
                      }}>
                        {TYPE_BADGE[node.type]}
                      </span>
                    </div>
                    <div style={{
                      ...styles.nodeDetail,
                      color: isActive ? '#5a7a90' : isDone ? '#1e293b' : '#111827',
                    }}>
                      {isActive ? node.detail : isDone ? 'completed' : '—'}
                    </div>
                  </div>

                  {/* Active pulse dot */}
                  {isActive && <div style={styles.activeDot} />}
                </div>
              </div>
            );
          })
        )}

        {/* Completion footer */}
        {isCompleted && (
          <div style={styles.completedBanner}>
            <span style={styles.completedCheck}>✓</span>
            <span style={styles.completedText}>Pipeline complete</span>
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 252,
    flexShrink: 0,
    background: '#060c17',
    borderLeft: '1px solid #111c2b',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    fontFamily: "'Inter', system-ui, sans-serif",
  },
  header: {
    height: 38,
    borderBottom: '1px solid #111c2b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 12px',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  headerDot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    flexShrink: 0,
    transition: 'all 0.3s',
  },
  headerTitle: {
    fontSize: 9,
    fontWeight: 800,
    color: '#2d3f52',
    letterSpacing: '0.14em',
  },
  headerStatus: {
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: '0.1em',
    transition: 'color 0.3s',
  },
  inputPreview: {
    padding: '7px 12px 8px',
    borderBottom: '1px solid #0d1829',
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
    flexShrink: 0,
  },
  inputPreviewLabel: {
    fontSize: 8,
    fontWeight: 700,
    color: '#2d3f52',
    letterSpacing: '0.1em',
  },
  inputPreviewText: {
    fontSize: 10,
    color: '#4a6070',
    lineHeight: 1.4,
    wordBreak: 'break-word',
  },
  flow: {
    flex: 1,
    overflowY: 'auto',
    padding: '10px 8px 16px',
    display: 'flex',
    flexDirection: 'column',
  },
  idleState: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingTop: 48,
  },
  idleIcon: {
    fontSize: 22,
    color: '#1e293b',
  },
  idleText: {
    fontSize: 11,
    color: '#253242',
    textAlign: 'center',
    lineHeight: 1.55,
  },
  connector: {
    width: 2,
    height: 10,
    margin: '0 auto',
    borderRadius: 2,
    transition: 'all 0.4s',
  },
  node: {
    borderRadius: 7,
    border: '1px solid',
    padding: '7px 9px',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    position: 'relative',
    transition: 'all 0.35s ease',
    overflow: 'hidden',
  },
  nodeIcon: {
    fontSize: 13,
    width: 16,
    textAlign: 'center',
    flexShrink: 0,
    transition: 'color 0.3s',
  },
  nodeContent: {
    flex: 1,
    minWidth: 0,
  },
  nodeLabel: {
    fontSize: 11,
    fontWeight: 600,
    transition: 'color 0.3s',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  nodeBadge: {
    fontSize: 7,
    fontWeight: 700,
    border: '1px solid',
    borderRadius: 3,
    padding: '1px 4px',
    letterSpacing: '0.06em',
    flexShrink: 0,
    transition: 'all 0.3s',
  },
  nodeDetail: {
    fontSize: 9,
    marginTop: 2,
    transition: 'color 0.3s',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
  },
  activeDot: {
    position: 'absolute',
    right: 8,
    top: '50%',
    transform: 'translateY(-50%)',
    width: 5,
    height: 5,
    borderRadius: '50%',
    background: '#f59e0b',
    animation: 'pulse-dot 1.2s ease-in-out infinite',
  },
  completedBanner: {
    marginTop: 10,
    padding: '8px 12px',
    borderRadius: 7,
    background: '#0a2420',
    border: '1px solid #10b98144',
    display: 'flex',
    alignItems: 'center',
    gap: 7,
  },
  completedCheck: {
    fontSize: 13,
    color: '#10b981',
  },
  completedText: {
    fontSize: 10,
    fontWeight: 600,
    color: '#34d399',
    letterSpacing: '0.04em',
  },
};
