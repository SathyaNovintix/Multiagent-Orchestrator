import { useState, useRef } from 'react';
import type { KeyboardEvent } from 'react';
import FormatSelector from './FormatSelector';

interface Props {
  onSendText: (text: string, formatId: string) => void;
  onSendAudio: (file: File, formatId: string) => void;
  disabled: boolean;
}

const ACCEPTED = '.mp3,.wav,.m4a,.ogg,.flac,.webm';
const MAX_MB = 100;

const VOICE_LANGUAGES = [
  { code: 'en-US', label: 'English' },
  { code: 'ta-IN', label: 'தமிழ்' },
  { code: 'hi-IN', label: 'हिंदी' },
];

export default function InputBar({ onSendText, onSendAudio, disabled }: Props) {
  const [text, setText]           = useState('');
  const [formatId, setFormatId]   = useState('standard');
  const [dragOver, setDragOver]   = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [voiceLang, setVoiceLang] = useState('en-US');
  const fileRef     = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);
  const accumulatedTranscript = useRef<string>('');

  // Initialize Web Speech API
  const startVoiceRecording = () => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setFileError('Speech recognition not supported in this browser. Use Chrome.');
      return;
    }

    // Store current text as base, will accumulate new speech on top
    accumulatedTranscript.current = text;

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = voiceLang; // User-selected language
    recognition.maxAlternatives = 1;
    
    recognition.onstart = () => {
      setIsRecording(true);
      setFileError(null);
      console.log('🎤 Voice recording started - speak now');
    };
    
    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      
      // Process all results from this event
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          // Add final result to accumulated transcript
          accumulatedTranscript.current += transcript + ' ';
          console.log('✅ Final:', transcript);
        } else {
          // Collect interim results
          interimTranscript += transcript;
        }
      }
      
      // Update display with accumulated + interim
      setText(accumulatedTranscript.current + interimTranscript);
    };
    
    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      if (event.error === 'no-speech') {
        // Auto-restart on no-speech to keep listening
        if (isRecording && recognitionRef.current) {
          console.log('🎤 No speech detected, restarting...');
          setTimeout(() => {
            if (recognitionRef.current && isRecording) {
              try {
                recognition.start();
              } catch (e) {
                console.error('Failed to restart:', e);
              }
            }
          }, 100);
        }
      } else if (event.error === 'not-allowed') {
        setFileError('Microphone access denied. Please allow microphone permissions in your browser.');
        setIsRecording(false);
      } else if (event.error === 'network') {
        setFileError('Network error. Check your internet connection.');
        setIsRecording(false);
      } else if (event.error !== 'aborted') {
        setFileError(`Speech recognition error: ${event.error}`);
        setIsRecording(false);
      }
    };
    
    recognition.onend = () => {
      console.log('🎤 Voice recording ended');
      // Only set recording to false if user manually stopped it
      if (!isRecording) {
        setIsRecording(false);
      }
    };
    
    recognitionRef.current = recognition;
    
    try {
      recognition.start();
    } catch (err: any) {
      setFileError(`Failed to start recording: ${err.message}`);
      setIsRecording(false);
    }
  };

  const stopVoiceRecording = () => {
    if (recognitionRef.current) {
      try {
        setIsRecording(false); // Set this first to prevent auto-restart
        recognitionRef.current.stop();
        console.log('🎤 Stopping voice recording');
      } catch (err: any) {
        console.error('Error stopping recording:', err);
        setIsRecording(false);
      }
    }
  };

  const handleSend = () => {
    if (text.trim()) {
      onSendText(text.trim(), formatId);
      setText('');
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  const validateAndSend = (file: File) => {
    setFileError(null);
    if (file.size > MAX_MB * 1024 * 1024) { setFileError(`File exceeds ${MAX_MB} MB limit.`); return; }
    onSendAudio(file, formatId);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndSend(file);
    e.target.value = '';
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) validateAndSend(file);
  };

  const canSend = !!text.trim() && !disabled;

  return (
    <div style={styles.shell}>
      {/* Error */}
      {fileError && (
        <div style={styles.errorBar}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" style={{ flexShrink: 0 }}>
            <circle cx="12" cy="12" r="10" stroke="#dc2626" strokeWidth="2" />
            <path d="M12 8v4M12 16h.01" stroke="#dc2626" strokeWidth="2" strokeLinecap="round" />
          </svg>
          {fileError}
          <button style={styles.errorClose} onClick={() => setFileError(null)}>✕</button>
        </div>
      )}

      {/* Main compose box */}
      <div
        style={{
          ...styles.compose,
          borderColor: dragOver ? '#f59e0b' : '#e2e8f0',
          background: dragOver ? '#fffbeb' : '#fff',
          opacity: disabled ? 0.65 : 1,
        }}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
      >
        {/* Top meta-row: format selector + attach */}
        <div style={styles.metaRow}>
          <div style={styles.metaLeft}>
            <span style={styles.metaLabel}>Format</span>
            <FormatSelector selectedId={formatId} onChange={setFormatId} disabled={disabled} />
          </div>
          <div style={styles.metaRight}>
            {/* Language selector for voice recording */}
            <select
              style={styles.langSelect}
              value={voiceLang}
              onChange={(e) => setVoiceLang(e.target.value)}
              disabled={disabled || isRecording}
              title="Voice recording language"
            >
              {VOICE_LANGUAGES.map(lang => (
                <option key={lang.code} value={lang.code}>{lang.label}</option>
              ))}
            </select>
            <button
              style={{
                ...styles.voiceBtn,
                background: isRecording ? '#ef4444' : '#fff',
                color: isRecording ? '#fff' : '#64748b',
              }}
              title={isRecording ? "Stop recording" : "Start voice recording"}
              disabled={disabled}
              onClick={isRecording ? stopVoiceRecording : startVoiceRecording}
            >
              {isRecording ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="6" width="12" height="12" rx="2" />
                </svg>
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v4M8 23h8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              {isRecording ? 'Stop' : 'Voice'}
            </button>
            <button
              style={styles.attachBtn}
              title="Upload audio (.mp3 .wav .m4a .ogg .flac .webm)"
              disabled={disabled}
              onClick={() => fileRef.current?.click()}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Attach audio
            </button>
            <input ref={fileRef} type="file" accept={ACCEPTED} style={{ display: 'none' }} onChange={handleFileChange} />
          </div>
        </div>

        {/* Divider */}
        <div style={styles.divider} />

        {/* Text input row */}
        <div style={styles.inputRow}>
          <textarea
            ref={textareaRef}
            style={styles.textarea}
            placeholder="Paste a meeting transcript or type a message…  (Shift+Enter for new line)"
            value={text}
            onChange={handleInput}
            onKeyDown={handleKey}
            disabled={disabled}
            rows={1}
          />
          <button
            style={{ ...styles.sendBtn, background: canSend ? '#0f172a' : '#e2e8f0' }}
            disabled={!canSend}
            onClick={handleSend}
            title="Send (Enter)"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"
                stroke={canSend ? '#fff' : '#94a3b8'} strokeWidth="2"
                strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      {/* Hint */}
      <div style={styles.hint}>
        {isRecording ? '🔴 Recording... Speak now, then click Stop when done'
          : dragOver ? '⬇ Drop audio file here to upload'
          : 'Text transcript · Voice recording (speak clearly) · Drag & drop audio · mp3 · wav · m4a · ogg · flac · webm · max 100 MB'}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  shell: {
    background: '#ffffff',
    borderTop: '1px solid #e2e8f0',
    padding: '10px 20px 12px',
    flexShrink: 0,
  },
  errorBar: {
    display: 'flex', alignItems: 'center', gap: 7,
    background: '#fef2f2', border: '1px solid #fecaca',
    borderRadius: 7, padding: '6px 10px',
    fontSize: 12, color: '#dc2626', marginBottom: 8,
  },
  errorClose: {
    marginLeft: 'auto', background: 'none', border: 'none',
    cursor: 'pointer', color: '#dc2626', fontSize: 12,
  },
  compose: {
    border: '1.5px solid #e2e8f0',
    borderRadius: 12,
    overflow: 'visible',
    transition: 'border-color 0.15s, background 0.15s',
  },
  metaRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '7px 12px 6px',
    background: '#f8fafc',
    gap: 12,
  },
  metaLeft: {
    display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0,
  },
  metaLabel: {
    fontSize: 11, fontWeight: 700, color: '#94a3b8',
    textTransform: 'uppercase', letterSpacing: '0.6px', flexShrink: 0,
  },
  metaRight: {
    display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0,
  },
  attachBtn: {
    display: 'flex', alignItems: 'center', gap: 5,
    background: '#fff', border: '1px solid #e2e8f0',
    borderRadius: 6, padding: '5px 10px',
    fontSize: 12, color: '#64748b', cursor: 'pointer',
    fontWeight: 500, transition: 'all 0.15s',
  },
  langSelect: {
    border: '1px solid #e2e8f0',
    borderRadius: 6, padding: '5px 8px',
    fontSize: 12, color: '#64748b',
    background: '#fff', cursor: 'pointer',
    fontWeight: 500, outline: 'none',
  },
  voiceBtn: {
    display: 'flex', alignItems: 'center', gap: 5,
    border: '1px solid #e2e8f0',
    borderRadius: 6, padding: '5px 10px',
    fontSize: 12, cursor: 'pointer',
    fontWeight: 500, transition: 'all 0.15s',
  },
  divider: { height: 1, background: '#f1f5f9' },
  inputRow: {
    display: 'flex', alignItems: 'flex-end',
    padding: '8px 10px 8px 14px', gap: 8,
  },
  textarea: {
    flex: 1, border: 'none', background: 'transparent',
    resize: 'none', fontSize: 14, lineHeight: 1.55,
    outline: 'none', color: '#0f172a',
    maxHeight: 160, overflowY: 'auto', minHeight: 22,
  },
  sendBtn: {
    width: 34, height: 34, border: 'none', borderRadius: 8,
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0, cursor: 'pointer', transition: 'background 0.15s',
  },
  hint: {
    fontSize: 11, color: '#cbd5e1', marginTop: 7,
    textAlign: 'center', letterSpacing: '0.1px',
  },
};
