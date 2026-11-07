export interface TranscriptWord {
  word: string;
  confidence: number;
  start_time: number;
  end_time: number;
  uncertain: boolean;
}

export interface CanonicalQuestion {
  id: string;
  original_text: string;
  detected_language: string;
  detected_language_name?: string;
  timestamp: string;
  speaker: string;
  audio_sample_url?: string;
  uncertain_words: string[];
  words?: TranscriptWord[];
}

export interface AIAnswerBundle {
  main_answer: string;
  concise_answer: string;
  brief_analysis: string;
  monitoring_issues?: string;
  resolution_recommendations?: string;
  kemenko_role?: string;
  field_monitoring_agenda?: string;
  latest_news?: string;
  model_version: string;
}

export interface DiplomaticResponseSet {
  canonical_question: CanonicalQuestion;
  canonical_translation_id: string;
  chatgpt: AIAnswerBundle;
  gemini: AIAnswerBundle;
  english_translations: Record<string, string>;
  is_live_grounded?: boolean;
  live_sources?: string[];
  latest_update_time?: string;
  knowledge_applied?: boolean;
  attachment_name?: string;
  selected_answer?: string;
}


export type SelectableCardId = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21;

export interface SelectedCardState {
  cardId: SelectableCardId;
  sourceAi: 'ChatGPT' | 'Gemini';
  answerType: 'main' | 'concise' | 'analysis' | 'monitoring' | 'recommendation' | 'role' | 'agenda' | 'news';
  answerTypeLabel: string;
  indonesianText: string;
  englishText: string;
}

export interface ScenarioMeta {
  id: string;
  title: string;
  speaker: string;
  timestamp: string;
}

export interface SavedFile {
  id: string;
  title: string;
  timestamp: string;
  speaker: string;
  original_audio_text: string;
  detected_language: string;
  detected_language_name: string;
  translated_indonesian_text: string;
  ai_answers: {
    main_answer: string;
    concise_answer: string;
    brief_analysis: string;
    monitoring_issues?: string;
    resolution_recommendations?: string;
    kemenko_role?: string;
    field_monitoring_agenda?: string;
    latest_news?: string;
    model_version?: string;
  };
  chatgpt_answers?: {
    main_answer: string;
    concise_answer: string;
    brief_analysis: string;
    monitoring_issues?: string;
    resolution_recommendations?: string;
    kemenko_role?: string;
    field_monitoring_agenda?: string;
    latest_news?: string;
    model_version?: string;
  };
  gemini_answers?: {
    main_answer: string;
    concise_answer: string;
    brief_analysis: string;
    monitoring_issues?: string;
    resolution_recommendations?: string;
    kemenko_role?: string;
    field_monitoring_agenda?: string;
    latest_news?: string;
    model_version?: string;
  };
  selected_answer?: string;
  notes?: string;
  knowledge_applied?: boolean;
  attachment_name?: string;
  created_at: string;
  updated_at: string;
}

