import React, { useState, useEffect } from 'react';
import { Header, type ViewMode } from './components/Header';
import { CardsGrid } from './components/CardsGrid';
import { DocumentPrompter, type QueueDocumentItem } from './components/DocumentPrompter';
import { LoginLandingPage } from './components/LoginLandingPage';
import { LoginModal } from './components/LoginModal';
import { SavedFilesModal } from './components/SavedFilesModal';
import { generatePdfBase64FromSessions } from './utils/exportPdf';
import type { DiplomaticResponseSet, SavedFile } from './types';
import type { User } from './types/auth';
import { API_BASE_URL } from './config';

const EMPTY_DATA: DiplomaticResponseSet = {
  canonical_question: {
    id: "",
    original_text: "",
    detected_language: "",
    timestamp: "",
    speaker: "",
    uncertain_words: []
  },
  canonical_translation_id: "",
  chatgpt: {
    main_answer: "",
    concise_answer: "",
    brief_analysis: "",
    monitoring_issues: "",
    resolution_recommendations: "",
    kemenko_role: "",
    field_monitoring_agenda: "",
    model_version: "ChatGPT"
  },
  gemini: {
    main_answer: "",
    concise_answer: "",
    brief_analysis: "",
    monitoring_issues: "",
    resolution_recommendations: "",
    kemenko_role: "",
    field_monitoring_agenda: "",
    model_version: "Gemini"
  },
  english_translations: {}
};

export const App: React.FC = () => {
  const [activeScenarioId, setActiveScenarioId] = useState<string>('');
  const [sessionData, setSessionData] = useState<DiplomaticResponseSet>(EMPTY_DATA);
  const [viewMode, setViewMode] = useState<ViewMode>('split');
  const [injectedPrompt, setInjectedPrompt] = useState<string | null>(null);

  // Saved Files State (Listed & Terdokumentasi)
  const [savedFiles, setSavedFiles] = useState<SavedFile[]>([]);
  const [isSavedFilesModalOpen, setIsSavedFilesModalOpen] = useState(false);
  const [triggerMicOnNewFile, setTriggerMicOnNewFile] = useState(false);
  const [injectedPrompterDoc, setInjectedPrompterDoc] = useState<QueueDocumentItem | null>(null);

  // Authentication State: defaults to null so landing page is the login page
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    try {
      const saved = localStorage.getItem('menkopolkam_active_user');
      if (saved) return JSON.parse(saved);
    } catch {
      // Fallback
    }
    return null;
  });
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false);

  // Sync user to localStorage
  useEffect(() => {
    try {
      if (currentUser) {
        localStorage.setItem('menkopolkam_active_user', JSON.stringify(currentUser));
      } else {
        localStorage.removeItem('menkopolkam_active_user');
      }
    } catch {
      // Ignored
    }
  }, [currentUser]);

  // Fetch saved files repository on mount and reload
  const fetchSavedFiles = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/saved-files`);
      if (res.ok) {
        const data: SavedFile[] = await res.json();
        setSavedFiles(data);
        if (data && data.length > 0) {
          // If active workspace is empty, auto-load the most recent saved session
          setSessionData((current) => {
            if (!current.canonical_question?.id && !current.canonical_question?.original_text) {
              const latest = data[0];
              setTimeout(() => handleLoadSavedFile(latest), 0);
            }
            return current;
          });
        } else {
          setSessionData((current) => {
            if (!current.canonical_question?.id && !current.canonical_question?.original_text) {
              setTimeout(() => fetchScenario('natuna_unclos'), 0);
            }
            return current;
          });
        }
      }
    } catch (err) {
      console.warn('Could not fetch saved files list:', err);
    }
  };

  useEffect(() => {
    fetchSavedFiles();
  }, []);

  // Fetch scenario data from FastAPI backend
  const fetchScenario = async (scenarioId: string) => {
    if (!scenarioId) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/session/${scenarioId}`);
      if (res.ok) {
        const json = await res.json();
        setSessionData(json);
        setActiveScenarioId(scenarioId);
      }
    } catch {
      setActiveScenarioId(scenarioId);
    }
  };

  const handleSendDocToAi = (promptText: string) => {
    setInjectedPrompt(promptText);
    if (viewMode === 'prompter') {
      setViewMode('split');
    }
  };

  const handleLoginSuccess = (user: User, token: string) => {
    setCurrentUser(user);
    try {
      localStorage.setItem('menkopolkam_jwt_token', token);
    } catch {
      // Ignored
    }
    setIsLoginModalOpen(false);
  };

  const handleLogout = () => {
    setCurrentUser(null);
    try {
      localStorage.removeItem('menkopolkam_active_user');
      localStorage.removeItem('menkopolkam_jwt_token');
    } catch {
      // Ignored
    }
  };

  // Load a saved file into active workspace
  const handleLoadSavedFile = (file: SavedFile) => {
    const loadedSet: DiplomaticResponseSet = {
      canonical_question: {
        id: file.id,
        original_text: file.original_audio_text,
        detected_language: file.detected_language,
        detected_language_name: file.detected_language_name,
        timestamp: file.timestamp,
        speaker: file.speaker,
        uncertain_words: []
      },
      canonical_translation_id: file.translated_indonesian_text,
      chatgpt: {
        main_answer: file.chatgpt_answers?.main_answer || file.ai_answers?.main_answer || '',
        concise_answer: file.chatgpt_answers?.concise_answer || file.ai_answers?.concise_answer || '',
        brief_analysis: file.chatgpt_answers?.brief_analysis || file.ai_answers?.brief_analysis || '',
        monitoring_issues: file.chatgpt_answers?.monitoring_issues || file.ai_answers?.monitoring_issues || `Hasil pemantauan operasional lapangan terhadap isu ${file.translated_indonesian_text || file.title}: Teridentifikasi dinamika koordinasi teknis dan kebutuhan validasi data faktual secara cepat.`,
        resolution_recommendations: file.chatgpt_answers?.resolution_recommendations || file.ai_answers?.resolution_recommendations || `1. Akselerasi debottlenecking hambatan operasional.\n2. Penyelarasan SOP taktis instansi teknis terkait.`,
        kemenko_role: file.chatgpt_answers?.kemenko_role || file.ai_answers?.kemenko_role || `Menko Polkam memimpin koordinasi lintas K/L terkait dan mengawal implementasi kebijakan.`,
        field_monitoring_agenda: file.chatgpt_answers?.field_monitoring_agenda || file.ai_answers?.field_monitoring_agenda || `1. Pelaksanaan rapat koordinasi terpadu pimpinan K/L.\n2. Peninjauan lapangan dan verifikasi faktual.`,
        latest_news: file.chatgpt_answers?.latest_news || file.ai_answers?.latest_news || `Liputan berita teraktual dan pemantauan isu '${file.translated_indonesian_text || file.title}' terus dimonitor secara real-time dari kantor berita resmi dan verifikasi fakta lapangan.`,
        model_version: "ChatGPT"
      },
      gemini: {
        main_answer: file.gemini_answers?.main_answer || file.ai_answers?.main_answer || '',
        concise_answer: file.gemini_answers?.concise_answer || file.ai_answers?.concise_answer || '',
        brief_analysis: file.gemini_answers?.brief_analysis || file.ai_answers?.brief_analysis || '',
        monitoring_issues: file.gemini_answers?.monitoring_issues || file.ai_answers?.monitoring_issues || `Kajian stabilitas dan pemantauan intelijen strategis atas isu ${file.translated_indonesian_text || file.title}: Menunjukkan urgensi perlindungan ketahanan sosial-politik dan mitigasi eskalasi konflik.`,
        resolution_recommendations: file.gemini_answers?.resolution_recommendations || file.ai_answers?.resolution_recommendations || `1. Formulasi kebijakan antisipatif jangka panjang.\n2. Konsolidasi kepemimpinan strategis nasional dan diplomasi preventif.`,
        kemenko_role: file.gemini_answers?.kemenko_role || file.ai_answers?.kemenko_role || `Menjalankan mandat sinkronisasi dan pengendalian kebijakan strategis kenegaraan.`,
        field_monitoring_agenda: file.gemini_answers?.field_monitoring_agenda || file.ai_answers?.field_monitoring_agenda || `1. Aktivasi desk pemantauan terpadu 24/7 di bawah Deputi terkait Kemenko Polkam.\n2. Agenda peninjauan lapangan berkala bersama Forkopimda.`,
        latest_news: file.gemini_answers?.latest_news || file.ai_answers?.latest_news || `Laporan pemberitaan media terverifikasi dan siaran pers resmi terkait '${file.translated_indonesian_text || file.title}' dihimpun secara komprehensif guna menjaga ketepatan informasi publik.`,
        model_version: "Gemini"
      },
      english_translations: {},
      selected_answer: file.selected_answer || file.ai_answers?.main_answer || file.chatgpt_answers?.main_answer || file.gemini_answers?.main_answer || ''
    };
    setSessionData(loadedSet);
    setActiveScenarioId(file.id);
  };

  // Delete saved file
  const handleDeleteSavedFile = async (fileId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/saved-files/${fileId}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        await fetchSavedFiles();
        if (activeScenarioId === fileId) {
          handleNewFile();
        }
      }
    } catch (err) {
      console.error('Error deleting file:', err);
    }
  };

  // Update/Edit saved file
  const handleUpdateSavedFile = async (fileId: string, updatedData: Partial<SavedFile>) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/saved-files/${fileId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedData)
      });
      if (res.ok) {
        const updated = await res.json();
        await fetchSavedFiles();
        if (activeScenarioId === fileId) {
          handleLoadSavedFile(updated);
        }
      }
    } catch (err) {
      console.error('Error updating file:', err);
    }
  };

  // Sync homepage updates directly to saved files
  const handleHomepageUpdate = (newSet: DiplomaticResponseSet) => {
    setSessionData(newSet);
    const qId = newSet.canonical_question?.id;
    if (qId) {
      const origText = newSet.canonical_question?.original_text || '';
      const transText = newSet.canonical_translation_id || '';
      const titleSummary = (transText.slice(0, 60) + (transText.length > 60 ? '...' : '')) || origText.slice(0, 60);

      const payload: Partial<SavedFile> = {
        title: titleSummary,
        original_audio_text: origText,
        translated_indonesian_text: transText,
        selected_answer: newSet.selected_answer || newSet.chatgpt?.main_answer || newSet.gemini?.main_answer || '',
        ai_answers: {
          main_answer: newSet.gemini?.main_answer || newSet.chatgpt?.main_answer || '',
          concise_answer: newSet.gemini?.concise_answer || newSet.chatgpt?.concise_answer || '',
          brief_analysis: newSet.gemini?.brief_analysis || newSet.chatgpt?.brief_analysis || '',
          monitoring_issues: newSet.gemini?.monitoring_issues || newSet.chatgpt?.monitoring_issues || '',
          resolution_recommendations: newSet.gemini?.resolution_recommendations || newSet.chatgpt?.resolution_recommendations || '',
          kemenko_role: newSet.gemini?.kemenko_role || newSet.chatgpt?.kemenko_role || '',
          field_monitoring_agenda: newSet.gemini?.field_monitoring_agenda || newSet.chatgpt?.field_monitoring_agenda || '',
          latest_news: newSet.gemini?.latest_news || newSet.chatgpt?.latest_news || '',
          model_version: 'GPT-4o & Gemini 1.5 Pro Hybrid'
        },
        chatgpt_answers: {
          main_answer: newSet.chatgpt?.main_answer || '',
          concise_answer: newSet.chatgpt?.concise_answer || '',
          brief_analysis: newSet.chatgpt?.brief_analysis || '',
          monitoring_issues: newSet.chatgpt?.monitoring_issues || '',
          resolution_recommendations: newSet.chatgpt?.resolution_recommendations || '',
          kemenko_role: newSet.chatgpt?.kemenko_role || '',
          field_monitoring_agenda: newSet.chatgpt?.field_monitoring_agenda || '',
          latest_news: newSet.chatgpt?.latest_news || '',
          model_version: 'ChatGPT'
        },
        gemini_answers: {
          main_answer: newSet.gemini?.main_answer || '',
          concise_answer: newSet.gemini?.concise_answer || '',
          brief_analysis: newSet.gemini?.brief_analysis || '',
          monitoring_issues: newSet.gemini?.monitoring_issues || '',
          resolution_recommendations: newSet.gemini?.resolution_recommendations || '',
          kemenko_role: newSet.gemini?.kemenko_role || '',
          field_monitoring_agenda: newSet.gemini?.field_monitoring_agenda || '',
          latest_news: newSet.gemini?.latest_news || '',
          model_version: 'Gemini'
        }
      };

      fetch(`${API_BASE_URL}/api/saved-files/${qId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(() => fetchSavedFiles())
      .catch(() => {});
    }
  };

  // New File: Clean reset, auto reload, and loop back to On Mic
  const handleNewFile = () => {
    setSessionData(EMPTY_DATA);
    setActiveScenarioId('');
    setInjectedPrompt(null);
    setTriggerMicOnNewFile(true);
  };

  // Upload Selected Questions/Answers to Document Teleprompter as official authentic PDF
  const handleUploadToPrompter = async (files: SavedFile[]) => {
    if (files.length === 0) return;

    try {
      // 1. Generate identical official formatted PDF as Ekspor PDF
      const { filename, base64 } = generatePdfBase64FromSessions(files);

      // 2. Extract through backend document extraction engine to render authentic high-res PDF pages
      const res = await fetch(`${API_BASE_URL}/api/document/extract`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename,
          file_base64: base64
        })
      });

      if (!res.ok) {
        throw new Error('Gagal mengekstrak PDF dokumen');
      }

      const data = await res.json();

      const docItem: QueueDocumentItem = {
        id: `pdf-export-${Date.now()}`,
        filename: data.filename || filename,
        text: data.text || '',
        pageImages: Array.isArray(data.page_images) ? data.page_images : [],
        wordCount: data.word_count || (data.text ? data.text.split(/\s+/).filter(Boolean).length : 0),
        charCount: data.char_count || (data.text ? data.text.length : 0),
        pageCount: data.page_count || 1,
        durationStr: data.estimated_speaking_duration || '00:00',
        fileType: 'pdf'
      };

      setInjectedPrompterDoc(docItem);
      setIsSavedFilesModalOpen(false);

      // Ensure prompter is visible
      if (viewMode === 'assistant') {
        setViewMode('split');
      }
    } catch (err) {
      console.error('Error uploading PDF to prompter:', err);
    }
  };

  // If not authenticated, render Login Landing Page
  if (!currentUser) {
    return <LoginLandingPage onLoginSuccess={handleLoginSuccess} />;
  }

  return (
    <div className={`app-container split-layout-active mode-${viewMode}`}>
      {/* Official Header with Logo, Title, Split Mode Switcher & Saved Files Button */}
      <Header
        viewMode={viewMode}
        onViewModeChange={(mode) => setViewMode(mode)}
        currentUser={currentUser}
        onOpenLogin={() => setIsLoginModalOpen(true)}
        onLogout={handleLogout}
        savedFilesCount={savedFiles.length}
        onOpenSavedFiles={() => setIsSavedFilesModalOpen(true)}
        onNewFile={handleNewFile}
      />

      {/* Viewer Notification Banner if logged in as Viewer */}
      {currentUser.role === 'Viewer' && (
        <div className="viewer-role-banner" role="status">
          <span className="viewer-badge-icon">👁️</span>
          <span>
            <strong>Akses Pengamat (Mode Pantau):</strong> Anda dapat meninjau seluruh data dokumen resmi, transkripsi, dan analisis kecerdasan AI. Fitur modifikasi dibatasi untuk pemantauan.
          </span>
        </div>
      )}

      {/* Split-Screen Workspace */}
      <div className={`workspace-split-wrapper mode-${viewMode}`}>
        {/* Left Pane: AI Assistant & 11 Diplomatic Response Cards */}
        {(viewMode === 'split' || viewMode === 'assistant') && (
          <section
            className={`pane-column pane-left-assistant ${viewMode === 'assistant' ? 'full-width' : ''}`}
            aria-label="Asisten Diplomasi AI Menkopolkam"
          >
            <CardsGrid
              data={sessionData}
              activeScenarioId={activeScenarioId}
              onSelectScenario={(id) => fetchScenario(id)}
              onNewQuestionReceived={handleHomepageUpdate}
              injectedPrompt={injectedPrompt}
              onClearInjectedPrompt={() => setInjectedPrompt(null)}
              savedFilesCount={savedFiles.length}
              onOpenSavedFilesModal={() => setIsSavedFilesModalOpen(true)}
              onRefreshSavedFiles={fetchSavedFiles}
              onNewFile={handleNewFile}
              triggerMicOnNewFile={triggerMicOnNewFile}
              onResetTriggerMic={() => setTriggerMicOnNewFile(false)}
            />
          </section>
        )}

        {/* Right Pane: Document Input, Viewer & Teleprompter */}
        {(viewMode === 'split' || viewMode === 'prompter') && (
          <section
            className={`pane-column pane-right-prompter ${viewMode === 'prompter' ? 'full-width' : ''}`}
            aria-label="Penampil Dokumen dan Teleprompter"
          >
            <DocumentPrompter
              onSendToAi={handleSendDocToAi}
              injectedDoc={injectedPrompterDoc}
              onInjectedDocHandled={() => setInjectedPrompterDoc(null)}
            />
          </section>
        )}
      </div>

      {/* Saved Files Management Modal (View, Edit, Delete, Listed & Terdokumentasi) */}
      <SavedFilesModal
        isOpen={isSavedFilesModalOpen}
        onClose={() => setIsSavedFilesModalOpen(false)}
        files={savedFiles}
        onLoadFile={handleLoadSavedFile}
        onDeleteFile={handleDeleteSavedFile}
        onUpdateFile={handleUpdateSavedFile}
        onNewFile={handleNewFile}
        onUploadToPrompter={handleUploadToPrompter}
      />

      {/* Login Modal for switching account inside the workspace */}
      <LoginModal
        isOpen={isLoginModalOpen}
        currentUser={currentUser}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />
    </div>
  );
};

export default App;
