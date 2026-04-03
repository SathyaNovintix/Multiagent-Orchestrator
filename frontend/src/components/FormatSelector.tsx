import { useEffect, useState, useRef } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface Format {
  id: string;
  name: string;
  description: string;
  icon: string;
  accent_color: string;
  is_custom?: boolean;
  template_structure?: {
    sections: Array<{ id: string; label: string }>;
    fields?: Record<string, any[]>;
    filename?: string;
    source?: string;
  };
}

interface Props {
  selectedId: string;
  onChange: (id: string) => void;
  disabled?: boolean;
}

/* ── Template preview definitions ─────────────────────────────────── */
const TEMPLATE_PREVIEWS: Record<string, { sections: { label: string; items: string[] }[]; headerColor: string }> = {
  standard: {
    headerColor: '#f59e0b',
    sections: [
      { label: 'Topics',    items: ['Q1 budget review', 'Team expansion plan'] },
      { label: 'Decisions', items: ['Approve new headcount', 'Delay product launch'] },
      { label: 'Actions',   items: ['John: draft budget by Fri', 'Sarah: schedule interviews'] },
    ],
  },
  agile: {
    headerColor: '#10b981',
    sections: [
      { label: 'Sprint Goals',   items: ['Complete auth module', 'Deploy staging'] },
      { label: 'Discussion',     items: ['Blocked on API keys', 'DB migration risk'] },
      { label: 'Action Items',   items: ['Dev: fix login bug', 'QA: run regression suite'] },
    ],
  },
  client: {
    headerColor: '#3b82f6',
    sections: [
      { label: 'Agenda Covered', items: ['Scope walkthrough', 'Timeline agreement'] },
      { label: 'Agreed Points',  items: ['Phase 1 by April 15', 'Weekly check-ins'] },
      { label: 'Follow-ups',     items: ['Send SOW by Monday', 'Client to provide access'] },
    ],
  },
  project: {
    headerColor: '#8b5cf6',
    sections: [
      { label: 'Status Update',  items: ['70% milestones done', 'CI pipeline live'] },
      { label: 'Milestones',     items: ['Beta release: Apr 20', 'UAT: May 1'] },
      { label: 'Next Steps',     items: ['Performance testing', 'Stakeholder sign-off'] },
    ],
  },
};

const FALLBACK_FORMATS: Format[] = [
  { id: 'standard', name: 'Standard MOM',  description: 'Classic minutes with topics, decisions, actions.', icon: '📋', accent_color: '#f59e0b' },
  { id: 'agile',    name: 'Agile / Sprint', description: 'Sprint retro: discussion points & action items.',  icon: '⚡', accent_color: '#10b981' },
  { id: 'client',   name: 'Client Meeting', description: 'Client-facing: agreed points & follow-ups.',       icon: '🤝', accent_color: '#3b82f6' },
  { id: 'project',  name: 'Project Review', description: 'Status updates, milestones, next steps.',          icon: '🗂️', accent_color: '#8b5cf6' },
];

export default function FormatSelector({ selectedId, onChange, disabled }: Props) {
  const [formats, setFormats]           = useState<Format[]>(FALLBACK_FORMATS);
  const [open, setOpen]                 = useState(false);
  const [activeTab, setActiveTab]       = useState<'formats' | 'custom'>('formats');
  const [previewId, setPreviewId]       = useState<string | null>(null);
  const [previewLocked, setPreviewLocked] = useState(false);
  const previewTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const [customName, setCustomName]     = useState('');
  const [customDesc, setCustomDesc]     = useState('');
  const [customColor, setCustomColor]   = useState('#6d28d9');
  const [templateFile, setTemplateFile] = useState<File | null>(null);
  const [templatePreview, setTemplatePreview] = useState<any>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadFormats();
  }, []);

  const loadFormats = () => {
    axios.get(`${API_BASE}/formats`)
      .then(r => { 
        console.log('[FormatSelector] Loaded formats:', r.data.formats);
        if (r.data.formats?.length) setFormats(r.data.formats); 
      })
      .catch(err => {
        console.error('[FormatSelector] Failed to load formats:', err);
      });
  };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) {
        setOpen(false); setPreviewId(null); setPreviewLocked(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => {
      document.removeEventListener('mousedown', handler);
      if (previewTimeoutRef.current) clearTimeout(previewTimeoutRef.current);
    };
  }, []);

  const selected = formats.find(f => f.id === selectedId) || formats[0];
  const previewFormat = previewId ? formats.find(f => f.id === previewId) : null;
  const preview = previewId ? TEMPLATE_PREVIEWS[previewId] : null;
  
  // Generate preview for custom templates
  const customPreview = previewFormat?.template_structure?.sections ? {
    headerColor: previewFormat.accent_color,
    sections: previewFormat.template_structure.sections.slice(0, 8).map((s: any) => {
      const fields = previewFormat.template_structure?.fields?.[s.id];
      let items: string[] = [];
      
      if (fields && fields.length > 0) {
        // Show actual field names from the template
        items = fields.slice(0, 4).map((f: any) => {
          // If there's a sample value, show it
          if (f.sample) {
            return `${f.name}: ${f.sample}`;
          }
          return f.name;
        });
      } else {
        // If no fields, show the section as a simple header
        items = ['(Metadata field)'];
      }
      
      return {
        label: s.label,
        items: items
      };
    })
  } : null;

  const handleAddCustom = async () => {
    if (!customName.trim()) return;
    setUploading(true);
    try {
      // Use FormData to support file upload
      const formData = new FormData();
      formData.append('name', customName);
      formData.append('description', customDesc);
      formData.append('accent_color', customColor);
      formData.append('header_color', '#1a1a2e');
      formData.append('sections', 'topics,decisions,actions');
      
      if (templateFile) {
        formData.append('template_file', templateFile);
      }
      
      const r = await axios.post(`${API_BASE}/formats/custom`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      const newFmt = r.data.format;
      // Reload all formats from server to ensure persistence
      loadFormats();
      onChange(newFmt.id);
      setActiveTab('formats');
      setCustomName(''); setCustomDesc(''); setCustomColor('#6d28d9');
      setTemplateFile(null); setTemplatePreview(null);
      setOpen(false);
      alert(`✓ Custom format "${newFmt.name}" added successfully!`);
    } catch (err: any) {
      alert(`Could not save custom format: ${err.response?.data?.detail || err.message || 'Backend not reachable'}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div ref={wrapRef} style={styles.wrap}>
      {/* Debug info */}
      {import.meta.env.DEV && (
        <div style={{ fontSize: 10, color: open ? '#10b981' : '#999', marginBottom: 4, fontWeight: open ? 'bold' : 'normal' }}>
          Formats loaded: {formats.length} | Open: {open ? 'YES ✓' : 'No'} | Disabled: {disabled ? 'Yes' : 'No'}
        </div>
      )}
      
      {/* Trigger button */}
      <button
        style={{
          ...styles.trigger,
          borderColor: open ? selected.accent_color : '#e2e8f0',
          opacity: disabled ? 0.6 : 1,
          cursor: disabled ? 'not-allowed' : 'pointer',
          boxShadow: open ? '0 0 0 3px rgba(245, 158, 11, 0.1)' : 'none',
        }}
        onMouseEnter={(e) => {
          if (!disabled) {
            e.currentTarget.style.borderColor = selected.accent_color;
            e.currentTarget.style.background = '#ffffff';
          }
        }}
        onMouseLeave={(e) => {
          if (!open) {
            e.currentTarget.style.borderColor = '#e2e8f0';
            e.currentTarget.style.background = '#f8fafc';
          }
        }}
        onClick={() => { 
          console.log('[FormatSelector] Button clicked! Disabled:', disabled, 'Current open:', open);
          setOpen(o => {
            console.log('[FormatSelector] Setting open from', o, 'to', !o);
            return !o;
          }); 
          setPreviewId(null);
        }}
        title="Click to select MOM output format"
      >
        <span style={{ ...styles.dot, background: selected.accent_color }} />
        <span style={styles.triggerIcon}>{selected.icon}</span>
        <span style={styles.triggerName}>{selected.name}</span>
        <span style={{ fontSize: 10, color: '#94a3b8', marginLeft: 4 }}>({formats.length})</span>
        <svg width="10" height="10" viewBox="0 0 24 24" fill="none"
          style={{ transform: open ? 'rotate(180deg)' : undefined, transition: 'transform 0.15s', marginLeft: 'auto' }}>
          <path d="M6 9l6 6 6-6" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </button>

      {/* Dropdown panel */}
      {open && (
        <div style={styles.panel}>
          {/* Tabs */}
          <div style={styles.tabs}>
            <button
              style={{ ...styles.tab, ...(activeTab === 'formats' ? styles.tabActive : {}) }}
              onClick={() => { setActiveTab('formats'); setPreviewId(null); }}
            >Templates</button>
            <button
              style={{ ...styles.tab, ...(activeTab === 'custom' ? styles.tabActive : {}) }}
              onClick={() => setActiveTab('custom')}
            >+ Custom</button>
          </div>

          {activeTab === 'formats' && (
            <div style={styles.formatsPane}>
              {/* Format list */}
              <div style={styles.formatList}>
                {formats.map(f => (
                  <button
                    key={f.id}
                    style={{
                      ...styles.formatRow,
                      borderLeft: f.id === selectedId ? `3px solid ${f.accent_color}` : '3px solid transparent',
                      background: f.id === selectedId ? '#f8fafc' : (previewId === f.id ? '#f1f5f9' : '#fff'),
                    }}
                    onClick={() => { onChange(f.id); setOpen(false); setPreviewId(null); setPreviewLocked(false); }}
                    onMouseEnter={() => {
                      if (previewTimeoutRef.current) clearTimeout(previewTimeoutRef.current);
                      // Show preview for built-in formats or custom formats with template structure
                      if (TEMPLATE_PREVIEWS[f.id] || f.template_structure?.sections) {
                        setPreviewId(f.id);
                      }
                    }}
                    onMouseLeave={() => {
                      if (!previewLocked) {
                        previewTimeoutRef.current = setTimeout(() => {
                          setPreviewId(null);
                        }, 150);
                      }
                    }}
                  >
                    <span style={styles.fIcon}>{f.icon}</span>
                    <div style={styles.fText}>
                      <div style={styles.fName}>{f.name}</div>
                      <div style={styles.fDesc}>{f.description}</div>
                    </div>
                    {f.id === selectedId && (
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
                        <path d="M20 6L9 17l-5-5" stroke={f.accent_color} strokeWidth="2.5" strokeLinecap="round" />
                      </svg>
                    )}
                    {f.is_custom && <span style={styles.customBadge}>custom</span>}
                    {f.template_structure && (
                      <span style={styles.templateBadge} title={`Template: ${f.template_structure.filename || 'uploaded'}`}>
                        {f.template_structure.source === 'excel' ? '📊' : f.template_structure.source === 'csv' ? '📊' : '📄'}
                      </span>
                    )}
                    {(TEMPLATE_PREVIEWS[f.id] || f.template_structure?.sections) && (
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, opacity: 0.4, marginLeft: 2 }}>
                        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#64748b" strokeWidth="2" />
                        <circle cx="12" cy="12" r="3" stroke="#64748b" strokeWidth="2" />
                      </svg>
                    )}
                  </button>
                ))}
              </div>

              {/* Preview pane */}
              {(preview || customPreview) && (
                <div 
                  style={styles.previewPane}
                  onMouseEnter={() => {
                    if (previewTimeoutRef.current) clearTimeout(previewTimeoutRef.current);
                    setPreviewLocked(true);
                  }}
                  onMouseLeave={() => {
                    setPreviewLocked(false);
                    setPreviewId(null);
                  }}
                >
                  <div style={styles.previewLabel}>Template Preview</div>
                  <div style={styles.previewCard}>
                    {/* Mini MOM header */}
                    <div style={{ ...styles.previewHeader, background: (preview || customPreview)!.headerColor }}>
                      <span style={styles.previewHeaderTitle}>
                        {previewFormat?.name || 'Minutes of Meeting'}
                      </span>
                    </div>
                    {(preview || customPreview)!.sections.map((sec, si) => (
                      <div key={si} style={styles.previewSection}>
                        <div style={{ ...styles.previewSectionLabel, color: (preview || customPreview)!.headerColor }}>
                          {sec.label}
                        </div>
                        {sec.items.slice(0, 2).map((item, ii) => (
                          <div key={ii} style={styles.previewItem}>
                            <div style={{ ...styles.previewItemDot, background: (preview || customPreview)!.headerColor }} />
                            <span>{item}</span>
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                  <div style={styles.previewHint}>
                    {customPreview ? 'Custom template structure' : 'Hover each template to preview its structure'}
                  </div>
                </div>
              )}
              {!preview && !customPreview && (
                <div style={styles.previewEmpty}>
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" style={{ opacity: 0.25 }}>
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" stroke="#64748b" strokeWidth="1.5" />
                    <circle cx="12" cy="12" r="3" stroke="#64748b" strokeWidth="1.5" />
                  </svg>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6, textAlign: 'center' }}>
                    Hover a template<br />to preview its layout
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === 'custom' && (
            <div style={styles.customPane}>
              <div style={styles.customTitle}>Create Custom Format</div>

              <label style={styles.fieldLabel}>Format name *</label>
              <input
                style={styles.input}
                placeholder="e.g. Board Meeting"
                value={customName}
                onChange={e => setCustomName(e.target.value)}
              />

              <label style={styles.fieldLabel}>Description</label>
              <input
                style={styles.input}
                placeholder="Short description of this format"
                value={customDesc}
                onChange={e => setCustomDesc(e.target.value)}
              />

              <label style={styles.fieldLabel}>Accent color</label>
              <div style={styles.colorRow}>
                <input
                  type="color"
                  value={customColor}
                  onChange={e => setCustomColor(e.target.value)}
                  style={styles.colorPicker}
                />
                <span style={{ ...styles.colorSwatch, background: customColor }} />
                <span style={styles.colorHex}>{customColor}</span>
              </div>

              {/* Template file upload */}
              <label style={styles.fieldLabel}>Template file <span style={styles.optional}>(Excel, Word, or CSV)</span></label>
              <div
                style={{
                  ...styles.uploadZone,
                  borderColor: templateFile ? '#10b981' : '#e2e8f0',
                  background: templateFile ? '#ecfdf5' : '#f8fafc',
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xlsx,.xls,.csv,.docx,.doc"
                  style={{ display: 'none' }}
                  onChange={async (e) => { 
                    const f = e.target.files?.[0]; 
                    if (f) {
                      setTemplateFile(f);
                      setTemplatePreview(null);
                      setPreviewLoading(true);
                      console.log('[FormatSelector] Uploading template for preview:', f.name);
                      
                      // Parse and preview the template
                      try {
                        const formData = new FormData();
                        formData.append('template_file', f);
                        console.log('[FormatSelector] Calling preview endpoint...');
                        const r = await axios.post(`${API_BASE}/formats/preview`, formData, {
                          headers: { 'Content-Type': 'multipart/form-data' }
                        });
                        console.log('[FormatSelector] Preview response:', r.data);
                        setTemplatePreview(r.data);
                      } catch (err: any) {
                        console.error('[FormatSelector] Failed to preview template:', err);
                        alert(`Could not preview template: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
                        setTemplatePreview(null);
                      } finally {
                        setPreviewLoading(false);
                      }
                    }
                    e.target.value = ''; 
                  }}
                />
                {templateFile ? (
                  <div style={styles.uploadedFile}>
                    <span style={styles.fileIcon}>
                      {templateFile.name.includes('.xls') || templateFile.name.includes('.csv') ? '📊' : '📄'}
                    </span>
                    <div>
                      <div style={styles.fileName}>{templateFile.name}</div>
                      <div style={styles.fileSize}>{(templateFile.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <button
                      style={styles.removeFile}
                      onClick={e => { e.stopPropagation(); setTemplateFile(null); setTemplatePreview(null); }}
                    >✕</button>
                  </div>
                ) : (
                  <div style={styles.uploadPlaceholder}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" style={{ opacity: 0.4 }}>
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"
                        stroke="#64748b" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span style={styles.uploadText}>Click to upload template file</span>
                    <span style={styles.uploadSubText}>Supports .xlsx, .xls, .csv, .docx, .doc formats</span>
                    <span style={styles.uploadSubText}>AI will extract structure automatically</span>
                  </div>
                )}
              </div>

              {/* Template preview hint */}
              {templateFile && previewLoading && (
                <div style={styles.templateHint}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0, animation: 'spin 1s linear infinite' }}>
                    <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"
                      stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                  Analyzing template structure...
                </div>
              )}

              {templateFile && !previewLoading && !templatePreview && (
                <div style={styles.templateHint}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
                    <circle cx="12" cy="12" r="10" stroke="#10b981" strokeWidth="2" />
                    <path d="M12 16v-4M12 8h.01" stroke="#10b981" strokeWidth="2" strokeLinecap="round" />
                  </svg>
                  Template uploaded! Ready to save.
                </div>
              )}

              {/* Template structure preview */}
              {templatePreview && (
                <div style={styles.previewBox}>
                  <div style={styles.previewTitle}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
                      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                        stroke="#0f172a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    Detected Structure
                  </div>
                  {templatePreview.sections && templatePreview.sections.length > 0 ? (
                    <>
                      <div style={styles.previewSections}>
                        {templatePreview.sections.map((section: any, idx: number) => (
                          <div key={idx} style={styles.previewSectionItem}>
                            <span style={{ ...styles.previewSectionDot, background: customColor }} />
                            <span style={styles.previewSectionLabel}>{section.label}</span>
                            {templatePreview.fields && templatePreview.fields[section.id] && (
                              <span style={styles.previewFieldCount}>
                                {templatePreview.fields[section.id].length} fields
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                      <div style={styles.previewFooter}>
                        ✓ {templatePreview.sections.length} section{templatePreview.sections.length !== 1 ? 's' : ''} detected from {templatePreview.source} file
                      </div>
                    </>
                  ) : (
                    <div style={styles.previewEmpty}>
                      No clear structure detected. Standard format will be used.
                    </div>
                  )}
                </div>
              )}

              <div style={styles.customActions}>
                <button
                  style={{ ...styles.saveBtn, opacity: (customName.trim() && !uploading) ? 1 : 0.5 }}
                  disabled={!customName.trim() || uploading}
                  onClick={handleAddCustom}
                >
                  {uploading ? 'Saving...' : '✓ Save Format & Add to Library'}
                </button>
                <button style={styles.cancelBtn} onClick={() => { setActiveTab('formats'); setTemplateFile(null); setTemplatePreview(null); }}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrap: { position: 'relative', flexShrink: 0, zIndex: 1 },

  trigger: {
    display: 'flex', alignItems: 'center', gap: 6,
    background: '#f8fafc', border: '1.5px solid #e2e8f0',
    borderRadius: 7, padding: '5px 9px', cursor: 'pointer',
    fontSize: 13, color: '#0f172a', whiteSpace: 'nowrap',
    fontWeight: 500, transition: 'all 0.15s',
  },
  dot: { width: 7, height: 7, borderRadius: '50%', flexShrink: 0 },
  triggerIcon: { fontSize: 14 },
  triggerName: { fontWeight: 600, fontSize: 12 },

  /* Panel */
  panel: {
    position: 'absolute',
    bottom: 'calc(100% + 8px)',
    left: 0,
    background: '#fff',
    border: '1px solid #e2e8f0',
    borderRadius: 12,
    boxShadow: '0 12px 40px rgba(0,0,0,0.14)',
    zIndex: 9999,
    overflow: 'hidden',
    minWidth: 560,
    maxHeight: '70vh',
  },

  /* Tabs */
  tabs: {
    display: 'flex',
    borderBottom: '1px solid #f1f5f9',
    padding: '6px 8px 0',
    gap: 2,
  },
  tab: {
    padding: '7px 14px',
    border: 'none', background: 'none',
    fontSize: 12, fontWeight: 600, cursor: 'pointer',
    color: '#94a3b8', borderRadius: '6px 6px 0 0',
    transition: 'color 0.15s',
  },
  tabActive: {
    color: '#0f172a',
    background: '#f8fafc',
    borderBottom: '2px solid #f59e0b',
  },

  /* Formats tab */
  formatsPane: {
    display: 'flex',
    minHeight: 240,
  },
  formatList: {
    width: 240,
    borderRight: '1px solid #f1f5f9',
    overflowY: 'auto',
    padding: '6px 0',
    maxHeight: '50vh',
  },
  formatRow: {
    width: '100%', display: 'flex', alignItems: 'center',
    gap: 9, padding: '9px 12px', border: 'none',
    cursor: 'pointer', textAlign: 'left', transition: 'background 0.1s',
  },
  fIcon: { fontSize: 18, flexShrink: 0 },
  fText: { flex: 1, minWidth: 0 },
  fName: { fontSize: 13, fontWeight: 600, color: '#0f172a' },
  fDesc: { fontSize: 11, color: '#94a3b8', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  customBadge: {
    fontSize: 10, background: '#ede9fe', color: '#7c3aed',
    borderRadius: 4, padding: '1px 5px', fontWeight: 600, flexShrink: 0,
  },
  templateBadge: {
    fontSize: 12, flexShrink: 0, opacity: 0.7,
  },

  /* Preview pane */
  previewPane: {
    flex: 1, padding: '12px 14px', display: 'flex', flexDirection: 'column',
    overflowY: 'auto', maxHeight: '50vh',
  },
  previewLabel: {
    fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
    letterSpacing: '0.7px', color: '#94a3b8', marginBottom: 8,
  },
  previewCard: {
    border: '1px solid #e2e8f0', borderRadius: 8, overflow: 'auto',
    flex: 1, maxHeight: '40vh',
  },
  previewHeader: {
    padding: '7px 10px',
  },
  previewHeaderTitle: { fontSize: 11, fontWeight: 700, color: '#fff' },
  previewSection: { padding: '7px 10px', borderBottom: '1px solid #f8fafc' },
  previewSectionLabel: {
    fontSize: 9, fontWeight: 700, textTransform: 'uppercase',
    letterSpacing: '0.6px', marginBottom: 5,
  },
  previewItem: {
    display: 'flex', alignItems: 'flex-start', gap: 5,
    fontSize: 10, color: '#475569', marginBottom: 3,
  },
  previewItemDot: {
    width: 4, height: 4, borderRadius: '50%', flexShrink: 0, marginTop: 3,
  },
  previewHint: {
    fontSize: 10, color: '#cbd5e1', marginTop: 6, textAlign: 'center',
  },
  previewEmpty: {
    flex: 1, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: '0 14px',
  },

  /* Custom tab */
  customPane: {
    padding: '14px 16px',
    minWidth: 300,
    maxWidth: 500,
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
    maxHeight: '60vh',
    overflowY: 'auto',
  },
  customTitle: {
    fontSize: 13, fontWeight: 700, color: '#0f172a', marginBottom: 12,
  },
  fieldLabel: {
    fontSize: 11, fontWeight: 600, color: '#64748b',
    textTransform: 'uppercase', letterSpacing: '0.5px',
    display: 'block', marginBottom: 5,
  },
  optional: { fontWeight: 400, textTransform: 'none', letterSpacing: 0, color: '#94a3b8' },
  input: {
    width: '100%', border: '1px solid #e2e8f0', borderRadius: 7,
    padding: '7px 10px', fontSize: 13, outline: 'none',
    background: '#f8fafc', color: '#0f172a', marginBottom: 10,
  },
  colorRow: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 },
  colorPicker: { width: 36, height: 30, border: '1px solid #e2e8f0', borderRadius: 6, cursor: 'pointer', padding: 2 },
  colorSwatch: { width: 22, height: 22, borderRadius: 5, border: '1px solid rgba(0,0,0,0.08)' },
  colorHex: { fontSize: 12, color: '#64748b', fontFamily: 'monospace' },

  /* Upload zone */
  uploadZone: {
    border: '1.5px dashed #e2e8f0', borderRadius: 8, cursor: 'pointer',
    transition: 'all 0.15s', marginBottom: 12,
  },
  uploadPlaceholder: {
    padding: '14px 12px', display: 'flex', flexDirection: 'column',
    alignItems: 'center', gap: 4, textAlign: 'center',
  },
  uploadText: { fontSize: 12, color: '#64748b', fontWeight: 500 },
  uploadSubText: { fontSize: 11, color: '#94a3b8' },
  templateHint: {
    display: 'flex', alignItems: 'center', gap: 6,
    background: '#ecfdf5', border: '1px solid #a7f3d0',
    borderRadius: 6, padding: '8px 10px', fontSize: 11,
    color: '#047857', marginTop: -6, marginBottom: 10,
  },
  previewBox: {
    background: '#f8fafc', border: '1px solid #e2e8f0',
    borderRadius: 8, padding: '12px', marginBottom: 12,
  },
  previewTitle: {
    display: 'flex', alignItems: 'center', gap: 6,
    fontSize: 11, fontWeight: 700, color: '#0f172a',
    marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px',
  },
  previewSections: {
    display: 'flex', flexDirection: 'column', gap: 6,
  },
  previewSectionItem: {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '6px 8px', background: '#fff',
    borderRadius: 6, border: '1px solid #e2e8f0',
  },
  previewSectionDot: {
    width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
  },
  previewSectionLabelCustom: {
    fontSize: 12, fontWeight: 600, color: '#0f172a', flex: 1,
  },
  previewFieldCount: {
    fontSize: 10, color: '#64748b', background: '#f1f5f9',
    padding: '2px 6px', borderRadius: 4,
  },
  previewFooter: {
    fontSize: 10, color: '#10b981', marginTop: 8,
    paddingTop: 8, borderTop: '1px solid #e2e8f0',
  },
  previewEmptyCustom: {
    fontSize: 11, color: '#94a3b8', fontStyle: 'italic',
    textAlign: 'center', padding: '8px 0',
  },
  uploadedFile: {
    padding: '10px 12px', display: 'flex', alignItems: 'center', gap: 10,
  },
  fileIcon: { fontSize: 22, flexShrink: 0 },
  fileName: { fontSize: 12, fontWeight: 600, color: '#0f172a' },
  fileSize: { fontSize: 11, color: '#64748b' },
  removeFile: {
    marginLeft: 'auto', background: 'none', border: 'none',
    cursor: 'pointer', color: '#94a3b8', fontSize: 13, padding: '2px 4px',
  },

  customActions: { display: 'flex', gap: 7, marginTop: 2 },
  saveBtn: {
    flex: 1, background: '#0f172a', color: '#fff', border: 'none',
    borderRadius: 7, padding: '8px', cursor: 'pointer', fontWeight: 600, fontSize: 12,
  },
  cancelBtn: {
    flex: 1, background: '#f1f5f9', color: '#475569', border: 'none',
    borderRadius: 7, padding: '8px', cursor: 'pointer', fontSize: 12, fontWeight: 500,
  },
};
