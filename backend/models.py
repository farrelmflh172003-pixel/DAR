from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class TranscriptWord(BaseModel):
    word: str
    confidence: float = 1.0
    start_time: float = 0.0
    end_time: float = 0.0
    uncertain: bool = False

class CanonicalQuestion(BaseModel):
    id: str
    original_text: str
    detected_language: str = "auto"
    detected_language_name: Optional[str] = "Bahasa Indonesia"
    timestamp: str
    speaker: str = "Delegasi Internasional"
    audio_sample_url: Optional[str] = None
    uncertain_words: List[str] = Field(default_factory=list)
    words: Optional[List[TranscriptWord]] = None

class AIAnswerBundle(BaseModel):
    main_answer: str
    concise_answer: str
    brief_analysis: str
    monitoring_issues: Optional[str] = ""
    resolution_recommendations: Optional[str] = ""
    kemenko_role: Optional[str] = ""
    field_monitoring_agenda: Optional[str] = ""
    latest_news: Optional[str] = ""
    model_version: str

class DiplomaticResponseSet(BaseModel):
    canonical_question: CanonicalQuestion
    canonical_translation_id: str
    chatgpt: AIAnswerBundle
    gemini: AIAnswerBundle
    # Precomputed high-quality English translations for each of the 6 answers
    english_translations: Dict[str, str]
    is_live_grounded: Optional[bool] = True
    live_sources: Optional[List[str]] = Field(default_factory=list)
    latest_update_time: Optional[str] = None
    knowledge_applied: Optional[bool] = False
    attachment_name: Optional[str] = None
    selected_answer: Optional[str] = ""


class ProcessRequest(BaseModel):
    question_text: str
    detected_language: Optional[str] = None
    speaker: Optional[str] = "Delegasi / Penanya"
    knowledge_context: Optional[str] = None
    attachment_name: Optional[str] = None

class SelectAnswerRequest(BaseModel):
    card_id: int  # 3, 4, 5, 8, 9, 10
    source_ai: str  # 'chatgpt' or 'gemini'
    answer_type: str  # 'main', 'concise', 'analysis'
    indonesian_text: str

class EnglishResponse(BaseModel):
    card_id: int
    source_ai: str
    answer_type_label: str
    english_text: str
