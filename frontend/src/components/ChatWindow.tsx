import { useEffect, useRef } from 'react';
import type { Message } from '../types';
import MOMCard from './MOMCard';

interface Props {
  messages: Message[];
  status: string | null;
  sessionLabel?: string;
  connected?: boolean;
  devMode?: boolean;
}

export default function ChatWindow({ messages, status, sessionLabel, connected = true, devMode = false }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, status]);

  return (
    <div style={styles.wrapper}>
      {/* Chat topbar */}
      <div style={styles.topbar}>
        <div style={styles.topbarLeft}>
          <div style={styles.topbarIcon}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"
                stroke="#0f172a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <span style={styles.topbarTitle}>{sessionLabel || 'Meeting Session'}</span>
        </div>
        <div style={styles.topbarRight}>
          {devMode && (
            <div style={styles.devBadge}>DEV MODE ACTIVE</div>
          )}
          <div style={{ ...styles.statusDot, background: connected ? '#10b981' : '#ef4444' }} />
          <span style={styles.statusText}>{connected ? 'Backend connected' : 'Backend offline'}</span>
        </div>
      </div>

      {/* Messages */}
      <div style={styles.window}>
        {messages.length === 0 && (
          <div style={styles.emptyState}>
            <div style={styles.emptyCard}>
              <div style={styles.emptyIconWrap}>
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#f59e0b" opacity="0.9" />
                  <path d="M2 17l10 5 10-5" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" fill="none" />
                  <path d="M2 12l10 5 10-5" stroke="#f59e0b" strokeWidth="1.5" strokeLinecap="round" fill="none" opacity="0.5" />
                </svg>
              </div>
              <div style={styles.emptyTitle}>Ready to generate your MOM</div>
              <div style={styles.emptyDesc}>
                Paste a meeting transcript, type a summary, or upload an audio file to get started. AgentMesh will extract topics, decisions, and action items automatically.
              </div>
              <div style={styles.emptyFeatures}>
                {['📝 Text transcripts', '🎙 Audio files (.mp3 .wav .m4a)', '🌐 Multilingual support', '📄 4 MOM formats'].map(f => (
                  <div key={f} style={styles.emptyFeature}>{f}</div>
                ))}
              </div>
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={msg.id}
            className="msg-enter"
            style={{
              ...styles.row,
              justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
              animationDelay: `${Math.min(idx * 0.03, 0.15)}s`,
            }}
          >
            {msg.role === 'assistant' && (
              <div style={styles.avatar}>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#f59e0b" />
                </svg>
              </div>
            )}

            <div style={msg.role === 'user' ? styles.userBubble : styles.assistantBubble}>
              {msg.type === 'mom' && msg.mom ? (
                <MOMCard mom={msg.mom} devMode={devMode} />
              ) : (
                <div style={styles.bubbleText}>{msg.content}</div>
              )}
              <div style={{
                ...styles.timestamp,
                textAlign: msg.role === 'user' ? 'right' : 'left',
                color: msg.role === 'user' ? 'rgba(255,255,255,0.4)' : '#94a3b8',
              }}>
                {formatTime(msg.timestamp)}
              </div>
            </div>

            {msg.role === 'user' && (
              <div style={styles.userAvatar}>You</div>
            )}
          </div>
        ))}

        {status && (
          <div style={styles.row}>
            <div style={styles.avatar}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#f59e0b" />
              </svg>
            </div>
            <div style={styles.typingBubble}>
              <div style={styles.typingDot} />
              <span>{status}</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} style={{ height: 8 }} />
      </div>
    </div>
  );
}

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return iso.slice(11, 16);
  }
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    background: '#f8fafc',
  },
  topbar: {
    height: 52,
    background: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0 20px',
    flexShrink: 0,
  },
  topbarLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  topbarIcon: {
    width: 28,
    height: 28,
    background: '#f1f5f9',
    borderRadius: 6,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid #e2e8f0',
  },
  topbarTitle: {
    fontWeight: 600,
    fontSize: 14,
    color: '#0f172a',
  },
  topbarRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: '50%',
  },
  statusText: {
    fontSize: 12,
    color: '#64748b',
    fontWeight: 500,
  },
  devBadge: {
    fontSize: 10,
    fontWeight: 800,
    background: '#3b82f6',
    color: '#fff',
    padding: '2px 8px',
    borderRadius: 4,
    marginRight: 10,
    letterSpacing: '0.05em',
  },
  window: {
    flex: 1,
    overflowY: 'auto',
    padding: '20px 24px',
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  emptyState: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 40,
  },
  emptyCard: {
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 16,
    padding: '36px 32px',
    maxWidth: 440,
    width: '100%',
    textAlign: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.04)',
  },
  emptyIconWrap: {
    width: 64,
    height: 64,
    background: 'rgba(245,158,11,0.08)',
    borderRadius: 16,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 16px',
    border: '1px solid rgba(245,158,11,0.15)',
  },
  emptyTitle: {
    fontSize: 17,
    fontWeight: 700,
    color: '#0f172a',
    marginBottom: 8,
  },
  emptyDesc: {
    fontSize: 13,
    color: '#64748b',
    lineHeight: 1.6,
    marginBottom: 20,
  },
  emptyFeatures: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    justifyContent: 'center',
  },
  emptyFeature: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 20,
    padding: '5px 12px',
    fontSize: 12,
    color: '#475569',
    fontWeight: 500,
  },
  row: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 8,
  },
  avatar: {
    width: 28,
    height: 28,
    borderRadius: 8,
    background: '#0f172a',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    border: '1px solid rgba(245,158,11,0.3)',
  },
  userAvatar: {
    width: 28,
    height: 28,
    borderRadius: 8,
    background: '#3b82f6',
    color: '#fff',
    fontWeight: 700,
    fontSize: 10,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  userBubble: {
    background: '#0f172a',
    color: '#f8fafc',
    borderRadius: '14px 14px 4px 14px',
    padding: '10px 14px 6px',
    maxWidth: 520,
    boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
  },
  assistantBubble: {
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '14px 14px 14px 4px',
    padding: '10px 14px 6px',
    maxWidth: 700,
    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
  },
  bubbleText: {
    fontSize: 14,
    lineHeight: 1.65,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  timestamp: {
    fontSize: 10,
    marginTop: 5,
    fontWeight: 400,
  },
  typingBubble: {
    background: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '14px 14px 14px 4px',
    padding: '10px 16px',
    fontSize: 13,
    color: '#64748b',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
  },
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#f59e0b',
    flexShrink: 0,
    animation: 'pulse 1.4s ease-in-out infinite',
  },
};
