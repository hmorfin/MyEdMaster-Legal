
from dataclasses import dataclass, field


@dataclass
class BenchmarkCase:
    id: str
    category: str           # definitional_factual | full_legal_scenario | mid_conversation_anaphora | sa_guided
    description: str
    query: str

    # Pipeline inputs
    user_id: str = "benchmark-user"
    chat_id: str = "benchmark-chat"
    document_paths: list = field(default_factory=list)
    conversation_history: list = field(default_factory=list)
    user_context: dict = field(default_factory=dict)
    self_assessment_context: dict = field(default_factory=dict)
    conversation_summary: str | None = None
    primary_topic: str | None = None

    # Evaluation hints (used by metrics, not the pipeline)
    expected_topics: list = field(default_factory=list)
    relevance_keywords: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Category 1 — definitional_factual (8 cases)
# ---------------------------------------------------------------------------

_SIMPLE = [
    BenchmarkCase(
        id="S01",
        category="definitional_factual",
        description="Definition: at-will employment",
        query="What is at-will employment and does it mean my employer can fire me for any reason?",
        user_context={"jurisdiction": "arizona", "knowledge_level": "low"},
        expected_topics=["Employment & Labor Law"],
        relevance_keywords=["at-will", "terminate", "employment", "reason"],
    ),
    BenchmarkCase(
        id="S02",
        category="definitional_factual",
        description="Timeline: security deposit return in AZ",
        query="How long does a landlord have to return a security deposit in Arizona?",
        user_context={"jurisdiction": "arizona", "knowledge_level": "low"},
        expected_topics=["Tenant & Landlord Rights", "Housing & Real Estate"],
        relevance_keywords=["deposit", "landlord", "14 days", "30 days", "Arizona"],
    ),
    BenchmarkCase(
        id="S03",
        category="definitional_factual",
        description="Definition: statute of limitations for personal injury in CA",
        query="What is the statute of limitations for filing a personal injury lawsuit in California?",
        user_context={"jurisdiction": "california", "knowledge_level": "low"},
        expected_topics=["Personal Injury & Liability"],
        relevance_keywords=["statute of limitations", "two years", "California", "personal injury"],
    ),
    BenchmarkCase(
        id="S04",
        category="definitional_factual",
        description="Definition: pro se representation",
        query="What does it mean to represent yourself 'pro se' in court and is it a good idea?",
        user_context={"knowledge_level": "low"},
        expected_topics=["Small Claims & Civil Disputes"],
        relevance_keywords=["pro se", "self-represent", "attorney", "court"],
    ),
    BenchmarkCase(
        id="S05",
        category="definitional_factual",
        description="Definition: small claims court scope",
        query="What is small claims court and what dollar amount can I sue for in Texas?",
        user_context={"jurisdiction": "texas", "knowledge_level": "low"},
        expected_topics=["Small Claims & Civil Disputes"],
        relevance_keywords=["small claims", "Texas", "dollar limit", "$20,000", "Justice Court"],
    ),
    BenchmarkCase(
        id="S06",
        category="definitional_factual",
        description="Definition: non-compete clause",
        query="What is a non-compete clause in an employment contract and is it enforceable?",
        user_context={"knowledge_level": "low"},
        expected_topics=["Employment & Labor Law", "Business & Contract Law"],
        relevance_keywords=["non-compete", "enforceable", "reasonable", "geographic", "time"],
    ),
    BenchmarkCase(
        id="S07",
        category="definitional_factual",
        description="Definition: Chapter 7 vs Chapter 13 bankruptcy",
        query="What is the difference between Chapter 7 and Chapter 13 bankruptcy?",
        user_context={"knowledge_level": "low"},
        expected_topics=["Bankruptcy & Debt"],
        relevance_keywords=["Chapter 7", "Chapter 13", "liquidation", "reorganization", "discharge"],
    ),
    BenchmarkCase(
        id="S08",
        category="definitional_factual",
        description="Factual: driving points duration in TX",
        query="How long do points from a speeding ticket stay on my driving record in Texas?",
        user_context={"jurisdiction": "texas", "knowledge_level": "low"},
        expected_topics=["Traffic & DUI Law"],
        relevance_keywords=["points", "driving record", "Texas", "three years", "surcharge"],
    ),
]

# ---------------------------------------------------------------------------
# Category 2 — full_legal_scenario (7 cases)
# ---------------------------------------------------------------------------

_COMPLEX = [
    BenchmarkCase(
        id="C01",
        category="full_legal_scenario",
        description="Wrongful termination after harassment report — employment, CA",
        query=(
            "I reported my manager to HR for sexual harassment three weeks ago. "
            "Yesterday I was told my position was 'eliminated' but my coworkers still have their jobs. "
            "I have email records and a witness who heard the harassment. What are my legal options?"
        ),
        user_context={"jurisdiction": "california", "knowledge_level": "low", "profession": "employee"},
        expected_topics=["Employment & Labor Law", "Civil Rights & Discrimination"],
        relevance_keywords=["retaliation", "harassment", "wrongful termination", "EEOC", "California DFEH"],
    ),
    BenchmarkCase(
        id="C02",
        category="full_legal_scenario",
        description="Security deposit dispute with photo evidence — tenant, AZ",
        query=(
            "My landlord is refusing to return my $2,400 security deposit, claiming carpet damage. "
            "I have timestamped move-in photos showing the carpet was already stained before I moved in. "
            "I moved out 45 days ago and never received an itemized deduction list. "
            "What are my options and what law applies?"
        ),
        user_context={"jurisdiction": "arizona", "knowledge_level": "low"},
        expected_topics=["Tenant & Landlord Rights", "Housing & Real Estate"],
        relevance_keywords=["security deposit", "itemized", "14 days", "Arizona", "double damages"],
    ),
    BenchmarkCase(
        id="C03",
        category="full_legal_scenario",
        description="First offense DUI — traffic/criminal, AZ",
        query=(
            "I was arrested for DUI last night. The breathalyzer read 0.12 BAC. "
            "I have never been arrested before. I have a professional license that could be affected. "
            "What are the likely consequences and what should I do immediately?"
        ),
        user_context={"jurisdiction": "arizona", "knowledge_level": "low"},
        expected_topics=["Traffic & DUI Law", "Criminal Law & Defense"],
        relevance_keywords=["DUI", "BAC", "Arizona", "first offense", "license suspension", "attorney"],
    ),
    BenchmarkCase(
        id="C04",
        category="full_legal_scenario",
        description="Contractor abandonment with deposit — contract, TX",
        query=(
            "I hired a contractor for a kitchen remodel and paid $8,000 upfront. "
            "After completing about 30% of the work, they stopped showing up 6 weeks ago. "
            "They are not answering calls or texts. I have a signed contract and payment receipts. "
            "What can I do to recover my money?"
        ),
        user_context={"jurisdiction": "texas", "knowledge_level": "low"},
        expected_topics=["Business & Contract Law", "Small Claims & Civil Disputes"],
        relevance_keywords=["breach of contract", "contractor", "small claims", "demand letter", "Texas"],
    ),
    BenchmarkCase(
        id="C05",
        category="full_legal_scenario",
        description="Insurance stall after car accident — personal injury, CA",
        query=(
            "I was rear-ended 14 months ago. The other driver was at fault and their insurance accepted liability. "
            "But the insurance adjuster keeps delaying, asking for more medical records, and offering low settlements. "
            "I still have ongoing back pain and therapy bills. What should I do at this point?"
        ),
        user_context={"jurisdiction": "california", "knowledge_level": "low"},
        expected_topics=["Personal Injury & Liability"],
        relevance_keywords=["statute of limitations", "bad faith", "demand letter", "attorney", "California", "settlement"],
    ),
    BenchmarkCase(
        id="C06",
        category="full_legal_scenario",
        description="Unilateral schedule reduction with signed agreement — employment, NY",
        query=(
            "I have a signed employment contract guaranteeing 40 hours per week at a set hourly rate. "
            "My employer just told me they are reducing my hours to 24 per week starting next month, "
            "citing slow business. I did not agree to this change. Do I have legal recourse?"
        ),
        user_context={"jurisdiction": "new york", "knowledge_level": "medium", "profession": "employee"},
        expected_topics=["Employment & Labor Law", "Business & Contract Law"],
        relevance_keywords=["breach of contract", "employment contract", "constructive dismissal", "New York"],
    ),
    BenchmarkCase(
        id="C07",
        category="full_legal_scenario",
        description="LLC dissolution dispute — business, general",
        query=(
            "My business partner wants to dissolve our 50/50 LLC. "
            "I want to continue the business and I believe the company is profitable. "
            "We have an operating agreement but it does not specify dissolution procedure. "
            "What are my rights and what can I do to prevent or negotiate the dissolution?"
        ),
        user_context={"knowledge_level": "medium"},
        expected_topics=["Business & Contract Law"],
        relevance_keywords=["LLC", "dissolution", "operating agreement", "buyout", "deadlock"],
    ),
]

# ---------------------------------------------------------------------------
# Category 3 — mid_conversation_anaphora (8 cases)
# Turn 3 of a conversation; conversation_history contains 2 prior turns.
# These test anaphora resolution ("it", "they", "that").
# ---------------------------------------------------------------------------

_MULTI_TURN = [
    BenchmarkCase(
        id="M01",
        category="mid_conversation_anaphora",
        description="Tenant: follow-up on demand letter timeline (anaphora: 'they')",
        query="How long do they have to respond after I send the letter?",
        conversation_history=[
            {"role": "user", "content": "My landlord kept my $1,500 security deposit and never gave me an itemized list of deductions. I moved out 30 days ago."},
            {"role": "assistant", "content": "In Arizona, landlords must provide an itemized statement within 14 days of move-out. Since they missed that deadline, they may have forfeited the right to make deductions. I'd recommend sending a written demand letter via certified mail requesting the full deposit back. Would you like to know what to include in that letter?"},
            {"role": "user", "content": "Yes, I already sent it yesterday via certified mail."},
            {"role": "assistant", "content": "Good move. A proper demand letter puts the landlord on notice and creates a paper trail. In Arizona, after receiving the letter, the landlord typically has a reasonable window to respond — usually around 5 to 10 days is considered standard before you escalate. How long do they have to respond after I send the letter?"},
        ],
        conversation_summary="User's landlord in Arizona withheld a $1,500 security deposit without an itemized list after 30-day move-out. User has sent a certified mail demand letter. Now asking about the landlord's response timeline.",
        user_context={"jurisdiction": "arizona", "knowledge_level": "low"},
        expected_topics=["Tenant & Landlord Rights", "Housing & Real Estate"],
        relevance_keywords=["demand letter", "response", "landlord", "Arizona", "small claims"],
    ),
    BenchmarkCase(
        id="M02",
        category="mid_conversation_anaphora",
        description="Employment: follow-up on interview disclosure after wrongful termination (anaphora: 'they')",
        query="What should I say if they ask why I left at my next job interview?",
        conversation_history=[
            {"role": "user", "content": "I was fired after I complained to HR about wage theft. I have documentation showing my employer was not paying overtime correctly."},
            {"role": "assistant", "content": "This sounds like potential retaliation, which is illegal under the Fair Labor Standards Act and California Labor Code. Your documentation of the wage violations and the timeline of events — complaint followed by termination — is exactly the kind of evidence that supports a retaliation claim. Have you filed a complaint with the California Labor Commissioner yet?"},
            {"role": "user", "content": "Not yet. I'm worried about the effect this will have on future employment."},
            {"role": "assistant", "content": "That concern is common and valid. The good news is that retaliation claims are on public record only if you file a lawsuit — a labor board complaint is generally not. Most employers cannot legally tell future employers why you left (only confirm dates of employment in many cases). What should I say if they ask why I left at my next job interview?"},
        ],
        conversation_summary="User in California was fired after reporting wage theft to HR. Has documentation of unpaid overtime. Exploring retaliation claim but worried about future employment impact.",
        user_context={"jurisdiction": "california", "knowledge_level": "low"},
        expected_topics=["Employment & Labor Law"],
        relevance_keywords=["interview", "termination reason", "reference", "defamation", "retaliation"],
    ),
    BenchmarkCase(
        id="M03",
        category="mid_conversation_anaphora",
        description="Traffic: contesting a ticket after paying (anaphora: 'it')",
        query="Can I still contest it if I already paid the fine online this morning?",
        conversation_history=[
            {"role": "user", "content": "I got a red light camera ticket in Phoenix for $250. I don't think the photo clearly shows my face."},
            {"role": "assistant", "content": "Arizona red light camera tickets are civil, not criminal, and you have the right to contest them. The prosecution must prove it was you driving. A photo that does not clearly identify the driver is a valid defense. You typically have 30 days from the notice to request a hearing."},
            {"role": "user", "content": "I just paid it online this morning by mistake before I read this. Can I still contest it if I already paid the fine online this morning?"},
        ],
        conversation_summary="User in Phoenix received a $250 red light camera ticket. Photo identification was unclear. User accidentally paid online before understanding contest options.",
        user_context={"jurisdiction": "arizona", "knowledge_level": "low"},
        expected_topics=["Traffic & DUI Law"],
        relevance_keywords=["contest", "paid", "refund", "camera ticket", "Arizona", "waiver"],
    ),
    BenchmarkCase(
        id="M04",
        category="mid_conversation_anaphora",
        description="Contract: accidental NDA violation (anaphora: 'it')",
        query="What happens if I violate it accidentally — like if I mention something in a normal conversation without thinking?",
        conversation_history=[
            {"role": "user", "content": "My new employer wants me to sign an NDA before I start. It covers all proprietary information and has a 2-year post-employment term."},
            {"role": "assistant", "content": "NDAs with post-employment terms are common but must be carefully reviewed. Key things to check: what exactly counts as 'proprietary information,' whether there are carve-outs for general skills and knowledge you had before, and whether the 2-year term is tied to specific information types or is a blanket restriction. Some states limit these NDAs heavily — what state are you in?"},
            {"role": "user", "content": "California. And what happens if I violate it accidentally?"},
        ],
        conversation_summary="User in California is reviewing a pre-employment NDA with a 2-year post-employment confidentiality term. Asking about accidental violations.",
        user_context={"jurisdiction": "california", "knowledge_level": "low"},
        expected_topics=["Business & Contract Law", "Employment & Labor Law"],
        relevance_keywords=["NDA", "breach", "accidental", "damages", "California", "intent"],
    ),
    BenchmarkCase(
        id="M05",
        category="mid_conversation_anaphora",
        description="Personal injury: settlement estimate (anaphora: 'this')",
        query="What is the average settlement for something like this?",
        conversation_history=[
            {"role": "user", "content": "I slipped on ice in a grocery store parking lot and fractured my wrist. I needed surgery and was out of work for 6 weeks."},
            {"role": "assistant", "content": "This is a premises liability case. The store owes a duty to maintain a reasonably safe parking lot, which includes treating or warning of ice. Key facts that will matter: did they know about the ice, was there a wet floor sign or warning, and do you have medical records documenting the fracture and surgery? What state are you in?"},
            {"role": "user", "content": "Texas. I have all my medical records and bills — about $18,000 total. What is the average settlement for something like this?"},
        ],
        conversation_summary="User in Texas fractured their wrist in a slip-and-fall on ice at a grocery store parking lot. Had surgery, 6 weeks off work, $18,000 in medical bills. Has full medical documentation.",
        user_context={"jurisdiction": "texas", "knowledge_level": "low"},
        expected_topics=["Personal Injury & Liability"],
        relevance_keywords=["settlement", "slip and fall", "premises liability", "Texas", "damages", "medical bills"],
    ),
    BenchmarkCase(
        id="M06",
        category="mid_conversation_anaphora",
        description="Small claims: how to file (ambiguous without context)",
        query="How do I actually file? Do I need to go in person?",
        conversation_history=[
            {"role": "user", "content": "My neighbor's tree fell on my fence during a storm and caused $1,800 in damage. They are refusing to pay saying it was an act of God."},
            {"role": "assistant", "content": "The 'act of God' defense is a common response but does not automatically eliminate liability. In most states, if your neighbor knew the tree was diseased or unstable and failed to address it, they can be held liable regardless of weather conditions. Did you notice any prior signs that the tree was dead, leaning, or rotting? And do you have photos of the damage?"},
            {"role": "user", "content": "Yes — I actually texted them last spring saying the tree looked dead. I have the text chain. I want to sue them in small claims court. How do I actually file?"},
        ],
        conversation_summary="User's neighbor's dead tree fell on their fence causing $1,800 damage. User has text chain from last spring warning the neighbor about the dead tree. Neighbor claims act of God defense. User wants to file in small claims.",
        user_context={"knowledge_level": "low"},
        expected_topics=["Small Claims & Civil Disputes"],
        relevance_keywords=["small claims", "file", "court clerk", "in person", "online", "fee"],
    ),
    BenchmarkCase(
        id="M07",
        category="mid_conversation_anaphora",
        description="Immigration: visa processing timeline (ambiguous without context)",
        query="How long does the process usually take from the time I submit?",
        conversation_history=[
            {"role": "user", "content": "I am on an H-1B visa and my employer wants to sponsor me for a green card. I work in software engineering."},
            {"role": "assistant", "content": "For software engineers from most countries, the EB-2 or EB-3 employment-based categories are typical paths. The process generally has three stages: PERM labor certification (filed by your employer), I-140 petition, and finally the I-485 adjustment of status or consular processing. The biggest variable is priority date backlogs, which can be substantial for applicants from certain countries. Where were you born?"},
            {"role": "user", "content": "India. How long does the process usually take from the time I submit?"},
        ],
        conversation_summary="User is an Indian software engineer on H-1B, employer is sponsoring EB-2/EB-3 green card. Asking about total processing timeline given India backlog.",
        user_context={"knowledge_level": "low"},
        expected_topics=["Immigration Law"],
        relevance_keywords=["green card", "India", "priority date", "backlog", "EB-2", "EB-3", "wait time"],
    ),
    BenchmarkCase(
        id="M08",
        category="mid_conversation_anaphora",
        description="Family law: first-filer advantage in divorce (anaphora: 'it')",
        query="Does it matter who files first?",
        conversation_history=[
            {"role": "user", "content": "I am considering filing for divorce in Arizona. We have been married for 12 years and have two kids, ages 8 and 11."},
            {"role": "assistant", "content": "Arizona is a no-fault, community property state. This means the reason for the divorce generally does not affect asset division — marital property is split 50/50 by default. Custody decisions are based on the best interests of the child, with Arizona courts strongly preferring joint legal custody. The length of your marriage (12 years) may also trigger spousal maintenance considerations. Have you and your spouse discussed the divorce, or is this unexpected for them?"},
            {"role": "user", "content": "We have not talked about it yet. Does it matter who files first?"},
        ],
        conversation_summary="User in Arizona considering divorce after 12-year marriage with two children (8 and 11). Community property state. Spouse has not been told yet. Asking about strategic first-filer advantage.",
        user_context={"jurisdiction": "arizona", "knowledge_level": "low"},
        expected_topics=["Family Law & Divorce"],
        relevance_keywords=["filing first", "divorce", "Arizona", "respondent", "petitioner", "advantage", "jurisdiction"],
    ),
]

# ---------------------------------------------------------------------------
# Category 4 — sa_guided (7 cases)
# Each has a self_assessment_context with priority_focus to test SA-adaptive retrieval.
# ---------------------------------------------------------------------------

_SA_GUIDED = [
    BenchmarkCase(
        id="A01",
        category="sa_guided",
        description="SA: False Knowledge — tenant believes no notice required in AZ",
        query="Can my landlord evict me without any warning if I'm two weeks late on rent?",
        self_assessment_context={
            "legal_domain": "tenant_rights",
            "jurisdiction": "arizona",
            "legal_situation": "Tenant is 2 weeks late on rent and fears immediate eviction.",
            "prior_experience": "Never dealt with eviction before.",
            "desired_outcome": "Understand eviction process and rights.",
            "baseline_familiarity": "low",
            "priority_focus": "Facts – False Knowledge",
            "evaluation_report": (
                "Facts [False Knowledge, Omission] — most critical gap: "
                "User incorrectly believes a landlord can evict immediately without notice."
            ),
        },
        expected_topics=["Tenant & Landlord Rights", "Housing & Real Estate"],
        relevance_keywords=["eviction", "notice", "5-day", "Arizona", "unlawful detainer"],
    ),
    BenchmarkCase(
        id="A02",
        category="sa_guided",
        description="SA: Omission — user unaware of AZ double-damage penalty",
        query="My landlord kept my deposit and won't explain why. What are my options?",
        self_assessment_context={
            "legal_domain": "tenant_rights",
            "jurisdiction": "arizona",
            "legal_situation": "Landlord withheld full $1,200 security deposit without itemization.",
            "prior_experience": "Never dealt with this before.",
            "desired_outcome": "Get deposit back.",
            "baseline_familiarity": "low",
            "priority_focus": "Facts – Omission",
            "evaluation_report": (
                "Facts [Omission] — most critical gap: "
                "User is unaware that Arizona law allows recovery of up to 2x the deposit "
                "if the landlord wrongfully withholds it."
            ),
        },
        expected_topics=["Tenant & Landlord Rights"],
        relevance_keywords=["double damages", "twice the amount", "ARS", "security deposit", "Arizona"],
    ),
    BenchmarkCase(
        id="A03",
        category="sa_guided",
        description="SA: Rationale Omission — user doesn't understand why written documentation matters",
        query="Does it really matter if I put everything in writing or can I just talk to my landlord?",
        self_assessment_context={
            "legal_domain": "tenant_rights",
            "jurisdiction": "texas",
            "legal_situation": "Disputes with landlord over repairs — user wants to handle verbally.",
            "prior_experience": "Some experience — had a landlord dispute 3 years ago.",
            "desired_outcome": "Get repairs done without conflict.",
            "baseline_familiarity": "medium",
            "priority_focus": "Rationales – Omission",
            "evaluation_report": (
                "Rationales [Omission] — most critical gap: "
                "User understands what to do but not why written records are legally essential — "
                "verbal agreements are nearly impossible to prove and waive specific rights."
            ),
        },
        expected_topics=["Tenant & Landlord Rights"],
        relevance_keywords=["written notice", "certified mail", "evidence", "verbal", "documentation"],
    ),
    BenchmarkCase(
        id="A04",
        category="sa_guided",
        description="SA: Know-Don't Know — user knows they have a case but unfamiliar with discovery",
        query="I know I have a strong wrongful termination case. What happens after I file the lawsuit?",
        self_assessment_context={
            "legal_domain": "employment_law",
            "jurisdiction": "california",
            "legal_situation": "Employee terminated after whistleblower complaint. Has strong documentation.",
            "prior_experience": "Has spoken with an attorney who confirmed a viable case.",
            "desired_outcome": "File lawsuit and win compensation.",
            "baseline_familiarity": "medium",
            "priority_focus": "Know-Don't Know",
            "evaluation_report": (
                "Know-Don't Know — most critical gap: "
                "User understands they have a case and has retained counsel, "
                "but has no knowledge of the litigation process — discovery, depositions, timelines."
            ),
        },
        expected_topics=["Employment & Labor Law"],
        relevance_keywords=["discovery", "deposition", "complaint", "litigation", "timeline", "EEOC"],
    ),
    BenchmarkCase(
        id="A05",
        category="sa_guided",
        description="SA: Strategies False Knowledge — user thinks hiring lawyer always helps in small claims",
        query="Should I hire a lawyer to help me win my small claims case?",
        self_assessment_context={
            "legal_domain": "small_claims",
            "jurisdiction": "california",
            "legal_situation": "User is suing a contractor for $3,200 in unfinished work.",
            "prior_experience": "No court experience.",
            "desired_outcome": "Recover $3,200.",
            "baseline_familiarity": "low",
            "priority_focus": "Strategies – False Knowledge",
            "evaluation_report": (
                "Strategies [False Knowledge] — most critical gap: "
                "User believes hiring an attorney for small claims court always improves chances, "
                "but attorneys are prohibited in California small claims court."
            ),
        },
        expected_topics=["Small Claims & Civil Disputes"],
        relevance_keywords=["small claims", "attorney", "California", "prohibited", "represent yourself"],
    ),
    BenchmarkCase(
        id="A06",
        category="sa_guided",
        description="SA: Procedure Omission — user unaware of mandatory mediation step",
        query="I'm ready to file my discrimination complaint. What's the first step?",
        self_assessment_context={
            "legal_domain": "employment_law",
            "jurisdiction": "arizona",
            "legal_situation": "Employee experienced racial discrimination at work over 8 months.",
            "prior_experience": "Has reported to HR, which took no action.",
            "desired_outcome": "File formal complaint and pursue legal action.",
            "baseline_familiarity": "medium",
            "priority_focus": "Procedures – Omission",
            "evaluation_report": (
                "Procedures [Omission] — most critical gap: "
                "User is unaware that before filing a federal discrimination lawsuit, "
                "a charge must first be filed with the EEOC, which may attempt mediation, "
                "and a Right to Sue letter must be obtained."
            ),
        },
        expected_topics=["Employment & Labor Law", "Civil Rights & Discrimination"],
        relevance_keywords=["EEOC", "charge", "mediation", "Right to Sue", "180 days", "filing"],
    ),
    BenchmarkCase(
        id="A07",
        category="sa_guided",
        description="SA: False Knowledge — user believes verbal employment contracts are unenforceable",
        query="I had a verbal promise from my employer about a bonus. Does that count for anything legally?",
        self_assessment_context={
            "legal_domain": "employment_law",
            "jurisdiction": "texas",
            "legal_situation": "Employer verbally promised a $5,000 annual bonus; never paid it.",
            "prior_experience": "No legal experience.",
            "desired_outcome": "Recover the promised bonus.",
            "baseline_familiarity": "low",
            "priority_focus": "Facts – False Knowledge",
            "evaluation_report": (
                "Facts [False Knowledge] — most critical gap: "
                "User incorrectly believes verbal promises have no legal standing — "
                "verbal contracts can be enforceable if offer, acceptance, and consideration are shown."
            ),
        },
        expected_topics=["Employment & Labor Law", "Business & Contract Law"],
        relevance_keywords=["verbal contract", "oral promise", "enforceable", "consideration", "offer", "acceptance"],
    ),
]

# ---------------------------------------------------------------------------
# Full dataset
# ---------------------------------------------------------------------------

BENCHMARK_DATASET: list[BenchmarkCase] = _SIMPLE + _COMPLEX + _MULTI_TURN + _SA_GUIDED

CATEGORIES = {
    "definitional_factual": [c for c in BENCHMARK_DATASET if c.category == "definitional_factual"],
    "full_legal_scenario": [c for c in BENCHMARK_DATASET if c.category == "full_legal_scenario"],
    "mid_conversation_anaphora": [c for c in BENCHMARK_DATASET if c.category == "mid_conversation_anaphora"],
    "sa_guided": [c for c in BENCHMARK_DATASET if c.category == "sa_guided"],
}
