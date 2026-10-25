"""Ground excerpts and conservatively interpret self-reported resume claims."""

import html
import re

from gapmap.apps.api.contracts import EvidenceStatus, ResumeEvidence


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


_MARKUP = re.compile(r"</?[a-z][a-z0-9]*(?:\s[^<>]*)?/?>|&(?:[a-z]+|#\d+|#x[0-9a-f]+);", re.I)


def clean_pasted_text(text: str) -> str:
    """Turn HTML pasted from a careers page into plain text.

    Models decode entities like &amp; when they quote, so excerpts only
    ground against a document that is already plain text.
    """
    if not _MARKUP.search(text):
        return text
    text = re.sub(r"<li\b[^>]*>", "\n- ", text, flags=re.I)
    text = re.sub(r"<br\s*/?>|</(?:p|div|li|h[1-6]|tr|ul|ol)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^<>]+>", "", text)
    text = html.unescape(text).replace("\xa0", " ")
    lines = [" ".join(line.split()) for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


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
        r"tables?|revenue|reconcil\w*|where\s+clauses?|group\s+by)\b", text, re.I
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
        "java": r"\bjava\b",
        "cpp": r"(?<![\w+])c\+\+|\bcpp\b",
        "csharp": r"(?<!\w)c#|\bc\s+sharp\b|(?<!\w)\.net\b",
        "javascript": r"\b(?:javascript|node\.?js|js)\b",
        "typescript": r"\btypescript\b",
        "cloud": r"\b(?:aws|amazon\s+web\s+services|gcp|google\s+cloud|azure|"
                 r"cloud\s+(?:platforms?|services|computing|infrastructure))\b",
        "git": r"\b(?:git|github|gitlab|version\s+control)\b",
        "apis": r"\b(?:rest(?:ful)?\s+(?:apis?|services|endpoints)|restful|apis?|graphql|microservices)\b",
        "testing": r"\b(?:unit\s+tests?|integration\s+tests?|automated\s+tests?|testing|"
                   r"test[- ]driven|tdd|pytest|junit|jest)\b",
        "machine_learning": r"\b(?:machine\s+learning|ml|deep\s+learning|pytorch|tensorflow|"
                            r"scikit[- ]learn|llms?)\b",
        "linux": r"\b(?:linux|unix|bash|shell\s+scripting)\b",
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


_ELIGIBILITY = re.compile(
    r"\b(?:bachelor['’]?s?|master['’]?s?|ph\.?\s?d|undergraduate|degree(?!\s+of)|"
    r"graduat(?:e|es|ing|ion)|class\s+of|enrolled|pursuing|gpa|"
    r"work\s+authori[sz]ation|authori[sz]ed\s+to\s+work|sponsorship|visa|citizen(?:ship)?|"
    r"security\s+clearance|relocat\w*|on[- ]?site|in[- ]office|hybrid|"
    r"available\s+(?:to\s+start|to\s+work|for)|\d+\s+hours\s+(?:per|a|each)\s+week)\b"
    r"|(?<!\w)(?:b\.?s|b\.?a)(?:\.|(?!\w))", re.I
)


def is_eligibility(text: str) -> bool:
    """Degree, graduation, authorization, or location conditions, not skills."""
    return bool(_ELIGIBILITY.search(text))


def requirement_skills(job_quote: str) -> list[str]:
    """Skills for a grounded excerpt; eligibility only when no skill is named."""
    found = skills_in_text(job_quote)
    if found:
        return found
    return ["eligibility"] if is_eligibility(job_quote) else ["other"]


def strip_list_marker(quote: str) -> str:
    """Drop a leading bullet or list number; the rest is still a verbatim substring."""
    return re.sub(r"^\s*(?:[-*•·–]|\d{1,2}[.)])\s+", "", quote) or quote


def clean_label(label: str) -> str:
    """Drop dates from labels: 'Bachelor's 2028' names a degree, not a skill."""
    cleaned = re.sub(r"\(?\b(?:19|20)\d{2}\b\)?", " ", label)
    cleaned = normalize_whitespace(re.sub(r"\s+([,;:])", r"\1", cleaned)).strip(" ,;:-–—/")
    return cleaned or label


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


def _matches_eligibility_fact(resume_quote: str, job_quote: str) -> bool:
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", job_quote))
    if not years.intersection(re.findall(r"\b(?:19|20)\d{2}\b", resume_quote)):
        return False
    job_is_graduation = re.search(r"\b(?:graduat(?:e|ion)|class\s+of|degree|ba|bs)\b", job_quote, re.I)
    resume_is_graduation = re.search(
        r"\b(?:graduat(?:e|ion)|class\s+of|degree|expected|education|ba|bs)\b", resume_quote, re.I
    )
    return bool(job_is_graduation and resume_is_graduation)


def match_resume_evidence(
    proposed_quotes: list[str], resume_text: str, skill_ids: list[str], job_quote: str = ""
) -> list[ResumeEvidence]:
    evidence = []
    seen = set()
    for proposed in proposed_quotes:
        quote = verified_excerpt(proposed, resume_text)
        if quote is not None:
            quote = strip_list_marker(quote)
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
        known_skills = set(skill_ids) - {"other", "eligibility"}
        if known_skills and not known_skills.intersection(resume_skills):
            continue
        if not known_skills:
            # Require shared substantive wording for skills outside the taxonomy.
            stopwords = {"experience", "required", "preferred", "skills", "strong", "with", "the", "and"}
            def terms(value: str) -> set[str]:
                return {
                    word[:8] for word in re.findall(r"[a-z]{4,}", value.lower())
                    if word not in stopwords
                }
            if not terms(quote).intersection(terms(job_quote)) and not _matches_eligibility_fact(quote, job_quote):
                continue
        contextual = (
            bool(_USAGE.search(quote)) and len(quote.split()) >= 3
        ) or _matches_eligibility_fact(quote, job_quote)
        evidence.append(ResumeEvidence(
            quote=quote, strength="contextual" if contextual else "keyword_only"
        ))
    return evidence


def initial_status(evidence: list[ResumeEvidence]) -> EvidenceStatus:
    if any(item.strength == "contextual" for item in evidence):
        return EvidenceStatus.RESUME_EVIDENCE
    return EvidenceStatus.UNVERIFIED
