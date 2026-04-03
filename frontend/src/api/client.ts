import axios from 'axios';
import type { Message } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const api = axios.create({ baseURL: API_BASE });

// ── Sessions ──────────────────────────────────────────────────────────────

export async function createSession(label?: string): Promise<{ session_id: string; label: string; created_at: string }> {
  const res = await api.post('/session', { label });
  return res.data;
}

export async function fetchSessions(): Promise<{ session_id: string; label: string; created_at: string }[]> {
  const res = await api.get('/sessions');
  return res.data.sessions;
}

// ── Messages ──────────────────────────────────────────────────────────────

export async function fetchMessages(sessionId: string): Promise<Message[]> {
  const res = await api.get(`/sessions/${sessionId}/messages`);
  return res.data.messages;
}

export async function persistMessage(sessionId: string, message: Message): Promise<void> {
  await api.post(`/sessions/${sessionId}/messages`, message);
}

// ── Audio Upload ──────────────────────────────────────────────────────────

export async function uploadAudio(file: File): Promise<{ file_path: string; filename: string; size: number }> {
  const formData = new FormData();
  formData.append('audio_file', file);
  const res = await api.post('/upload-audio', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

// ── Pipeline ──────────────────────────────────────────────────────────────

export async function runPipeline(params: {
  session_id: string;
  input_type: 'text' | 'audio';
  content: string;
  language_hint?: string;
  intent?: string;
  format_id?: string;
}) {
  const res = await api.post('/run', params);
  return res.data;
}

// ── MOM Download ──────────────────────────────────────────────────────────

export function getMOMDownloadURL(momId: string, formatId = 'standard'): string {
  return `${API_BASE}/api/mom/${momId}/download?format_id=${formatId}`;
}

export function getMOMExcelDownloadURL(momId: string, formatId = 'standard'): string {
  return `${API_BASE}/api/mom/${momId}/download/excel?format_id=${formatId}`;
}

// ── Send to Teams ─────────────────────────────────────────────────────────

export async function sendMOMToTeams(params: {
  mom_id: string;
}): Promise<{ status: string; message: string }> {
  const res = await api.post('/api/teams/send', params);
  return res.data;
}



// ── Update MOM ────────────────────────────────────────────────────────────

export async function updateMOM(params: {
  mom_id: string;
  topics?: any[];
  decisions?: any[];
  actions?: any[];
  sections?: any;
  participants?: string[];
}): Promise<{ status: string; message: string; mom_id: string }> {
  const res = await api.put(`/api/mom/${params.mom_id}`, {
    topics: params.topics,
    decisions: params.decisions,
    actions: params.actions,
    sections: params.sections,
    participants: params.participants,
  });
  return res.data;
}


// ── Get MOM by ID ─────────────────────────────────────────────────────────

export async function getMOM(momId: string): Promise<any> {
  const res = await api.get(`/api/mom/${momId}`);
  return res.data;
}
