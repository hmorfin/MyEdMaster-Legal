import logging

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import json

from langchain_openai import ChatOpenAI
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class FSPRInferRequest(BaseModel):
    user_message: str
    llm_response: str
    fspr_profile: dict = {}
    legal_domain: str = ""


class FSPRInferResponse(BaseModel):
    dimension: str
    label: str
    gap: str
    updated_score: float


@router.post("/infer", response_model=FSPRInferResponse)
def infer_fspr_delta(request: FSPRInferRequest):
    logger.info(
        "fspr_infer_requested",
        extra={"legal_domain": request.legal_domain, "user_message_length": len(request.user_message)},
    )
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=settings.openai_api_key,
        temperature=0.1,
    )

    current_scores = {
        "Facts": request.fspr_profile.get("Facts", {}).get("score", 0.1),
        "Strategies": request.fspr_profile.get("Strategies", {}).get("score", 0.1),
        "Procedures": request.fspr_profile.get("Procedures", {}).get("score", 0.1),
        "Rationales": request.fspr_profile.get("Rationales", {}).get("score", 0.1),
    }

    prompt = f"""You are evaluating a legal consultation exchange to update a user's knowledge profile.

LEGAL DOMAIN: {request.legal_domain or "General Legal"}

USER MESSAGE:
{request.user_message}

ASSISTANT RESPONSE:
{request.llm_response}

CURRENT KNOWLEDGE PROFILE SCORES (0.0-1.0):
- Facts: {current_scores["Facts"]}
- Strategies: {current_scores["Strategies"]}
- Procedures: {current_scores["Procedures"]}
- Rationales: {current_scores["Rationales"]}

FSPR DIMENSIONS:
- Facts: Legal facts, statutes, rights, obligations the user knows or doesn't know
- Strategies: Approaches and options the user is aware of or missing
- Procedures: Step-by-step processes the user understands or is uncertain about
- Rationales: The reasoning behind legal rules that the user grasps or misunderstands

Based on this exchange, identify the ONE dimension most revealed by the user's message.
Determine what knowledge label best describes the user's demonstrated knowledge:
- Know-Know: User clearly knows this
- Know-Don't Know: User knows they don't know something
- False Knowledge: User believes something incorrect
- Omission: User is missing important knowledge they don't know they're missing

Calculate the updated score for that dimension using:
new_score = current_score * 0.7 + signal_strength * 0.3

Where signal_strength is:
- Know-Know: 0.8
- Know-Don't Know: 0.4
- False Knowledge: 0.2
- Omission: 0.3

Return ONLY this JSON:
{{
    "dimension": "<Facts|Strategies|Procedures|Rationales>",
    "label": "<Know-Know|Know-Don't Know|False Knowledge|Omission>",
    "gap": "<one sentence describing the specific gap or strength identified>",
    "updated_score": <float 0.0-1.0>
}}"""

    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        parsed = json.loads(raw)
        logger.info(
            "fspr_infer_completed",
            extra={
                "dimension": parsed.get("dimension"),
                "label": parsed.get("label"),
                "updated_score": parsed.get("updated_score"),
            },
        )
        return FSPRInferResponse(
            dimension=parsed.get("dimension", "Facts"),
            label=parsed.get("label", "Know-Don't Know"),
            gap=parsed.get("gap", ""),
            updated_score=float(parsed.get("updated_score", 0.1)),
        )
    except Exception:
        logger.error("fspr_infer_failed", exc_info=True, extra={"legal_domain": request.legal_domain})
        return FSPRInferResponse(
            dimension="Facts",
            label="Know-Don't Know",
            gap="",
            updated_score=0.1,
        )