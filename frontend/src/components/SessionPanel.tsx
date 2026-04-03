import type { Session } from '../types';

interface Props {
  sessions: Session[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
}

export default function SessionPanel({ sessions, activeId, onSelect, onNew }: Props) {
  return (
    <aside style={styles.panel}>
      {/* Brand */}
      <div style={styles.brand}>
        <div style={styles.logoMark}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#f59e0b" />
            <path d="M2 17l10 5 10-5" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" fill="none" />
            <path d="M2 12l10 5 10-5" stroke="rgba(245,158,11,0.5)" strokeWidth="2" strokeLinecap="round" fill="none" />
          </svg>
        </div>
        <div>
          <div style={styles.brandName}>AgentMesh</div>
          <div style={styles.brandSub}>MOM Orchestrator</div>
        </div>
      </div>

      {/* New Session */}
      <div style={styles.newBtnWrap}>
        <button onClick={onNew} style={styles.newBtn}>
          <span style={styles.newBtnIcon}>+</span>
          New Session
        </button>
      </div>

      {/* Section label */}
      <div style={styles.sectionLabel}>Recent Sessions</div>

      {/* List */}
      <div style={styles.list}>
        {sessions.length === 0 && (
          <div style={styles.empty}>
            <div style={styles.emptyIcon}>📋</div>
            <div>No sessions yet</div>
          </div>
        )}
        {sessions.map((s) => {
          const isActive = s.session_id === activeId;
          return (
            <button
              key={s.session_id}
              onClick={() => onSelect(s.session_id)}
              style={{
                ...styles.item,
                background: isActive ? 'rgba(245,158,11,0.12)' : 'transparent',
                borderLeft: isActive ? '3px solid #f59e0b' : '3px solid transparent',
              }}
            >
              <div style={styles.itemIcon}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M9 12h6M9 16h4M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z"
                    stroke={isActive ? '#f59e0b' : '#64748b'} strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <div style={styles.itemContent}>
                <div style={{ ...styles.itemLabel, color: isActive ? '#f1f5f9' : '#cbd5e1' }}>
                  {s.label}
                </div>
                <div style={styles.itemDate}>{s.created_at.slice(0, 10)}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <div style={styles.footerBadge}>
          <div style={styles.footerDot} />
          AI Pipeline Ready
        </div>
      </div>
    </aside>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 248,
    minWidth: 248,
    background: '#0f172a',
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    borderRight: '1px solid rgba(255,255,255,0.06)',
  },
  brand: {
    padding: '20px 16px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    borderBottom: '1px solid rgba(255,255,255,0.06)',
  },
  logoMark: {
    width: 36,
    height: 36,
    background: 'rgba(245,158,11,0.12)',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    border: '1px solid rgba(245,158,11,0.2)',
  },
  brandName: {
    fontWeight: 700,
    fontSize: 14,
    color: '#f8fafc',
    letterSpacing: '-0.2px',
  },
  brandSub: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 1,
  },
  newBtnWrap: {
    padding: '14px 12px 8px',
  },
  newBtn: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '9px 12px',
    background: 'rgba(245,158,11,0.15)',
    border: '1px solid rgba(245,158,11,0.25)',
    borderRadius: 8,
    color: '#f59e0b',
    fontWeight: 600,
    fontSize: 13,
    cursor: 'pointer',
    transition: 'all 0.15s',
  },
  newBtnIcon: {
    fontSize: 16,
    lineHeight: 1,
    marginTop: -1,
  },
  sectionLabel: {
    padding: '4px 16px 6px',
    fontSize: 10,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.8px',
    color: '#475569',
  },
  list: {
    flex: 1,
    overflowY: 'auto',
    padding: '2px 8px',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 6,
    padding: '32px 0',
    color: '#475569',
    fontSize: 12,
  },
  emptyIcon: { fontSize: 22 },
  item: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    textAlign: 'left',
    border: 'none',
    borderRadius: 6,
    padding: '8px 10px',
    cursor: 'pointer',
    marginBottom: 2,
    transition: 'all 0.15s',
  },
  itemIcon: {
    flexShrink: 0,
    marginTop: 1,
  },
  itemContent: {
    minWidth: 0,
    flex: 1,
  },
  itemLabel: {
    fontSize: 13,
    fontWeight: 500,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  itemDate: {
    fontSize: 11,
    color: '#475569',
    marginTop: 1,
  },
  footer: {
    padding: '12px 14px',
    borderTop: '1px solid rgba(255,255,255,0.06)',
  },
  footerBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    color: '#475569',
  },
  footerDot: {
    width: 6,
    height: 6,
    borderRadius: '50%',
    background: '#10b981',
    boxShadow: '0 0 4px #10b981',
  },
};
