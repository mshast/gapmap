"""Structured job extraction followed by deterministic evidence mapping."""

import os
import re
from importlib.resources import files

from pydantic import ValidationError

from gapmap.apps.api.contracts import AnalyzeRequest, Requirement, VerificationCapability
from gapmap.apps.api.fixtures.loader import load_demo_fixture
from gapmap.apps.api.services.analysis.evidence import (
    clean_label, initial_status, match_resume_evidence, normalize_whitespace, requirement_skills,
    skills_in_text, verified_excerpt,
)
from gapmap.apps.api.services.analysis.llm_client import ExtractionError, Extractor, StructuredLLMClient
from gapmap.apps.api.services.analysis.ollama_client import OllamaStructuredClient
from gapmap.apps.api.services.analysis.matcher import apply_coverage, build_roadmap, select_project
from gapmap.apps.api.services.analysis.plans import plans_for
from gapmap.apps.api.services.analysis.schema import AnalysisResult, ExtractionResult
from gapmap.apps.api.services.interfaces import AnalysisUnavailableError


class StructuredAnalysisService:
    def __init__(self, *, extractor: Extractor | None = None, demo_mode: bool = False) -> None:
        self._extractor = extractor
        self._demo_mode = demo_mode

    @classmethod
    def from_env(cls) -> "StructuredAnalysisService":
        provider = os.environ.get("GAPMAP_LLM_PROVIDER", "openai").strip().lower()
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        if provider == "groq":
            key = os.environ.get("GROQ_API_KEY", "").strip()
            model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
            extractor = StructuredLLMClient(
                key, model, base_url="https://api.groq.com/openai/v1/chat/completions"
            ) if key else None
        elif provider == "ollama":
            extractor: Extractor | None = OllamaStructuredClient(
                os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                os.environ.get("OLLAMA_MODEL", "qwen2.5:3b").strip() or "qwen2.5:3b",
            )
        elif provider == "openai":
            extractor = StructuredLLMClient(key, model) if key else None
        elif provider == "demo":
            extractor = None
        else:
            raise ValueError(f"Unsupported GAPMAP_LLM_PROVIDER: {provider}")
        return cls(
            extractor=extractor,
            demo_mode=os.environ.get("GAPMAP_DEMO_MODE", "").lower() in {"1", "true", "yes"},
        )

    async def analyze(self, resume_text: str, job_text: str) -> AnalysisResult:
        # Validate even direct Python callers, before normalization or provider use.
        request = AnalyzeRequest(resume_text=resume_text, job_description=job_text)
        resume_text = request.resume_text.replace("\r\n", "\n").replace("\r", "\n")
        job_text = request.job_description.replace("\r\n", "\n").replace("\r", "\n")
        warnings = [
            "Resume claims are self-reported, not independently verified. Project results "
            "cover only this work sample; this analysis is not a hiring or job-fit prediction."
        ]
        if self._demo_mode:
            extracted = self._demo_extraction(resume_text, job_text)
            warnings.insert(0, "Deterministic demo fixture: no AI service ran. Only the bundled posting is supported.")
        else:
            if self._extractor is None:
                raise AnalysisUnavailableError(
                    "Analysis is not configured. Set OPENAI_API_KEY or GROQ_API_KEY for a hosted provider, or run Ollama with "
                    "GAPMAP_LLM_PROVIDER=ollama, or alternatively set "
                    "GAPMAP_DEMO_MODE=1 and use GET /api/demo/fixture."
                )
            try:
                proposed = await self._extractor.extract(resume_text, job_text)
                extracted = ExtractionResult.model_validate(
                    proposed.model_dump() if isinstance(proposed, ExtractionResult) else proposed
                )
            except (ExtractionError, ValidationError):
                raise AnalysisUnavailableError(
                    "AI extraction failed or returned invalid data. Check the server API key/model "
                    "and try again with a complete internship posting. For the bundled offline "
                    "fixture, explicitly enable GAPMAP_DEMO_MODE=1."
                ) from None

        requirements = []
        seen = set()
        # Re-establish original job order even if the model reorders requirements.
        normalized_job = normalize_whitespace(job_text)
        ordered = sorted(extracted.requirements, key=lambda item: (
            normalized_job.find(normalize_whitespace(item.job_quote))
        ))
        ids: dict[str, int] = {}
        ideas = {}
        dropped_quotes = False
        for item in ordered:
            job_quote = verified_excerpt(item.job_quote, job_text)
            if job_quote is None or normalize_whitespace(job_quote) in seen:
                dropped_quotes = True
                continue
            seen.add(normalize_whitespace(job_quote))
            # Reconcile model tags against the actual excerpt. This also preserves
            # uncovered skills in mixed SQL/React requirements.
            skill_ids = requirement_skills(job_quote)
            if "other" in item.skill_ids and skill_ids != ["eligibility"] and "other" not in skill_ids:
                skill_ids.append("other")
            evidence = match_resume_evidence(item.resume_quotes, resume_text, skill_ids, job_quote)
            if len(evidence) < len(item.resume_quotes):
                dropped_quotes = True
            base = "sql" if skill_ids[0].startswith("sql_") else skill_ids[0]
            if base in {"other", "eligibility"}:
                base = f"{base}-{len(requirements) + 1}"
            ids[base] = ids.get(base, 0) + 1
            suffix = f"-{ids[base]}" if ids[base] > 1 else ""
            requirements.append(Requirement(
                id=f"req-{base}{suffix}", label=clean_label(item.label), job_quote=job_quote,
                importance=item.importance, requirement_type=item.requirement_type,
                skill_ids=skill_ids,
                resume_quotes=[claim.quote for claim in evidence if claim.strength == "contextual"],
                resume_evidence=evidence, evidence_status=initial_status(evidence),
                verification_capability=VerificationCapability.NOT_ASSESSABLE,
            ))
            ideas[requirements[-1].id] = item.project_idea

        if len(requirements) < 5:
            raise AnalysisUnavailableError(
                "Fewer than five distinct requirements could be grounded in the posting. "
                "Paste the complete internship posting and retry; unsupported excerpts were discarded."
            )
        if dropped_quotes:
            warnings.append("Unsupported, duplicate, negative, or unrelated proposed excerpts were discarded.")
        project = select_project(requirements)
        for requirement in requirements:
            apply_coverage(requirement, project)
            requirement.project_plans = plans_for(requirement, project, ideas[requirement.id])
        target_role = verified_excerpt(extracted.target_role, job_text) or "Software Engineering Intern"
        return AnalysisResult(
            target_role=target_role, requirements=requirements,
            recommended_project_id=project.id if project else None,
            roadmap=build_roadmap(requirements),
            analysis_mode="demo" if self._demo_mode else "llm", warnings=warnings,
        )

    @staticmethod
    def _demo_extraction(resume_text: str, job_text: str) -> ExtractionResult:
        fixture = load_demo_fixture()
        if normalize_whitespace(job_text) != normalize_whitespace(fixture.job_description):
            raise AnalysisUnavailableError(
                "Demo mode supports only the bundled posting from GET /api/demo/fixture. "
                "For other postings, disable GAPMAP_DEMO_MODE and configure OPENAI_API_KEY on the server."
            )
        data = files("gapmap.apps.api.services.analysis.fixtures").joinpath("demo_extraction.json")
        extracted = ExtractionResult.model_validate_json(data.read_text(encoding="utf-8"))
        # Only propose actual input substrings. The live evidence checks decide
        # whether each line is contextual, weak, or unsupported.
        lines = [line.strip() for line in re.split(r"[\r\n]+", resume_text) if line.strip()]
        for requirement in extracted.requirements:
            skill_ids = [str(skill) for skill in requirement.skill_ids]
            candidates = [line for line in lines if (
                set(skills_in_text(line)).intersection(skill_ids)
                or ("other" in skill_ids and re.search(r"\bcollaborat\w*", line, re.I))
            ) and len(line) <= 400]
            requirement.resume_quotes = candidates[:4]
        return extracted
