import { useState, useEffect, useRef } from 'react';
import type { Message, Session } from './types';
import { createSession, fetchSessions, fetchMessages, persistMessage, runPipeline, uploadAudio } from './api/client';
import SessionPanel from './components/SessionPanel';
import ChatWindow from './components/ChatWindow';
import InputBar from './components/InputBar';
import PipelineFlowPanel from './components/PipelineFlowPanel';

const PIPELINE_STEPS = [
  'Transcribing audio…',
  'Detecting language…',
  'Translating content…',
  'Refining intent…',
  'Extracting topics, decisions & actions…',
  'Formatting MOM…',
  'Generating response…',
];

const ACTIVE_SESSION_KEY = 'agentmesh_active_session';

function makeId() { return Math.random().toString(36).slice(2); }
function nowISO() { return new Date().toISOString(); }

export default function App() {
  const [sessions, setSessions]        = useState<Session[]>([]);
  const [activeSessionId, setActiveId] = useState<string | null>(null);
  const [messageMap, setMessageMap]    = useState<Record<string, Message[]>>({});
  const [loading, setLoading]          = useState(false);
  const [statusText, setStatusText]    = useState<string | null>(null);
  const [connected, setConnected]      = useState(true);
  const [booting, setBooting]          = useState(true);
  const [devMode, setDevMode]          = useState(false);
  const [pipelineStep, setPipelineStep]   = useState(-1);     // -1=idle, 0..N=step, 99=done
  const [isAudioPipeline, setIsAudioPipeline] = useState(false);
  const [inputPreview, setInputPreview]   = useState('');
  const loadedSessions                 = useRef<Set<string>>(new Set());

  // ── Boot: load all sessions from MongoDB ─────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const serverSessions = await fetchSessions();
        setConnected(true);

        if (serverSessions.length === 0) {
          // First ever run — create a session
          await handleNewSession();
        } else {
          setSessions(serverSessions.map(s => ({
            session_id: s.session_id,
            label: s.label,
            created_at: s.created_at,
          })));

          // Restore the last active session from localStorage
          const savedId = localStorage.getItem(ACTIVE_SESSION_KEY);
          const exists  = serverSessions.find(s => s.session_id === savedId);
          const target  = exists ? savedId! : serverSessions[0].session_id;
          setActiveId(target);
        }
      } catch {
        setConnected(false);
        // Offline — use a local-only session
        const localId = `local-${makeId()}`;
        setSessions([{ session_id: localId, label: 'Local Session', created_at: nowISO() }]);
        setActiveId(localId);
      } finally {
        setBooting(false);
      }
    })();
  }, []);

  // ── Persist active session to localStorage ───────────────────────────────
  useEffect(() => {
    if (activeSessionId) {
      localStorage.setItem(ACTIVE_SESSION_KEY, activeSessionId);
      loadMessagesFor(activeSessionId);
    }
  }, [activeSessionId]);

  const loadMessagesFor = async (sid: string) => {
    if (loadedSessions.current.has(sid) || sid.startsWith('local-')) return;
    loadedSessions.current.add(sid);
    try {
      const msgs = await fetchMessages(sid);
      if (msgs.length > 0) {
        setMessageMap(prev => ({ ...prev, [sid]: msgs }));
      }
    } catch { /* ignore */ }
  };

  const activeSession = sessions.find(s => s.session_id === activeSessionId);
  const messages = activeSessionId ? (messageMap[activeSessionId] ?? []) : [];

  const addMessage = (sid: string, msg: Message) => {
    setMessageMap(prev => ({ ...prev, [sid]: [...(prev[sid] ?? []), msg] }));
    // Persist to MongoDB (fire-and-forget)
    if (!sid.startsWith('local-')) {
      persistMessage(sid, msg).catch(() => {});
    }
  };

  const handleNewSession = async () => {
    try {
      const label = `Session ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
      const data  = await createSession(label);
      setConnected(true);
      const session: Session = { session_id: data.session_id, label: data.label, created_at: data.created_at };
      setSessions(prev => [session, ...prev]);
      setActiveId(data.session_id);
    } catch {
      setConnected(false);
      const localId = `local-${makeId()}`;
      const session: Session = {
        session_id: localId,
        label: `Session ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        created_at: nowISO(),
      };
      setSessions(prev => [session, ...prev]);
      setActiveId(localId);
    }
  };

  const simulateProgress = (isAudio: boolean) => {
    setIsAudioPipeline(isAudio);
    setPipelineStep(0);
    const steps = isAudio ? PIPELINE_STEPS : PIPELINE_STEPS.slice(1);
    let i = 0;
    const id = setInterval(() => {
      if (i < steps.length) {
        setStatusText(steps[i]);
        setPipelineStep(i + 1);
        i++;
      } else {
        clearInterval(id);
      }
    }, 1800);
    return () => clearInterval(id);
  };

  const handleSendText = async (text: string, formatId: string) => {
    if (!activeSessionId || loading) return;
    const userMsg: Message = { id: makeId(), role: 'user', content: text, type: 'text', timestamp: nowISO() };
    addMessage(activeSessionId, userMsg);
    setLoading(true);
    setInputPreview(text);
    const stop = simulateProgress(false);
    try {
      const result = await runPipeline({ session_id: activeSessionId, input_type: 'text', content: text, intent: 'auto_detect', format_id: formatId });
      setConnected(true); stop(); setStatusText(null);
      setPipelineStep(99);
      handleResult(activeSessionId, result);
      setTimeout(() => setPipelineStep(-1), 3500);
    } catch (err: any) {
      stop(); setStatusText(null); setConnected(false);
      setPipelineStep(-1);
      addMessage(activeSessionId, { id: makeId(), role: 'assistant', content: `Error: ${err.message ?? 'Backend not reachable.'}`, type: 'text', timestamp: nowISO() });
    } finally { setLoading(false); }
  };

  const handleSendAudio = async (file: File, formatId: string) => {
    if (!activeSessionId || loading) return;
    const userMsg: Message = { id: makeId(), role: 'user', content: `🎙 Audio uploaded: ${file.name}`, type: 'text', timestamp: nowISO() };
    addMessage(activeSessionId, userMsg);
    setLoading(true);
    setInputPreview(file.name);
    const stop = simulateProgress(true);
    try {
      // Upload file to backend first
      const uploadResult = await uploadAudio(file);
      // Run pipeline with the uploaded file path
      const result = await runPipeline({ session_id: activeSessionId, input_type: 'audio', content: uploadResult.file_path, intent: 'generate_mom', format_id: formatId });
      setConnected(true); stop(); setStatusText(null);
      setPipelineStep(99);
      handleResult(activeSessionId, result);
      setTimeout(() => setPipelineStep(-1), 3500);
    } catch (err: any) {
      stop(); setStatusText(null); setConnected(false);
      setPipelineStep(-1);
      addMessage(activeSessionId, { id: makeId(), role: 'assistant', content: `Error: ${err.message ?? 'Backend not reachable.'}`, type: 'text', timestamp: nowISO() });
    } finally { setLoading(false); }
  };

  const handleResult = (sid: string, result: any) => {
    if (result.type === 'error') {
      addMessage(sid, { id: makeId(), role: 'assistant', content: `⚠ ${result.message}`, type: 'text', timestamp: nowISO() });
    } else if (result.type === 'clarification') {
      addMessage(sid, { id: makeId(), role: 'assistant', content: result.prompt, type: 'text', timestamp: nowISO() });
    } else if (result.type === 'success') {
      if (result.structured_mom) {
        addMessage(sid, { id: makeId(), role: 'assistant', content: result.user_message ?? 'MOM generated.', type: 'mom', mom: result.structured_mom, file_url: result.file_url, timestamp: nowISO() });
      } else {
        addMessage(sid, { id: makeId(), role: 'assistant', content: result.user_message ?? 'Done.', type: 'text', timestamp: nowISO() });
      }
    }
  };

  if (booting) {
    return (
      <div style={styles.boot}>
        <div style={styles.bootSpinner} />
        <div style={styles.bootText}>Loading AgentMesh…</div>
      </div>
    );
  }

  return (
    <div style={styles.root}>
      {!connected && (
        <div style={styles.banner}>
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0zM12 9v4M12 17h.01" stroke="#92400e" strokeWidth="2" strokeLinecap="round" />
          </svg>
          Backend not reachable at {import.meta.env.VITE_API_URL || 'http://localhost:8000'} — start FastAPI + MongoDB.
        </div>
      )}
      
      <header style={styles.appHeader}>
        <div style={styles.headerTitleContainer}>
          <div style={styles.headerLogo}>🤖</div>
          <div style={styles.headerMainTitle}>AgentMesh MOM Orchestrator</div>
        </div>
        
        <div style={styles.devToggleContainer} onClick={() => setDevMode(!devMode)}>
          <span style={{ fontSize: 11, fontWeight: 700, color: devMode ? '#3b82f6' : '#94a3b8', marginRight: 8 }}>DEV MODE</span>
          <div style={{
            ...styles.toggleBg,
            backgroundColor: devMode ? '#3b82f6' : '#e2e8f0'
          }}>
            <div style={{
              ...styles.toggleCircle,
              transform: devMode ? 'translateX(16px)' : 'translateX(0)'
            }} />
          </div>
        </div>
      </header>

      <div style={styles.body}>
        <SessionPanel sessions={sessions} activeId={activeSessionId} onSelect={setActiveId} onNew={handleNewSession} />
        <div style={styles.main}>
          <div style={styles.chatRow}>
            <ChatWindow messages={messages} status={statusText} sessionLabel={activeSession?.label} connected={connected} devMode={devMode} />
            {devMode && (
              <PipelineFlowPanel
                pipelineStep={pipelineStep}
                isAudio={isAudioPipeline}
                loading={loading}
                inputPreview={inputPreview}
              />
            )}
          </div>
          <InputBar onSendText={handleSendText} onSendAudio={handleSendAudio} disabled={loading} />
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: { height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden', fontFamily: "'Inter', system-ui, sans-serif" },
  appHeader: {
    height: 48,
    background: '#fff',
    borderBottom: '1px solid #e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 20px',
    zIndex: 10,
    boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
  },
  headerTitleContainer: { display: 'flex', alignItems: 'center', gap: 10 },
  headerLogo: { fontSize: 20 },
  headerMainTitle: { fontSize: 13, fontWeight: 700, color: '#0f172a', letterSpacing: '-0.2px' },
  devToggleContainer: {
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    padding: '4px 12px',
    borderRadius: 20,
    background: '#f1f5f9',
    transition: 'all 0.2s',
    userSelect: 'none',
    zIndex: 1000,
  },
  toggleBg: {
    width: 32,
    height: 16,
    borderRadius: 10,
    padding: 2,
    transition: 'background-color 0.2s'
  },
  toggleCircle: {
    width: 12,
    height: 12,
    background: '#fff',
    borderRadius: '60%',
    transition: 'transform 0.2s'
  },
  banner: {
    background: '#fef3c7', borderBottom: '1px solid #fde68a', color: '#92400e',
    fontSize: 12, fontWeight: 500, padding: '8px 18px',
    display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0,
  },
  body: { flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 },
  main: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0, background: '#f8fafc' },
  chatRow: { flex: 1, display: 'flex', overflow: 'hidden', minHeight: 0 },
  boot: {
    height: '100vh', display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center', background: '#f8fafc', gap: 12,
  },
  bootSpinner: {
    width: 28, height: 28, border: '3px solid #e2e8f0',
    borderTop: '3px solid #f59e0b', borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  bootText: { fontSize: 13, color: '#64748b', fontWeight: 500 },
};
