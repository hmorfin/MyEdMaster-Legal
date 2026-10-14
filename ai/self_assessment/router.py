import logging
import os
from typing import Any
from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, HTTPException
from .schemas import GenerateKBRequest, GenerateKBResponse, EvaluateRequest, EvaluateResponse
from .pipeline import (
    run_llm1_classifier, run_llm2_kb_generator, run_llm3_audit,
    run_llm4_example_generator, create_self_assessment_text, run_evaluation_pipeline
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate-kb", response_model=GenerateKBResponse)
def generate_kb(request: GenerateKBRequest) -> Any:
    logger.info(
        "generate_kb_requested",
        extra={"jurisdiction": request.jurisdiction, "debug": request.debug},
    )
    if request.debug:
        logger.warning(
            "generate_kb_debug_mode_enabled",
            extra={"note": "debug_log in the response will include raw prompts/LLM output — do not enable in production"},
        )

    debug_log = [] if request.debug else None

    # LLM1: classify domain
    classification = run_llm1_classifier(request, debug_log)
    legal_domain = classification.get("legal_domain", "general")
    branch = classification.get("branch", "general")
    baseline_familiarity = classification.get("baseline_familiarity", "low")
    primary_intent = classification.get("primary_intent", "understand_options")
    confidence = float(classification.get("confidence", 0.5))

    # LLM2: generate KB + Examples
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_kb_content = executor.submit(
            run_llm2_kb_generator,
            legal_domain=legal_domain,
            jurisdiction=request.jurisdiction,
            legal_situation=request.legal_situation,
            debug_log=debug_log,
        )
        future_example_output = executor.submit(
            run_llm4_example_generator,
            legal_domain=legal_domain,
            branch=branch,
            jurisdiction=request.jurisdiction,
            legal_situation=request.legal_situation,
            debug_log=debug_log,
        )
        kb_content = future_kb_content.result()
        example_output = future_example_output.result()

    # LLM3: audit KB
    if os.getenv("KB_AUDIT_ENABLED", "false").lower() == "true":
        audit = run_llm3_audit(kb_content, debug_log)
        if audit.get("status") == "regenerate":
            logger.warning(f"[LLM3] Regenerating KB — issues: {audit.get('issues')}")
            kb_content = run_llm2_kb_generator(
                legal_domain=legal_domain,
                jurisdiction=request.jurisdiction,
                legal_situation=request.legal_situation,
                prior_experience=request.prior_experience,
                desired_outcome=request.desired_outcome,
                debug_log=debug_log,
            )

    return GenerateKBResponse(
        legal_domain=legal_domain,
        branch=branch,
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


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate_self_assessment(request: EvaluateRequest) -> Any:
    """
    Step 2: Self-Assessment Evaluation Pipeline.
    Receives the user's four-dimension form submission along with kb_content
    passed by Django. Runs four parallel LLM dimension evaluators, computes
    the Most Critical Gap priority, and returns the structured report.
    Django is responsible for all DB access — the AI layer is stateless.
    """
    logger.info("evaluate_self_assessment_requested", extra={"chat_id": request.chat_id})

    debug_log = []

    # KB content is passed directly by Django — no DB access in AI layer
    kb_content = request.kb_content

    if not kb_content:
        raise HTTPException(
            status_code=400,
            detail="kb_content is required and cannot be empty",
        )

    # Flatten student input into a single text block
    student_text = create_self_assessment_text(request)

    # Run four parallel dimension evaluators
    eval_result = run_evaluation_pipeline(request, kb_content, debug_log)

    evaluation_report = eval_result["evaluation_report"]
    priority = eval_result["priority"]

    logger.info(
        "evaluate_self_assessment_completed",
        extra={"chat_id": request.chat_id, "top_dimension": priority.get("top_dimension")},
    )

    return EvaluateResponse(
        chat_id=request.chat_id,
        student_text=student_text,
        evaluation_report=[
            {
                "dimension": r["dimension"],
                "aspects": r.get("aspects", []),
                "most_critical_gap": r.get("most_critical_gap", ""),
            }
            for r in evaluation_report
        ],
        priority=priority,
    )