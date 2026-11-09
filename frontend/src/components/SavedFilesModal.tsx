import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { 
  X, 
  Eye, 
  Check, 
  Download,
  Upload,
  ArrowUpDown,
  Trash2,
  Bold,
  Italic,
  Heading,
  List,
  Languages,
  Loader2,
  EyeOff,
  Undo2,
  Redo2,
  AlignLeft,
  AlignCenter,
  AlignRight,
  AlignJustify,
  ListOrdered,
  Quote,
  Code
} from 'lucide-react';
import type { SavedFile } from '../types';
import type { User } from '../types/auth';
import { exportSingleSessionPdf, exportAllSessionsPdf, resolveEnglishSelectedAnswer, isLikelyIndonesianText } from '../utils/exportPdf';
import { HubAnimatedCard } from './ui/animated-card';
import { API_BASE_URL } from '../config';

interface SavedFilesModalProps {
  isOpen: boolean;
  onClose: () => void;
  files: SavedFile[];
  onLoadFile: (file: SavedFile) => void;
  onDeleteFile: (fileId: string) => Promise<void>;
  onDeleteMultipleFiles?: (fileIds: string[]) => Promise<void>;
  onUpdateFile: (fileId: string, updatedData: Partial<SavedFile>) => Promise<void>;
  onNewFile?: () => void;
  onUploadToPrompter?: (files: SavedFile[]) => void;
  currentUser?: User | null;
}

const LANGUAGE_OPTIONS = [
  { code: 'id', name: 'ID (Indonesia)' },
  { code: 'en', name: 'EN (Inggris)' },
  { code: 'ar', name: 'AR (Arab)' },
  { code: 'zh', name: 'ZH (Mandarin)' },
  { code: 'fr', name: 'FR (Prancis)' },
  { code: 'de', name: 'DE (Jerman)' },
  { code: 'ja', name: 'JA (Jepang)' },
  { code: 'ru', name: 'RU (Rusia)' },
  { code: 'es', name: 'ES (Spanyol)' },
  { code: 'ko', name: 'KO (Korea)' },
  { code: 'nl', name: 'NL (Belanda)' }
];

export function formatMarkdownToVisualHtml(raw: string): string {
  if (!raw) return '';
  let str = raw;

  // Code blocks: ```code``` -> <pre><code>code</code></pre>
  str = str.replace(/```([a-z]*)\n?([\s\S]*?)```/gi, '<pre><code>$2</code></pre>');
  str = str.replace(/`([^`]+)`/g, '<code style="background:#F1F5F9;padding:2px 5px;border-radius:4px;font-family:monospace;font-size:12px;">$1</code>');

  // Headings: ###, ##, #
  str = str.replace(/^###\s+(.+)$/gm, '<h3>$1</h3>');
  str = str.replace(/^##\s+(.+)$/gm, '<h2>$1</h2>');
  str = str.replace(/^#\s+(.+)$/gm, '<h1>$1</h1>');

  // Bold: **text** or __text__
  str = str.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  str = str.replace(/__([^_]+)__/g, '<strong>$1</strong>');

  // Italic: *text* (excluding bold/tags)
  str = str.replace(/(^|[^\*])\*([^\*\n]+)\*([^\*]|$)/g, '$1<em>$2</em>$3');

  // Blockquote: > text
  str = str.replace(/^>\s+(.+)$/gm, '<blockquote>$1</blockquote>');

  // Bullet points: - item or * item
  str = str.replace(/^[-\*]\s+(.+)$/gm, '<li>$1</li>');

  // Numbered list: 1. item
  str = str.replace(/^\d+\.\s+(.+)$/gm, '<li>$1</li>');

  // Wrap consecutive <li> into <ul>
  str = str.replace(/(?:<li>[\s\S]*?<\/li>\s*)+/g, (match) => {
    return `<ul>${match.trim()}</ul>`;
  });

  // Convert plain newlines to <br> if no block-level HTML tags
  if (!/<(p|div|h[1-6]|ul|ol|blockquote|pre)[^>]*>/i.test(str)) {
    str = str.replace(/\n\n+/g, '<br><br>').replace(/\n/g, '<br>');
  } else {
    str = str.replace(/([^>])\n([^<])/g, '$1<br>$2');
  }

  return str;
}

interface CardEditItemProps {
  id: string;
  title: string;
  value: string;
  onChange: (val: string) => void;
  minRows?: number;
  placeholder?: string;
  defaultTgtLang?: string;
  badge?: React.ReactNode;
  canSelect?: boolean;
  isSelected?: boolean;
  selectionNumber?: number | null;
  onToggleSelect?: (id: string) => void;
}

const CardEditItem: React.FC<CardEditItemProps> = ({
  id,
  title,
  value,
  onChange,
  minRows = 4,
  placeholder: _placeholder,
  defaultTgtLang = 'en',
  badge,
  canSelect = false,
  isSelected = false,
  selectionNumber,
  onToggleSelect
}) => {
  const [isPreview, setIsPreview] = useState(false);
  const [srcLang, setSrcLang] = useState('auto');
  const [tgtLang, setTgtLang] = useState(defaultTgtLang);
  const [isTranslating, setIsTranslating] = useState(false);

  const editorRef = useRef<HTMLDivElement>(null);

  // Local Card Undo & Redo History
  const [history, setHistory] = useState<string[]>([value || '']);
  const [historyIdx, setHistoryIdx] = useState<number>(0);
  const isInternalChangeRef = useRef(false);

  useEffect(() => {
    if (isInternalChangeRef.current) {
      isInternalChangeRef.current = false;
      return;
    }
    setHistory(prev => {
      if (prev[prev.length - 1] === value) return prev;
      const next = [...prev.slice(0, historyIdx + 1), value || ''];
      return next.slice(-40);
    });
    setHistoryIdx(prev => prev + 1);

    if (editorRef.current) {
      const formatted = formatMarkdownToVisualHtml(value || '');
      if (editorRef.current.innerHTML !== formatted) {
        editorRef.current.innerHTML = formatted;
      }
    }
  }, [value]);

  const updateVal = (newVal: string) => {
    if (newVal === value) return;
    isInternalChangeRef.current = true;
    const nextHist = [...history.slice(0, historyIdx + 1), newVal].slice(-40);
    setHistory(nextHist);
    setHistoryIdx(nextHist.length - 1);
    onChange(newVal);
  };

  const handleUndo = () => {
    if (historyIdx > 0) {
      const targetIdx = historyIdx - 1;
      isInternalChangeRef.current = true;
      setHistoryIdx(targetIdx);
      const val = history[targetIdx];
      if (editorRef.current) {
        editorRef.current.innerHTML = val;
      }
      onChange(val);
    } else {
      document.execCommand('undo');
    }
  };

  const handleRedo = () => {
    if (historyIdx < history.length - 1) {
      const targetIdx = historyIdx + 1;
      isInternalChangeRef.current = true;
      setHistoryIdx(targetIdx);
      const val = history[targetIdx];
      if (editorRef.current) {
        editorRef.current.innerHTML = val;
      }
      onChange(val);
    } else {
      document.execCommand('redo');
    }
  };

  const executeCmd = (command: string, arg?: string) => {
    const el = editorRef.current;
    if (!el) return;
    el.focus();
    if (command === 'formatBlock') {
      document.execCommand('formatBlock', false, arg || '<p>');
    } else {
      document.execCommand(command, false, arg || undefined);
    }
    const newHtml = el.innerHTML;
    updateVal(newHtml);
  };

  const handleTranslate = async () => {
    if (!value || !value.trim()) return;
    setIsTranslating(true);
    try {
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = value;
      const textToTranslate = tempDiv.innerText || tempDiv.textContent || value;

      const res = await fetch(`${API_BASE_URL}/api/translate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToTranslate.trim(),
          target_lang: tgtLang,
          source_lang: srcLang,
        })
      });
      if (res.ok) {
        const data = await res.json();
        if (data.translated_text) {
          const formatted = formatMarkdownToVisualHtml(data.translated_text);
          if (editorRef.current) {
            editorRef.current.innerHTML = formatted;
          }
          updateVal(formatted);
        }
      }
    } catch (err) {
      console.error('Error translating card:', err);
    } finally {
      setIsTranslating(false);
    }
  };

  const headerActions = (
    <div className="saved-edit-card-actions">
      {/* Rich Text Toolbar (All Icons Only, No Text) */}
      <div className="saved-white-toolbar">
        {/* Undo */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); handleUndo(); }}
          disabled={historyIdx <= 0}
          className="saved-white-fmt-btn"
          title="Undo Card (Ctrl+Z)"
        >
          <Undo2 size={11} />
        </button>

        {/* Redo */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); handleRedo(); }}
          disabled={historyIdx >= history.length - 1}
          className="saved-white-fmt-btn"
          title="Redo Card (Ctrl+Y)"
        >
          <Redo2 size={11} />
        </button>

        <span className="saved-toolbar-separator" />

        {/* Bold */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('bold'); }}
          className="saved-white-fmt-btn"
          title="Tebal (Bold)"
        >
          <Bold size={11} />
        </button>

        {/* Italic */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('italic'); }}
          className="saved-white-fmt-btn"
          title="Miring (Italic)"
        >
          <Italic size={11} />
        </button>

        {/* Heading */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('formatBlock', '<h3>'); }}
          className="saved-white-fmt-btn"
          title="Header (Sub-topik)"
        >
          <Heading size={11} />
        </button>

        <span className="saved-toolbar-separator" />

        {/* Align Left */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('justifyLeft'); }}
          className="saved-white-fmt-btn"
          title="Rata Kiri (Align Left)"
        >
          <AlignLeft size={11} />
        </button>

        {/* Align Center */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('justifyCenter'); }}
          className="saved-white-fmt-btn"
          title="Rata Tengah (Align Center)"
        >
          <AlignCenter size={11} />
        </button>

        {/* Align Right */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('justifyRight'); }}
          className="saved-white-fmt-btn"
          title="Rata Kanan (Align Right)"
        >
          <AlignRight size={11} />
        </button>

        {/* Align Justify */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('justifyFull'); }}
          className="saved-white-fmt-btn"
          title="Rata Kanan Kiri (Justify)"
        >
          <AlignJustify size={11} />
        </button>

        <span className="saved-toolbar-separator" />

        {/* Numbered List */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('insertOrderedList'); }}
          className="saved-white-fmt-btn"
          title="Daftar Nomor (Numbered List)"
        >
          <ListOrdered size={11} />
        </button>

        {/* Bullet List */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('insertUnorderedList'); }}
          className="saved-white-fmt-btn"
          title="Daftar Poin (Bullet List)"
        >
          <List size={11} />
        </button>

        {/* Quote */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('formatBlock', '<blockquote>'); }}
          className="saved-white-fmt-btn"
          title="Kutipan (Quote)"
        >
          <Quote size={11} />
        </button>

        {/* Code */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); executeCmd('formatBlock', '<pre>'); }}
          className="saved-white-fmt-btn"
          title="Blok Kode / Format Khusus"
        >
          <Code size={11} />
        </button>

        <span className="saved-toolbar-separator" />

        {/* Preview / Edit Toggle (Icon Only) */}
        <button
          type="button"
          onMouseDown={(e) => { e.preventDefault(); setIsPreview(prev => !prev); }}
          className={`saved-white-fmt-btn ${isPreview ? 'active' : ''}`}
          title={isPreview ? "Kembali ke Mode Edit" : "Pratinjau Rich Text"}
        >
          {isPreview ? <EyeOff size={11} /> : <Eye size={11} />}
        </button>
      </div>

      {/* Multilingual Translation Controller (Icon Only) */}
      <div className="saved-white-trans-bar">
        <select
          value={srcLang}
          onChange={(e) => setSrcLang(e.target.value)}
          className="saved-white-select"
          title="Bahasa Asal"
        >
          <option value="auto">AUTO</option>
          {LANGUAGE_OPTIONS.map(l => (
            <option key={l.code} value={l.code}>{l.code.toUpperCase()}</option>
          ))}
        </select>

        <button
          type="button"
          className="saved-white-swap-btn"
          onClick={() => {
            if (srcLang !== 'auto') {
              const temp = srcLang;
              setSrcLang(tgtLang);
              setTgtLang(temp);
            }
          }}
          title="Tukar Bahasa Asal & Tujuan"
        >
          ⇄
        </button>

        <select
          value={tgtLang}
          onChange={(e) => setTgtLang(e.target.value)}
          className="saved-white-select"
          title="Bahasa Tujuan"
        >
          {LANGUAGE_OPTIONS.map(l => (
            <option key={l.code} value={l.code}>{l.code.toUpperCase()}</option>
          ))}
        </select>

        <button
          type="button"
          onClick={handleTranslate}
          disabled={isTranslating || !value.trim()}
          className="saved-white-fmt-btn"
          title={`Terjemahkan Card Ini (${srcLang.toUpperCase()} → ${tgtLang.toUpperCase()})`}
        >
          {isTranslating ? (
            <Loader2 size={11} className="animate-spin" />
          ) : (
            <Languages size={11} />
          )}
        </button>
      </div>
    </div>
  );

  return (
    <HubAnimatedCard
      id={id}
      title={title}
      badge={badge}
      headerAction={headerActions}
      isSelectable={canSelect}
      isSelected={isSelected}
      selectionNumber={selectionNumber}
      onClick={canSelect ? (e: React.MouseEvent<HTMLDivElement>) => {
        const target = e.target as HTMLElement;
        if (target && (target.tagName === 'TEXTAREA' || target.tagName === 'INPUT' || target.tagName === 'BUTTON' || target.tagName === 'SELECT' || target.closest('button') || target.closest('.saved-white-toolbar') || target.closest('.saved-white-trans-bar') || target.closest('.saved-white-card-editor'))) {
          return;
        }
        onToggleSelect && onToggleSelect(id);
      } : undefined}
      className="w-full"
    >
      {isPreview ? (
        <div className="saved-white-card-preview prose-rich-text">
          <ReactMarkdown rehypePlugins={[rehypeRaw]}>{value || '*Tidak ada konten teks.*'}</ReactMarkdown>
        </div>
      ) : (
        <div
          ref={editorRef}
          id={`editor-${id}`}
          contentEditable
          suppressContentEditableWarning
          onInput={(e) => updateVal(e.currentTarget.innerHTML)}
          onKeyDown={(e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
              if (e.shiftKey) {
                e.preventDefault();
                handleRedo();
              } else {
                e.preventDefault();
                handleUndo();
              }
            } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'y') {
              e.preventDefault();
              handleRedo();
            }
          }}
          className="saved-white-card-editor"
          data-placeholder=""
          style={{ minHeight: `${(minRows || 4) * 24}px` }}
        />
      )}
    </HubAnimatedCard>
  );
};

export const SavedFilesModal: React.FC<SavedFilesModalProps> = ({
  isOpen,
  onClose,
  files,
  onLoadFile: _onLoadFile,
  onDeleteFile,
  onDeleteMultipleFiles,
  onUpdateFile,
  onNewFile: _onNewFile,
  onUploadToPrompter,
  currentUser
}) => {
  const isViewer = currentUser?.role === 'Viewer';
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFileForView, setSelectedFileForView] = useState<SavedFile | null>(null);
  const [fileToEdit, setFileToEdit] = useState<SavedFile | null>(null);
  const [isDeletingId, setIsDeletingId] = useState<string | null>(null);
  const [isConfirmingBulkDelete, setIsConfirmingBulkDelete] = useState(false);
  const [isSavingEdit, setIsSavingEdit] = useState(false);

  // Edit form state
  const [editTitle, setEditTitle] = useState('');
  const [editNotes, setEditNotes] = useState('');

  // Column 1 (Left / ChatGPT)
  const [editChatgptOriginal, setEditChatgptOriginal] = useState('');
  const [editChatgptTranslated, setEditChatgptTranslated] = useState('');
  const [editChatgptMain, setEditChatgptMain] = useState('');
  const [editChatgptConcise, setEditChatgptConcise] = useState('');
  const [editChatgptAnalysis, setEditChatgptAnalysis] = useState('');
  const [editChatgptMonitoringIssues, setEditChatgptMonitoringIssues] = useState('');
  const [editChatgptResolution, setEditChatgptResolution] = useState('');
  const [editChatgptKemenkoRole, setEditChatgptKemenkoRole] = useState('');
  const [editChatgptFieldAgenda, setEditChatgptFieldAgenda] = useState('');
  const [editChatgptLatestNews, setEditChatgptLatestNews] = useState('');

  // Column 2 (Right / Gemini)
  const [editGeminiOriginal, setEditGeminiOriginal] = useState('');
  const [editGeminiTranslated, setEditGeminiTranslated] = useState('');
  const [editGeminiMain, setEditGeminiMain] = useState('');
  const [editGeminiConcise, setEditGeminiConcise] = useState('');
  const [editGeminiAnalysis, setEditGeminiAnalysis] = useState('');
  const [editGeminiMonitoringIssues, setEditGeminiMonitoringIssues] = useState('');
  const [editGeminiResolution, setEditGeminiResolution] = useState('');
  const [editGeminiKemenkoRole, setEditGeminiKemenkoRole] = useState('');
  const [editGeminiFieldAgenda, setEditGeminiFieldAgenda] = useState('');
  const [editGeminiLatestNews, setEditGeminiLatestNews] = useState('');

  // Translate All State
  const [isTranslatingAll, setIsTranslatingAll] = useState(false);
  const [translateAllProgress, setTranslateAllProgress] = useState('');
  const [translateAllTargetLang, setTranslateAllTargetLang] = useState('en');

  // Bottom Card (Card 11 / Jawaban Terpilih)
  const [editSelectedAnswer, setEditSelectedAnswer] = useState('');

  // Global Undo & Redo History State for Entire Document Workspace
  interface DocSnapshot {
    editTitle: string;
    editNotes: string;
    editChatgptOriginal: string;
    editChatgptTranslated: string;
    editChatgptMain: string;
    editChatgptConcise: string;
    editChatgptAnalysis: string;
    editChatgptMonitoringIssues: string;
    editChatgptResolution: string;
    editChatgptKemenkoRole: string;
    editChatgptFieldAgenda: string;
    editChatgptLatestNews: string;
    editGeminiOriginal: string;
    editGeminiTranslated: string;
    editGeminiMain: string;
    editGeminiConcise: string;
    editGeminiAnalysis: string;
    editGeminiMonitoringIssues: string;
    editGeminiResolution: string;
    editGeminiKemenkoRole: string;
    editGeminiFieldAgenda: string;
    editGeminiLatestNews: string;
    editSelectedAnswer: string;
  }

  const [undoStack, setUndoStack] = useState<DocSnapshot[]>([]);
  const [redoStack, setRedoStack] = useState<DocSnapshot[]>([]);

  const getCurrentSnapshot = (): DocSnapshot => ({
    editTitle,
    editNotes,
    editChatgptOriginal,
    editChatgptTranslated,
    editChatgptMain,
    editChatgptConcise,
    editChatgptAnalysis,
    editChatgptMonitoringIssues,
    editChatgptResolution,
    editChatgptKemenkoRole,
    editChatgptFieldAgenda,
    editChatgptLatestNews,
    editGeminiOriginal,
    editGeminiTranslated,
    editGeminiMain,
    editGeminiConcise,
    editGeminiAnalysis,
    editGeminiMonitoringIssues,
    editGeminiResolution,
    editGeminiKemenkoRole,
    editGeminiFieldAgenda,
    editGeminiLatestNews,
    editSelectedAnswer,
  });

  const applySnapshot = (s: DocSnapshot) => {
    setEditTitle(s.editTitle);
    setEditNotes(s.editNotes);
    setEditChatgptOriginal(s.editChatgptOriginal);
    setEditChatgptTranslated(s.editChatgptTranslated);
    setEditChatgptMain(s.editChatgptMain);
    setEditChatgptConcise(s.editChatgptConcise);
    setEditChatgptAnalysis(s.editChatgptAnalysis);
    setEditChatgptMonitoringIssues(s.editChatgptMonitoringIssues);
    setEditChatgptResolution(s.editChatgptResolution);
    setEditChatgptKemenkoRole(s.editChatgptKemenkoRole);
    setEditChatgptFieldAgenda(s.editChatgptFieldAgenda);
    setEditChatgptLatestNews(s.editChatgptLatestNews || '');
    setEditGeminiOriginal(s.editGeminiOriginal);
    setEditGeminiTranslated(s.editGeminiTranslated);
    setEditGeminiMain(s.editGeminiMain);
    setEditGeminiConcise(s.editGeminiConcise);
    setEditGeminiAnalysis(s.editGeminiAnalysis);
    setEditGeminiMonitoringIssues(s.editGeminiMonitoringIssues);
    setEditGeminiResolution(s.editGeminiResolution);
    setEditGeminiKemenkoRole(s.editGeminiKemenkoRole);
    setEditGeminiFieldAgenda(s.editGeminiFieldAgenda);
    setEditGeminiLatestNews(s.editGeminiLatestNews || '');
    setEditSelectedAnswer(s.editSelectedAnswer);
  };

  const handleGlobalUndo = () => {
    if (undoStack.length === 0) return;
    const prevSnap = undoStack[undoStack.length - 1];
    setUndoStack(prev => prev.slice(0, prev.length - 1));
    setRedoStack(prev => [...prev, getCurrentSnapshot()]);
    applySnapshot(prevSnap);
  };

  const handleGlobalRedo = () => {
    if (redoStack.length === 0) return;
    const nextSnap = redoStack[redoStack.length - 1];
    setRedoStack(prev => prev.slice(0, prev.length - 1));
    setUndoStack(prev => [...prev, getCurrentSnapshot()]);
    applySnapshot(nextSnap);
  };

  // Sort order: default 'oldest_first' per user request (mengurut dari atas yang paling lama ke yang terbaru)
  const [sortOrder, setSortOrder] = useState<'oldest_first' | 'newest_first'>('oldest_first');

  // Multiple choice selection for PDF export
  const [selectedExportIds, setSelectedExportIds] = useState<Set<string>>(new Set());

  // Multiple choice selection for uniting answers into Card 11 (Jawaban Terpilih)
  const [selectedCardIds, setSelectedCardIds] = useState<string[]>([]);

  if (!isOpen) return null;

  const filteredFiles = files.filter(f => {
    const q = searchQuery.toLowerCase();
    return (
      f.title?.toLowerCase().includes(q) ||
      f.original_audio_text?.toLowerCase().includes(q) ||
      f.translated_indonesian_text?.toLowerCase().includes(q) ||
      f.speaker?.toLowerCase().includes(q) ||
      f.timestamp?.toLowerCase().includes(q)
    );
  });

  const sortedFiles = [...filteredFiles].sort((a, b) => {
    const timeA = a.created_at || a.timestamp || '';
    const timeB = b.created_at || b.timestamp || '';
    if (sortOrder === 'oldest_first') {
      return timeA.localeCompare(timeB);
    }
    return timeB.localeCompare(timeA);
  });

  // Multiple selection helpers
  const allSelected = sortedFiles.length > 0 && sortedFiles.every(f => selectedExportIds.has(f.id));
  const someSelected = sortedFiles.some(f => selectedExportIds.has(f.id));

  const toggleSelectAll = () => {
    if (allSelected) {
      setSelectedExportIds(new Set());
    } else {
      setSelectedExportIds(new Set(sortedFiles.map(f => f.id)));
    }
  };

  const toggleSelectFile = (id: string) => {
    setSelectedExportIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleExportSelected = () => {
    const selectedFiles = sortedFiles.filter(f => selectedExportIds.has(f.id));
    if (selectedFiles.length === 0) return;
    if (selectedFiles.length === 1) {
      exportSingleSessionPdf(selectedFiles[0]);
    } else {
      exportAllSessionsPdf(selectedFiles);
    }
  };

  const handleUploadSelectedToPrompter = () => {
    if (isViewer) {
      alert("Akses Ditolak: Peran Pengamat (Viewer) hanya memiliki hak akses pantau (Read-Only). Anda tidak diizinkan mengunggah dokumen ke Prompter.");
      return;
    }
    const selectedFiles = sortedFiles.filter(f => selectedExportIds.has(f.id));
    if (selectedFiles.length === 0) return;
    if (onUploadToPrompter) {
      onUploadToPrompter(selectedFiles);
    }
  };

  const handleBulkDelete = async () => {
    if (isViewer) {
      alert("Akses Ditolak: Peran Pengamat (Viewer) tidak diizinkan menghapus dokumen.");
      setIsConfirmingBulkDelete(false);
      return;
    }
    const idsToDelete = Array.from(selectedExportIds);
    setIsConfirmingBulkDelete(false);
    if (onDeleteMultipleFiles) {
      await onDeleteMultipleFiles(idsToDelete);
    } else {
      for (const id of idsToDelete) {
        await onDeleteFile(id);
      }
    }
    setSelectedExportIds(new Set());
  };

  // Multiple Choice helper for Card 11 (Jawaban Terpilih)
  const syncSelectedAnswer = (activeIds: string[], overrides?: Record<string, string>) => {
    if (activeIds.length === 0) {
      const defaultAns = fileToEdit?.selected_answer || fileToEdit?.chatgpt_answers?.main_answer || fileToEdit?.gemini_answers?.main_answer || fileToEdit?.ai_answers?.main_answer || '';
      setEditSelectedAnswer(defaultAns);
      return;
    }
    const getVal = (id: string) => {
      if (overrides && id in overrides) return overrides[id];
      switch (id) {
        case 'chatgpt-orig': return editChatgptOriginal;
        case 'chatgpt-trans': return editChatgptTranslated;
        case 'chatgpt-main': return editChatgptMain;
        case 'chatgpt-concise': return editChatgptConcise;
        case 'chatgpt-analysis': return editChatgptAnalysis;
        case 'chatgpt-monitoring': return editChatgptMonitoringIssues;
        case 'chatgpt-resolution': return editChatgptResolution;
        case 'chatgpt-role': return editChatgptKemenkoRole;
        case 'chatgpt-agenda': return editChatgptFieldAgenda;
        case 'chatgpt-news': return editChatgptLatestNews;
        case 'gemini-orig': return editGeminiOriginal;
        case 'gemini-trans': return editGeminiTranslated;
        case 'gemini-main': return editGeminiMain;
        case 'gemini-concise': return editGeminiConcise;
        case 'gemini-analysis': return editGeminiAnalysis;
        case 'gemini-monitoring': return editGeminiMonitoringIssues;
        case 'gemini-resolution': return editGeminiResolution;
        case 'gemini-role': return editGeminiKemenkoRole;
        case 'gemini-agenda': return editGeminiFieldAgenda;
        case 'gemini-news': return editGeminiLatestNews;
        default: return '';
      }
    };

    const texts = activeIds
      .map(id => getVal(id).trim())
      .filter(t => t.length > 0);

    setEditSelectedAnswer(texts.join('\n\n'));
  };

  const toggleCardChoice = (id: string) => {
    setSelectedCardIds(prev => {
      const next = prev.includes(id)
        ? prev.filter(x => x !== id)
        : [...prev, id];
      syncSelectedAnswer(next);
      return next;
    });
  };

  const getCardSelectionNumber = (id: string): number | null => {
    const idx = selectedCardIds.indexOf(id);
    return idx !== -1 ? idx + 1 : null;
  };

  const handleCardValueChange = (id: string, newVal: string, setter: (val: string) => void) => {
    setUndoStack(prev => [...prev.slice(-30), getCurrentSnapshot()]);
    setRedoStack([]);
    setter(newVal);
    if (selectedCardIds.includes(id)) {
      syncSelectedAnswer(selectedCardIds, { [id]: newVal });
    }
  };

  const handleOpenEdit = (f: SavedFile) => {
    if (isViewer) {
      alert("Akses Ditolak: Peran Pengamat (Viewer) hanya memiliki hak akses pantau (Read-Only). Anda tidak diizinkan mengubah dokumen.");
      return;
    }
    setFileToEdit(f);
    setUndoStack([]);
    setRedoStack([]);
    setEditTitle(f.title || '');
    setEditNotes(f.notes || '');

    // Auto-detect previously chosen cards from saved selected_answer
    const rawSaved = (f.selected_answer || '').toLowerCase().replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
    const detectedIds: string[] = [];
    const checkCandidates = [
      { id: 'chatgpt-main', text: f.chatgpt_answers?.main_answer || f.ai_answers?.main_answer || '' },
      { id: 'chatgpt-concise', text: f.chatgpt_answers?.concise_answer || f.ai_answers?.concise_answer || '' },
      { id: 'chatgpt-analysis', text: f.chatgpt_answers?.brief_analysis || f.ai_answers?.brief_analysis || '' },
      { id: 'chatgpt-monitoring', text: f.chatgpt_answers?.monitoring_issues || f.ai_answers?.monitoring_issues || '' },
      { id: 'chatgpt-resolution', text: f.chatgpt_answers?.resolution_recommendations || f.ai_answers?.resolution_recommendations || '' },
      { id: 'chatgpt-role', text: f.chatgpt_answers?.kemenko_role || f.ai_answers?.kemenko_role || '' },
      { id: 'chatgpt-agenda', text: f.chatgpt_answers?.field_monitoring_agenda || f.ai_answers?.field_monitoring_agenda || '' },
      { id: 'chatgpt-news', text: f.chatgpt_answers?.latest_news || f.ai_answers?.latest_news || '' },
      { id: 'gemini-main', text: f.gemini_answers?.main_answer || f.ai_answers?.main_answer || '' },
      { id: 'gemini-concise', text: f.gemini_answers?.concise_answer || f.ai_answers?.concise_answer || '' },
      { id: 'gemini-analysis', text: f.gemini_answers?.brief_analysis || f.ai_answers?.brief_analysis || '' },
      { id: 'gemini-monitoring', text: f.gemini_answers?.monitoring_issues || f.ai_answers?.monitoring_issues || '' },
      { id: 'gemini-resolution', text: f.gemini_answers?.resolution_recommendations || f.ai_answers?.resolution_recommendations || '' },
      { id: 'gemini-role', text: f.gemini_answers?.kemenko_role || f.ai_answers?.kemenko_role || '' },
      { id: 'gemini-agenda', text: f.gemini_answers?.field_monitoring_agenda || f.ai_answers?.field_monitoring_agenda || '' },
      { id: 'gemini-news', text: f.gemini_answers?.latest_news || f.ai_answers?.latest_news || '' }
    ];
    if (rawSaved) {
      for (const cand of checkCandidates) {
        const clean = cand.text.toLowerCase().replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
        if (clean.length > 15 && (rawSaved.includes(clean.slice(0, 30)) || clean.includes(rawSaved.slice(0, 30)))) {
          detectedIds.push(cand.id);
        }
      }
    }
    setSelectedCardIds(detectedIds);

    const questionTopic = f.translated_indonesian_text || f.original_audio_text || f.title || 'isu strategis kenegaraan';

    // Left Column (ChatGPT)
    setEditChatgptOriginal(f.original_audio_text || '');
    setEditChatgptTranslated(f.translated_indonesian_text || '');
    setEditChatgptMain(f.chatgpt_answers?.main_answer || f.ai_answers?.main_answer || '');
    setEditChatgptConcise(f.chatgpt_answers?.concise_answer || f.ai_answers?.concise_answer || '');
    setEditChatgptAnalysis(f.chatgpt_answers?.brief_analysis || f.ai_answers?.brief_analysis || '');
    setEditChatgptMonitoringIssues(
      f.chatgpt_answers?.monitoring_issues ||
      f.ai_answers?.monitoring_issues ||
      `Hasil pemantauan operasional lapangan terhadap isu **${questionTopic}**: Teridentifikasi dinamika koordinasi teknis, potensi friksi prosedural antardaerah, dan kebutuhan validasi data faktual secara cepat.`
    );
    setEditChatgptResolution(
      f.chatgpt_answers?.resolution_recommendations ||
      f.ai_answers?.resolution_recommendations ||
      `1. Akselerasi debottlenecking hambatan operasional penanganan '${questionTopic}'.\n2. Penyelarasan SOP taktis dan penguatan respons cepat instansi teknis terkait.`
    );
    setEditChatgptKemenkoRole(
      f.chatgpt_answers?.kemenko_role ||
      f.ai_answers?.kemenko_role ||
      `Dialogue AI Representative memimpin koordinasi lintas instansi terkait dan memastikan tidak ada hambatan birokrasi dalam implementasi kebijakan.`
    );
    setEditChatgptFieldAgenda(
      f.chatgpt_answers?.field_monitoring_agenda ||
      f.ai_answers?.field_monitoring_agenda ||
      `1. Pelaksanaan rapat koordinasi terpadu bersama pimpinan K/L terkait.\n2. Peninjauan lapangan dan verifikasi faktual di lokasi prioritas dalam waktu 72 jam.`
    );
    setEditChatgptLatestNews(
      f.chatgpt_answers?.latest_news ||
      f.ai_answers?.latest_news ||
      `Liputan berita teraktual dan kronologi isu '${questionTopic}' terus dimonitor secara real-time dari kantor berita resmi dan verifikasi fakta lapangan.`
    );

    // Right Column (Gemini)
    setEditGeminiOriginal(f.original_audio_text || '');
    setEditGeminiTranslated(f.translated_indonesian_text || '');
    setEditGeminiMain(f.gemini_answers?.main_answer || f.ai_answers?.main_answer || '');
    setEditGeminiConcise(f.gemini_answers?.concise_answer || f.ai_answers?.concise_answer || '');
    setEditGeminiAnalysis(f.gemini_answers?.brief_analysis || f.ai_answers?.brief_analysis || '');
    setEditGeminiMonitoringIssues(
      f.gemini_answers?.monitoring_issues ||
      f.ai_answers?.monitoring_issues ||
      `Kajian stabilitas dan pemantauan intelijen strategis atas isu **${questionTopic}**: Menunjukkan urgensi perlindungan ketahanan sosial-politik, kedaulatan hukum, dan mitigasi eskalasi konflik.`
    );
    setEditGeminiResolution(
      f.gemini_answers?.resolution_recommendations ||
      f.ai_answers?.resolution_recommendations ||
      `1. Formulasi kebijakan antisipatif jangka menengah dan panjang terhadap '${questionTopic}'.\n2. Konsolidasi kepemimpinan strategis nasional dan diplomasi preventif terukur.`
    );
    setEditGeminiKemenkoRole(
      f.gemini_answers?.kemenko_role ||
      f.ai_answers?.kemenko_role ||
      `Menjalankan mandat sinkronisasi dan pengendalian kebijakan strategis Dialogue AI Representative, menyatukan postur aparat penegak hukum dan pertahanan-keamanan nasional.`
    );
    setEditGeminiFieldAgenda(
      f.gemini_answers?.field_monitoring_agenda ||
      f.ai_answers?.field_monitoring_agenda ||
      `1. Aktivasi desk pemantauan terpadu 24/7 di bawah Dialogue AI Representative.\n2. Agenda peninjauan lapangan berkala dan evaluasi dampak komprehensif bersama Forkopimda.`
    );
    setEditGeminiLatestNews(
      f.gemini_answers?.latest_news ||
      f.ai_answers?.latest_news ||
      `Laporan pemberitaan media terverifikasi dan siaran pers resmi terkait '${questionTopic}' dihimpun secara komprehensif guna menjaga ketepatan informasi publik.`
    );

    // Bottom Card (Jawaban Terpilih)
    setEditSelectedAnswer(f.selected_answer || f.ai_answers?.main_answer || f.chatgpt_answers?.main_answer || f.gemini_answers?.main_answer || '');
  };

  const handleTranslateAll = async () => {
    if (isTranslatingAll) return;
    setUndoStack(prev => [...prev.slice(-30), getCurrentSnapshot()]);
    setRedoStack([]);
    setIsTranslatingAll(true);
    setTranslateAllProgress('0%');

    const translateText = async (text: string): Promise<string> => {
      if (!text || !text.trim()) return text;
      try {
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = text;
        const cleanTextToTranslate = tempDiv.innerText || tempDiv.textContent || text;

        const res = await fetch(`${API_BASE_URL}/api/translate`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            text: cleanTextToTranslate.trim(),
            target_lang: translateAllTargetLang,
            source_lang: 'auto'
          })
        });
        if (res.ok) {
          const data = await res.json();
          return formatMarkdownToVisualHtml(data.translated_text || text);
        }
      } catch (err) {
        console.error('Translation error:', err);
      }
      return text;
    };

    try {
      // NOTE: Translate all editable cards EXCEPT the 2 "Pertanyaan Asli" cards (editChatgptOriginal and editGeminiOriginal)
      const targetItems: Array<{
        name: string;
        currentVal: string;
        setter: (v: string) => void;
      }> = [
        { name: 'chatgpt-trans', currentVal: editChatgptTranslated, setter: setEditChatgptTranslated },
        { name: 'chatgpt-main', currentVal: editChatgptMain, setter: setEditChatgptMain },
        { name: 'chatgpt-concise', currentVal: editChatgptConcise, setter: setEditChatgptConcise },
        { name: 'chatgpt-analysis', currentVal: editChatgptAnalysis, setter: setEditChatgptAnalysis },
        { name: 'chatgpt-monitoring', currentVal: editChatgptMonitoringIssues, setter: setEditChatgptMonitoringIssues },
        { name: 'chatgpt-resolution', currentVal: editChatgptResolution, setter: setEditChatgptResolution },
        { name: 'chatgpt-role', currentVal: editChatgptKemenkoRole, setter: setEditChatgptKemenkoRole },
        { name: 'chatgpt-agenda', currentVal: editChatgptFieldAgenda, setter: setEditChatgptFieldAgenda },
        { name: 'chatgpt-news', currentVal: editChatgptLatestNews, setter: setEditChatgptLatestNews },
        { name: 'gemini-trans', currentVal: editGeminiTranslated, setter: setEditGeminiTranslated },
        { name: 'gemini-main', currentVal: editGeminiMain, setter: setEditGeminiMain },
        { name: 'gemini-concise', currentVal: editGeminiConcise, setter: setEditGeminiConcise },
        { name: 'gemini-analysis', currentVal: editGeminiAnalysis, setter: setEditGeminiAnalysis },
        { name: 'gemini-monitoring', currentVal: editGeminiMonitoringIssues, setter: setEditGeminiMonitoringIssues },
        { name: 'gemini-resolution', currentVal: editGeminiResolution, setter: setEditGeminiResolution },
        { name: 'gemini-role', currentVal: editGeminiKemenkoRole, setter: setEditGeminiKemenkoRole },
        { name: 'gemini-agenda', currentVal: editGeminiFieldAgenda, setter: setEditGeminiFieldAgenda },
        { name: 'gemini-news', currentVal: editGeminiLatestNews, setter: setEditGeminiLatestNews },
        { name: 'selected-answer', currentVal: editSelectedAnswer, setter: setEditSelectedAnswer },
      ];

      const activeItems = targetItems.filter(item => item.currentVal && item.currentVal.trim().length > 0);
      let done = 0;
      const translatedMap: Record<string, string> = {};

      await Promise.all(
        activeItems.map(async (item) => {
          const res = await translateText(item.currentVal);
          translatedMap[item.name] = res;
          item.setter(res);
          done++;
          setTranslateAllProgress(`${done}/${activeItems.length}`);
        })
      );

      // If user has cards selected in Card 11 (Jawaban Terpilih), synchronize Jawaban Terpilih from the freshly translated cards!
      if (selectedCardIds.length > 0) {
        syncSelectedAnswer(selectedCardIds, translatedMap);
      } else if (translatedMap['selected-answer']) {
        setEditSelectedAnswer(translatedMap['selected-answer']);
      }
    } finally {
      setIsTranslatingAll(false);
      setTranslateAllProgress('');
    }
  };

  const handleSaveEditSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (isViewer) {
      alert("Akses Ditolak: Peran Pengamat (Viewer) tidak diizinkan mengubah dokumen arsip negara.");
      return;
    }
    if (!fileToEdit) return;
    setIsSavingEdit(true);
    try {
      const origText = editChatgptOriginal.trim() || editGeminiOriginal.trim();
      const transText = editChatgptTranslated.trim() || editGeminiTranslated.trim();
      const mainAns = editChatgptMain.trim() || editGeminiMain.trim();
      const conciseAns = editChatgptConcise.trim() || editGeminiConcise.trim();
      const analysisAns = editChatgptAnalysis.trim() || editGeminiAnalysis.trim();
      const chosenAns = editSelectedAnswer.trim();

      await onUpdateFile(fileToEdit.id, {
        title: editTitle.trim(),
        notes: editNotes.trim(),
        original_audio_text: origText,
        translated_indonesian_text: transText,
        ai_answers: {
          ...fileToEdit.ai_answers,
          main_answer: chosenAns || mainAns,
          concise_answer: conciseAns,
          brief_analysis: analysisAns,
          monitoring_issues: editChatgptMonitoringIssues.trim() || editGeminiMonitoringIssues.trim(),
          resolution_recommendations: editChatgptResolution.trim() || editGeminiResolution.trim(),
          kemenko_role: editChatgptKemenkoRole.trim() || editGeminiKemenkoRole.trim(),
          field_monitoring_agenda: editChatgptFieldAgenda.trim() || editGeminiFieldAgenda.trim(),
          latest_news: editChatgptLatestNews.trim() || editGeminiLatestNews.trim(),
        },
        chatgpt_answers: {
          main_answer: editChatgptMain.trim(),
          concise_answer: editChatgptConcise.trim(),
          brief_analysis: editChatgptAnalysis.trim(),
          monitoring_issues: editChatgptMonitoringIssues.trim(),
          resolution_recommendations: editChatgptResolution.trim(),
          kemenko_role: editChatgptKemenkoRole.trim(),
          field_monitoring_agenda: editChatgptFieldAgenda.trim(),
          latest_news: editChatgptLatestNews.trim(),
          model_version: 'ChatGPT'
        },
        gemini_answers: {
          main_answer: editGeminiMain.trim(),
          concise_answer: editGeminiConcise.trim(),
          brief_analysis: editGeminiAnalysis.trim(),
          monitoring_issues: editGeminiMonitoringIssues.trim(),
          resolution_recommendations: editGeminiResolution.trim(),
          kemenko_role: editGeminiKemenkoRole.trim(),
          field_monitoring_agenda: editGeminiFieldAgenda.trim(),
          latest_news: editGeminiLatestNews.trim(),
          model_version: 'Gemini'
        },
        selected_answer: chosenAns,
        selected_answer_en: !isLikelyIndonesianText(chosenAns) && chosenAns ? chosenAns : (fileToEdit.selected_answer_en || chosenAns),
        english_translations: {
          ...(fileToEdit.english_translations || {}),
          ...(!isLikelyIndonesianText(chosenAns) && chosenAns ? { card_11: chosenAns, selected_answer: chosenAns } : {})
        }
      });
      setFileToEdit(null);
    } finally {
      setIsSavingEdit(false);
    }
  };

  return (
    <div className="saved-files-overlay">
      <div className="saved-files-container">
        {/* Header */}
        <div className="saved-files-header">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide">
              Daftar Pertanyaan
            </h2>
          </div>

          <div className="flex items-center gap-2">
            {isViewer && (
              <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold bg-zinc-800 text-zinc-300 border border-zinc-700 flex items-center gap-1.5" title="Akses Pengamat: Hanya diperbolehkan membaca data dan preview/export PDF.">
                <Eye size={12} className="text-blue-400" />
                Mode Pengamat (Read-Only)
              </span>
            )}
            <button
              type="button"
              className="saved-close-btn"
              onClick={onClose}
              aria-label="Tutup"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Search & Filter Toolbar */}
        <div className="saved-files-toolbar">
          <div className="saved-search-box">
            <input
              type="text"
              placeholder=""
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="saved-search-input"
            />
            {searchQuery && (
              <button 
                type="button" 
                onClick={() => setSearchQuery('')}
                className="text-xs text-zinc-500 hover:text-white"
              >
                Clear
              </button>
            )}
          </div>

          <div className="saved-toolbar-actions">
            <button
              type="button"
              className="saved-sort-btn"
              onClick={() => setSortOrder(prev => prev === 'oldest_first' ? 'newest_first' : 'oldest_first')}
              title="Ubah urutan arsip waktu"
            >
              <ArrowUpDown size={13} className="text-zinc-200 shrink-0" />
              <span>{sortOrder === 'oldest_first' ? 'Urutan: Terlama → Terbaru' : 'Urutan: Terbaru → Terlama'}</span>
            </button>

            <button
              type="button"
              className="saved-export-all-btn"
              onClick={handleExportSelected}
              title={
                selectedExportIds.size > 0
                  ? `Export ${selectedExportIds.size} dokumen terpilih ke PDF resmi`
                  : 'Pilih minimal 1 dokumen pada tabel untuk dieksport'
              }
              disabled={selectedExportIds.size === 0}
              style={{
                opacity: selectedExportIds.size === 0 ? 0.45 : 1,
                cursor: selectedExportIds.size === 0 ? 'not-allowed' : 'pointer'
              }}
            >
              <Download size={13} className="text-zinc-200 shrink-0" />
              <span>Export PDF Terpilih ({selectedExportIds.size})</span>
            </button>

            <button
              type="button"
              id="saved-upload-prompter-btn"
              className="saved-upload-prompter-btn"
              onClick={handleUploadSelectedToPrompter}
              title={
                selectedExportIds.size > 0
                  ? `Upload ${selectedExportIds.size} pertanyaan terpilih ke Prompter naskah`
                  : 'Pilih minimal 1 dokumen pada tabel untuk diupload ke Prompter'
              }
              disabled={selectedExportIds.size === 0}
              style={{
                opacity: selectedExportIds.size === 0 ? 0.45 : 1,
                cursor: selectedExportIds.size === 0 ? 'not-allowed' : 'pointer'
              }}
            >
              <Upload size={13} className="text-zinc-200 shrink-0" />
              <span>Upload ke Prompter {selectedExportIds.size > 0 ? `(${selectedExportIds.size})` : ''}</span>
            </button>

            {!isViewer && selectedExportIds.size > 0 && (
              <button
                type="button"
                className="saved-action-btn flex items-center gap-1.5 font-bold"
                style={{ color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.45)', background: 'rgba(239, 68, 68, 0.12)' }}
                onClick={() => setIsConfirmingBulkDelete(true)}
                title={`Hapus ${selectedExportIds.size} pertanyaan terpilih`}
              >
                <Trash2 size={13} className="text-red-400 shrink-0" />
                <span>Hapus Terpilih ({selectedExportIds.size})</span>
              </button>
            )}

            {selectedExportIds.size > 0 && (
              <button
                type="button"
                onClick={() => setSelectedExportIds(new Set())}
                className="text-xs text-zinc-400 hover:text-white underline cursor-pointer"
                title="Batalkan pilihan semua"
              >
                Batal Pilih
              </button>
            )}
          </div>
        </div>

        {/* Files List Table */}
        <div className="saved-files-list-body">
          <div className="saved-table-wrapper">
            <table className="saved-table">
                <thead>
                  <tr>
                    <th style={{ width: '70px', textAlign: 'center' }}>
                      <label className="inline-flex items-center justify-center gap-1.5 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          className="saved-checkbox"
                          checked={allSelected}
                          ref={(el) => {
                            if (el) el.indeterminate = !allSelected && someSelected;
                          }}
                          onChange={toggleSelectAll}
                          title={allSelected ? "Batal Pilih Semua" : "Pilih Semua Dokumen"}
                        />
                        <span className="text-[11px] font-bold text-zinc-300">Select</span>
                      </label>
                    </th>
                    <th style={{ width: '22%' }}>Nomor Pertanyaan Asli</th>
                    <th style={{ width: '22%' }}>Terjemahan Indonesia</th>
                    <th style={{ width: '42%' }}>Jawaban Terpilih</th>
                    <th style={{ textAlign: 'center', width: '14%' }}>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedFiles.length === 0 && (
                    <tr>
                      <td colSpan={5} className="text-center py-12 text-zinc-400">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <span className="text-3xl">📋</span>
                          <span className="font-semibold text-zinc-300">Daftar Pertanyaan Kosong</span>
                          <span className="text-xs text-zinc-500">Semua riwayat pertanyaan telah dihapus. Data baru akan otomatis tersimpan saat sesi analisis baru dimulai.</span>
                        </div>
                      </td>
                    </tr>
                  )}
                  {sortedFiles.map((file, idx) => {
                    const isSelected = selectedExportIds.has(file.id);
                    const chosenText = file.selected_answer || file.ai_answers?.main_answer || file.chatgpt_answers?.main_answer || file.gemini_answers?.main_answer || '';
                    return (
                      <tr 
                        key={file.id}
                        className={isSelected ? 'saved-table-row-selected' : ''}
                        onClick={(e) => {
                          const target = e.target as HTMLElement;
                          if (target.closest('.saved-action-btn') || target.tagName === 'INPUT') return;
                          toggleSelectFile(file.id);
                        }}
                        style={{ cursor: 'pointer' }}
                      >
                        <td 
                          style={{ textAlign: 'center' }}
                          onClick={(e) => e.stopPropagation()}
                        >
                          <input
                            type="checkbox"
                            className="saved-checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelectFile(file.id)}
                            title={isSelected ? "Batal pilih dokumen ini" : "Pilih dokumen ini"}
                          />
                        </td>
                        <td>
                          <div className="flex items-start gap-2.5">
                            <span className="inline-flex items-center justify-center min-w-[22px] h-[22px] px-1.5 rounded bg-zinc-800 text-zinc-300 text-xs font-mono font-bold border border-zinc-700/80 mt-0.5 shrink-0">
                              {idx + 1}
                            </span>
                            <div className="flex-1 min-w-0">
                              <div className="text-xs text-zinc-200 font-medium whitespace-pre-wrap break-words leading-relaxed">
                                {file.original_audio_text || file.title || "-"}
                              </div>
                            </div>
                          </div>
                        </td>
                        <td>
                          <div className="text-xs text-zinc-200 font-medium whitespace-pre-wrap break-words leading-relaxed">
                            {file.translated_indonesian_text || "-"}
                          </div>
                        </td>
                        <td>
                          <div className="text-xs text-zinc-200 whitespace-pre-wrap break-words leading-relaxed">
                            {chosenText || "-"}
                          </div>
                        </td>
                        <td onClick={(e) => e.stopPropagation()}>
                          <div className="saved-table-actions justify-center">
                            <button
                              type="button"
                              className="saved-action-btn"
                              onClick={() => setSelectedFileForView(file)}
                              title="Lihat Preview Dokumen (View)"
                            >
                              View
                            </button>

                            {!isViewer && (
                              <>
                                <button
                                  type="button"
                                  className="saved-action-btn"
                                  onClick={() => handleOpenEdit(file)}
                                  title="Edit Dokumen & Jawaban (Edit)"
                                >
                                  Edit
                                </button>

                                <button
                                  type="button"
                                  className="saved-action-btn"
                                  onClick={() => setIsDeletingId(file.id)}
                                  title="Hapus Dokumen (Delete)"
                                >
                                  Delete
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
        </div>

        {/* Delete Confirmation Modal */}
        {isDeletingId && !isViewer && (
          <div className="saved-submodal-overlay">
            <div className="saved-submodal-card">
              <h3 className="text-sm font-bold text-white mb-4">Konfirmasi Hapus?</h3>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className="saved-cancel-btn"
                  onClick={() => setIsDeletingId(null)}
                >
                  Batal
                </button>
                <button
                  type="button"
                  className="saved-danger-btn"
                  onClick={async () => {
                    if (isViewer) {
                      alert("Akses Ditolak: Peran Pengamat (Viewer) tidak diizinkan menghapus dokumen.");
                      setIsDeletingId(null);
                      return;
                    }
                    const id = isDeletingId;
                    setIsDeletingId(null);
                    await onDeleteFile(id);
                  }}
                >
                  Hapus Berkas
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Bulk Delete Confirmation Modal */}
        {isConfirmingBulkDelete && !isViewer && (
          <div className="saved-submodal-overlay">
            <div className="saved-submodal-card">
              <h3 className="text-sm font-bold text-white mb-2">Hapus {selectedExportIds.size} Pertanyaan Terpilih?</h3>
              <p className="text-xs text-zinc-400 mb-4">
                Dokumen terpilih akan dihapus permanen dari basis data arsip dan tidak akan muncul kembali.
              </p>
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  className="saved-cancel-btn"
                  onClick={() => setIsConfirmingBulkDelete(false)}
                >
                  Batal
                </button>
                <button
                  type="button"
                  className="saved-danger-btn"
                  onClick={handleBulkDelete}
                >
                  Hapus ({selectedExportIds.size}) Dokumen
                </button>
              </div>
            </div>
          </div>
        )}

        {/* View Modal: Official A4 Document "Export PDF" Preview */}
        {selectedFileForView && (
          <div className="pdf-preview-overlay" role="dialog" aria-modal="true" aria-label="Preview Dokumen Export PDF">
            {/* Top Toolbar */}
            <div className="pdf-preview-header">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white tracking-wide">
                  Preview Dokumen
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="saved-action-btn flex items-center gap-1.5 font-bold"
                  onClick={() => exportSingleSessionPdf(selectedFileForView)}
                  title="Download / Unduh Dokumen ke Format PDF (A4)"
                >
                  <Download size={13} />
                  <span>Download PDF</span>
                </button>

                <button
                  type="button"
                  className="saved-cancel-btn flex items-center gap-1.5"
                  onClick={() => setSelectedFileForView(null)}
                >
                  <X size={14} />
                  <span>Tutup</span>
                </button>
              </div>
            </div>

            {/* Scrollable Document Container */}
            <div className="pdf-preview-body">
              <div className="pdf-preview-sheet">
                {/* 1. Official Header Banner (Dialogue AI Representative saja) */}
                <div className="pdf-header-banner">
                  <span className="text-xs font-black tracking-wider uppercase text-white">
                    DIALOGUE AI REPRESENTATIVE
                  </span>
                </div>

                {/* 4. Document Sections matching on-point official titles */}
                {/* Section 1: Pertanyaan Asli */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Pertanyaan Asli
                  </div>
                  <div className="pdf-section-content italic font-medium text-slate-700 bg-slate-50/60 p-3 rounded border border-slate-100">
                    "{selectedFileForView.original_audio_text || '-'}"
                  </div>
                </div>

                {/* Section 2: Terjemahan Bahasa Indonesia */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Terjemahan Bahasa Indonesia
                  </div>
                  <div className="pdf-section-content font-semibold text-slate-900 bg-slate-50/60 p-3 rounded border border-slate-100">
                    "{selectedFileForView.translated_indonesian_text || '-'}"
                  </div>
                </div>

                {/* Section 3: Jawaban Utama */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Jawaban Utama
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.main_answer && selectedFileForView.gemini_answers?.main_answer && selectedFileForView.chatgpt_answers.main_answer !== selectedFileForView.gemini_answers.main_answer
                        ? `${selectedFileForView.chatgpt_answers.main_answer}\n\n${selectedFileForView.gemini_answers.main_answer}`
                        : (selectedFileForView.ai_answers?.main_answer ||
                           selectedFileForView.selected_answer ||
                           selectedFileForView.chatgpt_answers?.main_answer ||
                           selectedFileForView.gemini_answers?.main_answer ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 4: Jawaban Singkat */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Jawaban Singkat
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.concise_answer && selectedFileForView.gemini_answers?.concise_answer && selectedFileForView.chatgpt_answers.concise_answer !== selectedFileForView.gemini_answers.concise_answer
                        ? `${selectedFileForView.chatgpt_answers.concise_answer}\n\n${selectedFileForView.gemini_answers.concise_answer}`
                        : (selectedFileForView.ai_answers?.concise_answer ||
                           selectedFileForView.chatgpt_answers?.concise_answer ||
                           selectedFileForView.gemini_answers?.concise_answer ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 5: Analisis */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Analisis
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.brief_analysis && selectedFileForView.gemini_answers?.brief_analysis && selectedFileForView.chatgpt_answers.brief_analysis !== selectedFileForView.gemini_answers.brief_analysis
                        ? `${selectedFileForView.chatgpt_answers.brief_analysis}\n\n${selectedFileForView.gemini_answers.brief_analysis}`
                        : (selectedFileForView.ai_answers?.brief_analysis ||
                           selectedFileForView.chatgpt_answers?.brief_analysis ||
                           selectedFileForView.gemini_answers?.brief_analysis ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 6: Masalah dan Hasil Pemantauan */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Masalah dan Hasil Pemantauan
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.monitoring_issues && selectedFileForView.gemini_answers?.monitoring_issues && selectedFileForView.chatgpt_answers.monitoring_issues !== selectedFileForView.gemini_answers.monitoring_issues
                        ? `${selectedFileForView.chatgpt_answers.monitoring_issues}\n\n${selectedFileForView.gemini_answers.monitoring_issues}`
                        : (selectedFileForView.ai_answers?.monitoring_issues ||
                           selectedFileForView.chatgpt_answers?.monitoring_issues ||
                           selectedFileForView.gemini_answers?.monitoring_issues ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 7: Rekomendasi Penyelesaian */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Rekomendasi Penyelesaian
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.resolution_recommendations && selectedFileForView.gemini_answers?.resolution_recommendations && selectedFileForView.chatgpt_answers.resolution_recommendations !== selectedFileForView.gemini_answers.resolution_recommendations
                        ? `${selectedFileForView.chatgpt_answers.resolution_recommendations}\n\n${selectedFileForView.gemini_answers.resolution_recommendations}`
                        : (selectedFileForView.ai_answers?.resolution_recommendations ||
                           selectedFileForView.chatgpt_answers?.resolution_recommendations ||
                           selectedFileForView.gemini_answers?.resolution_recommendations ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 8: Peran Kemenkopolkam */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Peran Kemenkopolkam
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.kemenko_role && selectedFileForView.gemini_answers?.kemenko_role && selectedFileForView.chatgpt_answers.kemenko_role !== selectedFileForView.gemini_answers.kemenko_role
                        ? `${selectedFileForView.chatgpt_answers.kemenko_role}\n\n${selectedFileForView.gemini_answers.kemenko_role}`
                        : (selectedFileForView.ai_answers?.kemenko_role ||
                           selectedFileForView.chatgpt_answers?.kemenko_role ||
                           selectedFileForView.gemini_answers?.kemenko_role ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 9: Usulan Agenda Pemantauan Lapangan */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Usulan Agenda Pemantauan Lapangan
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.field_monitoring_agenda && selectedFileForView.gemini_answers?.field_monitoring_agenda && selectedFileForView.chatgpt_answers.field_monitoring_agenda !== selectedFileForView.gemini_answers.field_monitoring_agenda
                        ? `${selectedFileForView.chatgpt_answers.field_monitoring_agenda}\n\n${selectedFileForView.gemini_answers.field_monitoring_agenda}`
                        : (selectedFileForView.ai_answers?.field_monitoring_agenda ||
                           selectedFileForView.chatgpt_answers?.field_monitoring_agenda ||
                           selectedFileForView.gemini_answers?.field_monitoring_agenda ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 10: Berita Terbaru */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Berita Terbaru
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-800 leading-relaxed">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {selectedFileForView.chatgpt_answers?.latest_news && selectedFileForView.gemini_answers?.latest_news && selectedFileForView.chatgpt_answers.latest_news !== selectedFileForView.gemini_answers.latest_news
                        ? `${selectedFileForView.chatgpt_answers.latest_news}\n\n${selectedFileForView.gemini_answers.latest_news}`
                        : (selectedFileForView.ai_answers?.latest_news ||
                           selectedFileForView.chatgpt_answers?.latest_news ||
                           selectedFileForView.gemini_answers?.latest_news ||
                           '-')}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Section 11: Jawaban Terpilih */}
                <div className="pdf-section-block">
                  <div className="pdf-section-title">
                    Jawaban Terpilih
                  </div>
                  <div className="pdf-section-content prose-rich-text text-slate-900 font-medium leading-relaxed bg-blue-50/50 p-3 rounded border border-blue-100">
                    <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                      {resolveEnglishSelectedAnswer(selectedFileForView)}
                    </ReactMarkdown>
                  </div>
                </div>

                {/* Optional: Rujukan Bahasa Indonesia (hanya jika pilihan asli bahasa Indonesia dan berbeda dari versi Inggris) */}
                {Boolean(
                  selectedFileForView.selected_answer &&
                  selectedFileForView.selected_answer.trim() &&
                  isLikelyIndonesianText(selectedFileForView.selected_answer) &&
                  selectedFileForView.selected_answer.trim() !== resolveEnglishSelectedAnswer(selectedFileForView).trim()
                ) && (
                  <div className="pdf-section-block">
                    <div className="pdf-section-title">
                      Rujukan Jawaban Terpilih (Bahasa Indonesia)
                    </div>
                    <div className="pdf-section-content prose-rich-text italic text-slate-700 bg-slate-50/70 p-3 rounded border border-slate-100">
                      <ReactMarkdown rehypePlugins={[rehypeRaw]}>
                        {selectedFileForView.selected_answer}
                      </ReactMarkdown>
                    </div>
                  </div>
                )}

                {/* Optional: Catatan Khusus */}
                {selectedFileForView.notes && (
                  <div className="pdf-section-block">
                    <div className="pdf-section-title">
                      Catatan
                    </div>
                    <div className="pdf-section-content italic text-slate-700 bg-amber-50/50 p-3 rounded border border-amber-100">
                      {selectedFileForView.notes}
                    </div>
                  </div>
                )}

                {/* 5. Document Footer */}
                <div className="mt-6 pt-4 border-t border-slate-200 text-center">
                  <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Dokumen Resmi Terarsip - Dialogue AI Representative
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Fullscreen Rich Text & Per-Column Translate Edit Workspace */}
        {fileToEdit && (
          <div className="saved-edit-fullscreen-overlay" role="dialog" aria-modal="true" aria-label="Editor Dokumen Fullscreen">
            {/* Fullscreen Header */}
            <div className="saved-edit-fullscreen-header">
              <div>
                <h2 className="text-base font-bold text-white tracking-wide">
                  Edit Dokumen
                </h2>
              </div>

              <div className="saved-edit-header-actions">
                {/* Tombol Undo & Redo Dokumen (Di sebelah kiri translate, tanpa tulisan) */}
                <div className="flex items-center gap-1 mr-1">
                  <button
                    type="button"
                    onClick={handleGlobalUndo}
                    disabled={undoStack.length === 0 || isSavingEdit || isTranslatingAll}
                    className="saved-header-icon-btn"
                    title="Undo Dokumen (Ctrl+Z)"
                  >
                    <Undo2 size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={handleGlobalRedo}
                    disabled={redoStack.length === 0 || isSavingEdit || isTranslatingAll}
                    className="saved-header-icon-btn"
                    title="Redo Dokumen (Ctrl+Y)"
                  >
                    <Redo2 size={14} />
                  </button>
                </div>

                {/* Pilihan Bahasa Tujuan Translate All */}
                <select
                  value={translateAllTargetLang}
                  onChange={(e) => setTranslateAllTargetLang(e.target.value)}
                  className="saved-lang-select"
                  disabled={isTranslatingAll || isSavingEdit}
                  title="Pilih bahasa tujuan Translate All"
                >
                  {LANGUAGE_OPTIONS.map((opt) => (
                    <option key={opt.code} value={opt.code}>
                      {opt.name}
                    </option>
                  ))}
                </select>

                {/* Tombol Pojok Kanan Atas: Translate All (Kecuali 2 Card Pertanyaan Asli) */}
                <button
                  type="button"
                  onClick={handleTranslateAll}
                  disabled={isTranslatingAll || isSavingEdit}
                  className="saved-translate-all-btn"
                  title="Terjemahkan seluruh card sekaligus kecuali 2 card Pertanyaan Asli"
                >
                  {isTranslatingAll ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      <span>{translateAllProgress ? `Translating (${translateAllProgress})...` : 'Translating...'}</span>
                    </>
                  ) : (
                    <>
                      <Languages size={13} />
                      <span>Translate All</span>
                    </>
                  )}
                </button>

                <button
                  type="button"
                  className="saved-cancel-btn flex items-center gap-1.5"
                  onClick={() => setFileToEdit(null)}
                  disabled={isSavingEdit || isTranslatingAll}
                >
                  <X size={14} />
                  <span>Tutup</span>
                </button>
                <button
                  type="button"
                  onClick={handleSaveEditSubmit}
                  className="saved-save-btn flex items-center gap-1.5 px-4 py-2"
                  disabled={isSavingEdit || isTranslatingAll}
                >
                  {isSavingEdit ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>Menyimpan...</span>
                    </>
                  ) : (
                    <>
                      <Check size={14} />
                      <span>Simpan Perubahan</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Fullscreen Workspace Body */}
            <form onSubmit={handleSaveEditSubmit} className="saved-edit-fullscreen-body">
              {/* Row 1: Judul Dokumen */}
              <div className="w-full mb-1">
                <HubAnimatedCard
                  id="edit-card-title"
                  title="Judul"
                  className="w-full"
                >
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    className="saved-white-card-input font-bold"
                    placeholder=""
                    required
                  />
                </HubAnimatedCard>
              </div>

              {/* 10-Card Layout (2 Columns matching CardsGrid) */}
              <div className="cards-columns-grid">
                {/* LEFT COLUMN — CHATGPT */}
                <div className="column-cards">
                  {/* Card 1 — Pertanyaan Asli */}
                  <CardEditItem
                    id="chatgpt-orig"
                    title="Pertanyaan Asli"
                    value={editChatgptOriginal}
                    onChange={(val) => handleCardValueChange('chatgpt-orig', val, setEditChatgptOriginal)}
                    minRows={3}
                    placeholder=""
                    defaultTgtLang="id"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-orig')}
                    selectionNumber={getCardSelectionNumber('chatgpt-orig')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 2 — Terjemahan Bahasa Indonesia */}
                  <CardEditItem
                    id="chatgpt-trans"
                    title="Terjemahan Bahasa Indonesia"
                    value={editChatgptTranslated}
                    onChange={(val) => handleCardValueChange('chatgpt-trans', val, setEditChatgptTranslated)}
                    minRows={3}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-trans')}
                    selectionNumber={getCardSelectionNumber('chatgpt-trans')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 3 — Jawaban Utama */}
                  <CardEditItem
                    id="chatgpt-main"
                    title="Jawaban Utama"
                    value={editChatgptMain}
                    onChange={(val) => handleCardValueChange('chatgpt-main', val, setEditChatgptMain)}
                    minRows={7}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-main')}
                    selectionNumber={getCardSelectionNumber('chatgpt-main')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 4 — Jawaban Singkat */}
                  <CardEditItem
                    id="chatgpt-concise"
                    title="Jawaban Singkat"
                    value={editChatgptConcise}
                    onChange={(val) => handleCardValueChange('chatgpt-concise', val, setEditChatgptConcise)}
                    minRows={4}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-concise')}
                    selectionNumber={getCardSelectionNumber('chatgpt-concise')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 5 — Analisis */}
                  <CardEditItem
                    id="chatgpt-analysis"
                    title="Analisis"
                    value={editChatgptAnalysis}
                    onChange={(val) => handleCardValueChange('chatgpt-analysis', val, setEditChatgptAnalysis)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-analysis')}
                    selectionNumber={getCardSelectionNumber('chatgpt-analysis')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 12 — Masalah dan Hasil Pemantauan */}
                  <CardEditItem
                    id="chatgpt-monitoring"
                    title="Masalah dan Hasil Pemantauan"
                    value={editChatgptMonitoringIssues}
                    onChange={(val) => handleCardValueChange('chatgpt-monitoring', val, setEditChatgptMonitoringIssues)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-monitoring')}
                    selectionNumber={getCardSelectionNumber('chatgpt-monitoring')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 13 — Rekomendasi Penyelesaian */}
                  <CardEditItem
                    id="chatgpt-resolution"
                    title="Rekomendasi Penyelesaian"
                    value={editChatgptResolution}
                    onChange={(val) => handleCardValueChange('chatgpt-resolution', val, setEditChatgptResolution)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-resolution')}
                    selectionNumber={getCardSelectionNumber('chatgpt-resolution')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 14 — Peran Kemenkopolkam */}
                  <CardEditItem
                    id="chatgpt-role"
                    title="Peran Kemenkopolkam"
                    value={editChatgptKemenkoRole}
                    onChange={(val) => handleCardValueChange('chatgpt-role', val, setEditChatgptKemenkoRole)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-role')}
                    selectionNumber={getCardSelectionNumber('chatgpt-role')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 15 — Usulan Agenda Pemantauan Lapangan */}
                  <CardEditItem
                    id="chatgpt-agenda"
                    title="Usulan Agenda Pemantauan Lapangan"
                    value={editChatgptFieldAgenda}
                    onChange={(val) => handleCardValueChange('chatgpt-agenda', val, setEditChatgptFieldAgenda)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-agenda')}
                    selectionNumber={getCardSelectionNumber('chatgpt-agenda')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 20 — Berita Terbaru (ChatGPT) */}
                  <CardEditItem
                    id="chatgpt-news"
                    title="Berita Terbaru"
                    value={editChatgptLatestNews}
                    onChange={(val) => handleCardValueChange('chatgpt-news', val, setEditChatgptLatestNews)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('chatgpt-news')}
                    selectionNumber={getCardSelectionNumber('chatgpt-news')}
                    onToggleSelect={toggleCardChoice}
                  />
                </div>

                {/* RIGHT COLUMN — GEMINI */}
                <div className="column-cards">
                  {/* Card 6 — Pertanyaan Asli */}
                  <CardEditItem
                    id="gemini-orig"
                    title="Pertanyaan Asli"
                    value={editGeminiOriginal}
                    onChange={(val) => handleCardValueChange('gemini-orig', val, setEditGeminiOriginal)}
                    minRows={3}
                    placeholder=""
                    defaultTgtLang="id"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-orig')}
                    selectionNumber={getCardSelectionNumber('gemini-orig')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 7 — Terjemahan Bahasa Indonesia */}
                  <CardEditItem
                    id="gemini-trans"
                    title="Terjemahan Bahasa Indonesia"
                    value={editGeminiTranslated}
                    onChange={(val) => handleCardValueChange('gemini-trans', val, setEditGeminiTranslated)}
                    minRows={3}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-trans')}
                    selectionNumber={getCardSelectionNumber('gemini-trans')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 8 — Jawaban Utama */}
                  <CardEditItem
                    id="gemini-main"
                    title="Jawaban Utama"
                    value={editGeminiMain}
                    onChange={(val) => handleCardValueChange('gemini-main', val, setEditGeminiMain)}
                    minRows={7}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-main')}
                    selectionNumber={getCardSelectionNumber('gemini-main')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 9 — Jawaban Singkat */}
                  <CardEditItem
                    id="gemini-concise"
                    title="Jawaban Singkat"
                    value={editGeminiConcise}
                    onChange={(val) => handleCardValueChange('gemini-concise', val, setEditGeminiConcise)}
                    minRows={4}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-concise')}
                    selectionNumber={getCardSelectionNumber('gemini-concise')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 10 — Analisis */}
                  <CardEditItem
                    id="gemini-analysis"
                    title="Analisis"
                    value={editGeminiAnalysis}
                    onChange={(val) => handleCardValueChange('gemini-analysis', val, setEditGeminiAnalysis)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-analysis')}
                    selectionNumber={getCardSelectionNumber('gemini-analysis')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 16 — Masalah dan Hasil Pemantauan */}
                  <CardEditItem
                    id="gemini-monitoring"
                    title="Masalah dan Hasil Pemantauan"
                    value={editGeminiMonitoringIssues}
                    onChange={(val) => handleCardValueChange('gemini-monitoring', val, setEditGeminiMonitoringIssues)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-monitoring')}
                    selectionNumber={getCardSelectionNumber('gemini-monitoring')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 17 — Rekomendasi Penyelesaian */}
                  <CardEditItem
                    id="gemini-resolution"
                    title="Rekomendasi Penyelesaian"
                    value={editGeminiResolution}
                    onChange={(val) => handleCardValueChange('gemini-resolution', val, setEditGeminiResolution)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-resolution')}
                    selectionNumber={getCardSelectionNumber('gemini-resolution')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 18 — Peran Kemenkopolkam */}
                  <CardEditItem
                    id="gemini-role"
                    title="Peran Kemenkopolkam"
                    value={editGeminiKemenkoRole}
                    onChange={(val) => handleCardValueChange('gemini-role', val, setEditGeminiKemenkoRole)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-role')}
                    selectionNumber={getCardSelectionNumber('gemini-role')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 19 — Usulan Agenda Pemantauan Lapangan */}
                  <CardEditItem
                    id="gemini-agenda"
                    title="Usulan Agenda Pemantauan Lapangan"
                    value={editGeminiFieldAgenda}
                    onChange={(val) => handleCardValueChange('gemini-agenda', val, setEditGeminiFieldAgenda)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-agenda')}
                    selectionNumber={getCardSelectionNumber('gemini-agenda')}
                    onToggleSelect={toggleCardChoice}
                  />

                  {/* Card 21 — Berita Terbaru (Gemini) */}
                  <CardEditItem
                    id="gemini-news"
                    title="Berita Terbaru"
                    value={editGeminiLatestNews}
                    onChange={(val) => handleCardValueChange('gemini-news', val, setEditGeminiLatestNews)}
                    minRows={5}
                    placeholder=""
                    defaultTgtLang="en"
                    canSelect={true}
                    isSelected={selectedCardIds.includes('gemini-news')}
                    selectionNumber={getCardSelectionNumber('gemini-news')}
                    onToggleSelect={toggleCardChoice}
                  />
                </div>
              </div>

              {/* BOTTOM — CARD 11 (JAWABAN TERPILIH) */}
              <div className="w-full mt-2">
                <CardEditItem
                  id="selected-answer"
                  title="Jawaban Terpilih"
                  value={editSelectedAnswer}
                  onChange={setEditSelectedAnswer}
                  minRows={6}
                  placeholder=""
                  defaultTgtLang="en"
                  canSelect={false}
                  badge={
                    selectedCardIds.length > 0 ? (
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedCardIds([]);
                          const defaultAns = fileToEdit?.selected_answer || fileToEdit?.chatgpt_answers?.main_answer || fileToEdit?.gemini_answers?.main_answer || fileToEdit?.ai_answers?.main_answer || '';
                          setEditSelectedAnswer(defaultAns);
                        }}
                        className="saved-chosen-reset-btn"
                        title="Hapus semua pilihan kotak"
                      >
                        Reset Pilihan
                      </button>
                    ) : null
                  }
                />
              </div>

              {/* BOTTOM — CARD CATATAN (HANYA DIISI DI MENU EDIT) */}
              <div className="w-full mt-2">
                <CardEditItem
                  id="notes"
                  title="Catatan"
                  value={editNotes}
                  onChange={(val) => handleCardValueChange('notes', val, setEditNotes)}
                  minRows={4}
                  placeholder=""
                  defaultTgtLang="en"
                  canSelect={false}
                />
              </div>

              {/* Bottom Actions Bar */}
              <div className="saved-edit-bottom-bar">
                <div className="saved-edit-bottom-actions">
                  <button
                    type="button"
                    className="saved-cancel-btn"
                    onClick={() => setFileToEdit(null)}
                    disabled={isSavingEdit}
                  >
                    Batal
                  </button>
                  <button
                    type="submit"
                    className="saved-save-btn px-5 py-2 font-bold"
                    disabled={isSavingEdit}
                  >
                    {isSavingEdit ? 'Menyimpan...' : 'Simpan Perubahan'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        )}
      </div>
    </div>
  );
};
