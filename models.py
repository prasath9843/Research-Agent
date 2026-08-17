from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

# --- LLM Structured Output Models ---

class SubQuestion(BaseModel):
    id: str = Field(description="Unique tag like sq_1, sq_2")
    text: str = Field(description="Sub-question research target")
    category: str = Field(description="Background, Data, Counterarguments, Recent, Expert Consensus")

class QueryPlannerOutput(BaseModel):
    sub_questions: List[SubQuestion]
    summary_intent: str = Field(description="Brief overview of research strategy")

class SearchQuery(BaseModel):
    sub_question_id: str
    query_text: str

class SearchResultItem(BaseModel):
    url: str
    title: str
    snippet: str
    sub_question_id: str

class SourceScore(BaseModel):
    url: str
    relevant: bool
    domain_score: float = Field(default=0.5, description="Domain heuristic score (0.0 to 1.0)")
    reason: str

class AtomicClaim(BaseModel):
    claim: str = Field(description="Factual assertion extracted from the source")
    quote_or_paraphrase: str = Field(description="Verbatim excerpt or close paraphrase supporting the claim")
    sub_question_tag: str = Field(description="Sub-question ID like sq_1")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_url: Optional[str] = ""
    source_title: Optional[str] = ""

class ClaimsExtractionOutput(BaseModel):
    claims: List[AtomicClaim]

class GapAnalysisOutput(BaseModel):
    has_gaps: bool
    under_covered_sub_questions: List[str]
    new_search_queries: List[SearchQuery]
    reasoning: str

class ContradictionItem(BaseModel):
    topic: str
    consensus_summary: str
    conflicting_views: List[str]
    affected_source_ids: List[int]

class ContradictionAnalysisOutput(BaseModel):
    contradictions: List[ContradictionItem]
    has_disagreements: bool

class SynthesizedSection(BaseModel):
    title: str
    content: str = Field(description="Markdown section text using [source_id] citations")
    sub_question_tag: str

class ReportOutput(BaseModel):
    title: str
    executive_summary: str
    sections: List[SynthesizedSection]
    contradictions_section: Optional[str] = None
    conclusion: str

class CitationVerificationResult(BaseModel):
    total_citations: int
    valid_citations: List[int]
    invalid_citations: List[int]
    is_fully_verified: bool
    corrected_markdown: str

class QualityEvaluationResult(BaseModel):
    overall_score: float = Field(ge=0.0, le=10.0, description="Overall quality score out of 10")
    passed: bool = Field(description="True if overall_score >= 9.0")
    specificity_score: float = Field(description="Score for regional/localized specificity out of 10")
    quantitative_score: float = Field(description="Score for quantitative metrics & numbers out of 10")
    citation_score: float = Field(description="Score for citation verification out of 10")
    structure_score: float = Field(description="Score for 15-section structural completeness out of 10")
    feedback_reasons: List[str] = Field(default=[], description="Specific weaknesses identified")
    missing_aspects: List[str] = Field(default=[], description="Topics or metrics to research further if failed")

# --- API & DB Session Models ---

class ResearchRequest(BaseModel):
    query: str
    fast_model: Optional[str] = None
    strong_model: Optional[str] = None
    max_rounds: Optional[int] = None
    max_sources: Optional[int] = None
    search_provider: Optional[str] = None
    user_suggestions: Optional[str] = None
    target_pages: Optional[int] = Field(default=4, description="Target report length in pages (default: 4)")

class UpdateReportRequest(BaseModel):
    markdown_content: str

class SessionLogEntry(BaseModel):
    timestamp: str
    stage: str
    message: str
    level: str = "INFO"

class ResearchStatusResponse(BaseModel):
    session_id: str
    query: str
    status: str  # pending, running, completed, failed
    current_stage: str
    progress_percentage: int
    rounds_completed: int
    total_sources_found: int
    total_claims_extracted: int
    logs: List[SessionLogEntry]
    error: Optional[str] = None
