import React, { useState, useEffect, useRef, useCallback } from 'react';
import { API_BASE_URL } from '../config';
import {
  Upload,
  Play,
  Pause,
  RotateCcw,
  Type,
  Eye,
  AlertCircle,
  CheckCircle2,
  Minus,
  Plus,
  Trash2,
  GripVertical,
  X,
  FolderPlus,
  Sparkles,
  ZoomIn,
  ZoomOut,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

interface DocumentPrompterProps {
  onSendToAi?: (text: string) => void;
  injectedDoc?: QueueDocumentItem | null;
  onInjectedDocHandled?: () => void;
}

export interface QueueDocumentItem {
  id: string;
  filename: string;
  text: string;
  pageImages: string[];
  wordCount: number;
  charCount: number;
  pageCount: number;
  durationStr: string;
  fileType: string;
}

const SPEED_LEVELS = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 2.5, 3, 4, 5, 6, 7, 8, 9, 10];

export const DocumentPrompter: React.FC<DocumentPrompterProps> = ({ 
  onSendToAi,
  injectedDoc,
  onInjectedDocHandled
}) => {
  // Document Queue State (Capacity up to 10 files - starts empty from 0)
  const [queue, setQueue] = useState<QueueDocumentItem[]>([]);
  const [activeDocId, setActiveDocId] = useState<string>('');
  const [isDeckOpen, setIsDeckOpen] = useState<boolean>(true);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  // Active Document State (Empty initially)
  const [docText, setDocText] = useState<string>('');
  const [pageImages, setPageImages] = useState<string[]>([]);
  const [activeFilename, setActiveFilename] = useState<string>('');
  const [activePageCount, setActivePageCount] = useState<number>(0);

  // Visual Display Theme & Scale
  const viewTheme = 'authentic_doc';
  const docScale = 'fit_width';

  // View / Mode State
  const [activeTab, setActiveTab] = useState<'prompter' | 'editor'>('prompter');
  const [isLoadingFile, setIsLoadingFile] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Prompter Controls (Default 0.75x)
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(0.75); // 0.5 to 10 with default 0.75
  const [fontSize, setFontSize] = useState<number>(20); // 16px to 38px
  const isMirrored = false;
  const [showFocalLine, setShowFocalLine] = useState<boolean>(true);
  const [scrollProgress, setScrollProgress] = useState<number>(0);
  const [zoomLevel, setZoomLevel] = useState<number>(100);

  // Refs for smooth 60fps animation
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number | null>(null);
  const scrollSubPixelRef = useRef<number>(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const deckFileInputRef = useRef<HTMLInputElement | null>(null);

  // Convert binary file to base64
  const fileToBase64 = (file: File | Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.includes(',') ? result.split(',')[1] : result;
        resolve(base64);
      };
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
    });
  };

  // Switch active document from queue
  const handleSelectQueueItem = useCallback((item: QueueDocumentItem) => {
    setActiveDocId(item.id);
    setDocText(item.text);
    setPageImages(item.pageImages || []);
    setActiveFilename(item.filename);
    setActivePageCount(item.pageCount);

    if (viewportRef.current) {
      viewportRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    setScrollProgress(0);
    setIsPlaying(false);
    setUploadSuccess(`Menampilkan dokumen: "${item.filename}"`);
  }, []);

  // Handle external/injected document upload (e.g. from Saved Files / List Pertanyaan)
  useEffect(() => {
    if (injectedDoc) {
      setQueue((prev) => {
        const exists = prev.some((d) => d.id === injectedDoc.id);
        if (exists) return prev;
        return [...prev, injectedDoc];
      });
      handleSelectQueueItem(injectedDoc);
      setActiveTab('prompter');
      setUploadSuccess(`Naskah "${injectedDoc.filename}" berhasil dimuat ke Prompter.`);
      onInjectedDocHandled?.();
    }
  }, [injectedDoc, handleSelectQueueItem, onInjectedDocHandled]);

  // Previous & Next Document Navigation
  const currentDocIndex = queue.findIndex((item) => item.id === activeDocId);
  const hasPrevDoc = currentDocIndex > 0;
  const hasNextDoc = currentDocIndex >= 0 && currentDocIndex < queue.length - 1;

  const handlePrevDoc = () => {
    if (hasPrevDoc) {
      handleSelectQueueItem(queue[currentDocIndex - 1]);
    }
  };

  const handleNextDoc = () => {
    if (hasNextDoc) {
      handleSelectQueueItem(queue[currentDocIndex + 1]);
    }
  };

  const handleZoomIn = () => setZoomLevel((z) => Math.min(200, z + 10));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(50, z - 10));
  const handleResetZoom = () => setZoomLevel(100);

  // Delete document from queue (can be deleted down to 0)
  const handleDeleteQueueItem = (idToDelete: string, e?: React.MouseEvent) => {
    e?.stopPropagation();
    setQueue((prevQueue) => {
      const updatedQueue = prevQueue.filter((item) => item.id !== idToDelete);

      // If the active document was deleted, switch to the first available document or reset to empty
      if (activeDocId === idToDelete) {
        if (updatedQueue.length > 0) {
          handleSelectQueueItem(updatedQueue[0]);
        } else {
          setActiveDocId('');
          setDocText('');
          setPageImages([]);
          setActiveFilename('');
          setActivePageCount(0);
          setScrollProgress(0);
          setIsPlaying(false);
        }
      }
      return updatedQueue;
    });
    setUploadSuccess("Dokumen berhasil dihapus dari antrean.");
  };

  // Drag and Drop reordering within queue
  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', String(index));
  };

  const handleDragOverItem = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleDropOnItem = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    e.stopPropagation();

    if (draggedIndex === null || draggedIndex === targetIndex) {
      setDraggedIndex(null);
      setDragOverIndex(null);
      return;
    }

    setQueue((prevQueue) => {
      const updated = [...prevQueue];
      const [movedItem] = updated.splice(draggedIndex, 1);
      updated.splice(targetIndex, 0, movedItem);
      return updated;
    });

    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // Process Document File (PDF, DOCX, TXT) and add to queue
  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);

    // Limit check: 10 files max
    if (queue.length >= 10) {
      setUploadError("Batas antrean maksimal 10 file telah tercapai. Silakan hapus file yang tidak diperlukan.");
      return;
    }

    setIsLoadingFile(true);
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const cleanExt = ext.replace('.', '') || 'txt';

    // Plain text / Markdown
    if (['.txt', '.md', '.rtf'].includes(ext)) {
      try {
        const text = await file.text();
        const words = text.split(/\s+/).filter(Boolean);
        const readingSecs = Math.round((words.length / 130) * 60);
        const mins = Math.floor(readingSecs / 60);
        const secs = readingSecs % 60;
        const durStr = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

        const newItem: QueueDocumentItem = {
          id: `doc-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
          filename: file.name,
          text,
          pageImages: [],
          wordCount: words.length,
          charCount: text.length,
          pageCount: 1,
          durationStr: durStr,
          fileType: cleanExt
        };

        setQueue((prev) => [...prev, newItem]);
        handleSelectQueueItem(newItem);
        setUploadSuccess(`File "${file.name}" ditambahkan ke antrean (${queue.length + 1}/10).`);
        setActiveTab('prompter');
        setIsLoadingFile(false);
        return;
      } catch (err) {
        setUploadError(`Gagal membaca file teks: ${String(err)}`);
        setIsLoadingFile(false);
        return;
      }
    }

    // PDF and DOCX: Send to FastAPI backend extraction engine
    try {
      const base64Data = await fileToBase64(file);
      const res = await fetch(`${API_BASE_URL}/api/document/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: file.name,
          file_base64: base64Data
        })
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({ detail: 'Terjadi kesalahan pada server' }));
        throw new Error(errJson.detail || `Server status ${res.status}`);
      }

      const data = await res.json();
      if (!data.text || !data.text.trim()) {
        throw new Error('Dokumen tidak berisi teks yang dapat diekstrak.');
      }

      const newItem: QueueDocumentItem = {
        id: `doc-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        filename: data.filename || file.name,
        text: data.text,
        pageImages: Array.isArray(data.page_images) ? data.page_images : [],
        wordCount: data.word_count || data.text.split(/\s+/).filter(Boolean).length,
        charCount: data.char_count || data.text.length,
        pageCount: data.page_count || 1,
        durationStr: data.estimated_speaking_duration || '00:00',
        fileType: cleanExt
      };

      setQueue((prev) => [...prev, newItem]);
      handleSelectQueueItem(newItem);
      setUploadSuccess(`File "${file.name}" berhasil diunggah dan ditambahkan ke antrean (${queue.length + 1}/10).`);
      setActiveTab('prompter');
    } catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : String(err);
      setUploadError(`Gagal mengekstrak "${file.name}": ${errorMsg}`);
    } finally {
      setIsLoadingFile(false);
    }
  };


  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  // Teleprompter 60fps Smooth Auto-Scroll Loop
  useEffect(() => {
    if (!isPlaying) {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
        animFrameIdRef.current = null;
      }
      lastTimeRef.current = null;
      return;
    }

    const step = (time: number) => {
      if (lastTimeRef.current === null) {
        lastTimeRef.current = time;
      }
      const deltaMs = Math.min(time - lastTimeRef.current, 60);
      lastTimeRef.current = time;

      const pxPerSec = speed * 22;
      const movePixels = (pxPerSec * deltaMs) / 1000;

      scrollSubPixelRef.current += movePixels;

      if (viewportRef.current) {
        const vp = viewportRef.current;
        if (scrollSubPixelRef.current >= 1) {
          const wholePixels = Math.floor(scrollSubPixelRef.current);
          vp.scrollTop += wholePixels;
          scrollSubPixelRef.current -= wholePixels;
        }

        const maxScroll = vp.scrollHeight - vp.clientHeight;
        if (maxScroll > 0) {
          const pct = Math.min(100, Math.round((vp.scrollTop / maxScroll) * 100));
          setScrollProgress(pct);

          if (vp.scrollTop >= maxScroll - 2) {
            setIsPlaying(false);
          }
        }
      }

      animFrameIdRef.current = requestAnimationFrame(step);
    };

    animFrameIdRef.current = requestAnimationFrame(step);

    return () => {
      if (animFrameIdRef.current) {
        cancelAnimationFrame(animFrameIdRef.current);
      }
    };
  }, [isPlaying, speed]);

  const handleScroll = () => {
    if (viewportRef.current) {
      const vp = viewportRef.current;
      const maxScroll = vp.scrollHeight - vp.clientHeight;
      if (maxScroll > 0) {
        const pct = Math.min(100, Math.round((vp.scrollTop / maxScroll) * 100));
        setScrollProgress(pct);
      }
    }
  };

  const handleRewind = () => {
    if (viewportRef.current) {
      viewportRef.current.scrollTo({ top: 0, behavior: 'smooth' });
    }
    setScrollProgress(0);
    setIsPlaying(false);
  };

  const handleDecreaseSpeed = useCallback(() => {
    setSpeed((current) => {
      const idx = SPEED_LEVELS.findIndex((v) => v >= current);
      if (idx <= 0) return SPEED_LEVELS[0];
      return SPEED_LEVELS[idx - 1];
    });
  }, []);

  const handleIncreaseSpeed = useCallback(() => {
    setSpeed((current) => {
      const nextVal = SPEED_LEVELS.find((v) => v > current);
      return nextVal !== undefined ? nextVal : SPEED_LEVELS[SPEED_LEVELS.length - 1];
    });
  }, []);

  // Keyboard Shortcuts: Space to Play/Pause, +/- to change speed
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        return;
      }
      if (e.code === 'Space') {
        e.preventDefault();
        setIsPlaying((prev) => !prev);
      } else if (e.key === 'ArrowUp' || e.key === '+') {
        e.preventDefault();
        handleIncreaseSpeed();
      } else if (e.key === 'ArrowDown' || e.key === '-') {
        e.preventDefault();
        handleDecreaseSpeed();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleIncreaseSpeed, handleDecreaseSpeed]);

  const handleSendPrompt = () => {
    if (!onSendToAi) return;
    const query = `Berdasarkan naskah dokumen "${activeFilename}", berikan ringkasan eksekutif poin penting kebijakan dan potensi pertanyaan pers diplomatik berikut:\n\n${docText.slice(0, 1500)}`;
    onSendToAi(query);
  };

  return (
    <div className="prompter-root-container">
      {/* Prompter Top Bar */}
      <div className="prompter-header-bar">
        <div className="prompter-doc-identity">
          <span className="prompter-doc-title" title={activeFilename || ''}>
            {activeFilename || ''}
          </span>
        </div>
      </div>

      {/* Main Split Body: Prompter View on Left, Queue Deck on Far Right */}
      <div className="prompter-split-body">
        {/* Left Side: Prompter View or Editor View */}
        <div className={`prompter-main-content ${isDeckOpen ? 'deck-active' : ''}`}>
          {activeTab === 'editor' ? (
            /* Document Upload & Edit Mode */
            <div className="prompter-editor-view">
              {/* File Dropzone */}
              <div
                className={`prompter-dropzone ${isLoadingFile ? 'loading' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.txt,.md"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files && e.target.files.length > 0) {
                      handleFileUpload(e.target.files[0]);
                    }
                  }}
                />
                <div className="dropzone-icon-box">
                  <Upload className="w-6 h-6 text-white" />
                </div>
                <div className="dropzone-text">
                  <div className="dropzone-title">
                    {isLoadingFile ? "Sedang mengekstrak file..." : "Klik atau seret file PDF / DOCX / TXT ke sini"}
                  </div>
                  <div className="dropzone-subtitle">
                    Tersedia antrean hingga 10 file dokumen (.pdf, .docx, .txt, .md maks 25MB)
                  </div>
                </div>
              </div>

              {/* Feedback messages */}
              {uploadError && (
                <div className="prompter-alert error">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{uploadError}</span>
                </div>
              )}
              {uploadSuccess && (
                <div className="prompter-alert success">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>{uploadSuccess}</span>
                </div>
              )}

              {/* Direct Textarea Editor */}
              <div className="prompter-textarea-wrapper">
                <div className="textarea-label-row">
                  <span>Naskah Teleprompter (Dapat Diedit Langsung)</span>
                  <span>{docText.length} Karakter</span>
                </div>
                <textarea
                  className="prompter-textarea"
                  value={docText}
                  onChange={(e) => {
                    setDocText(e.target.value);
                  }}
                  placeholder=""
                  rows={12}
                />
              </div>

              <div className="prompter-editor-actions">
                <button
                  type="button"
                  className="btn-apply-prompter"
                  onClick={() => setActiveTab('prompter')}
                >
                  <Play className="w-4 h-4" />
                  Tampilkan Dokumen di Prompter
                </button>
                {onSendToAi && (
                  <button
                    type="button"
                    className="btn-send-ai"
                    onClick={handleSendPrompt}
                  >
                    <Sparkles className="w-4 h-4" />
                    Analisis Naskah via Asisten AI
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* Teleprompter Active Viewer Mode */
            <div className="prompter-viewer-view">
              {/* Floating Control Toolbar */}
              <div className="prompter-toolbar">
                {/* Play/Pause Button */}
                <button
                  type="button"
                  id="prompter-play-toggle-btn"
                  className={`prompter-btn-play ${isPlaying ? 'playing' : ''}`}
                  onClick={() => setIsPlaying(!isPlaying)}
                  title={isPlaying ? "Jeda (Spasi)" : "Mulai Gulir Otomatis (Spasi)"}
                >
                  {isPlaying ? <Pause className="w-4 h-4 fill-current" /> : <Play className="w-4 h-4 fill-current" />}
                </button>

                {/* Rewind Button */}
                <button
                  type="button"
                  id="prompter-rewind-btn"
                  className="prompter-toolbar-btn"
                  onClick={handleRewind}
                  title="Kembali ke Awal (0%)"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>

                {/* Speed Control */}
                <div className="prompter-speed-group">
                  <span className="control-label">
                    Kecepatan:
                  </span>
                  <button
                    type="button"
                    className="prompter-stepper-btn"
                    onClick={handleDecreaseSpeed}
                    title="Perlambat (-)"
                  >
                    <Minus className="w-3 h-3" />
                  </button>
                  <input
                    type="range"
                    min={0.5}
                    max={10}
                    step={0.25}
                    value={speed}
                    onChange={(e) => setSpeed(Number(e.target.value))}
                    className="prompter-speed-slider"
                    id="prompter-speed-slider"
                  />
                  <button
                    type="button"
                    className="prompter-stepper-btn"
                    onClick={handleIncreaseSpeed}
                    title="Percepat (+)"
                  >
                    <Plus className="w-3 h-3" />
                  </button>
                  <span className="speed-val-badge">{speed}x</span>
                </div>

                {/* Zoom In & Zoom Out Controls */}
                <div className="prompter-zoom-group">
                  <button
                    type="button"
                    className="prompter-stepper-btn"
                    onClick={handleZoomOut}
                    title="Perkecil Tampilan (Zoom Out)"
                  >
                    <ZoomOut className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    className="zoom-val-badge"
                    onClick={handleResetZoom}
                    title="Klik untuk reset zoom (100%)"
                  >
                    {zoomLevel}%
                  </button>
                  <button
                    type="button"
                    className="prompter-stepper-btn"
                    onClick={handleZoomIn}
                    title="Perbesar Tampilan (Zoom In)"
                  >
                    <ZoomIn className="w-3.5 h-3.5" />
                  </button>
                </div>

                {/* Font Size Adjuster (for text/docx) */}
                {(!pageImages || pageImages.length === 0) && (
                  <div className="prompter-font-group">
                    <Type className="w-3.5 h-3.5 text-neutral-400" />
                    <button
                      type="button"
                      className="prompter-stepper-btn"
                      onClick={() => setFontSize((sz) => Math.max(16, sz - 2))}
                      title="Perkecil Font"
                    >
                      A-
                    </button>
                    <span className="font-val-label">{fontSize}px</span>
                    <button
                      type="button"
                      className="prompter-stepper-btn"
                      onClick={() => setFontSize((sz) => Math.min(38, sz + 2))}
                      title="Perbesar Font"
                    >
                      A+
                    </button>
                  </div>
                )}

                {/* Guide line toggle */}
                <button
                  type="button"
                  className={`prompter-toolbar-btn ${showFocalLine ? 'active' : ''}`}
                  onClick={() => setShowFocalLine(!showFocalLine)}
                  title="Garis Pandu Baca"
                >
                  <Eye className="w-4 h-4" />
                </button>

                {/* Previous & Next Document Navigation (di sebelah tombol mata) */}
                <button
                  type="button"
                  className="prompter-toolbar-btn"
                  onClick={handlePrevDoc}
                  disabled={!hasPrevDoc}
                  title={hasPrevDoc ? `Dokumen Sebelumnya: ${queue[currentDocIndex - 1]?.filename}` : "Tidak ada dokumen sebelumnya"}
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  className="prompter-toolbar-btn"
                  onClick={handleNextDoc}
                  disabled={!hasNextDoc}
                  title={hasNextDoc ? `Dokumen Berikutnya: ${queue[currentDocIndex + 1]?.filename}` : "Tidak ada dokumen berikutnya"}
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>

              {/* Progress bar line */}
              <div className="prompter-progress-line-track">
                <div
                  className="prompter-progress-line-fill"
                  style={{ width: `${scrollProgress}%` }}
                />
              </div>

              {/* Prompter Scrolling Viewport */}
              <div className="prompter-viewport-container">
                {/* Focal guide line */}
                {showFocalLine && <div className="prompter-focal-line" />}

                {/* Floating Edge Tab to open Deck if closed */}
                {!isDeckOpen && (
                  <button
                    type="button"
                    className="deck-floating-edge-handle"
                    onClick={() => setIsDeckOpen(true)}
                    title="Buka List Dokumen"
                  >
                    <span>List Dokumen</span>
                  </button>
                )}

                {/* Scrolling Content */}
                <div
                  ref={viewportRef}
                  onScroll={handleScroll}
                  className={`prompter-scroll-viewport ${isMirrored ? 'mirrored' : ''} ${viewTheme}`}
                >
                  {(!docText.trim() && pageImages.length === 0) ? null : viewTheme === 'authentic_doc' ? (
                    /* 100% AUTHENTIC UPLOADED FILE VIEW */
                    <div
                      className={`authentic-doc-outer-pad scale-${docScale}`}
                      style={{
                        transform: `scale(${zoomLevel / 100})`,
                        transformOrigin: 'top center',
                        transition: 'transform 0.15s ease'
                      }}
                    >
                      {pageImages && pageImages.length > 0 ? (
                        /* RENDERED ORIGINAL PDF FILE PAGES (100% VISUAL FIDELITY) */
                        <div className="authentic-pdf-pages-stack">
                          {pageImages.map((imgSrc, idx) => (
                            <div key={idx} className="authentic-pdf-page-sheet">
                              <div className="pdf-page-top-indicator">
                                <span className="pdf-badge">Halaman {idx + 1} dari {pageImages.length}</span>
                                <span className="pdf-doc-name">{activeFilename}</span>
                              </div>
                              <img
                                src={imgSrc}
                                alt={`Halaman Dokumen ${idx + 1}`}
                                className="authentic-pdf-rendered-img"
                              />
                            </div>
                          ))}
                        </div>
                      ) : (
                        /* AUTHENTIC GOVERNMENT A4 PAPER SHEET VIEW (DOCX / TEXT) */
                        <div className="authentic-paper-sheet-card">
                          {/* Official Government Letterhead */}
                          <div className="authentic-letterhead">
                            <img
                              src="/Kemenkopolkam.webp"
                              alt="Garuda Pancasila Logo"
                              className="letterhead-garuda-logo"
                            />
                            <div className="letterhead-header-text">
                              <div className="letterhead-sub">KEMENTERIAN KOORDINATOR BIDANG POLITIK DAN KEAMANAN</div>
                              <div className="letterhead-main">REPUBLIK INDONESIA</div>
                              <div className="letterhead-address">Jl. Medan Merdeka Barat No. 15, Jakarta Pusat 10110 • www.polkam.go.id</div>
                            </div>
                          </div>
                          <div className="letterhead-double-rule">
                            <div className="rule-thick" />
                            <div className="rule-thin" />
                          </div>

                          {/* Official Metadata Bar */}
                          <div className="authentic-meta-table">
                            <div className="meta-col">
                              <div className="meta-row">
                                <span className="meta-label">Nomor</span>
                                <span className="meta-val">: NK-084/POLKAM/X/2026</span>
                              </div>
                              <div className="meta-row">
                                <span className="meta-label">Sifat</span>
                                <span className="meta-val">: SANGAT RAHASIA / RESMI</span>
                              </div>
                            </div>
                            <div className="meta-col text-right">
                              <div className="meta-row">
                                <span className="meta-label">Tanggal</span>
                                <span className="meta-val">: 26 Oktober 2026</span>
                              </div>
                              <div className="meta-row">
                                <span className="meta-label">Lampiran</span>
                                <span className="meta-val">: 1 (Satu) Berkas Naskah</span>
                              </div>
                            </div>
                          </div>

                          {/* Document Body */}
                          <div className="authentic-doc-content" style={{ fontSize: `${fontSize}px` }}>
                            {docText.split('\n\n').map((paragraph, index) => {
                              const trimmed = paragraph.trim();
                              if (!trimmed) return null;
                              const isHeader = index === 0 && trimmed.length < 140;
                              return (
                                <p
                                  key={index}
                                  className={`authentic-doc-para ${isHeader ? 'authentic-para-title' : ''}`}
                                >
                                  {trimmed}
                                </p>
                              );
                            })}
                          </div>

                          {/* Official Signatory Block */}
                          <div className="authentic-signature-block">
                            <div className="sig-city-date">Jakarta, 26 Oktober 2026</div>
                            <div className="sig-role">Menteri Koordinator Bidang Politik dan Keamanan</div>
                            <div className="sig-republic">Republik Indonesia</div>
                            <div className="sig-stamp-mark">
                              <div className="stamp-circle">
                                <span className="stamp-text">KEMENKO POLKAM RI</span>
                              </div>
                              <div className="sig-signed">[ TERTANDA RESMI ]</div>
                            </div>
                          </div>

                          {/* Footer */}
                          <div className="authentic-paper-footer">
                            <span>Halaman 1 dari {activePageCount}</span>
                            <span>KLASIFIKASI: DOKUMEN RESMI KEMENTERIAN KOORDINATOR BIDANG POLITIK DAN KEAMANAN</span>
                          </div>
                        </div>
                      )}

                      <div className="prompter-bottom-spacer" />
                    </div>
                  ) : (
                    /* TRADITIONAL HIGH CONTRAST DARK PROMPTER VIEW */
                    <div
                      className="prompter-content-pad"
                      style={{
                        fontSize: `${fontSize}px`,
                        transform: `scale(${zoomLevel / 100})`,
                        transformOrigin: 'top center',
                        transition: 'transform 0.15s ease'
                      }}
                    >
                      {docText.split('\n\n').map((paragraph, index) => {
                        const trimmed = paragraph.trim();
                        if (!trimmed) return null;
                        const isTitle = index === 0 && trimmed.length < 120;
                        return (
                          <p
                            key={index}
                            className={`prompter-paragraph ${isTitle ? 'prompter-headline' : ''}`}
                          >
                            {trimmed}
                          </p>
                        );
                      })}
                      <div className="prompter-bottom-spacer" />
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Far Right: DECK KHUSUS LIST UPLOADAN FILE (QUEUE) */}
        <div className={`prompter-queue-deck ${isDeckOpen ? 'open' : 'closed'}`}>
          <div className="deck-header">
            <div className="deck-title-row">
              <span className="deck-title">List Dokumen</span>
              <span className="deck-badge-counter">{queue.length} / 10 File</span>
            </div>
            <button
              type="button"
              className="deck-close-btn"
              onClick={() => setIsDeckOpen(false)}
              title="Tutup Deck"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Deck Action & Drop Area */}
          <div
            className="deck-drop-area"
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onClick={() => deckFileInputRef.current?.click()}
            title="Klik untuk memilih file PDF / DOCX"
          >
            <input
              ref={deckFileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              style={{ display: 'none' }}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
            />
            <FolderPlus className="w-4 h-4 text-white" />
            <span className="text-xs font-semibold text-white">Upload Dokumen Baru</span>
          </div>

          {/* Queue Items List (Draggable, Selectable, Deletable) */}
          <div className="deck-items-scrollable">
            {queue.length === 0 ? null : (
              queue.map((item, idx) => {
                const isActive = item.id === activeDocId;
                const isOver = dragOverIndex === idx;
                const isDragging = draggedIndex === idx;

                return (
                  <div
                    key={item.id}
                    draggable={true}
                    onDragStart={(e) => handleDragStart(e, idx)}
                    onDragOver={(e) => handleDragOverItem(e, idx)}
                    onDrop={(e) => handleDropOnItem(e, idx)}
                    onClick={() => handleSelectQueueItem(item)}
                    className={`deck-item-card ${isActive ? 'active' : ''} ${isOver ? 'drag-over' : ''} ${isDragging ? 'is-dragging' : ''}`}
                  >
                    {/* Drag Handle */}
                    <div
                      className="deck-item-drag-handle"
                      title="Tahan dan geser untuk ubah urutan"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <GripVertical className="w-4 h-4 text-neutral-500 hover:text-neutral-300" />
                    </div>

                    {/* Document Type Badge & Index */}
                    <div className="deck-item-info">
                      <div className="deck-item-top">
                        <span className="deck-item-index">#{idx + 1}</span>
                        <span className={`deck-type-tag type-${item.fileType}`}>
                          {item.fileType.toUpperCase()}
                        </span>
                        {isActive && (
                          <span className="deck-active-tag">
                            <CheckCircle2 className="w-3 h-3 inline mr-1" />
                            SEDANG AKTIF
                          </span>
                        )}
                      </div>

                      <div className="deck-item-filename" title={item.filename}>
                        {item.filename}
                      </div>

                      <div className="deck-item-meta">
                        <span>{item.pageCount} Hal</span>
                        <span>•</span>
                        <span>{item.wordCount} Kata</span>
                        <span>•</span>
                        <span>Est. {item.durationStr}</span>
                      </div>
                    </div>

                    {/* Delete Button */}
                    <button
                      type="button"
                      className="deck-item-delete-btn"
                      onClick={(e) => handleDeleteQueueItem(item.id, e)}
                      title="Hapus dari antrean"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>

          {/* Deck Footer */}
          <div className="deck-footer">
            <span className="deck-footer-status">
              Kapasitas: {queue.length} dari 10 slot terpakai
            </span>
            <div className="deck-capacity-bar-track">
              <div
                className="deck-capacity-bar-fill"
                style={{ width: `${(queue.length / 10) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
