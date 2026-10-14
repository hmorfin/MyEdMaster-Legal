CLASSIFIER_PROMPT = """
You are a legal domain classifier for a legal information chatbot.
Given the user's legal situation and their jurisdiction, classify the situation
into the most appropriate legal domain, branch, baseline familiarity, and primary intent.

---
STEP 1 - Classify primary_intent FIRST before anything else.
Use ONLY these definitions:

- understand_options: user wants to know what legal choices or rights they have
- contest: user wants to challenge, dispute, or fight against a decision, charge,
  ticket, or refusal — including seeking refunds when a seller is refusing
- comply: user wants to fulfill a legal obligation correctly
- draft: user wants to create a new legal document from scratch
- review: user wants to examine and understand an existing document they have
  ALREADY RECEIVED — such as a contract, agreement, or terms and conditions
  they are being asked to sign

Key distinction — review vs understand_options:
- "I want to understand this contract before I sign it" → review
- "I want to know if I can get out of my contract" → understand_options
- "I was sent a service agreement and want to know what I am agreeing to" → review

---
STEP 2 - Classify legal_domain and branch.
Branch should describe the TYPE OF LEGAL SITUATION, not the desired outcome.
Example: a broken laptop where the seller refuses a refund → branch=defective_product
NOT branch=refund_dispute (that is the desired outcome, not the situation type)

Available domains and example branches (not exhaustive, expand when confident):
- traffic_law: speeding_ticket, red_light_violation, dui, reckless_driving, parking_violation, license_suspension
- contract_law: service_agreement, employment_contract, lease_agreement, purchase_agreement, nda
- landlord_tenant_law: repairs_and_habitability, eviction, security_deposit, rent_increase, lease_termination
- consumer_rights: defective_product, refund_dispute, false_advertising, debt_collection, warranty_claim
- employment_law: wrongful_termination, unpaid_wages, workplace_discrimination, harassment, non_compete
- family_law: divorce, child_custody, child_support, adoption, domestic_violence
- criminal_law: dui, assault, theft, drug_offense, expungement
- personal_injury: car_accident, slip_and_fall, medical_malpractice, product_liability, dog_bite
- immigration_law: visa_application, work_permit, deportation, citizenship, asylum
- estate_law: will_creation, probate, inheritance_dispute, power_of_attorney, trust
- small_claims: debt_recovery, property_damage, security_deposit, unpaid_services
- intellectual_property: copyright, trademark, patent, trade_secret
- bankruptcy: chapter_7, chapter_13, debt_relief, creditor_dispute
- civil_rights: discrimination, police_misconduct, ada_violation, voting_rights
- healthcare_law: medical_billing, insurance_denial, hipaa_violation, malpractice

If domain is unclear or situation spans multiple domains with no clear primary,
set legal_domain="general" and branch="general".
Only use general when there is genuinely no specific domain that fits.

---
STEP 3 - Classify baseline_familiarity from prior_experience:
- low: no prior experience with legal matters
- medium: some relevant experience but no formal legal knowledge - includes having dealt with a similar situation once before without
  deep understanding of the legal process
- high: has dealt with this type of situation before multiple times or has formal legal background or training.

---
Return strict JSON:
{{
  "legal_domain": "string",
  "branch": "string",
  "baseline_familiarity": "low | medium | high",
  "primary_intent": "understand_options | contest | comply | draft | review",
  "confidence": float,
  "reasoning": "string"
}}

User inputs:
Legal situation: {legal_situation}
Jurisdiction: {jurisdiction}
Prior experience: {prior_experience}
Desired outcome: {desired_outcome}
"""
GENERAL_DOMAIN_INSTRUCTION = """
SPECIAL INSTRUCTION — GENERAL DOMAIN:
The user has not identified a specific legal domain. Do NOT generate a random
sample of different laws. Instead, generate a knowledge base focused on:
- How to identify what type of legal issue you have
- How to find legal aid and pro bono resources in {jurisdiction}
- What questions to ask when consulting a lawyer
- Basic legal process in {jurisdiction} (filing complaints, statutes of limitations)
- How to document and preserve evidence for any legal matter
- Key {jurisdiction} legal resources and government agencies
This KB should help the user navigate to the right legal domain, not inform
them about a specific one.
"""

KB_GENERATOR_PROMPT = """
You are a legal knowledge base architect generating a reusable, high-accuracy
knowledge base for a legal information chatbot.
You MUST FOLLOW ALL THE REQUIREMENTS SERIOUSLY!!!

Focus domain: {legal_domain}
Focus jurisdiction: {jurisdiction}
User inputs:
- Legal situation: {legal_situation}
(adapt tone, depth, and examples accordingly)

{general_domain_instruction}

---
Knowledge Base Generation Goals & Constraints:
1) Strict Compliance: Populate EVERY field defined in the JSON schema below.
2) Completeness & Quality: No placeholders. Every item must be substantive.
3) Conceptual Precision: Provide layered explanations per item.
4) Jurisdiction-specific: All content must be specific to {jurisdiction}.
   Never generate generic content that ignores jurisdiction.

---
Field Requirements:
1. global_highlights (minimum 10 items — do not stop at 10, include all critical points needed to fully cover this domain/branch/jurisdiction):
   - Key legal facts, statutes, and procedures specific to {legal_domain}
     in {jurisdiction}.
   - Items must not overlap; cover distinct critical ideas.

2. rag_snippets (min 8):
   - Self-contained legal reference paragraphs suitable for retrieval.
   - No duplication across snippets.

3. few_shot_examples (facts, strategies, procedures, rationales, tutor):
   - For each category, provide >= 2 input/analysis pairs.
   - Input: realistic legal question/misconception (~15-40 words).
   - Analysis: >= 4 sentences, supportive tone; include acknowledgment,
     core concept, concrete example, common pitfall.

4. cot_checklist (min 5):
   - Reasoning steps: clarify user intent -> retrieve highlights ->
     plan solution path -> verify claims -> tailor to user intent ->
     present concise answer + next action.

Return strict JSON:
{{
  "title": "string (>=10 chars)",
  "global_highlights": ["string"],
  "rag_snippets": ["string"],
  "few_shot_examples": {{
    "facts": [{{"input": "string", "analysis": "string"}}],
    "strategies": [{{"input": "string", "analysis": "string"}}],
    "procedures": [{{"input": "string", "analysis": "string"}}],
    "rationales": [{{"input": "string", "analysis": "string"}}],
    "tutor": [{{"input": "string", "analysis": "string"}}]
  }},
  "cot_checklist": ["string"]
}}
"""

KB_AUDIT_PROMPT = """
You are a strict reviewer for knowledge base JSON used in an adaptive legal chatbot.

Return ONLY a JSON object with exactly these keys:
{{
  "status": "ok" or "regenerate",
  "issues": ["issue1", ...],
  "recommendation": "one sentence summary"
}}
No markdown, no prose, no extra keys.

Trigger "regenerate" if any of the following hold:
- Title is missing, generic, under 8 characters, or a placeholder.
- global_highlights has < 5 substantive items or any item is a placeholder.
- rag_snippets has < 5 self-contained paragraphs or any item is a placeholder.
- Any few_shot_examples entry has placeholder text or analysis under 4 sentences.
- cot_checklist has < 5 steps or any step is a placeholder.
- JSON is malformed or any required field is null/empty.

Knowledge Base JSON:
{kb_json}
"""

EXAMPLE_GENERATION_SYSTEM_PROMPT = """
You are an AI that emits ONLY JSON per the schema:
{
  "fspr": {
    "facts": ["string"],
    "strategies": ["string"],
    "procedures": ["string"],
    "rationales": ["string"],
    "notes": "string"
  },
  "example_text": "string",
  "empty_template": {
    "title": "string",
    "sections": [
      {
        "heading": "string",
        "prompt": "string",
        "placeholders": ["string"]
      }
    ]
  }
}

Rules:
- No prose outside JSON. Output valid UTF-8 JSON only.

- Generate example_text: A detailed self-assessment example (4-6 paragraphs,
  500-800 words) for a CLOSELY RELATED legal topic in the same legal domain.

- Hard rule: The "do_not_use_this_situation" field contains the user's actual situation.
  You MUST NOT use this scenario or any facts, events, or circumstances from it
  in your example_text. Choose a clearly adjacent scenario in the same domain and branch.
  For employment law paycheck dispute → use wrongful termination instead.
  For traffic speeding ticket → use parking violation or expired registration instead.
  For contract review → use a lease agreement instead of a service agreement.

- Structure of example_text:
  1. Opening: Start IMMEDIATELY with a specific scenario sentence.
     Do NOT open with a meta-description of knowledge types.

     WRONG: "In the realm of traffic law, understanding the four knowledge
     types is crucial for navigating legal situations effectively."

     CORRECT: "Suppose you received a parking ticket last Tuesday in Dallas
     for an expired meter. Here is how you might assess your own knowledge
     about that situation."

     The opening sentence must name a specific concrete scenario. Then briefly
     explain the four knowledge types using that scenario as the anchor.

  2. Facts: relevant laws, fines, rights in the jurisdiction
  3. Strategies: available legal options and when to use each
  4. Procedures: step-by-step process for the chosen strategy
  5. Rationales: why this approach is preferred given the situation
  6. Self-reflection: strengths and gaps across all four dimensions

- Generate empty_template: blank prompts for the user's actual legal situation
  using the same four-dimension structure
"""

EXAMPLE_GENERATION_GUIDE = """
Self-assessment framework for mapping any legal situation to
FSPR (facts, strategies, procedures, rationales).

TRAFFIC LAW example (running a red light, Texas):
- Facts: Texas Transportation Code section 544.007 prohibits proceeding
  through a red signal. Fine ranges $75-$200. Points may be added to record.
- Strategies: pay the fine, attend defensive driving, or contest in court.
- Procedures: 1) Check citation for response deadline 2) Choose response
  method 3) Submit payment or request hearing before deadline.
- Rationales: defensive driving keeps ticket off record and prevents
  insurance increase; contesting is viable if signal was malfunctioning.

CONTRACT LAW example (breach of service agreement):
- Facts: a valid contract requires offer, acceptance, and consideration.
  Breach occurs when one party fails to perform.
- Strategies: negotiate a resolution, send a demand letter, or file in
  small claims court.
- Procedures: 1) Document the breach in writing 2) Send formal demand
  letter 3) File claim if unresolved within response period.
- Rationales: demand letter creates a paper trail and often resolves
  disputes without litigation.

Always fit the current legal situation to this mapping.
"""

DIMENSION_EVALUATOR_PROMPT = """
You are an expert legal knowledge evaluator assessing a student's self-assessment
for a legal chatbot onboarding system.

Your task is to evaluate the student's understanding of the {dimension} dimension
of their legal situation and label each aspect of their response.

---
CONTEXT:
Legal domain: {legal_domain}
Branch: {branch}
Jurisdiction: {jurisdiction}
Baseline familiarity: {baseline_familiarity}
Primary intent: {primary_intent}
Legal situation: {legal_situation}
Prior experience: {prior_experience}
Desired outcome: {desired_outcome}

Calibration rules:
- low familiarity: do not penalize missing procedural detail; focus on whether
  core facts and concepts are correct or absent
- medium familiarity: expect basic strategic awareness; flag missing procedures
  as Omission only if they are straightforward
- high familiarity: apply strict evaluation across all four dimensions; False
  Knowledge and Omission should be flagged precisely

Primary intent weighting:
- contest: evaluate Strategies dimension most strictly
- comply: evaluate Procedures dimension most strictly
- draft: evaluate Procedures and Facts dimensions most strictly
- review: evaluate Facts dimension most strictly
- understand_options: apply balanced evaluation across all dimensions

---
KNOWLEDGE BASE REFERENCE:
Global highlights:
{global_highlights}

RAG snippets (filtered for this branch):
{rag_snippets}

Few-shot examples for {dimension}:
{few_shot_examples}

---
STUDENT INPUT — {dimension}:
Examples provided: {student_examples}
Uncertainties noted: {student_uncertainties}

---
LABEL DEFINITIONS:
- Know-Know: student correctly understands this aspect
- Know-Don't Know: student correctly identifies a gap in their own knowledge
- False Knowledge: student states something incorrect or misleading
- Omission: student is missing a critical concept they did not acknowledge
- Irrelevant Knowledge: student includes information not relevant to their situation

---
Return strict JSON:
{{
  "dimension": "{dimension}",
  "aspects": [
    {{"labels": ["string"], "text": "string"}}
  ],
  "most_critical_gap": "one sentence identifying the single most important gap"
}}

Rules:
- aspects must cover ALL distinct claims or absences in the student input
- most_critical_gap must be a single actionable sentence
- do not include any prose outside the JSON
"""

SELF_ASSESSMENT_TEXT_TEMPLATE = """
Legal situation: {legal_situation}

Facts:
- Examples: {facts_examples}
- Uncertainties: {facts_uncertainties}

Strategies:
- Examples: {strategies_examples}
- Uncertainties: {strategies_uncertainties}

Procedures:
- Examples: {procedures_examples}
- Uncertainties: {procedures_uncertainties}

Rationales:
- Examples: {rationales_examples}
- Uncertainties: {rationales_uncertainties}
"""