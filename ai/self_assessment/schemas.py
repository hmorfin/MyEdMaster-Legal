from pydantic import BaseModel

class LLMCallLog(BaseModel):
    llm: str
    model: str
    prompt: str
    raw_response: str
    parsed_output: dict | None
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class GenerateKBRequest(BaseModel):
    legal_situation: str
    prior_experience: str
    desired_outcome: str
    jurisdiction: str
    debug: bool = False


class GenerateKBResponse(BaseModel):
    legal_domain: str
    branch: str
    jurisdiction: str
    baseline_familiarity: str
    primary_intent: str
    confidence: float
    kb_title: str
    global_highlights: list[str]
    rag_snippets: list[str] = []
    few_shot_examples: dict
    example_text: str
    empty_template: dict | None
    debug_log: list[LLMCallLog] | None = None

class DimensionInput(BaseModel):
    examples: str
    uncertainties: str


class EvaluateRequest(BaseModel):
    chat_id: str
    legal_situation: str
    legal_domain: str
    branch: str
    jurisdiction: str
    baseline_familiarity: str  # low | medium | high
    primary_intent: str
    prior_experience: str
    desired_outcome: str
    kb_content: dict  # passed by Django — AI layer does not fetch from DB
    facts: DimensionInput
    strategies: DimensionInput
    procedures: DimensionInput
    rationales: DimensionInput


class AspectLabel(BaseModel):
    labels: list[str]  # Know-Know | Know-Don't Know | False Knowledge | Omission | Irrelevant Knowledge
    text: str


class DimensionReport(BaseModel):
    dimension: str
    aspects: list[AspectLabel]
    most_critical_gap: str


class PriorityReport(BaseModel):
    top_dimension: str
    top_label_in_top_dimension: str
    dimension_scores: dict[str, float]
    dimension_counts: dict[str, dict[str, int]]


class EvaluateResponse(BaseModel):
    chat_id: str
    student_text: str
    evaluation_report: list[DimensionReport]
    priority: PriorityReport