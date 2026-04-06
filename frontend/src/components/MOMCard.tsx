import type { StructuredMOM } from '../types';
import { getMOMDownloadURL, getMOMExcelDownloadURL, sendMOMToTeams, getMOM, assignTasksToPM } from '../api/client';
import { useState } from 'react';
import EditMOMModal from './EditMOMModal';

const PRIORITY_STYLE: Record<string, { color: string; bg: string; label: string }> = {
  high:   { color: '#dc2626', bg: '#fef2f2', label: 'High' },
  medium: { color: '#d97706', bg: '#fffbeb', label: 'Medium' },
  low:    { color: '#059669', bg: '#ecfdf5', label: 'Low' },
};

/** Convert ANY value type to a clean, human-readable string — never raw JSON. */
function renderValue(val: unknown): string {
  if (val === undefined || val === null || val === 'N/A' || val === '') return 'N/A';
  if (typeof val === 'string') {
    const s = val.trim();
    return s && s.toLowerCase() !== 'n/a' ? s : 'N/A';
  }
  if (typeof val === 'number' || typeof val === 'boolean') return String(val);
  if (Array.isArray(val)) {
    if (val.length === 0) return 'N/A';
    return val.map(item => {
      if (typeof item === 'object' && item !== null) {
        return Object.values(item).filter(v => v && v !== 'N/A').join(', ');
      }
      return String(item);
    }).filter(s => s && s !== 'N/A').join(' | ') || 'N/A';
  }
  if (typeof val === 'object') {
    const obj = val as Record<string, unknown>;
    // Try common "value" keys
    for (const key of ['value', 'text', 'content', 'data']) {
      if (key in obj && typeof obj[key] !== 'object') return String(obj[key]);
    }
    return Object.values(obj).filter(v => typeof v !== 'object' && v).join(', ') || 'N/A';
  }
  return String(val);
}

const DataTable = ({ data, fields, accent }: { data: any[], fields: any[], accent: string }) => {
  if (!Array.isArray(data) || data.length === 0) return <div style={styles.noData}>No records found</div>;
  
  // Use fields meta or keys from first item
  const headers = fields.length > 0 
    ? fields.map(f => ({ id: f.id || (f.name || '').toLowerCase().replace(/\s+/g, '_'), label: f.label || f.name }))
    : Object.keys(data[0]).map(k => ({ id: k, label: k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) }));

  return (
    <div style={styles.tableWrapper}>
      <table style={styles.table}>
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} style={{ ...styles.th, borderBottom: `2px solid ${accent}` }}>{h.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, ri) => (
            <tr key={ri} style={ri % 2 === 0 ? {} : styles.trEven}>
              {headers.map((h, ci) => (
                <td key={ci} style={styles.td}>
                  {renderValue(typeof row === 'object' && row !== null ? (row as any)[h.id] : row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};


const DevTrace = ({ trace }: { trace: any[] }) => {
  if (!trace || trace.length === 0) return null;
  return (
    <div style={styles.devTrace}>
      <div style={styles.devTraceHeader}>
        <span style={{ fontSize: 13 }}>🛠 Backend Process</span>
        <span style={styles.devTraceBadge}>Pipeline Trace</span>
      </div>
      <div style={styles.devStepList}>
        {trace.map((step, i) => (
          <div key={i} style={styles.devStep}>
            <div style={{
              ...styles.devStepDot,
              background: step.status === 'success' ? '#10b981' : '#ef4444',
              boxShadow: step.status === 'success' ? '0 0 8px rgba(16,185,129,0.3)' : '0 0 8px rgba(239,68,68,0.3)'
            }} />
            <div style={styles.devStepContent}>
              <div style={styles.devStepMain}>
                <span style={styles.devStepAgent}>{step.agent}</span>
                <span style={{
                  ...styles.devStepStatus, 
                  color: step.status === 'success' ? '#10b981' : '#ef4444',
                  background: step.status === 'success' ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)'
                }}>
                  {step.status.toUpperCase()}
                </span>
                <span style={styles.devStepTime}>{step.execution_ms}ms</span>
              </div>
              <div style={styles.devStepReason}>
                {step.reasoning || 'Agent executed successfully without specific reasoning notes.'}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};


export default function MOMCard({ mom, devMode = false, onUpdate }: { mom: StructuredMOM; devMode?: boolean; onUpdate?: (updatedMOM: StructuredMOM) => void }) {
  const [isSending, setIsSending] = useState(false);
  const [sendStatus, setSendStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [currentMOM, setCurrentMOM] = useState(mom);
  const [isAssigning, setIsAssigning] = useState(false);
  
  const downloadUrl = currentMOM.file_url
    ? getMOMDownloadURL(currentMOM.mom_id, currentMOM.format_id || 'standard')
    : null;
  const excelUrl = currentMOM.mom_id
    ? getMOMExcelDownloadURL(currentMOM.mom_id, currentMOM.format_id || 'standard')
    : null;

  const totalItems = currentMOM.topics.length + currentMOM.decisions.length + currentMOM.actions.length;

  // Use custom template rendering when there IS a template structure with sections
  const hasCustomTemplate =
    !!currentMOM.template_structure &&
    Array.isArray(currentMOM.template_structure.sections) &&
    currentMOM.template_structure.sections.length > 0 &&
    !!currentMOM.sections;

  const handleEditMOM = () => {
    setIsEditModalOpen(true);
  };

  const handleSaveEdit = async () => {
    try {
      // Fetch the updated MOM from backend
      const updatedMOM = await getMOM(currentMOM.mom_id);
      setCurrentMOM(updatedMOM);
      
      // Notify parent component if callback provided
      if (onUpdate) {
        onUpdate(updatedMOM);
      }
      
      setSendStatus({
        type: 'success',
        message: 'MOM updated successfully!',
      });
      setTimeout(() => setSendStatus(null), 3000);
    } catch (error) {
      console.error('[MOMCard] Failed to fetch updated MOM:', error);
      setSendStatus({
        type: 'error',
        message: 'MOM saved but failed to refresh. Please reload the page.',
      });
    }
  };

  const handleSendToTeams = async () => {
    setIsSending(true);
    setSendStatus(null);

    try {
      const result = await sendMOMToTeams({
        mom_id: currentMOM.mom_id,
      });

      setSendStatus({
        type: 'success',
        message: result.message || 'MOM sent to Teams successfully!',
      });

      // Clear success message after 5 seconds
      setTimeout(() => setSendStatus(null), 5000);
    } catch (error: any) {
      setSendStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to send to Teams. Please check configuration.',
      });

      // Clear error message after 8 seconds
      setTimeout(() => setSendStatus(null), 8000);
    } finally {
      setIsSending(false);
    }
  };

  const handleAssignTasks = async () => {
    setIsAssigning(true);
    setSendStatus(null);

    try {
      const result = await assignTasksToPM({
        mom_id: currentMOM.mom_id,
        // pm_session_id is optional, backend will use mom_id if not provided
      });

      setSendStatus({
        type: 'success',
        message: result.message || 'Tasks assigned to PM tool successfully!',
      });

      // Clear success message after 5 seconds
      setTimeout(() => setSendStatus(null), 5000);
    } catch (error: any) {
      setSendStatus({
        type: 'error',
        message: error.response?.data?.detail || 'Failed to assign tasks. Please try again.',
      });

      // Clear error message after 8 seconds
      setTimeout(() => setSendStatus(null), 8000);
    } finally {
      setIsAssigning(false);
    }
  };

  return (
    <div style={styles.card}>
      {/* Edit Modal */}
      {isEditModalOpen && (
        <EditMOMModal
          mom={currentMOM}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleSaveEdit}
        />
      )}

      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.headerIcon}>📋</div>
          <div>
            <div style={styles.headerTitle}>
              {currentMOM.format_name ? `MOM: ${currentMOM.format_name}` : 'Minutes of Meeting'}
            </div>
            <div style={styles.headerMeta}>
              {totalItems} item{totalItems !== 1 ? 's' : ''} extracted
              {currentMOM.original_language && currentMOM.original_language !== 'en' && (
                <span style={styles.langTag}>{currentMOM.original_language.toUpperCase()}</span>
              )}
            </div>
          </div>
        </div>
        <div style={styles.downloadBtns}>
          {downloadUrl && (
            <a href={downloadUrl} target="_blank" rel="noreferrer" style={styles.downloadBtnTop}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style={{ marginRight: 4 }}>
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              PDF
            </a>
          )}
          {excelUrl && (
            <a href={excelUrl} target="_blank" rel="noreferrer" style={{ ...styles.downloadBtnTop, background: 'rgba(16,185,129,0.15)', borderColor: 'rgba(16,185,129,0.35)', color: '#059669' }}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style={{ marginRight: 4 }}>
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Excel
            </a>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div style={styles.stats}>
        <StatBadge icon="💬" label="Topics" count={currentMOM.topics.length} color="#3b82f6" />
        <StatBadge icon="✅" label="Decisions" count={currentMOM.decisions.length} color="#10b981" />
        <StatBadge icon="⚡" label="Actions" count={currentMOM.actions.length} color="#f59e0b" />
      </div>

      {/* Participants Section - Extract from sections or participants field */}
      {(() => {
        // Try to get participants from multiple sources
        let participantsList: string[] = [];
        
        // 1. From direct participants field
        if (currentMOM.participants && currentMOM.participants.length > 0) {
          participantsList = currentMOM.participants;
        }
        
        // 2. From custom template sections (attendees field)
        if (participantsList.length === 0 && currentMOM.sections) {
          // Check meeting_info section for attendees
          const meetingInfo = currentMOM.sections['meeting_info'];
          if (meetingInfo && typeof meetingInfo === 'object') {
            const attendees = (meetingInfo as any).attendees;
            if (attendees && attendees !== 'N/A' && attendees !== '') {
              participantsList = attendees.split(',').map((n: string) => n.trim()).filter((n: string) => n);
            }
          }
          
          // Extract from action points (responsible_person)
          if (participantsList.length === 0) {
            const actionPoints = currentMOM.sections['action_points'];
            if (Array.isArray(actionPoints)) {
              const names = new Set<string>();
              actionPoints.forEach((action: any) => {
                const person = action.responsible_person || action.owner;
                if (person && person !== 'N/A' && person !== 'Not specified') {
                  names.add(person);
                }
              });
              participantsList = Array.from(names);
            }
          }
          
          // Extract from decisions (owner)
          if (participantsList.length === 0) {
            const decisions = currentMOM.sections['decisions_made'];
            if (Array.isArray(decisions)) {
              const names = new Set<string>();
              decisions.forEach((decision: any) => {
                const owner = decision.owner;
                if (owner && owner !== 'N/A' && owner !== 'Not specified' && owner !== 'Team') {
                  names.add(owner);
                }
              });
              participantsList = Array.from(names);
            }
          }
        }
        
        // 3. From standard actions/decisions
        if (participantsList.length === 0) {
          const names = new Set<string>();
          currentMOM.actions.forEach((action: any) => {
            if (action.owner && action.owner !== 'N/A' && action.owner !== 'Unassigned') {
              names.add(action.owner);
            }
          });
          currentMOM.decisions.forEach((decision: any) => {
            if (decision.owner && decision.owner !== 'N/A' && decision.owner !== 'Team') {
              names.add(decision.owner);
            }
          });
          participantsList = Array.from(names);
        }
        
        // Display participants if found
        if (participantsList.length > 0) {
          return (
            <div style={styles.participantsSection}>
              <div style={styles.participantsHeader}>
                <span style={styles.participantsIcon}>👥</span>
                <span style={styles.participantsTitle}>Meeting Participants</span>
                <span style={styles.participantsCount}>{participantsList.length}</span>
              </div>
              <div style={styles.participantsList}>
                {participantsList.map((name, idx) => (
                  <span key={idx} style={styles.participantChip}>{name}</span>
                ))}
              </div>
            </div>
          );
        }
        return null;
      })()}

      {/* ── Custom template sections ── */}
      {hasCustomTemplate ? (
        <>
          {currentMOM.template_structure!.sections.map((section: any, idx: number) => {
            const sectionData = currentMOM.sections![section.id];
            const sectionFields: any[] = (currentMOM.template_structure as any)?.fields?.[section.id] || [];

            return (
              <Section key={idx} title={section.label} accent="#3b82f6">
                {(!sectionData || sectionData === 'N/A' || (Array.isArray(sectionData) && sectionData.length === 0)) ? (
                  <div style={{ fontSize: 13, color: '#94a3b8', fontStyle: 'italic', padding: '4px 0' }}>N/A</div>
                ) : Array.isArray(sectionData) && sectionData.length > 0 && typeof sectionData[0] === 'object' ? (
                  // ── Render as Table ──
                  <DataTable 
                    data={sectionData} 
                    fields={sectionFields} 
                    accent="#3b82f6" 
                  />
                ) : (
                  // ── Render as Key-Value / Simple ──
                  <div style={styles.customFieldsContainer}>
                     {sectionFields.length > 0 ? (
                       sectionFields.map((field: any, fi: number) => {
                         const fieldId = field.id || (field.name || '').toLowerCase().replace(/\s+/g, '_');
                         const rawVal = typeof sectionData === 'object' && sectionData !== null && !Array.isArray(sectionData)
                           ? (sectionData as Record<string, unknown>)[fieldId]
                           : sectionData;
                         
                         // If field is part of template but missing in data, show N/A
                         const displayVal = (rawVal === undefined || rawVal === '' || rawVal === null) ? 'N/A' : rawVal;

                         return (
                           <div key={fi} style={styles.customField}>
                             <div style={styles.customFieldLabel}>{field.label || field.name}:</div>
                             <div style={styles.customFieldValue}>{renderValue(displayVal)}</div>
                           </div>
                         );
                       })
                    ) : typeof sectionData === 'object' && sectionData !== null && !Array.isArray(sectionData) ? (
                      Object.entries(sectionData as Record<string, unknown>)
                        .filter(([k]) => k !== 'label')
                        .map(([key, value], ki) => (
                          <div key={ki} style={styles.customField}>
                            <div style={styles.customFieldLabel}>
                              {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}:
                            </div>
                            <div style={styles.customFieldValue}>{renderValue(value)}</div>
                          </div>
                        ))
                    ) : (
                      <div style={styles.customFieldValue}>{renderValue(sectionData)}</div>
                    )}
                  </div>
                )}
              </Section>
            );
          })}


          {/* Smart duplication hiding: Only show standard sections if they ARE NOT covered by the custom template */}
          {currentMOM.topics.length > 0 && 
            currentMOM.format_id !== 'agile' && // agile usually wants 'Discussion Points' only
            !currentMOM.template_structure?.sections.some(s => {
              const id = s.id.toLowerCase();
              const lbl = (s.label || '').toLowerCase();
              return id.includes('topic') || id.includes('agenda') || id.includes('discussion') || id.includes('minutes') ||
                     lbl.includes('topic') || lbl.includes('agenda') || lbl.includes('discussion') || lbl.includes('summary');
            }) && (
              <Section title="Topics Discussed" accent="#3b82f6"><StandardTopics topics={currentMOM.topics} /></Section>
            )}

          {currentMOM.decisions.length > 0 && 
            currentMOM.format_id !== 'agile' && // agile doesn't show decisions by default
            !currentMOM.template_structure?.sections.some(s => {
              const id = s.id.toLowerCase();
              const lbl = (s.label || '').toLowerCase();
              return id.includes('decision') || id.includes('agree') || id.includes('conclu') ||
                     lbl.includes('decision') || lbl.includes('agree') || lbl.includes('resolution');
            }) && (
              <Section title="Decisions Made" accent="#10b981"><StandardDecisions decisions={currentMOM.decisions} /></Section>
            )}

          {currentMOM.actions.length > 0 && 
            !currentMOM.template_structure?.sections.some(s => {
              const id = s.id.toLowerCase();
              const lbl = (s.label || '').toLowerCase();
              return id.includes('action') || id.includes('task') || id.includes('todo') || id.includes('assign') || id.includes('next') ||
                     lbl.includes('action') || lbl.includes('task') || lbl.includes('todo') || lbl.includes('follow');
            }) && (
              <Section title="Action Items" accent="#f59e0b"><StandardActions actions={currentMOM.actions} /></Section>
            )}

        </>
      ) : (
        // ── Standard rendering ──
        <>
          {currentMOM.topics.length > 0 && (
            <Section title="Topics Discussed" accent="#3b82f6">
              <StandardTopics topics={currentMOM.topics} />
            </Section>
          )}
          {currentMOM.decisions.length > 0 && (
            <Section title="Decisions Made" accent="#10b981">
              <StandardDecisions decisions={currentMOM.decisions} />
            </Section>
          )}
          {currentMOM.actions.length > 0 && (
            <Section title="Action Items" accent="#f59e0b">
              <StandardActions actions={currentMOM.actions} />
            </Section>
          )}
        </>
      )}

      {/* Action buttons footer */}
      <div style={styles.downloadFooter}>
        <button 
          onClick={handleEditMOM}
          style={{
            ...styles.downloadBtnFull, 
            background: '#0ea5e9',
            cursor: 'pointer',
            border: 'none',
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ marginRight: 7 }}>
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Edit MOM
        </button>
        {downloadUrl && (
          <a href={downloadUrl} target="_blank" rel="noreferrer" style={styles.downloadBtnFull}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ marginRight: 7 }}>
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Download PDF
          </a>
        )}
        {excelUrl && (
          <a href={excelUrl} target="_blank" rel="noreferrer" style={{ ...styles.downloadBtnFull, background: '#064e3b' }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ marginRight: 7 }}>
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            Download Excel
          </a>
        )}
        <button 
          onClick={handleSendToTeams} 
          disabled={isSending}
          style={{
            ...styles.downloadBtnFull, 
            background: isSending ? '#64748b' : '#5b21b6',
            cursor: isSending ? 'not-allowed' : 'pointer',
            border: 'none',
            opacity: isSending ? 0.7 : 1,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ marginRight: 7 }}>
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" 
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {isSending ? 'Sending...' : 'Send to Teams'}
        </button>
        <button 
          onClick={handleAssignTasks} 
          disabled={currentMOM.actions.length === 0 || isAssigning}
          style={{
            ...styles.downloadBtnFull, 
            background: currentMOM.actions.length === 0 ? '#94a3b8' : isAssigning ? '#64748b' : '#ea580c',
            cursor: currentMOM.actions.length === 0 || isAssigning ? 'not-allowed' : 'pointer',
            border: 'none',
            opacity: currentMOM.actions.length === 0 ? 0.5 : isAssigning ? 0.7 : 1,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ marginRight: 7 }}>
            <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" 
              stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          {isAssigning ? 'Assigning...' : 'Assign Tasks'}
        </button>
      </div>

      {/* Send status message */}
      {sendStatus && (
        <div style={{
          ...styles.sendStatus,
          background: sendStatus.type === 'success' ? '#ecfdf5' : '#fef2f2',
          borderColor: sendStatus.type === 'success' ? '#10b981' : '#ef4444',
          color: sendStatus.type === 'success' ? '#065f46' : '#991b1b',
        }}>
          <span style={{ fontSize: 14 }}>
            {sendStatus.type === 'success' ? '✅' : '❌'}
          </span>
          <span style={{ fontSize: 13, fontWeight: 500 }}>
            {sendStatus.message}
          </span>
        </div>
      )}

      {/* Dev trace */}
      {devMode && (
        currentMOM.trace && currentMOM.trace.length > 0 ? (
          <DevTrace trace={currentMOM.trace} />
        ) : (
          <div style={styles.devNoTrace}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#475569' }}>🛠 Backend Process:</span>
            <span style={{ fontSize: 12, color: '#94a3b8', fontStyle: 'italic', marginLeft: 8 }}>
              No execution trace available for this session. Please generate a new MOM.
            </span>
          </div>
        )
      )}
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Section({ title, accent, children }: { title: string; accent: string; children: React.ReactNode }) {
  return (
    <div style={styles.section}>
      <div style={{ ...styles.sectionTitle, color: accent }}>{title}</div>
      <div style={styles.sectionBody}>{children}</div>
    </div>
  );
}

function StandardTopics({ topics }: { topics: any[] }) {
  return (
    <>
      {topics.map((t, i) => (
        <div key={i} style={styles.item}>
          <div style={styles.itemHeader}>
            <span style={styles.itemIndex}>{i + 1}</span>
            <span style={styles.itemTitle}>{t.title}</span>
            {t.timestamp && <span style={styles.itemTimestamp}>⏱ {t.timestamp}</span>}
          </div>
          {t.summary && <div style={styles.itemBody}>{t.summary}</div>}
        </div>
      ))}
    </>
  );
}

function StandardDecisions({ decisions }: { decisions: any[] }) {
  return (
    <>
      {decisions.map((d, i) => (
        <div key={i} style={styles.item}>
          <div style={styles.itemHeader}>
            <span style={{ ...styles.itemIndex, background: '#ecfdf5', color: '#059669' }}>{i + 1}</span>
            <span style={styles.itemBody}>{d.decision}</span>
          </div>
          <div style={styles.itemMeta}>
            <Chip>{d.owner}</Chip>
            {d.condition && <Chip color="#2563eb" bg="#eff6ff">{d.condition}</Chip>}
          </div>
        </div>
      ))}
    </>
  );
}

function StandardActions({ actions }: { actions: any[] }) {
  return (
    <>
      {actions.map((a, i) => {
        const p = PRIORITY_STYLE[a.priority] || PRIORITY_STYLE.medium;
        return (
          <div key={i} style={styles.item}>
            <div style={styles.actionRow}>
              <div style={{ ...styles.priorityStrip, background: p.color }} />
              <div style={styles.actionContent}>
                <div style={styles.actionTask}>{a.task}</div>
                <div style={styles.itemMeta}>
                  <Chip>{a.owner}</Chip>
                  {a.deadline && <Chip>📅 {a.deadline}</Chip>}
                  <Chip color={p.color} bg={p.bg}>{p.label}</Chip>
                  {a.ambiguous && <Chip color="#dc2626" bg="#fef2f2">⚠ Ambiguous</Chip>}
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}

function StatBadge({ icon, label, count, color }: { icon: string; label: string; count: number; color: string }) {
  return (
    <div style={{ ...styles.statBadge, borderColor: color + '30', background: color + '08' }}>
      <span style={styles.statIcon}>{icon}</span>
      <div>
        <div style={{ ...styles.statCount, color }}>{count}</div>
        <div style={styles.statLabel}>{label}</div>
      </div>
    </div>
  );
}

function Chip({ children, color = '#475569', bg = '#f1f5f9' }: { children: React.ReactNode; color?: string; bg?: string }) {
  return (
    <span style={{ ...styles.chip, color, background: bg }}>{children}</span>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    background: '#fff',
    borderRadius: 12,
    border: '1px solid #e2e8f0',
    overflow: 'hidden',
    width: '100%',
    maxWidth: 680,
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
  },
  header: {
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
    padding: '14px 18px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  headerIcon: { fontSize: 22, flexShrink: 0 },
  headerTitle: { fontWeight: 700, fontSize: 14, color: '#f8fafc', letterSpacing: '-0.2px' },
  headerMeta: { fontSize: 11, color: '#94a3b8', marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 },
  langTag: {
    background: 'rgba(245,158,11,0.2)',
    color: '#f59e0b',
    borderRadius: 4,
    padding: '1px 5px',
    fontSize: 10,
    fontWeight: 700,
  },
  downloadBtns: { display: 'flex', gap: 6, flexShrink: 0 },
  downloadBtnTop: {
    display: 'flex',
    alignItems: 'center',
    background: 'rgba(245,158,11,0.15)',
    border: '1px solid rgba(245,158,11,0.3)',
    borderRadius: 6,
    color: '#f59e0b',
    textDecoration: 'none',
    padding: '5px 10px',
    fontSize: 12,
    fontWeight: 600,
    flexShrink: 0,
  },
  stats: {
    display: 'flex',
    gap: 10,
    padding: '12px 16px',
    background: '#f8fafc',
    borderBottom: '1px solid #f1f5f9',
  },
  statBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flex: 1,
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
    padding: '8px 10px',
  },
  statIcon: { fontSize: 16 },
  statCount: { fontSize: 16, fontWeight: 700, lineHeight: 1 },
  statLabel: { fontSize: 10, color: '#94a3b8', marginTop: 1 },
  section: { padding: '14px 16px', borderBottom: '1px solid #f1f5f9' },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.7px',
    marginBottom: 10,
  },
  sectionBody: { display: 'flex', flexDirection: 'column', gap: 6 },
  item: {
    background: '#f8fafc',
    border: '1px solid #f1f5f9',
    borderRadius: 8,
    padding: '9px 12px',
  },
  itemHeader: { display: 'flex', alignItems: 'flex-start', gap: 8, flexWrap: 'wrap' },
  itemIndex: {
    background: '#e0e7ff',
    color: '#3730a3',
    borderRadius: 4,
    padding: '1px 6px',
    fontSize: 11,
    fontWeight: 700,
    flexShrink: 0,
    marginTop: 1,
  },
  itemTitle: { fontSize: 13, fontWeight: 600, color: '#0f172a', flex: 1 },
  itemTimestamp: { fontSize: 11, color: '#94a3b8', flexShrink: 0 },
  itemBody: { fontSize: 13, color: '#475569', lineHeight: 1.55, marginTop: 4 },
  itemMeta: { display: 'flex', flexWrap: 'wrap', gap: 5, marginTop: 7 },
  chip: { fontSize: 11, borderRadius: 5, padding: '2px 7px', fontWeight: 500 },
  actionRow: { display: 'flex', gap: 10 },
  priorityStrip: { width: 3, borderRadius: 2, flexShrink: 0, alignSelf: 'stretch', minHeight: 28 },
  actionContent: { flex: 1, minWidth: 0 },
  actionTask: { fontSize: 13, color: '#0f172a', fontWeight: 500, lineHeight: 1.5 },
  downloadFooter: { display: 'flex' },
  downloadBtnFull: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
    padding: '12px',
    background: '#0f172a',
    color: '#f8fafc',
    textDecoration: 'none',
    fontWeight: 600,
    fontSize: 13,
    transition: 'background 0.15s',
  },
  sendStatus: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '12px 16px',
    border: '1px solid',
    borderRadius: '0 0 12px 12px',
    marginTop: -1,
  },
  devTrace: {
    marginTop: 16,
    padding: '14px',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 8,
  },
  devTraceHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  devTraceBadge: {
    fontSize: 10,
    fontWeight: 700,
    color: '#6366f1',
    background: '#eef2ff',
    padding: '3px 8px',
    borderRadius: 4,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  devStepList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: 12,
  },
  devStep: {
    display: 'flex',
    gap: 12,
    alignItems: 'flex-start',
  },
  devStepDot: {
    width: 10,
    height: 10,
    borderRadius: '50%',
    marginTop: 4,
    flexShrink: 0,
  },
  devStepContent: {
    flex: 1,
    minWidth: 0,
  },
  devStepMain: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexWrap: 'wrap' as const,
  },
  devStepAgent: {
    fontSize: 12,
    fontWeight: 700,
    color: '#1e293b',
  },
  devStepStatus: {
    fontSize: 10,
    fontWeight: 700,
    padding: '2px 6px',
    borderRadius: 4,
  },
  devStepTime: {
    fontSize: 11,
    color: '#64748b',
    marginLeft: 'auto',
  },
  devStepReason: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 4,
    lineHeight: 1.5,
  },
  tableWrapper: {
    width: '100%',
    overflowX: 'auto' as const,
    margin: '8px 0',
    borderRadius: '8px',
    border: '1px solid #e2e8f0',
    background: '#fff',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '0.85rem',
  },
  th: {
    textAlign: 'left' as const,
    padding: '10px 12px',
    backgroundColor: '#f8fafc',
    color: '#475569',
    fontWeight: '700',
    textTransform: 'uppercase' as const,
    fontSize: '0.75rem',
    letterSpacing: '0.05em',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #f1f5f9',
    color: '#1e293b',
    verticalAlign: 'top' as const,
    lineHeight: '1.4',
  },
  trEven: {
    backgroundColor: '#f9fafb',
  },
  noData: {
    padding: '12px',
    color: '#94a3b8',
    fontSize: '0.85rem',
    fontStyle: 'italic' as const,
    textAlign: 'center' as const,
    background: '#f8fafc',
    borderRadius: '6px',
  },
  customFieldsContainer: { display: 'flex', flexDirection: 'column', gap: 6 },
  customField: {
    background: '#fff',
    border: '1px solid #f1f5f9',
    borderRadius: 6,
    padding: '8px 12px',
    display: 'flex',
    gap: 12,
    alignItems: 'baseline' as const,
  },
  devNoTrace: {
    marginTop: 16,
    padding: '12px 14px',
    background: '#f8fafc',
    border: '1px dashed #cbd5e1',
    borderRadius: 8,
    display: 'flex',
    alignItems: 'center',
  },
  customFieldLabel: {
    fontSize: 11,
    fontWeight: 700,
    color: '#64748b',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
    minWidth: 140,
    flexShrink: 0,
  },
  customFieldValue: { fontSize: 13, color: '#0f172a', flex: 1, lineHeight: 1.5 },
  participantsSection: {
    padding: '14px 16px',
    background: '#f8fafc',
    borderBottom: '1px solid #e2e8f0',
  },
  participantsHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  participantsIcon: {
    fontSize: 16,
  },
  participantsTitle: {
    fontSize: 12,
    fontWeight: 700,
    color: '#475569',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.5px',
  },
  participantsCount: {
    fontSize: 11,
    fontWeight: 700,
    color: '#3b82f6',
    background: '#eff6ff',
    padding: '2px 8px',
    borderRadius: 12,
  },
  participantsList: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 6,
  },
  participantChip: {
    fontSize: 12,
    fontWeight: 500,
    color: '#1e293b',
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 6,
    padding: '4px 10px',
  },
};

