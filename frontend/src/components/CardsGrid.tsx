import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { Square, Play, Pause, Send, Pencil, Check, X, Gauge, Paperclip, FileText, Loader2, BookOpen } from 'lucide-react';
import type { DiplomaticResponseSet, SelectableCardId } from '../types';
import { HubAnimatedCard } from './ui/animated-card';
import { VoicePlatformBar } from './VoicePlatformBar';
import { useRealtimeSession } from '../hooks/useRealtimeSession';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import { API_BASE_URL } from '../config';

interface CardsGridProps {
  data: DiplomaticResponseSet;
  activeScenarioId?: string;
  onSelectScenario?: (id: string) => void;
  onNewQuestionReceived?: (newSet: DiplomaticResponseSet) => void;
  injectedPrompt?: string | null;
  onClearInjectedPrompt?: () => void;
  savedFilesCount?: number;
  onOpenSavedFilesModal?: () => void;
  onRefreshSavedFiles?: () => void;
  onNewFile?: () => void;
  triggerMicOnNewFile?: boolean;
  onResetTriggerMic?: () => void;
}

export const CardsGrid: React.FC<CardsGridProps> = ({
  data,
  onNewQuestionReceived,
  injectedPrompt,
  onClearInjectedPrompt,
  onOpenSavedFilesModal: _onOpenSavedFilesModal,
  onRefreshSavedFiles,
  triggerMicOnNewFile,
  onResetTriggerMic
}) => {
  const { canonical_question, canonical_translation_id, chatgpt, gemini } = data;

  const [liveStreamingText, setLiveStreamingText] = useState<string>('');

  const hasExistingData = Boolean(
    canonical_question?.original_text?.trim() ||
    canonical_translation_id?.trim() ||
    chatgpt?.main_answer?.trim() ||
    gemini?.main_answer?.trim() ||
    liveStreamingText?.trim()
  );

  // Multiple Choice Card Selection on Main Page
  const [selectedCardIds, setSelectedCardIds] = useState<SelectableCardId[]>([]);
  const [selectedAnswerLang, setSelectedAnswerLang] = useState<'en' | 'id'>('en');
  const [translatedEnglishText, setTranslatedEnglishText] = useState<string>('');
  const [isTranslatingSelected, setIsTranslatingSelected] = useState<boolean>(false);
  const [cardTranslations, setCardTranslations] = useState<Record<string, string>>({});
  const lastTranslatedSourceRef = useRef<string>('');
  const cardTranslationCacheRef = useRef<Record<string, string>>({});

  useEffect(() => {
    if (hasExistingData && selectedCardIds.length === 0) {
      setSelectedCardIds([3]);
    }
  }, [hasExistingData]);

  // Inline editing state for cards on main page
  const [editingCardId, setEditingCardId] = useState<SelectableCardId | null>(null);
  const [editingText, setEditingText] = useState<string>('');

  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [isAudioPaused, setIsAudioPaused] = useState<boolean>(false);
  const [isAudioLoading, setIsAudioLoading] = useState<boolean>(false);
  const [audioCurrentTime, setAudioCurrentTime] = useState<number>(0);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(() => {
    try {
      localStorage.removeItem('menkopolkam_tts_speed');
      localStorage.removeItem('menkopolkam_tts_speed_v2');
      const saved = localStorage.getItem('dialogue_ai_tts_speed_v3');
      if (saved) {
        const val = Number(saved);
        if (!isNaN(val) && val > 0) return val;
      }
    } catch {}
    return 0.75;
  });
  const currentAudioTextRef = useRef<string>('');
  const webSpeechTimerRef = useRef<any>(null);
  // Full-Duplex Continuous Live Voice State (Gemini & ChatGPT Live Experience)
  const [isUnifiedLiveActive, setIsUnifiedLiveActive] = useState<boolean>(false);
  const isUnifiedLiveActiveRef = useRef<boolean>(false);
  const [isProcessingLive, setIsProcessingLive] = useState<boolean>(false);
  const [isAiSpeaking, setIsAiSpeaking] = useState<boolean>(false);
  const isAiSpeakingRef = useRef<boolean>(false);
  const [liveLanguage, setLiveLanguage] = useState<string>('auto');
  const [typedQuestion, setTypedQuestion] = useState<string>('');
  const [showSources, setShowSources] = useState<boolean>(true);
  const [showConfirmModal, setShowConfirmModal] = useState<boolean>(false);
  const [pendingAction, setPendingAction] = useState<(() => void) | null>(null);

  const resetAllSessionData = () => {
    stopAllAudio();
    setSelectedCardIds([]);
    setLiveStreamingText('');
    latestSpokenRef.current = '';
    accumulatedTranscriptRef.current = '';
    const emptySet: DiplomaticResponseSet = {
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
        model_version: "ChatGPT"
      },
      gemini: {
        main_answer: "",
        concise_answer: "",
        brief_analysis: "",
        model_version: "Gemini"
      },
      english_translations: {},
      live_sources: []
    };
    onNewQuestionReceived?.(emptySet);
  };

  const realtime = useRealtimeSession({
    onTranscriptDelta: (_role, _delta) => {
    },
    onTurnComplete: (completedText) => {
      if (realtime.mode === 'dual_intelligence' && completedText) {
        realtime.requestDualAnalysis(completedText);
      }
    }
  });

  interface AttachedKnowledgeFile {
    name: string;
    text: string;
    sizeStr: string;
    wordCount: number;
  }
  const [attachedFile, setAttachedFile] = useState<AttachedKnowledgeFile | null>(null);
  const [isExtractingDoc, setIsExtractingDoc] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileAttach = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsExtractingDoc(true);
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const sizeStr = file.size > 1024 * 1024
      ? `${(file.size / (1024 * 1024)).toFixed(1)} MB`
      : `${Math.round(file.size / 1024)} KB`;

    try {
      let extractedText = '';

      if (['.txt', '.md', '.csv', '.json'].includes(ext)) {
        extractedText = await file.text();
      } else {
        // PDF or Word DOCX: use backend extraction engine
        const reader = new FileReader();
        const base64Promise = new Promise<string>((resolve, reject) => {
          reader.onload = () => {
            const result = reader.result as string;
            const base64 = result.split(',')[1] || '';
            resolve(base64);
          };
          reader.onerror = reject;
        });
        reader.readAsDataURL(file);
        const base64Data = await base64Promise;

        const res = await fetch(`${API_BASE_URL}/api/document/extract`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            filename: file.name,
            file_base64: base64Data
          })
        });

        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: 'Gagal mengekstrak dokumen' }));
          throw new Error(err.detail || 'Gagal memproses dokumen');
        }

        const data = await res.json();
        extractedText = data.text || '';
      }

      if (!extractedText || !extractedText.trim()) {
        alert('Berkas lampiran tidak memiliki teks yang dapat diekstrak sebagai knowledge.');
        return;
      }

      const words = extractedText.split(/\s+/).filter(Boolean);
      setAttachedFile({
        name: file.name,
        text: extractedText,
        sizeStr,
        wordCount: words.length
      });
    } catch (err: any) {
      console.error('Error attaching knowledge file:', err);
      alert(`Gagal melampirkan berkas knowledge: ${err?.message || String(err)}`);
    } finally {
      setIsExtractingDoc(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveAttachment = () => {
    setAttachedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleQuerySubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const query = typedQuestion.trim();
    if (!query || isProcessingLive) return;

    resetAllSessionData();
    submitLiveSpeech(query);
    setTypedQuestion('');
  };


  const recognitionRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const latestSpokenRef = useRef<string>('');
  const accumulatedTranscriptRef = useRef<string>('');
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const silenceTimeoutRef = useRef<any>(null);


  useEffect(() => {
    isUnifiedLiveActiveRef.current = isUnifiedLiveActive;
  }, [isUnifiedLiveActive]);

  useEffect(() => {
    isAiSpeakingRef.current = isAiSpeaking;
  }, [isAiSpeaking]);

  useEffect(() => {
    if (injectedPrompt && injectedPrompt.trim()) {
      const promptToRun = injectedPrompt.trim();
      onClearInjectedPrompt?.();

      const executeInjectedPrompt = () => {
        resetAllSessionData();
        setTypedQuestion(promptToRun);
        submitLiveSpeech(promptToRun);
      };

      if (hasExistingData) {
        setPendingAction(() => executeInjectedPrompt);
        setShowConfirmModal(true);
      } else {
        executeInjectedPrompt();
      }
    }
  }, [injectedPrompt]);

  // Alur New File -> loop ke On Mic
  useEffect(() => {
    if (triggerMicOnNewFile) {
      onResetTriggerMic?.();
      resetAllSessionData();
      setTimeout(() => {
        setIsUnifiedLiveActive(true);
        setLiveStreamingText('');
        latestSpokenRef.current = '';
        accumulatedTranscriptRef.current = '';
        startLiveListening();
      }, 150);
    }
  }, [triggerMicOnNewFile]);

  const formatTime = (secs: number) => {
    if (!secs || isNaN(secs) || !isFinite(secs)) return '0:00';
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const stopAllAudio = () => {
    if (webSpeechTimerRef.current) {
      clearInterval(webSpeechTimerRef.current);
      webSpeechTimerRef.current = null;
    }
    if (audioPlayerRef.current) {
      try {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      } catch {}
      audioPlayerRef.current = null;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    setIsAiSpeaking(false);
    setIsPlayingAudio(false);
    setIsAudioPaused(false);
    setIsAudioLoading(false);
    setAudioCurrentTime(0);
  };

  const handleSpeedChange = (newSpeed: number) => {
    setPlaybackSpeed(newSpeed);
    try {
      localStorage.setItem('dialogue_ai_tts_speed_v3', String(newSpeed));
    } catch {}
    if (audioPlayerRef.current) {
      try {
        audioPlayerRef.current.playbackRate = newSpeed;
      } catch (err) {
        console.warn('Failed to update playbackRate:', err);
      }
    }
  };

  const handleSeek = (newTime: number) => {
    setAudioCurrentTime(newTime);
    if (audioPlayerRef.current) {
      try {
        audioPlayerRef.current.currentTime = newTime;
      } catch {}
    }
  };

  const playNeuralSpeech = async (text: string, onEnded?: () => void) => {
    if (!text || !text.trim()) {
      onEnded?.();
      return;
    }
    stopAllAudio();
    setIsAiSpeaking(true);
    setIsAudioLoading(true);
    setIsPlayingAudio(true);
    setIsAudioPaused(false);
    currentAudioTextRef.current = text.trim();

    try {
      const res = await fetch(`${API_BASE_URL}/api/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim(), voice: 'Aoede' })
      });

      if (res.ok) {
        const blob = await res.blob();
        setIsAudioLoading(false);

        // Calculate real duration immediately for PCM 24000Hz 16-bit Mono (48,000 bytes/sec)
        const calcDuration = Math.max(0, (blob.size - 44) / 48000);
        if (calcDuration > 0) {
          setAudioDuration(calcDuration);
        }

        const audioUrl = URL.createObjectURL(blob);
        const audio = new Audio(audioUrl);
        audio.playbackRate = playbackSpeed;
        audioPlayerRef.current = audio;

        const syncDur = () => {
          if (audio.duration && !isNaN(audio.duration) && isFinite(audio.duration) && audio.duration > 0) {
            setAudioDuration(audio.duration);
          }
        };

        audio.onloadedmetadata = syncDur;
        audio.ondurationchange = syncDur;
        audio.oncanplay = syncDur;

        audio.ontimeupdate = () => {
          setAudioCurrentTime(audio.currentTime);
          syncDur();
        };

        audio.onended = () => {
          setIsAiSpeaking(false);
          setIsPlayingAudio(false);
          setIsAudioPaused(false);
          setIsAudioLoading(false);
          setAudioCurrentTime(0);
          audioPlayerRef.current = null;
          URL.revokeObjectURL(audioUrl);
          onEnded?.();
        };

        audio.onerror = () => {
          setIsAiSpeaking(false);
          setIsPlayingAudio(false);
          setIsAudioPaused(false);
          setIsAudioLoading(false);
          audioPlayerRef.current = null;
          fallbackWebSpeech(text, onEnded);
        };

        await audio.play();
        return;
      }
    } catch (err) {
      console.warn('Backend Gemini TTS error, falling back to speech synthesis:', err);
    } finally {
      setIsAudioLoading(false);
    }

    fallbackWebSpeech(text, onEnded);
  };

  const fallbackWebSpeech = (text: string, onEnded?: () => void) => {
    if (!('speechSynthesis' in window)) {
      setIsAiSpeaking(false);
      setIsPlayingAudio(false);
      setIsAudioPaused(false);
      setIsAudioLoading(false);
      onEnded?.();
      return;
    }
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = selectedAnswerLang === 'en' ? 'en-US' : 'id-ID';
    utterance.rate = playbackSpeed;

    // Strictly select female voice (cewe) only
    try {
      const allVoices = window.speechSynthesis.getVoices();
      if (allVoices && allVoices.length > 0) {
        const langPrefix = selectedAnswerLang === 'en' ? 'en' : 'id';
        const matchingLangVoices = allVoices.filter(v => v.lang.toLowerCase().startsWith(langPrefix));
        const candidatePool = matchingLangVoices.length > 0 ? matchingLangVoices : allVoices;

        const femaleNames = [
          'female', 'zira', 'jenny', 'ava', 'samantha', 'victoria', 'karen', 'susan',
          'gadis', 'putri', 'siti', 'indah', 'aria', 'hazel', 'cathy', 'natasha',
          'google us english', 'google bahasa indonesia'
        ];
        const maleNames = ['male', 'david', 'mark', 'george', 'andika', 'guy', 'stefan', 'richard'];

        // 1. Explicit female voice in target language
        let chosenFemaleVoice = candidatePool.find(v => {
          const nameLower = v.name.toLowerCase();
          return femaleNames.some(fn => nameLower.includes(fn)) && !maleNames.some(mn => nameLower.includes(mn));
        });

        // 2. Fallback: Any voice that is not male
        if (!chosenFemaleVoice) {
          chosenFemaleVoice = candidatePool.find(v => !maleNames.some(mn => v.name.toLowerCase().includes(mn)));
        }

        if (chosenFemaleVoice) {
          utterance.voice = chosenFemaleVoice;
        }
      }
    } catch {
      // Ignored
    }

    // Estimate duration so timeline slider and timer actively display progress
    const words = text.trim().split(/\s+/).length;
    const estimatedDuration = Math.max(3, Math.round(words / 2.5));
    setAudioDuration(estimatedDuration);
    setAudioCurrentTime(0);

    const startTime = Date.now();
    if (webSpeechTimerRef.current) clearInterval(webSpeechTimerRef.current);
    webSpeechTimerRef.current = setInterval(() => {
      const elapsed = ((Date.now() - startTime) / 1000) * playbackSpeed;
      if (elapsed <= estimatedDuration) {
        setAudioCurrentTime(elapsed);
      }
    }, 200);

    utterance.onend = () => {
      if (webSpeechTimerRef.current) clearInterval(webSpeechTimerRef.current);
      setIsAiSpeaking(false);
      setIsPlayingAudio(false);
      setIsAudioPaused(false);
      setIsAudioLoading(false);
      setAudioCurrentTime(0);
      onEnded?.();
    };
    utterance.onerror = () => {
      if (webSpeechTimerRef.current) clearInterval(webSpeechTimerRef.current);
      setIsAiSpeaking(false);
      setIsPlayingAudio(false);
      setIsAudioPaused(false);
      setIsAudioLoading(false);
      onEnded?.();
    };
    window.speechSynthesis.speak(utterance);
  };

  const getCardContent = (cardId: SelectableCardId): string => {
    switch (cardId) {
      case 1:
        return canonical_question?.original_text || '';
      case 2:
        return canonical_translation_id || '';
      case 3:
        return chatgpt?.main_answer || '';
      case 4:
        return chatgpt?.concise_answer || '';
      case 5:
        return chatgpt?.brief_analysis || '';
      case 6:
        return canonical_question?.original_text || '';
      case 7:
        return canonical_translation_id || '';
      case 8:
        return gemini?.main_answer || '';
      case 9:
        return gemini?.concise_answer || '';
      case 10:
        return gemini?.brief_analysis || '';
      case 12:
        return chatgpt?.monitoring_issues || '';
      case 13:
        return chatgpt?.resolution_recommendations || '';
      case 14:
        return chatgpt?.kemenko_role || '';
      case 15:
        return chatgpt?.field_monitoring_agenda || '';
      case 20:
        return (chatgpt?.latest_news && chatgpt.latest_news.trim().length > 0)
          ? chatgpt.latest_news.trim()
          : (data.live_sources && data.live_sources.length > 0)
            ? `**Rangkuman Berita & Pemantauan Terkini (ChatGPT)**:\n\n` + data.live_sources.slice(0, 4).map(s => `- 📰 **Berita Terpantau**: ${s}`).join('\n') + `\n\n- **Status Pemantauan**: Informasi terus dimutakhirkan melalui pelaporan terpercaya media arus utama dan kanal resmi pemerintah.`
            : (canonical_question?.original_text && canonical_question.original_text.trim())
              ? `**Rangkuman Berita & Pemantauan Terkini (ChatGPT)**:\n\n- 📰 **Liputan Terkini**: Perkembangan isu **${canonical_question.original_text}** terus dipantau secara real-time dari kanal informasi resmi dan kantor berita nasional.\n- **Status Verifikasi**: Data diperbarui secara berkala guna mendukung analisis situasional yang akurat.`
              : '';
      case 16:
        return gemini?.monitoring_issues || '';
      case 17:
        return gemini?.resolution_recommendations || '';
      case 18:
        return gemini?.kemenko_role || '';
      case 19:
        return gemini?.field_monitoring_agenda || '';
      case 21:
        return (gemini?.latest_news && gemini.latest_news.trim().length > 0)
          ? gemini.latest_news.trim()
          : (data.live_sources && data.live_sources.length > 0)
            ? `**Laporan Berita & Data Faktual Terupdate (Gemini)**:\n\n` + data.live_sources.slice(0, 4).map(s => `- 🌐 **Laporan Berita**: ${s}`).join('\n') + `\n\n- **Sorotan Utama**: Rilis resmi kementerian/lembaga dan perkembangan media dihimpun untuk memastikan ketepatan data situasi nasional.`
            : (canonical_question?.original_text && canonical_question.original_text.trim())
              ? `**Laporan Berita & Data Faktual Terupdate (Gemini)**:\n\n- 🌐 **Rilis Media & Fakta**: Laporan pemberitaan mutakhir dan siaran pers resmi terkait isu **${canonical_question.original_text}** dihimpun secara komprehensif.\n- **Sorotan**: Pemutakhiran dilakukan secara kontinu guna menjamin keandalan data dan koordinasi penanganan strategis.`
              : '';
      default:
        return '';
    }
  };

  const selectedCardsContent = selectedCardIds
    .map(id => getCardContent(id).trim())
    .filter(text => text.length > 0)
    .join('\n\n');

  // Fallback hierarchy: User chosen cards -> saved answer in data -> ChatGPT Main -> Gemini Main
  const combinedSelectedText = selectedCardsContent
    || (data.selected_answer && data.selected_answer.trim())
    || (chatgpt?.main_answer && chatgpt.main_answer.trim())
    || (gemini?.main_answer && gemini.main_answer.trim())
    || '';

  // Helper to detect if a string is still Indonesian (not translated to English)
  const isLikelyIndonesian = useCallback((text: string): boolean => {
    if (!text || !text.trim()) return false;
    const lower = ` ${text.toLowerCase()} `;
    const idMarkers = [
      ' yang ', ' dan ', ' di ', ' dari ', ' ini ', ' untuk ', ' pada ', ' adalah ',
      ' dengan ', ' secara ', ' oleh ', ' berdasarkan ', ' kemenangan ', ' mencetak ',
      ' perpanjangan ', ' waktu ', ' terkini ', ' terupdate ', ' pemantauan ', ' laporan ',
      ' hasil ', ' rekomendasi ', ' kementerian ', ' kebijakan ', ' babak '
    ];
    let matches = 0;
    for (const m of idMarkers) {
      if (lower.includes(m)) matches++;
    }
    return matches >= 2;
  }, []);

  // Helper to retrieve precomputed or cached English translation for any card
  const getCardEnglishContent = useCallback((cardId: SelectableCardId): string => {
    // 1. Direct from React state translation map
    const stateTr = cardTranslations[`card_${cardId}`];
    if (stateTr && stateTr.trim() && !isLikelyIndonesian(stateTr)) {
      return stateTr.trim();
    }
    // 2. Direct from backend english_translations
    const direct = data.english_translations?.[`card_${cardId}`];
    if (direct && direct.trim() && !isLikelyIndonesian(direct)) {
      return direct.trim();
    }
    // 3. Direct from local card translation cache
    const cached = cardTranslationCacheRef.current[`card_${cardId}`];
    if (cached && cached.trim() && !isLikelyIndonesian(cached)) {
      return cached.trim();
    }
    // 4. Question cards (1, 2, 6, 7): if source question was in English, return original English
    if ((cardId === 1 || cardId === 6) && canonical_question?.detected_language === 'en') {
      return (canonical_question.original_text || '').trim();
    }
    if ((cardId === 2 || cardId === 7) && canonical_question?.detected_language === 'en') {
      return (canonical_question.original_text || '').trim();
    }
    return '';
  }, [data.english_translations, canonical_question, cardTranslations, isLikelyIndonesian]);

  // Synchronously compute composite English text matching EXACT selection order (0ms instant!)
  const compositeEnglishFromCards = useMemo(() => {
    if (selectedCardIds.length === 0) {
      const c11 = data.english_translations?.card_11;
      if (c11 && !isLikelyIndonesian(c11)) return c11.trim();
      const selEn = data.selected_answer_en;
      if (selEn && !isLikelyIndonesian(selEn)) return selEn.trim();
      const c3 = getCardEnglishContent(3);
      if (c3) return c3;
      const directC3 = data.english_translations?.card_3;
      if (directC3 && !isLikelyIndonesian(directC3)) return directC3.trim();
      return '';
    }
    const parts = selectedCardIds
      .map(id => getCardEnglishContent(id))
      .filter(t => t.trim().length > 0 && !isLikelyIndonesian(t));
    return parts.join('\n\n');
  }, [selectedCardIds, getCardEnglishContent, data.english_translations, data.selected_answer_en, cardTranslations, isLikelyIndonesian]);

  // Automatic translation for any selected cards missing English translation
  useEffect(() => {
    if (!combinedSelectedText || !combinedSelectedText.trim()) {
      setTranslatedEnglishText('');
      lastTranslatedSourceRef.current = '';
      setIsTranslatingSelected(false);
      return;
    }

    const activeIdsToTranslate = selectedCardIds.length > 0 ? selectedCardIds : ([3] as SelectableCardId[]);
    // Check which selected cards are missing English translation
    const missingCardIds = activeIdsToTranslate.filter(id => !getCardEnglishContent(id));
    if (missingCardIds.length === 0) {
      setIsTranslatingSelected(false);
      return;
    }

    let isCancelled = false;
    setIsTranslatingSelected(true);

    const translateMissing = async () => {
      try {
        await Promise.all(
          missingCardIds.map(async (id) => {
            const rawText = getCardContent(id).trim();
            if (!rawText) return;
            const res = await fetch(`${API_BASE_URL}/api/translate`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                text: rawText,
                target_lang: 'en',
                source_lang: 'id'
              })
            });
            if (res.ok && !isCancelled) {
              const resJson = await res.json();
              if (resJson.translated_text) {
                const tr = resJson.translated_text.trim();
                if (!isLikelyIndonesian(tr)) {
                  cardTranslationCacheRef.current[`card_${id}`] = tr;
                  if (data.english_translations) {
                    data.english_translations[`card_${id}`] = tr;
                  }
                  setCardTranslations(prev => ({ ...prev, [`card_${id}`]: tr }));
                }
              }
            }
          })
        );
        if (!isCancelled) {
          const freshEnglish = activeIdsToTranslate
            .map(id => getCardEnglishContent(id) || cardTranslationCacheRef.current[`card_${id}`] || '')
            .filter(t => t && !isLikelyIndonesian(t))
            .join('\n\n');
          if (freshEnglish) {
            setTranslatedEnglishText(freshEnglish);
          }
        }
      } catch (err) {
        console.warn('Auto translation of missing cards failed:', err);
      } finally {
        if (!isCancelled) {
          setIsTranslatingSelected(false);
        }
      }
    };

    translateMissing();

    return () => {
      isCancelled = true;
    };
  }, [selectedCardIds, combinedSelectedText, getCardEnglishContent, data.english_translations, isLikelyIndonesian]);

  // Sync selected answer to saved file in database (including English translation for Card 11)
  useEffect(() => {
    if (!combinedSelectedText || !data.canonical_question?.id) return;
    const timer = setTimeout(() => {
      const token = localStorage.getItem('menkopolkam_jwt_token');
      const activeEn = (compositeEnglishFromCards.trim() || translatedEnglishText.trim());
      const updatedPayload: Record<string, any> = {
        selected_answer: combinedSelectedText
      };
      if (activeEn) {
        updatedPayload.selected_answer_en = activeEn;
        updatedPayload.english_translations = {
          ...(data.english_translations || {}),
          card_11: activeEn,
          selected_answer: activeEn
        };
      }
      fetch(`${API_BASE_URL}/api/saved-files/${data.canonical_question.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        body: JSON.stringify(updatedPayload)
      })
      .then(() => onRefreshSavedFiles?.())
      .catch(() => {});
    }, 600);

    return () => clearTimeout(timer);
  }, [combinedSelectedText, compositeEnglishFromCards, translatedEnglishText, data.canonical_question?.id, data.english_translations]);

  // Determine active text for Card 11 based on language toggle (default 'en')
  // Instantaneous English synthesis strictly ordered by card selection!
  const currentCard11Text = selectedAnswerLang === 'en'
    ? (compositeEnglishFromCards.trim() || (!isLikelyIndonesian(translatedEnglishText) ? translatedEnglishText.trim() : ''))
    : combinedSelectedText.trim();

  const getSelectedSourceLabel = (): string => {
    if (selectedCardIds.length === 0) {
      if (data.selected_answer) return 'Jawaban Tersimpan';
      return 'Belum Ada Pilihan';
    }
    if (selectedCardIds.length === 1) {
      const id = selectedCardIds[0];
      switch (id) {
        case 3: return 'ChatGPT (Utama)';
        case 4: return 'ChatGPT (Singkat)';
        case 5: return 'ChatGPT (Analisis)';
        case 12: return 'ChatGPT (Isu Lapangan)';
        case 13: return 'ChatGPT (Rekomendasi)';
        case 14: return 'Jawaban (Peran Kemenkopolkam)';
        case 15: return 'ChatGPT (Agenda Lapangan)';
        case 20: return 'ChatGPT (Berita Terkini)';
        case 8: return 'Gemini (Utama)';
        case 9: return 'Gemini (Singkat)';
        case 10: return 'Gemini (Analisis)';
        case 16: return 'Gemini (Isu Kerentanan)';
        case 17: return 'Gemini (Rekomendasi)';
        case 18: return 'Gemini (Fungsi Pengawalan)';
        case 19: return 'Gemini (Agenda Pemantauan)';
        case 21: return 'Gemini (Berita Faktual)';
        default: return `Kartu #${id}`;
      }
    }
    return `${selectedCardIds.length} Kartu Tergabung`;
  };

  const toggleCardSelection = (cardId: SelectableCardId) => {
    stopAllAudio();
    setSelectedCardIds(prev => {
      return prev.includes(cardId)
        ? prev.filter(id => id !== cardId)
        : [...prev, cardId];
    });
  };

  useEffect(() => {
    stopAllAudio();
    lastTranslatedSourceRef.current = '';
    setTranslatedEnglishText('');
    if (data.selected_answer || chatgpt?.main_answer || gemini?.main_answer) {
      if (data.selected_answer && data.selected_answer.trim()) {
        const matched: SelectableCardId[] = [];
        const candidateCards: SelectableCardId[] = [3, 8, 4, 9, 5, 10, 14, 18, 15, 19, 12, 16, 13, 17, 20, 21];
        const cleanSaved = data.selected_answer.toLowerCase().replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
        for (const cid of candidateCards) {
          const content = getCardContent(cid).trim();
          const cleanIndo = content.toLowerCase().replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
          const englishContent = getCardEnglishContent(cid).trim();
          const cleanEn = englishContent.toLowerCase().replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
          if (cleanIndo.length > 15 && (cleanSaved.includes(cleanIndo.slice(0, 30)) || cleanIndo.includes(cleanSaved.slice(0, 30)))) {
            matched.push(cid);
          } else if (cleanEn.length > 15 && (cleanSaved.includes(cleanEn.slice(0, 30)) || cleanEn.includes(cleanSaved.slice(0, 30)))) {
            matched.push(cid);
          }
        }
        if (matched.length > 0) {
          setSelectedCardIds(matched);
          return;
        }
      }
      if (chatgpt?.main_answer && chatgpt.main_answer.trim()) {
        setSelectedCardIds([3]);
      } else if (gemini?.main_answer && gemini.main_answer.trim()) {
        setSelectedCardIds([8]);
      } else {
        setSelectedCardIds([3]);
      }
    }
  }, [data.canonical_question?.id, data.selected_answer]);

  const handleTogglePlayPause = () => {
    const textToPlay = currentCard11Text;
    if (!textToPlay) return;

    if (isPlayingAudio) {
      // Jeda (Pause)
      if (audioPlayerRef.current) {
        try {
          audioPlayerRef.current.pause();
        } catch {}
      } else if (window.speechSynthesis && window.speechSynthesis.speaking) {
        window.speechSynthesis.pause();
      }
      setIsPlayingAudio(false);
      setIsAudioPaused(true);
    } else if (isAudioPaused) {
      // Lanjutkan (Resume)
      if (audioPlayerRef.current && currentAudioTextRef.current === textToPlay.trim()) {
        try {
          audioPlayerRef.current.playbackRate = playbackSpeed;
          audioPlayerRef.current.play();
          setIsPlayingAudio(true);
          setIsAudioPaused(false);
          return;
        } catch {}
      }
      if (window.speechSynthesis && window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
        setIsPlayingAudio(true);
        setIsAudioPaused(false);
        return;
      }
      playNeuralSpeech(textToPlay);
    } else {
      // Putar baru
      playNeuralSpeech(textToPlay);
    }
  };

  const handleStopAudio = () => {
    stopAllAudio();
  };

  const getSelectionNumber = (cardId: SelectableCardId): number | null => {
    const idx = selectedCardIds.indexOf(cardId);
    return idx !== -1 ? idx + 1 : null;
  };

  const handleStartEdit = (cardId: SelectableCardId) => {
    setEditingCardId(cardId);
    setEditingText(getCardContent(cardId));
  };

  const handleCancelEdit = () => {
    setEditingCardId(null);
    setEditingText('');
  };

  const handleSaveEdit = (cardId: SelectableCardId) => {
    const updatedText = editingText.trim();
    const updatedData: DiplomaticResponseSet = {
      ...data,
      canonical_question: { ...data.canonical_question },
      chatgpt: { ...data.chatgpt },
      gemini: { ...data.gemini },
      english_translations: { ...data.english_translations }
    };

    switch (cardId) {
      case 1:
      case 6:
        updatedData.canonical_question.original_text = updatedText;
        break;
      case 2:
      case 7:
        updatedData.canonical_translation_id = updatedText;
        break;
      case 3:
        updatedData.chatgpt.main_answer = updatedText;
        delete updatedData.english_translations.card_3;
        delete cardTranslationCacheRef.current.card_3;
        break;
      case 4:
        updatedData.chatgpt.concise_answer = updatedText;
        delete updatedData.english_translations.card_4;
        delete cardTranslationCacheRef.current.card_4;
        break;
      case 5:
        updatedData.chatgpt.brief_analysis = updatedText;
        delete updatedData.english_translations.card_5;
        delete cardTranslationCacheRef.current.card_5;
        break;
      case 8:
        updatedData.gemini.main_answer = updatedText;
        delete updatedData.english_translations.card_8;
        delete cardTranslationCacheRef.current.card_8;
        break;
      case 9:
        updatedData.gemini.concise_answer = updatedText;
        delete updatedData.english_translations.card_9;
        delete cardTranslationCacheRef.current.card_9;
        break;
      case 10:
        updatedData.gemini.brief_analysis = updatedText;
        delete updatedData.english_translations.card_10;
        delete cardTranslationCacheRef.current.card_10;
        break;
      case 12:
        updatedData.chatgpt.monitoring_issues = updatedText;
        delete updatedData.english_translations.card_12;
        delete cardTranslationCacheRef.current.card_12;
        break;
      case 13:
        updatedData.chatgpt.resolution_recommendations = updatedText;
        delete updatedData.english_translations.card_13;
        delete cardTranslationCacheRef.current.card_13;
        break;
      case 14:
        updatedData.chatgpt.kemenko_role = updatedText;
        delete updatedData.english_translations.card_14;
        delete cardTranslationCacheRef.current.card_14;
        break;
      case 15:
        updatedData.chatgpt.field_monitoring_agenda = updatedText;
        delete updatedData.english_translations.card_15;
        delete cardTranslationCacheRef.current.card_15;
        break;
      case 20:
        updatedData.chatgpt.latest_news = updatedText;
        delete updatedData.english_translations.card_20;
        delete cardTranslationCacheRef.current.card_20;
        break;
      case 16:
        updatedData.gemini.monitoring_issues = updatedText;
        delete updatedData.english_translations.card_16;
        delete cardTranslationCacheRef.current.card_16;
        break;
      case 17:
        updatedData.gemini.resolution_recommendations = updatedText;
        delete updatedData.english_translations.card_17;
        delete cardTranslationCacheRef.current.card_17;
        break;
      case 18:
        updatedData.gemini.kemenko_role = updatedText;
        delete updatedData.english_translations.card_18;
        delete cardTranslationCacheRef.current.card_18;
        break;
      case 19:
        updatedData.gemini.field_monitoring_agenda = updatedText;
        delete updatedData.english_translations.card_19;
        delete cardTranslationCacheRef.current.card_19;
        break;
      case 21:
        updatedData.gemini.latest_news = updatedText;
        delete updatedData.english_translations.card_21;
        delete cardTranslationCacheRef.current.card_21;
        break;
    }

    // Trigger instant background translation of the edited card so its English version stays in sync
    fetch(`${API_BASE_URL}/api/translate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: updatedText.trim(),
        target_lang: 'en',
        source_lang: 'id'
      })
    })
    .then(r => r.json())
    .then(res => {
      if (res && res.translated_text) {
        const tr = res.translated_text.trim();
        cardTranslationCacheRef.current[`card_${cardId}`] = tr;
        if (updatedData.english_translations) {
          updatedData.english_translations[`card_${cardId}`] = tr;
        }
        onNewQuestionReceived?.({ ...updatedData });
      }
    })
    .catch(() => {});

    onNewQuestionReceived?.(updatedData);
    setEditingCardId(null);
    setEditingText('');
  };

  const renderCardHeaderAction = (cardId: SelectableCardId) => {
    if (editingCardId === cardId) {
      return (
        <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
          <button
            type="button"
            onClick={() => handleSaveEdit(cardId)}
            className="main-card-save-btn"
            title="Simpan perubahan teks (Ctrl+Enter)"
          >
            <Check size={11} />
            <span>Selesai</span>
          </button>
          <button
            type="button"
            onClick={handleCancelEdit}
            className="main-card-cancel-btn"
            title="Batalkan edit"
          >
            <X size={11} />
          </button>
        </div>
      );
    }

    return (
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          handleStartEdit(cardId);
        }}
        className="main-card-edit-btn"
        title="Edit teks kotak ini"
      >
        <Pencil size={11} />
        <span>Edit</span>
      </button>
    );
  };

  // Continuous Live Voice Session (Real-Time Speech-to-Text)
  const startLiveListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Browser Anda belum mendukung Web Speech Recognition. Disarankan menggunakan Google Chrome atau Microsoft Edge.");
      return;
    }

    try {
      if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch {}
        recognitionRef.current = null;
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      // Default bahasa Indonesia agar menangkap ucapan secara real-time dan akurat
      recognition.lang = liveLanguage === 'auto' ? 'id-ID' : liveLanguage;

      recognition.onresult = (event: any) => {
        let interimTranscript = '';
        let currentSessionFinal = '';

        for (let i = 0; i < event.results.length; ++i) {
          const chunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            currentSessionFinal += chunk + ' ';
          } else {
            interimTranscript += chunk;
          }
        }

        // Unlimited / Infinity continuous transcript:
        // Always concatenate the accumulated history from previous auto-restarts + current session's final chunks + interim chunk
        const combined = (accumulatedTranscriptRef.current + ' ' + currentSessionFinal + ' ' + interimTranscript).replace(/\s+/g, ' ').trim();

        if (combined) {
          setLiveStreamingText(combined);
          latestSpokenRef.current = combined;
        }
      };

      recognition.onend = () => {
        // Continuous transcription: reconnect if user hasn't explicitly clicked off
        if (isUnifiedLiveActiveRef.current) {
          if (latestSpokenRef.current) {
            accumulatedTranscriptRef.current = latestSpokenRef.current.trim() + ' ';
          }
          try {
            recognition.start();
          } catch {}
        }
      };

      recognition.onerror = (e: any) => {
        console.warn("Speech recognition event:", e.error);
        if (e.error === 'not-allowed') {
          alert("Akses mikrofon diblokir browser. Harap klik ikon gembok/setelan di sebelah URL browser dan pilih 'Izinkan Mikrofon'.");
          stopLiveListening();
        } else if (e.error === 'audio-capture') {
          alert("Mikrofon tidak terdeteksi atau sedang dikunci aplikasi lain. Harap periksa mikrofon Anda.");
          stopLiveListening();
        } else if (e.error === 'network') {
          console.warn("Koneksi layanan speech recognition terganggu.");
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Speech recognition startup error:", err);
    }
  };

  const stopLiveListening = () => {
    if (silenceTimeoutRef.current) {
      clearTimeout(silenceTimeoutRef.current);
      silenceTimeoutRef.current = null;
    }
    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
    if (mediaStreamRef.current) {
      try {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
      } catch {}
      mediaStreamRef.current = null;
    }
    setIsUnifiedLiveActive(false);
  };

  const toggleUnifiedLive = async () => {
    // If mic is currently active, clicking again STOPS transcription and SUBMITS the captured speech!
    if (isUnifiedLiveActive) {
      const textToSubmit = (latestSpokenRef.current || liveStreamingText).trim();
      stopAllAudio();
      stopLiveListening();

      if (textToSubmit) {
        submitLiveSpeech(textToSubmit);
      }
      return;
    }

    // Starting mic ("nyalain mic"):
    const executeStartMic = () => {
      resetAllSessionData();
      setIsUnifiedLiveActive(true);
      setLiveStreamingText('');
      latestSpokenRef.current = '';
      accumulatedTranscriptRef.current = '';

      startLiveListening();
    };

    if (hasExistingData) {
      setPendingAction(() => executeStartMic);
      setShowConfirmModal(true);
    } else {
      executeStartMic();
    }
  };

  const submitLiveSpeech = async (textToSubmit: string) => {
    if (!textToSubmit || !textToSubmit.trim()) return;

    setIsProcessingLive(true);
    setLiveStreamingText('');
    latestSpokenRef.current = '';
    accumulatedTranscriptRef.current = '';

    if (recognitionRef.current) {
      try { recognitionRef.current.abort(); } catch {}
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question_text: textToSubmit.trim(),
          detected_language: liveLanguage === 'auto' ? undefined : (liveLanguage.startsWith('en') ? 'en' : (liveLanguage.startsWith('id') ? 'id' : liveLanguage)),
          knowledge_context: attachedFile?.text,
          attachment_name: attachedFile?.name
        })
      });

      if (res.ok) {
        const updatedData: DiplomaticResponseSet = await res.json();
        if (onNewQuestionReceived) {
          onNewQuestionReceived(updatedData);
        }
        setSelectedCardIds([3]);
        setLiveStreamingText('');
        latestSpokenRef.current = '';
        accumulatedTranscriptRef.current = '';
        // Auto reload listed saved files
        onRefreshSavedFiles?.();
      } else {
        const errText = await res.text();
        console.error('API Error:', res.status, errText);
      }
    } catch (err) {
      console.error('Error submitting live speech:', err);
    } finally {
      setIsProcessingLive(false);
      setLiveStreamingText('');
    }
  };

  const changeLiveLanguage = (lang: string) => {
    setLiveLanguage(lang);
    if (isUnifiedLiveActive) {
      stopLiveListening();
      setTimeout(() => {
        setIsUnifiedLiveActive(true);
        startLiveListening();
      }, 150);
    }
  };

  return (
    <div className="cards-layout">
      {/* Top Bar: Live Speech & Real-Time Query Controls Combined in One Single Card */}
      <div className="unified-live-container">
        <VoicePlatformBar
          status={realtime.status}
          provider={realtime.provider}
          mode={realtime.mode}
          isMuted={realtime.isMuted}
          isRecording={realtime.isRecording || isUnifiedLiveActive}
          telemetry={realtime.telemetry}
          errorMessage={realtime.errorMessage}
          onToggleRecording={() => {
            toggleUnifiedLive();
          }}
          onInterrupt={() => {
            realtime.interruptPlayback();
            stopAllAudio();
          }}
          onToggleMute={() => realtime.setIsMuted(!realtime.isMuted)}
          onSwitchProvider={(p) => realtime.switchProvider(p)}
          onSetMode={(m) => realtime.setMode(m)}
          liveStreamingText={liveStreamingText}
          liveLanguage={liveLanguage}
          onChangeLanguage={changeLiveLanguage}
        >
          {/* Interactive Query Input Bar Grounded with Real-Time Data & Knowledge AI (Inside the Exact Same Card) */}
          <form onSubmit={handleQuerySubmit} className="live-search-form">
            {/* Knowledge Attachment Active Pill */}
            {attachedFile && (
              <div className="knowledge-attachment-pill">
                <FileText size={13} className="text-blue-400 shrink-0" />
                <span className="knowledge-filename" title={attachedFile.name}>
                  {attachedFile.name}
                </span>
                <span className="knowledge-badge">Knowledge Tambahan ({attachedFile.sizeStr})</span>
                <button
                  type="button"
                  onClick={handleRemoveAttachment}
                  className="knowledge-remove-btn"
                  title="Hapus Lampiran Knowledge"
                >
                  <X size={12} />
                </button>
              </div>
            )}

            <div className="live-search-wrapper">
              {/* Paperclip Button for Lampiran / Knowledge Tambahan */}
              <label
                className={`live-attach-btn ${attachedFile ? 'active' : ''}`}
                title={attachedFile ? `Knowledge tambahan aktif: ${attachedFile.name} (hanya digunakan jika relate). Klik untuk ganti berkas.` : "Lampirkan Dokumen sebagai Knowledge Tambahan (PDF, Word DOCX, TXT, CSV, MD)"}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileAttach}
                  accept=".pdf,.docx,.doc,.txt,.csv,.json,.md"
                  style={{ display: 'none' }}
                  disabled={isProcessingLive || isExtractingDoc}
                />
                {isExtractingDoc ? (
                  <Loader2 size={16} className="animate-spin text-blue-400" />
                ) : (
                  <Paperclip size={16} />
                )}
              </label>

              <input
                type="text"
                className="live-search-input"
                value={typedQuestion}
                onChange={(e) => setTypedQuestion(e.target.value)}
                placeholder=""
                disabled={isProcessingLive}
              />
              <button
                type="submit"
                className="live-search-btn"
                disabled={!typedQuestion.trim() || isProcessingLive || isExtractingDoc}
                title="Kirim Pertanyaan"
                aria-label="Kirim Pertanyaan"
              >
                {isProcessingLive ? (
                  <span className="live-dot pulse" />
                ) : (
                  <Send size={15} />
                )}
              </button>
            </div>
          </form>
        </VoicePlatformBar>

        {/* Knowledge Applied Status Banner - Hanya muncul jika relate */}
        {Boolean(data.knowledge_applied && data.attachment_name) && (
          <div className="knowledge-applied-banner">
            <div className="flex items-center gap-2">
              <BookOpen size={14} className="text-blue-400 shrink-0" />
              <span>
                <strong>Knowledge Tambahan Terkait:</strong> Jawaban diperkaya dari dokumen lampiran <u>{data.attachment_name}</u> (relevan dengan topik ini)
              </span>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-blue-600/30 text-blue-300 border border-blue-500/30">
              Relate / Relevan
            </span>
          </div>
        )}

        {/* Real-Time Grounding Sources List - Only shown when real-time sources exist for current query */}
        {Boolean(canonical_question?.original_text && data.live_sources && data.live_sources.length > 0) && (
          <div className="grounding-sources-container my-1">
            <div className="flex items-center justify-between py-1 px-1">
              <button
                type="button"
                className="sources-toggle-btn"
                onClick={() => setShowSources(!showSources)}
              >
                <span className="font-semibold text-white">
                  📡 {data.live_sources?.length || 0} Data Berita & Dokumen Terkini Terpantau
                </span>
                <span className="text-zinc-400 text-[11px] ml-1">{showSources ? '▲ Tutup' : '▼ Lihat Sumber'}</span>
              </button>
            </div>

            {showSources && (
              <div className="grounding-sources-list">
                <div className="sources-title">Sumber Berita & Media Resmi yang Ditelusuri AI:</div>
                {(data.live_sources || []).map((src, i) => (
                  <a
                    key={i}
                    href={`https://www.google.com/search?q=${encodeURIComponent(src)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="source-item source-item-clickable"
                    title={`Buka verifikasi berita: ${src}`}
                  >
                    • {src} <span className="source-external-arrow">↗</span>
                  </a>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Mode B: Dual Intelligence Secondary Verification Banner */}
        {realtime.mode === 'dual_intelligence' && realtime.dualAnalysis?.secondary_analysis && (
          <div className="dual-intelligence-secondary-card p-3 my-2 rounded-lg bg-zinc-900/90 border border-indigo-500/30 text-xs text-zinc-200">
            <div className="flex items-center gap-2 mb-1 text-indigo-400 font-semibold tracking-wide">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
              <span>PERSPEKTIF SEKUNDER: {realtime.dualAnalysis.perspective?.toUpperCase() || 'ANALISIS YURIDIS / OPERASIONAL'}</span>
              <span className="text-[10px] text-zinc-400 font-normal">({realtime.dualAnalysis.secondary_provider === 'gemini_live' ? 'Gemini Engine' : 'ChatGPT Engine'})</span>
            </div>
            <p className="leading-relaxed text-zinc-300">
              {realtime.dualAnalysis.secondary_analysis}
            </p>
          </div>
        )}
      </div>


      {/* Cards 1 to 10 in two columns — White Cards with Crisp Black Text & Rich Text Markdown */}
      <div className="cards-columns-grid">
        {/* LEFT COLUMN — CHATGPT */}
        <div className="column-cards">
          {/* Card 1 — Pertanyaan Asli */}
          <HubAnimatedCard
            id="card-1"
            title="Pertanyaan Asli"
            isSelectable
            isSelected={selectedCardIds.includes(1)}
            selectionNumber={getSelectionNumber(1)}
            onClick={() => toggleCardSelection(1)}
            headerAction={renderCardHeaderAction(1)}
            badge={
              canonical_question?.detected_language_name ? (
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: '#EFF6FF',
                    color: '#1D4ED8',
                    border: '1px solid #BFDBFE',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title={`Bahasa Terdeteksi: ${canonical_question.detected_language_name}`}
                >
                  {canonical_question.detected_language_name}
                </span>
              ) : null
            }
          >
            {editingCardId === 1 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(1);
                    }
                  }}
                  className="main-card-textarea"
                  rows={3}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : (
              <div className="min-h-[50px] flex items-center">
                {liveStreamingText ? (
                  <div style={{ color: '#2563EB', fontStyle: 'italic', fontWeight: 500 }}>
                    "{liveStreamingText}"
                  </div>
                ) : canonical_question.original_text ? (
                  <div className="font-semibold text-zinc-900">
                    {canonical_question.original_text}
                  </div>
                ) : null}
              </div>
            )}
          </HubAnimatedCard>

          {/* Card 2 — Terjemahan Bahasa Indonesia */}
          <HubAnimatedCard
            id="card-2"
            title="Terjemahan Bahasa Indonesia"
            isSelectable
            isSelected={selectedCardIds.includes(2)}
            selectionNumber={getSelectionNumber(2)}
            onClick={() => toggleCardSelection(2)}
            headerAction={renderCardHeaderAction(2)}
          >
            {editingCardId === 2 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(2);
                    }
                  }}
                  className="main-card-textarea"
                  rows={3}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : (
              <div className="min-h-[50px] flex items-center">
                {isProcessingLive ? (
                  <div className="flex items-center gap-2 min-h-[50px]">
                    <span className="live-dot pulse" />
                  </div>
                ) : isUnifiedLiveActive && liveStreamingText ? (
                  <div className="flex items-center gap-2 min-h-[50px]">
                    <span className="live-dot pulse" />
                  </div>
                ) : canonical_translation_id ? (
                  <div className="text-zinc-800 font-medium">
                    {canonical_translation_id}
                  </div>
                ) : null}
              </div>
            )}
          </HubAnimatedCard>

          {/* Card 3 — Jawaban Utama */}
          <HubAnimatedCard
            id="card-3"
            title="Jawaban Utama"
            isSelectable
            isSelected={selectedCardIds.includes(3)}
            selectionNumber={getSelectionNumber(3)}
            onClick={() => toggleCardSelection(3)}
            headerAction={renderCardHeaderAction(3)}
          >
            {editingCardId === 3 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(3);
                    }
                  }}
                  className="main-card-textarea"
                  rows={6}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[90px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : isUnifiedLiveActive && liveStreamingText ? (
              <div className="min-h-[90px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : chatgpt.main_answer ? (
              <div className="prose-rich-text min-h-[90px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{chatgpt.main_answer}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[90px]" />
            )}
          </HubAnimatedCard>

          {/* Card 4 — Jawaban Singkat */}
          <HubAnimatedCard
            id="card-4"
            title="Jawaban Singkat"
            isSelectable
            isSelected={selectedCardIds.includes(4)}
            selectionNumber={getSelectionNumber(4)}
            onClick={() => toggleCardSelection(4)}
            headerAction={renderCardHeaderAction(4)}
          >
            {editingCardId === 4 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(4);
                    }
                  }}
                  className="main-card-textarea"
                  rows={4}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[55px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : chatgpt.concise_answer ? (
              <div className="prose-rich-text min-h-[55px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{chatgpt.concise_answer}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[55px]" />
            )}
          </HubAnimatedCard>

          {/* Card 5 — Analisis */}
          <HubAnimatedCard
            id="card-5"
            title="Analisis"
            isSelectable
            isSelected={selectedCardIds.includes(5)}
            selectionNumber={getSelectionNumber(5)}
            onClick={() => toggleCardSelection(5)}
            headerAction={renderCardHeaderAction(5)}
          >
            {editingCardId === 5 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(5);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : chatgpt.brief_analysis ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{chatgpt.brief_analysis}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 12 — MASALAH DAN HASIL PEMANTAUAN (ChatGPT) */}
          <HubAnimatedCard
            id="card-12"
            title="Masalah dan Hasil Pemantauan"
            isSelectable
            isSelected={selectedCardIds.includes(12)}
            selectionNumber={getSelectionNumber(12)}
            onClick={() => toggleCardSelection(12)}
            headerAction={renderCardHeaderAction(12)}
          >
            {editingCardId === 12 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(12);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : chatgpt.monitoring_issues ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{chatgpt.monitoring_issues}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 13 — REKOMENDASI PENYELESAIAN (ChatGPT) */}
          <HubAnimatedCard
            id="card-13"
            title="Rekomendasi Penyelesaian"
            isSelectable
            isSelected={selectedCardIds.includes(13)}
            selectionNumber={getSelectionNumber(13)}
            onClick={() => toggleCardSelection(13)}
            headerAction={renderCardHeaderAction(13)}
          >
            {editingCardId === 13 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(13);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : chatgpt.resolution_recommendations ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{chatgpt.resolution_recommendations}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 14 — PERAN KEMENKOPOLKAM (ChatGPT) */}
          <HubAnimatedCard
            id="card-14"
            title="Peran Kemenkopolkam"
            isSelectable
            isSelected={selectedCardIds.includes(14)}
            selectionNumber={getSelectionNumber(14)}
            onClick={() => toggleCardSelection(14)}
            headerAction={renderCardHeaderAction(14)}
          >
            {editingCardId === 14 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(14);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : chatgpt.kemenko_role ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{chatgpt.kemenko_role}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 15 — USULAN AGENDA PEMANTAUAN LAPANGAN (ChatGPT) */}
          <HubAnimatedCard
            id="card-15"
            title="Usulan Agenda Pemantauan Lapangan"
            isSelectable
            isSelected={selectedCardIds.includes(15)}
            selectionNumber={getSelectionNumber(15)}
            onClick={() => toggleCardSelection(15)}
            headerAction={renderCardHeaderAction(15)}
          >
            {editingCardId === 15 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(15);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : chatgpt.field_monitoring_agenda ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{chatgpt.field_monitoring_agenda}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 20 — BERITA TERBARU (ChatGPT) */}
          <HubAnimatedCard
            id="card-20"
            title="Berita Terbaru"
            isSelectable
            isSelected={selectedCardIds.includes(20)}
            selectionNumber={getSelectionNumber(20)}
            onClick={() => toggleCardSelection(20)}
            headerAction={renderCardHeaderAction(20)}
          >
            {editingCardId === 20 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(20);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : getCardContent(20) ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{getCardContent(20)}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>
        </div>

        {/* RIGHT COLUMN — GEMINI */}
        <div className="column-cards">
          {/* Card 6 — Pertanyaan Asli */}
          <HubAnimatedCard
            id="card-6"
            title="Pertanyaan Asli"
            isSelectable
            isSelected={selectedCardIds.includes(6)}
            selectionNumber={getSelectionNumber(6)}
            onClick={() => toggleCardSelection(6)}
            headerAction={renderCardHeaderAction(6)}
            badge={
              canonical_question?.detected_language_name ? (
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: '#EFF6FF',
                    color: '#1D4ED8',
                    border: '1px solid #BFDBFE',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}
                  title={`Bahasa Terdeteksi: ${canonical_question.detected_language_name}`}
                >
                  {canonical_question.detected_language_name}
                </span>
              ) : null
            }
          >
            {editingCardId === 6 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(6);
                    }
                  }}
                  className="main-card-textarea"
                  rows={3}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : (
              <div className="min-h-[50px] flex items-center">
                {liveStreamingText ? (
                  <div style={{ color: '#2563EB', fontStyle: 'italic', fontWeight: 500 }}>
                    "{liveStreamingText}"
                  </div>
                ) : canonical_question.original_text ? (
                  <div className="font-semibold text-zinc-900">
                    {canonical_question.original_text}
                  </div>
                ) : null}
              </div>
            )}
          </HubAnimatedCard>

          {/* Card 7 — Terjemahan Bahasa Indonesia */}
          <HubAnimatedCard
            id="card-7"
            title="Terjemahan Bahasa Indonesia"
            isSelectable
            isSelected={selectedCardIds.includes(7)}
            selectionNumber={getSelectionNumber(7)}
            onClick={() => toggleCardSelection(7)}
            headerAction={renderCardHeaderAction(7)}
          >
            {editingCardId === 7 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(7);
                    }
                  }}
                  className="main-card-textarea"
                  rows={3}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : (
              <div className="min-h-[50px] flex items-center">
                {isProcessingLive ? (
                  <div className="flex items-center gap-2 min-h-[50px]">
                    <span className="live-dot pulse" />
                  </div>
                ) : isUnifiedLiveActive && liveStreamingText ? (
                  <div className="flex items-center gap-2 min-h-[50px]">
                    <span className="live-dot pulse" />
                  </div>
                ) : canonical_translation_id ? (
                  <div className="text-zinc-800 font-medium">
                    {canonical_translation_id}
                  </div>
                ) : null}
              </div>
            )}
          </HubAnimatedCard>

          {/* Card 8 — Jawaban Utama */}
          <HubAnimatedCard
            id="card-8"
            title="Jawaban Utama"
            isSelectable
            isSelected={selectedCardIds.includes(8)}
            selectionNumber={getSelectionNumber(8)}
            onClick={() => toggleCardSelection(8)}
            headerAction={renderCardHeaderAction(8)}
          >
            {editingCardId === 8 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(8);
                    }
                  }}
                  className="main-card-textarea"
                  rows={6}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[90px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : isUnifiedLiveActive && liveStreamingText ? (
              <div className="min-h-[90px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : gemini.main_answer ? (
              <div className="prose-rich-text min-h-[90px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{gemini.main_answer}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[90px]" />
            )}
          </HubAnimatedCard>

          {/* Card 9 — Jawaban Singkat */}
          <HubAnimatedCard
            id="card-9"
            title="Jawaban Singkat"
            isSelectable
            isSelected={selectedCardIds.includes(9)}
            selectionNumber={getSelectionNumber(9)}
            onClick={() => toggleCardSelection(9)}
            headerAction={renderCardHeaderAction(9)}
          >
            {editingCardId === 9 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(9);
                    }
                  }}
                  className="main-card-textarea"
                  rows={4}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[55px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : gemini.concise_answer ? (
              <div className="prose-rich-text min-h-[55px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{gemini.concise_answer}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[55px]" />
            )}
          </HubAnimatedCard>

          {/* Card 10 — Analisis */}
          <HubAnimatedCard
            id="card-10"
            title="Analisis"
            isSelectable
            isSelected={selectedCardIds.includes(10)}
            selectionNumber={getSelectionNumber(10)}
            onClick={() => toggleCardSelection(10)}
            headerAction={renderCardHeaderAction(10)}
          >
            {editingCardId === 10 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(10);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : gemini.brief_analysis ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{gemini.brief_analysis}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 16 — MASALAH DAN HASIL PEMANTAUAN (Gemini) */}
          <HubAnimatedCard
            id="card-16"
            title="Masalah dan Hasil Pemantauan"
            isSelectable
            isSelected={selectedCardIds.includes(16)}
            selectionNumber={getSelectionNumber(16)}
            onClick={() => toggleCardSelection(16)}
            headerAction={renderCardHeaderAction(16)}
          >
            {editingCardId === 16 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(16);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : gemini.monitoring_issues ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{gemini.monitoring_issues}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 17 — REKOMENDASI PENYELESAIAN (Gemini) */}
          <HubAnimatedCard
            id="card-17"
            title="Rekomendasi Penyelesaian"
            isSelectable
            isSelected={selectedCardIds.includes(17)}
            selectionNumber={getSelectionNumber(17)}
            onClick={() => toggleCardSelection(17)}
            headerAction={renderCardHeaderAction(17)}
          >
            {editingCardId === 17 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(17);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : gemini.resolution_recommendations ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{gemini.resolution_recommendations}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 18 — PERAN KEMENKOPOLKAM (Gemini) */}
          <HubAnimatedCard
            id="card-18"
            title="Peran Kemenkopolkam"
            isSelectable
            isSelected={selectedCardIds.includes(18)}
            selectionNumber={getSelectionNumber(18)}
            onClick={() => toggleCardSelection(18)}
            headerAction={renderCardHeaderAction(18)}
          >
            {editingCardId === 18 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(18);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : gemini.kemenko_role ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{gemini.kemenko_role}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 19 — USULAN AGENDA PEMANTAUAN LAPANGAN (Gemini) */}
          <HubAnimatedCard
            id="card-19"
            title="Usulan Agenda Pemantauan Lapangan"
            isSelectable
            isSelected={selectedCardIds.includes(19)}
            selectionNumber={getSelectionNumber(19)}
            onClick={() => toggleCardSelection(19)}
            headerAction={renderCardHeaderAction(19)}
          >
            {editingCardId === 19 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(19);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : gemini.field_monitoring_agenda ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{gemini.field_monitoring_agenda}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>

          {/* Card 21 — BERITA TERBARU (Gemini) */}
          <HubAnimatedCard
            id="card-21"
            title="Berita Terbaru"
            isSelectable
            isSelected={selectedCardIds.includes(21)}
            selectionNumber={getSelectionNumber(21)}
            onClick={() => toggleCardSelection(21)}
            headerAction={renderCardHeaderAction(21)}
          >
            {editingCardId === 21 ? (
              <div onClick={(e) => e.stopPropagation()} className="pt-0.5">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                      handleSaveEdit(21);
                    }
                  }}
                  className="main-card-textarea"
                  rows={5}
                  placeholder=""
                  autoFocus
                />
              </div>
            ) : isProcessingLive ? (
              <div className="min-h-[70px] flex items-center gap-2">
                <span className="live-dot pulse" />
              </div>
            ) : getCardContent(21) ? (
              <div className="prose-rich-text min-h-[70px]">
                <ReactMarkdown rehypePlugins={[rehypeRaw]}>{getCardContent(21)}</ReactMarkdown>
              </div>
            ) : (
              <div className="min-h-[70px]" />
            )}
          </HubAnimatedCard>
        </div>
      </div>

      {/* BOTTOM — SELECTED RESPONSE (CARD 11) */}
      <HubAnimatedCard
        id="card-11"
        title={selectedAnswerLang === 'en' ? "Jawaban Terpilih (English)" : "Jawaban Terpilih"}
        className="w-full mt-1"
        circleSize={500}
        badge={
          <div className="flex items-center gap-2">
            {/* Language toggle: EN (default) vs ID */}
            <div className="flex items-center gap-1 bg-zinc-900/90 border border-zinc-700/80 rounded-md p-0.5">
              <button
                type="button"
                onClick={() => {
                  if (selectedAnswerLang !== 'en') {
                    stopAllAudio();
                    setSelectedAnswerLang('en');
                  }
                }}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                  selectedAnswerLang === 'en'
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
                title="Tampilkan & Dengarkan Terjemahan Bahasa Inggris"
              >
                EN (Inggris)
              </button>
              <button
                type="button"
                onClick={() => {
                  if (selectedAnswerLang !== 'id') {
                    stopAllAudio();
                    setSelectedAnswerLang('id');
                  }
                }}
                className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-all ${
                  selectedAnswerLang === 'id'
                    ? 'bg-zinc-700 text-white shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
                title="Tampilkan Teks Asli Bahasa Indonesia"
              >
                ID (Indonesia)
              </button>
            </div>

            {/* Sumber Jawaban Pill */}
            <span
              className="text-[10px] font-mono font-medium text-blue-700 bg-blue-50 border border-blue-200 px-2 py-0.5 rounded shadow-xs"
              title="Sumber data jawaban Card 11"
            >
              Sumber: {getSelectedSourceLabel()}
            </span>

            {selectedCardIds.length > 0 ? (
              <button
                type="button"
                onClick={() => {
                  stopAllAudio();
                  setSelectedCardIds([3]);
                }}
                className="saved-chosen-reset-btn"
                title="Kembalikan pilihan ke Jawaban Utama default"
              >
                Reset Pilihan
              </button>
            ) : null}
          </div>
        }
        headerAction={
          currentCard11Text ? (
            <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
              {/* Play / Pause (Symbol only) */}
              <button
                type="button"
                onClick={handleTogglePlayPause}
                aria-label={isAudioLoading ? "Memuat Suara..." : isPlayingAudio ? "Pause" : "Play"}
                className={`audio-symbol-btn ${isPlayingAudio || isAudioLoading ? 'active' : ''}`}
                title={isAudioLoading ? "Memuat Suara..." : isPlayingAudio ? "Pause" : "Play"}
              >
                {isAudioLoading ? (
                  <Loader2 size={13} className="animate-spin text-white" />
                ) : isPlayingAudio ? (
                  <Pause size={13} fill="currentColor" />
                ) : (
                  <Play size={13} fill="currentColor" className="ml-0.5" />
                )}
              </button>

              {/* Stop (Symbol only) */}
              <button
                type="button"
                onClick={handleStopAudio}
                aria-label="Stop"
                className="audio-symbol-btn audio-symbol-btn-stop"
                title="Stop"
                disabled={!isPlayingAudio && !isAudioPaused && audioCurrentTime === 0}
              >
                <Square size={12} fill="currentColor" />
              </button>

              {/* Garis Waktu Play (Timeline) */}
              <div className="flex items-center gap-2 bg-zinc-900/90 border border-zinc-700/80 rounded-md px-2 py-1 shadow-sm">
                <input
                  type="range"
                  min={0}
                  max={audioDuration > 0 ? audioDuration : 100}
                  step={0.1}
                  value={audioDuration > 0 ? audioCurrentTime : 0}
                  onChange={(e) => handleSeek(Number(e.target.value))}
                  className="audio-timeline-slider"
                  disabled={audioDuration === 0}
                />
                <span className="text-[10px] font-mono font-medium text-zinc-400 whitespace-nowrap min-w-[56px] text-right">
                  {formatTime(audioCurrentTime)} / {formatTime(audioDuration)}
                </span>
              </div>

              {/* Kecepatan (Speed Symbol only) */}
              <div className="flex items-center gap-1 bg-zinc-900/90 border border-zinc-700/80 rounded-md px-1.5 py-1 shadow-sm">
                <Gauge size={13} className="text-zinc-400 shrink-0" />
                <select
                  value={playbackSpeed}
                  onChange={(e) => handleSpeedChange(Number(e.target.value))}
                  className="bg-transparent text-xs font-bold text-zinc-200 outline-none cursor-pointer pr-0.5"
                >
                  <option value={0.5} className="bg-zinc-900 text-white">0.5x</option>
                  <option value={0.75} className="bg-zinc-900 text-white">0.75x</option>
                  <option value={1.0} className="bg-zinc-900 text-white">1.0x</option>
                  <option value={1.25} className="bg-zinc-900 text-white">1.25x</option>
                  <option value={1.5} className="bg-zinc-900 text-white">1.5x</option>
                  <option value={1.75} className="bg-zinc-900 text-white">1.75x</option>
                  <option value={2.0} className="bg-zinc-900 text-white">2.0x</option>
                </select>
              </div>
            </div>
          ) : null
        }
      >
        <div className="min-h-[70px] select-text">
          {(isTranslatingSelected || (selectedAnswerLang === 'en' && (!currentCard11Text || isLikelyIndonesian(currentCard11Text)))) && combinedSelectedText ? (
            <div className="flex items-center gap-2 text-xs text-blue-600 font-medium py-3">
              <Loader2 size={15} className="animate-spin text-blue-600" />
              <span>Menerjemahkan ke Bahasa Inggris...</span>
            </div>
          ) : currentCard11Text ? (
            <div className="prose-rich-text">
              <ReactMarkdown rehypePlugins={[rehypeRaw]}>{currentCard11Text}</ReactMarkdown>
            </div>
          ) : (
            <div className="text-xs text-zinc-600 italic py-3 flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              <span>Belum ada jawaban terpilih. Rekam suara mikrofon atau ajukan pertanyaan untuk menghasilkan analisis dan jawaban terpilih terbaru.</span>
            </div>
          )}
        </div>
      </HubAnimatedCard>

      {/* Confirmation Modal: Apakah anda yakin akan menghapus? */}
      {showConfirmModal && (
        <div className="confirm-modal-overlay">
          <div className="confirm-modal-card">
            <div className="confirm-modal-icon">⚠️</div>
            <h3 className="confirm-modal-title">Apakah anda yakin akan menghapus?</h3>
            <p className="confirm-modal-desc">
              Memulai proses baru akan menghapus seluruh data sebelumnya dan mengosongkan riwayat analisis.
            </p>
            <div className="confirm-modal-actions">
              <button
                type="button"
                className="confirm-btn-no"
                onClick={() => {
                  setShowConfirmModal(false);
                  setPendingAction(null);
                }}
              >
                Tidak
              </button>
              <button
                type="button"
                className="confirm-btn-yes"
                onClick={() => {
                  setShowConfirmModal(false);
                  if (pendingAction) {
                    const actionToRun = pendingAction;
                    setPendingAction(null);
                    actionToRun();
                  }
                }}
              >
                Ya
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
