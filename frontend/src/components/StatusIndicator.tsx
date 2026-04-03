interface Props {
  status: string | null;
}

export default function StatusIndicator({ status }: Props) {
  if (!status) return null;

  return (
    <div style={styles.wrap}>
      <span style={styles.dot} />
      <span style={styles.text}>{status}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 8,
    background: '#f7f8fc',
    border: '1px solid #e2e8f0',
    borderRadius: 20,
    padding: '6px 14px',
    fontSize: 12,
    color: '#4a5568',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    background: '#e6a817',
    display: 'inline-block',
    animation: 'pulse 1.2s infinite',
  },
  text: { fontWeight: 500 },
};
