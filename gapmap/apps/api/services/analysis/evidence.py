"""Ground excerpts and conservatively interpret self-reported resume claims."""

import re

from gapmap.apps.api.contracts import EvidenceStatus, ResumeEvidence


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def verified_excerpt(quote: str, document: str) -> str | None:
    """Return the original substring, allowing only whitespace differences."""
    normalized = normalize_whitespace(quote)
    if not normalized:
        return None
    pattern = r"\s+".join(re.escape(word) for word in normalized.split(" "))
    match = re.search(pattern, document)
    return match.group(0) if match else None


def skills_in_text(text: str) -> list[str]:
    """A deliberately small, inspectable taxonomy, grounded in the cited text."""
    sql_context = bool(re.search(
        r"\b(?:sql|postgres(?:ql)?|mysql|sqlite|databases?|relational|queries|querying|"
        r"tables?|revenue|where\s+clauses?|group\s+by)\b", text, re.I
    ))
    patterns = {
        "sql_joins": r"\bjoins?\b",
        "sql_filtering": r"\b(?:sql[_ ]filtering|where\s+clauses?|filter(?:ing)?\s+(?:rows|orders|queries))\b",
        "sql_aggregation": r"\b(?:aggregat(?:e|es|ion|ions|ing)|group\s+by)\b",
        "sql_refund_edge_cases": r"\b(?:refunds?|double[- ]count(?:ing)?|sql_refund_edge_cases)\b",
        "python": r"\bpython(?:\s*3)?\b",
        "react": r"\breact(?:\.js|js)?\b",
        "docker": r"\bdocker\b",
        "dsa": r"\b(?:dsa|data\s+structures?|algorithms?)\b",
    }
    found = [
        skill for skill, pattern in patterns.items()
        if re.search(pattern, text, re.I) and (not skill.startswith("sql_") or sql_context)
    ]
    if re.search(r"\b(?:sql|postgres(?:ql)?|mysql|sqlite|relational\s+(?:databases?|querying))\b", text, re.I):
        # Generic SQL means the project's basic relational query competencies;
        # refunds are included only when the posting explicitly mentions them.
        if not any(skill.startswith("sql_") for skill in found):
            found = ["sql_joins", "sql_filtering", "sql_aggregation", *found]
    return found


_USAGE = re.compile(
    r"\b(?:built|build|developed|implemented|used|using|wrote|written|created|"
    r"maintained|deployed|designed|tested|debugged|optimized|analysed|analyzed|"
    r"queried|worked|collaborated|experience|proficient|proficiency)\b", re.I
)
_NEGATION = re.compile(
    r"\b(?:no|not|never|without|lack|lacks|lacking|haven['’]t|hasn['’]t|"
    r"didn['’]t|don['’]t|doesn['’]t|can['’]t|cannot|learning|learn|beginner|"
    r"want\s+to|plan\s+to|hope\s+to|new\s+to)\b", re.I
)
_INSTRUCTION = re.compile(
    r"\b(?:ignore|instructions?|system\s*prompt|always\s+mark|mark\s+(?:every|all)|"
    r"verified|demonstrated|override|assistant|pretend)\b", re.I
)


def match_resume_evidence(
    proposed_quotes: list[str], resume_text: str, skill_ids: list[str], job_quote: str = ""
) -> list[ResumeEvidence]:
    evidence = []
    seen = set()
    for proposed in proposed_quotes:
        quote = verified_excerpt(proposed, resume_text)
        if quote is None or quote in seen:
            continue
        seen.add(quote)
        start = resume_text.find(quote)
        # Check the enclosing sentence as well: the model must not turn
        # "I have not used SQL" into a positive "used SQL" excerpt.
        left = max(resume_text.rfind(char, 0, start) for char in "\n.!?") + 1
        end = start + len(quote)
        boundaries = [resume_text.find(char, end) for char in "\n.!?"]
        right = min((pos for pos in boundaries if pos >= 0), default=len(resume_text))
        context = resume_text[left:right]
        if _NEGATION.search(context) or _INSTRUCTION.search(context):
            continue
        resume_skills = skills_in_text(quote)
        known_skills = set(skill_ids) - {"other"}
        if known_skills and not known_skills.intersection(resume_skills):
            continue
        if skill_ids == ["other"]:
            # Require shared substantive wording for skills outside the taxonomy.
            stopwords = {"experience", "required", "preferred", "skills", "strong", "with", "the", "and"}
            def terms(value: str) -> set[str]:
                return {
                    word[:8] for word in re.findall(r"[a-z]{4,}", value.lower())
                    if word not in stopwords
                }
            if not terms(quote).intersection(terms(job_quote)):
                continue
        contextual = bool(_USAGE.search(quote)) and len(quote.split()) >= 3
        evidence.append(ResumeEvidence(
            quote=quote, strength="contextual" if contextual else "keyword_only"
        ))
    return evidence


def initial_status(evidence: list[ResumeEvidence]) -> EvidenceStatus:
    if any(item.strength == "contextual" for item in evidence):
        return EvidenceStatus.RESUME_EVIDENCE
    return EvidenceStatus.UNVERIFIED
