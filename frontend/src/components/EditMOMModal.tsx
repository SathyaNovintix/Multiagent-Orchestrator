import { useState } from 'react';
import type { StructuredMOM } from '../types';
import { updateMOM } from '../api/client';

interface EditMOMModalProps {
  mom: StructuredMOM;
  onClose: () => void;
  onSave: () => void;
}

export default function EditMOMModal({ mom, onClose, onSave }: EditMOMModalProps) {
  const [editedData, setEditedData] = useState<any>({
    topics: mom.topics || [],
    decisions: mom.decisions || [],
    actions: mom.actions || [],
    sections: mom.sections || {},
    participants: mom.participants || [],
  });
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Handle custom template sections
  const hasCustomTemplate = !!mom.sections && Object.keys(mom.sections).length > 0;

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);

    console.log('[EditMOM] Saving changes...', {
      mom_id: mom.mom_id,
      editedData,
    });

    try {
      const result = await updateMOM({
        mom_id: mom.mom_id,
        ...editedData,
      });
      console.log('[EditMOM] Save successful:', result);
      onSave();
      onClose();
    } catch (err: any) {
      console.error('[EditMOM] Save failed:', err);
      setError(err.response?.data?.detail || 'Failed to save changes');
    } finally {
      setIsSaving(false);
    }
  };

  const updateSection = (sectionId: string, value: any) => {
    setEditedData((prev: any) => ({
      ...prev,
      sections: {
        ...prev.sections,
        [sectionId]: value,
      },
    }));
  };

  const updateArrayItem = (type: 'topics' | 'decisions' | 'actions', index: number, field: string, value: any) => {
    setEditedData((prev: any) => ({
      ...prev,
      [type]: prev[type].map((item: any, i: number) =>
        i === index ? { ...item, [field]: value } : item
      ),
    }));
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <h2 style={styles.title}>✏️ Edit MOM</h2>
          <button onClick={onClose} style={styles.closeBtn}>✕</button>
        </div>

        <div style={styles.content}>
          {error && (
            <div style={styles.error}>
              ❌ {error}
            </div>
          )}

          {/* Custom Template Sections */}
          {hasCustomTemplate && mom.template_structure?.sections && (
            <>
              {mom.template_structure.sections.map((section: any) => {
                const sectionData = editedData.sections[section.id];
                const isArray = Array.isArray(sectionData);

                return (
                  <div key={section.id} style={styles.section}>
                    <h3 style={styles.sectionTitle}>{section.label}</h3>
                    
                    {isArray ? (
                      // Array of items (like action points, decisions)
                      <div style={styles.arraySection}>
                        {sectionData.map((item: any, idx: number) => (
                          <div key={idx} style={styles.arrayItem}>
                            <div style={styles.arrayItemHeader}>Item {idx + 1}</div>
                            {Object.entries(item).map(([key, value]) => (
                              <div key={key} style={styles.field}>
                                <label style={styles.label}>
                                  {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}:
                                </label>
                                <textarea
                                  value={String(value || '')}
                                  onChange={(e) => {
                                    const newData = [...sectionData];
                                    newData[idx] = { ...newData[idx], [key]: e.target.value };
                                    updateSection(section.id, newData);
                                  }}
                                  style={styles.textarea}
                                  rows={2}
                                />
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                    ) : typeof sectionData === 'object' && sectionData !== null ? (
                      // Object with key-value pairs (like meeting info)
                      <div>
                        {Object.entries(sectionData).map(([key, value]) => (
                          <div key={key} style={styles.field}>
                            <label style={styles.label}>
                              {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}:
                            </label>
                            <input
                              type="text"
                              value={String(value || '')}
                              onChange={(e) => {
                                updateSection(section.id, {
                                  ...sectionData,
                                  [key]: e.target.value,
                                });
                              }}
                              style={styles.input}
                            />
                          </div>
                        ))}
                      </div>
                    ) : (
                      // Simple value
                      <div style={styles.field}>
                        <input
                          type="text"
                          value={String(sectionData || '')}
                          onChange={(e) => updateSection(section.id, e.target.value)}
                          style={styles.input}
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </>
          )}

          {/* Standard Topics */}
          {!hasCustomTemplate && editedData.topics.length > 0 && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>📋 Topics</h3>
              {editedData.topics.map((topic: any, idx: number) => (
                <div key={idx} style={styles.arrayItem}>
                  <div style={styles.arrayItemHeader}>Topic {idx + 1}</div>
                  <div style={styles.field}>
                    <label style={styles.label}>Title:</label>
                    <input
                      type="text"
                      value={topic.title || ''}
                      onChange={(e) => updateArrayItem('topics', idx, 'title', e.target.value)}
                      style={styles.input}
                    />
                  </div>
                  <div style={styles.field}>
                    <label style={styles.label}>Summary:</label>
                    <textarea
                      value={topic.summary || ''}
                      onChange={(e) => updateArrayItem('topics', idx, 'summary', e.target.value)}
                      style={styles.textarea}
                      rows={3}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Standard Decisions */}
          {!hasCustomTemplate && editedData.decisions.length > 0 && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>✅ Decisions</h3>
              {editedData.decisions.map((decision: any, idx: number) => (
                <div key={idx} style={styles.arrayItem}>
                  <div style={styles.arrayItemHeader}>Decision {idx + 1}</div>
                  <div style={styles.field}>
                    <label style={styles.label}>Decision:</label>
                    <textarea
                      value={decision.decision || ''}
                      onChange={(e) => updateArrayItem('decisions', idx, 'decision', e.target.value)}
                      style={styles.textarea}
                      rows={2}
                    />
                  </div>
                  <div style={styles.field}>
                    <label style={styles.label}>Owner:</label>
                    <input
                      type="text"
                      value={decision.owner || ''}
                      onChange={(e) => updateArrayItem('decisions', idx, 'owner', e.target.value)}
                      style={styles.input}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Standard Actions */}
          {!hasCustomTemplate && editedData.actions.length > 0 && (
            <div style={styles.section}>
              <h3 style={styles.sectionTitle}>⚡ Actions</h3>
              {editedData.actions.map((action: any, idx: number) => (
                <div key={idx} style={styles.arrayItem}>
                  <div style={styles.arrayItemHeader}>Action {idx + 1}</div>
                  <div style={styles.field}>
                    <label style={styles.label}>Task:</label>
                    <textarea
                      value={action.task || ''}
                      onChange={(e) => updateArrayItem('actions', idx, 'task', e.target.value)}
                      style={styles.textarea}
                      rows={2}
                    />
                  </div>
                  <div style={styles.field}>
                    <label style={styles.label}>Owner:</label>
                    <input
                      type="text"
                      value={action.owner || ''}
                      onChange={(e) => updateArrayItem('actions', idx, 'owner', e.target.value)}
                      style={styles.input}
                    />
                  </div>
                  <div style={styles.field}>
                    <label style={styles.label}>Deadline:</label>
                    <input
                      type="text"
                      value={action.deadline || ''}
                      onChange={(e) => updateArrayItem('actions', idx, 'deadline', e.target.value)}
                      style={styles.input}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={styles.footer}>
          <button onClick={onClose} style={styles.cancelBtn} disabled={isSaving}>
            Cancel
          </button>
          <button onClick={handleSave} style={styles.saveBtn} disabled={isSaving}>
            {isSaving ? 'Saving...' : '💾 Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0, 0, 0, 0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: 20,
  },
  modal: {
    background: '#fff',
    borderRadius: 12,
    width: '100%',
    maxWidth: 800,
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '20px 24px',
    borderBottom: '1px solid #e2e8f0',
  },
  title: {
    margin: 0,
    fontSize: 20,
    fontWeight: 700,
    color: '#0f172a',
  },
  closeBtn: {
    background: 'none',
    border: 'none',
    fontSize: 24,
    color: '#64748b',
    cursor: 'pointer',
    padding: 0,
    width: 32,
    height: 32,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 6,
  },
  content: {
    flex: 1,
    overflowY: 'auto',
    padding: 24,
  },
  error: {
    background: '#fef2f2',
    border: '1px solid #ef4444',
    color: '#991b1b',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
    fontSize: 14,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: 700,
    color: '#0f172a',
    marginBottom: 12,
    paddingBottom: 8,
    borderBottom: '2px solid #e2e8f0',
  },
  arraySection: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  arrayItem: {
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: 16,
  },
  arrayItemHeader: {
    fontSize: 13,
    fontWeight: 700,
    color: '#64748b',
    marginBottom: 12,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  field: {
    marginBottom: 12,
  },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 600,
    color: '#475569',
    marginBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  input: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #cbd5e1',
    borderRadius: 6,
    fontSize: 14,
    fontFamily: 'inherit',
    color: '#0f172a',
  },
  textarea: {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #cbd5e1',
    borderRadius: 6,
    fontSize: 14,
    fontFamily: 'inherit',
    color: '#0f172a',
    resize: 'vertical',
  },
  footer: {
    display: 'flex',
    gap: 12,
    padding: '16px 24px',
    borderTop: '1px solid #e2e8f0',
    justifyContent: 'flex-end',
  },
  cancelBtn: {
    padding: '10px 20px',
    background: '#f1f5f9',
    border: '1px solid #cbd5e1',
    borderRadius: 6,
    fontSize: 14,
    fontWeight: 600,
    color: '#475569',
    cursor: 'pointer',
  },
  saveBtn: {
    padding: '10px 20px',
    background: '#0ea5e9',
    border: 'none',
    borderRadius: 6,
    fontSize: 14,
    fontWeight: 600,
    color: '#fff',
    cursor: 'pointer',
  },
};
