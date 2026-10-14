import json
import logging
import time
import os

from fastapi import HTTPException
from openai import OpenAI

from config import settings
from .prompts import (
    CLASSIFIER_PROMPT,
    GENERAL_DOMAIN_INSTRUCTION,
    KB_GENERATOR_PROMPT,
    KB_AUDIT_PROMPT,
    EXAMPLE_GENERATION_SYSTEM_PROMPT,
    EXAMPLE_GENERATION_GUIDE,
    DIMENSION_EVALUATOR_PROMPT,
    SELF_ASSESSMENT_TEXT_TEMPLATE,
)
from .schemas import GenerateKBRequest, GenerateKBResponse, LLMCallLog

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.openai_api_key)


def _safe_parse_json(text: str) -> dict | None:
    if not text:
        return None
    s = text.strip()
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return None


def run_llm1_classifier(
    request: GenerateKBRequest,
    debug_log: list | None = None,
) -> dict:
    prompt = CLASSIFIER_PROMPT.format(
        legal_situation=request.legal_situation,
        jurisdiction=request.jurisdiction,
        prior_experience=request.prior_experience,
        desired_outcome=request.desired_outcome,
    )

    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=300,
        response_format={"type": "json_object"},
    )
    latency_ms = round((time.time() - start) * 1000)
    raw = response.choices[0].message.content or ""
    parsed = _safe_parse_json(raw)

    if debug_log is not None:
        debug_log.append(LLMCallLog(
            llm="LLM1",
            model="gpt-4o-mini",
            prompt=prompt,
            raw_response=raw,
            parsed_output=parsed,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        ))

    if not parsed or not parsed.get("legal_domain"):
        raise HTTPException(status_code=500, detail="LLM1 classifier failed")

    logger.info(f"[LLM1] domain={parsed.get('legal_domain')} latency={latency_ms}ms tokens={response.usage.total_tokens}")
    return parsed


def run_llm2_kb_generator(
    legal_domain: str,
    jurisdiction: str,
    legal_situation: str,
    debug_log: list | None = None,
) -> dict:
    
    if legal_domain == 'general':
        general_domain_instruction = GENERAL_DOMAIN_INSTRUCTION.format(jurisdiction=jurisdiction)
    else:
        general_domain_instruction = ""

    prompt = KB_GENERATOR_PROMPT.format(
        legal_domain=legal_domain,
        jurisdiction=jurisdiction,
        legal_situation=legal_situation,
        general_domain_instruction=general_domain_instruction
    )

    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=3000,
        response_format={"type": "json_object"},
    )
    latency_ms = round((time.time() - start) * 1000)
    raw = response.choices[0].message.content or ""
    parsed = _safe_parse_json(raw)

    if debug_log is not None:
        debug_log.append(LLMCallLog(
            llm="LLM2",
            model="gpt-4o",
            prompt=prompt,
            raw_response=raw,
            parsed_output=parsed,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        ))

    if not parsed:
        raise HTTPException(status_code=500, detail="LLM2 KB generator failed")

    logger.info(f"[LLM2] title={parsed.get('title')} latency={latency_ms}ms tokens={response.usage.total_tokens}")
    return parsed


def run_llm3_audit(
    kb_content: dict,
    debug_log: list | None = None,
) -> dict:

    prompt = KB_AUDIT_PROMPT.format(
        kb_json=json.dumps(kb_content, ensure_ascii=False)
    )

    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=500,
        response_format={"type": "json_object"},
    )
    latency_ms = round((time.time() - start) * 1000)
    raw = response.choices[0].message.content or ""
    parsed = _safe_parse_json(raw) or {
        "status": "ok",
        "issues": [],
        "recommendation": "Audit returned no output: proceeding"
    }

    if debug_log is not None:
        debug_log.append(LLMCallLog(
            llm="LLM3",
            model="gpt-4o-mini",
            prompt=prompt,
            raw_response=raw,
            parsed_output=parsed,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        ))

    logger.info(f"[LLM3] status={parsed.get('status')} latency={latency_ms}ms tokens={response.usage.total_tokens}")
    return parsed


def run_llm4_example_generator(
    legal_domain: str,
    branch: str,
    jurisdiction: str,
    legal_situation: str,
    debug_log: list | None = None,
) -> dict:
    user_payload = json.dumps({
        "user_prompt": f"Self-assessment example for {legal_domain}/{branch} in {jurisdiction}",
        "do_not_use_this_situation": legal_situation,
    }, ensure_ascii=False)

    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": EXAMPLE_GENERATION_SYSTEM_PROMPT},
            {"role": "system", "content": EXAMPLE_GENERATION_GUIDE},
            {"role": "user", "content": user_payload},
        ],
        temperature=0.3,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )
    latency_ms = round((time.time() - start) * 1000)
    raw = response.choices[0].message.content or ""
    parsed = _safe_parse_json(raw) or {
        "example_text": "",
        "empty_template": None,
        "fspr": None
    }

    if debug_log is not None:
        debug_log.append(LLMCallLog(
            llm="LLM4",
            model="gpt-4o-mini",
            prompt=user_payload,
            raw_response=raw,
            parsed_output=parsed,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        ))

    logger.info(f"[LLM4] example_length={len(parsed.get('example_text', ''))} latency={latency_ms}ms tokens={response.usage.total_tokens}")
    return parsed


def run_generate_kb_pipeline(request: GenerateKBRequest) -> GenerateKBResponse:
    debug_log = [] if request.debug else None

    # LLM1: classify domain
    classification = run_llm1_classifier(request, debug_log)
    legal_domain = classification.get("legal_domain", "general")
    branch = classification.get("branch", "general")
    baseline_familiarity = classification.get("baseline_familiarity", "low")
    primary_intent = classification.get("primary_intent", "understand_options")
    confidence = float(classification.get("confidence", 0.5))

    # LLM2: generate KB
    kb_content = run_llm2_kb_generator(
        legal_domain=legal_domain,
        jurisdiction=request.jurisdiction,
        legal_situation=request.legal_situation,
        prior_experience=request.prior_experience,
        desired_outcome=request.desired_outcome,
        debug_log=debug_log,
    )

    # LLM3: audit KB, retry once if needed
    if os.getenv('KB_AUDIT_ENABLED',default=False):
        audit = run_llm3_audit(kb_content, debug_log)
        if audit.get("status") == "regenerate":
            logger.warning(f"[LLM3] Regenerating KB: issues: {audit.get('issues')}")
            kb_content = run_llm2_kb_generator(
                legal_domain=legal_domain,
                branch=branch,
                jurisdiction=request.jurisdiction,
                legal_situation=request.legal_situation,
                prior_experience=request.prior_experience,
                desired_outcome=request.desired_outcome,
                debug_log=debug_log,
            )

    # LLM4: generate example text
    example_output = run_llm4_example_generator(
        legal_domain=legal_domain,
        jurisdiction=request.jurisdiction,
        legal_situation=request.legal_situation,
        debug_log=debug_log,
    )

    return GenerateKBResponse(
        legal_domain=legal_domain,
        jurisdiction=request.jurisdiction,
        baseline_familiarity=baseline_familiarity,
        primary_intent=primary_intent,
        confidence=confidence,
        kb_title=kb_content.get("title", "Legal Knowledge Base"),
        global_highlights=kb_content.get("global_highlights", []),
        rag_snippets=kb_content.get("rag_snippets", []),
        few_shot_examples=kb_content.get("few_shot_examples", {}),
        example_text=example_output.get("example_text", ""),
        empty_template=example_output.get("empty_template"),
        debug_log=debug_log,
    )

def create_self_assessment_text(request) -> str:
    """Flatten all four dimension inputs into a single student_text block."""
    return SELF_ASSESSMENT_TEXT_TEMPLATE.format(
        legal_situation=request.legal_situation,
        facts_examples=request.facts.examples,
        facts_uncertainties=request.facts.uncertainties,
        strategies_examples=request.strategies.examples,
        strategies_uncertainties=request.strategies.uncertainties,
        procedures_examples=request.procedures.examples,
        procedures_uncertainties=request.procedures.uncertainties,
        rationales_examples=request.rationales.examples,
        rationales_uncertainties=request.rationales.uncertainties,
    )


def compute_full_priority_from_report(evaluation_report: list) -> dict:
    """
    Compute priority JSON from dimension reports using legal-specific weights.
    Weights: False Knowledge=0.40, Omission=0.30, Know-Don't Know=0.20,
             Irrelevant Knowledge=0.10, Know-Know=0.00
    """
    WEIGHTS = {
        "False Knowledge": 0.40,
        "Omission": 0.30,
        "Know-Don't Know": 0.20,
        "Irrelevant Knowledge": 0.10,
        "Know-Know": 0.00,
    }

    dimension_scores = {}
    dimension_counts = {}

    for dim_report in evaluation_report:
        dimension = dim_report.get("dimension", "unknown")
        aspects = dim_report.get("aspects", [])

        counts = {}
        score = 0.0
        for aspect in aspects:
            labels = aspect.get("labels", [])
            for label in labels:
                counts[label] = counts.get(label, 0) + 1
                score += WEIGHTS.get(label, 0.0)

        dimension_scores[dimension] = round(score, 4)
        dimension_counts[dimension] = counts

    top_dimension = max(dimension_scores, key=dimension_scores.get) if dimension_scores else "unknown"

    top_label_in_top_dimension = "unknown"
    if top_dimension in dimension_counts:
        top_counts = dimension_counts[top_dimension]
        # Pick highest-weight label that actually appears
        for label in ["False Knowledge", "Omission", "Know-Don't Know", "Irrelevant Knowledge", "Know-Know"]:
            if top_counts.get(label, 0) > 0:
                top_label_in_top_dimension = label
                break

    return {
        "top_dimension": top_dimension,
        "top_label_in_top_dimension": top_label_in_top_dimension,
        "dimension_scores": dimension_scores,
        "dimension_counts": dimension_counts,
    }


def run_dimension_evaluator(
    dimension: str,
    student_examples: str,
    student_uncertainties: str,
    legal_domain: str,
    branch: str,
    jurisdiction: str,
    baseline_familiarity: str,
    primary_intent: str,
    legal_situation: str,
    prior_experience: str,
    desired_outcome: str,
    kb_content: dict,
    debug_log: list | None = None,
) -> dict:
    """Run a single LLM evaluator call for one dimension."""
    few_shot = kb_content.get("few_shot_examples", {})
    dim_key = dimension.lower()
    dim_examples = few_shot.get(dim_key, [])
    examples_text = "\n".join(
        f"Q: {ex.get('input', '')}\nA: {ex.get('analysis', '')}"
        for ex in dim_examples
    )

    # Token-overlap RAG filtering biased toward branch
    rag_snippets = kb_content.get("rag_snippets", [])
    branch_tokens = set(branch.lower().replace("_", " ").split())
    scored = []
    for snippet in rag_snippets:
        snippet_tokens = set(snippet.lower().split())
        overlap = len(branch_tokens & snippet_tokens)
        scored.append((overlap, snippet))
    scored.sort(key=lambda x: x[0], reverse=True)
    filtered_snippets = [s for _, s in scored[:5]]

    global_highlights = kb_content.get("global_highlights", [])

    prompt = DIMENSION_EVALUATOR_PROMPT.format(
        dimension=dimension,
        legal_domain=legal_domain,
        branch=branch,
        jurisdiction=jurisdiction,
        baseline_familiarity=baseline_familiarity,
        primary_intent=primary_intent,
        legal_situation=legal_situation,
        prior_experience=prior_experience,
        desired_outcome=desired_outcome,
        global_highlights="\n".join(f"- {h}" for h in global_highlights),
        rag_snippets="\n".join(f"- {s}" for s in filtered_snippets),
        few_shot_examples=examples_text,
        student_examples=student_examples,
        student_uncertainties=student_uncertainties,
    )

    start = time.time()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1000,
        response_format={"type": "json_object"},
    )
    latency_ms = round((time.time() - start) * 1000)
    raw = response.choices[0].message.content or ""
    parsed = _safe_parse_json(raw) or {
        "dimension": dimension,
        "aspects": [],
        "most_critical_gap": "Unable to evaluate this dimension.",
    }
    # Normalize label → labels for backward compatibility
    if parsed and "aspects" in parsed:
        for aspect in parsed["aspects"]:
            if "label" in aspect and "labels" not in aspect:
                aspect["labels"] = [aspect.pop("label")]

    if debug_log is not None:
        debug_log.append(LLMCallLog(
            llm=f"EVAL_{dimension.upper()}",
            model="gpt-4o-mini",
            prompt=prompt,
            raw_response=raw,
            parsed_output=parsed,
            latency_ms=latency_ms,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        ))

    logger.info(f"[EVAL_{dimension.upper()}] latency={latency_ms}ms tokens={response.usage.total_tokens}")
    return parsed


def run_evaluation_pipeline(request, kb_content: dict, debug_log: list | None = None) -> dict:
    """
    Run all four dimension evaluators in parallel, compute priority,
    and return the full structured result.
    """
    from concurrent.futures import ThreadPoolExecutor

    dimensions = ["Facts", "Strategies", "Procedures", "Rationales"]
    dimension_inputs = {
        "Facts": request.facts,
        "Strategies": request.strategies,
        "Procedures": request.procedures,
        "Rationales": request.rationales,
    }

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            dim: executor.submit(
                run_dimension_evaluator,
                dimension=dim,
                student_examples=dimension_inputs[dim].examples,
                student_uncertainties=dimension_inputs[dim].uncertainties,
                legal_domain=request.legal_domain,
                branch=request.branch,
                jurisdiction=request.jurisdiction,
                baseline_familiarity=request.baseline_familiarity,
                primary_intent=request.primary_intent,
                legal_situation=request.legal_situation,
                prior_experience=request.prior_experience,
                desired_outcome=request.desired_outcome,
                kb_content=kb_content,
                debug_log=debug_log,
            )
            for dim in dimensions
        }
        evaluation_report = [futures[dim].result() for dim in dimensions]

    priority = compute_full_priority_from_report(evaluation_report)

    return {
        "evaluation_report": evaluation_report,
        "priority": priority,
    }