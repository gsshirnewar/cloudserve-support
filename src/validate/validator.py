"""Pre-release validation and guardrails (T22).

Always-on checks before response release:
- PII/private-data scan (regex + rules)
- Groundedness/claim-support (rule-based citation overlap; optional LLM judge hook)
- Tone/policy (no promises/SLA/refund commitments, no blame)

Guardrails cannot be disabled in this module/path; callers may only tighten policy.
Any failed check blocks release and requires escalation.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from src.schemas import (
    Answer,
    Citation,
    Classification,
    GuardrailCheck,
    NormalisedTicket,
    RetrievalResult,
    RetrievedChunk,
    RouteDecision,
    Ticket,
    ValidationResult,
)

logger = logging.getLogger(__name__)

VALIDATOR_VERSION = "validator@t22-v1"

# --- PII / private-data patterns (regex + rules) ---
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}(?!\w)"
)
# Common API keys/tokens/secrets (heuristic, intentionally conservative for safety)
_SECRET_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("openai_like_key", re.compile(r"\bsk-[A-Za-z0-9]{16,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b")),
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("bearer_token", re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b", re.IGNORECASE)),
    ("jwt_like", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")),
    ("labeled_secret", re.compile(r"\b(?:api[_-]?key|secret|token|password|passwd|pwd)\b\s*[:=]\s*\S{6,}", re.IGNORECASE)),
    ("long_hex_secret", re.compile(r"\b[a-f0-9]{32,}\b", re.IGNORECASE)),
]
# Cross-customer / log / private data leakage indicators
_OTHER_CUSTOMER_RE = re.compile(
    r"\b(last|previous|another|other)\s+customer(?:'s)?\b|\bfrom\s+(?:our|the)\s+logs\b|\bcustomer\s+record\s+of\b",
    re.IGNORECASE,
)

# --- Tone/policy patterns ---
_PROMISE_SLA_REFUND_RE = re.compile(
    r"\b(i\s+promise|we\s+promise|guarantee(?:d)?|refund\s+(?:approved|issued|processed|will\s+be|is\s+approved)|"
    r"we\s+will\s+(?:definitely|certainly)\s+(?:refund|fix|resolve)|sla\b|service[- ]level\s+agreement|"
    r"within\s+\d+\s*(?:minute|hour|day|business\s+day)s?\s+we\s+will|100%\s+(?:uptime|guaranteed|resolution))\b",
    re.IGNORECASE,
)
_BLAME_RE = re.compile(
    r"\b(your\s+fault|you\s+caused|it's\s+your\s+mistake|user\s+error\s+on\s+your\s+part|you\s+messed\s+up)\b",
    re.IGNORECASE,
)
_SYSTEM_PROMPT_LEAK_RE = re.compile(
    r"\b(system\s+prompt|developer\s+message|internal\s+instructions|reveal\s+your\s+prompt)\b",
    re.IGNORECASE,
)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "to", "of", "in", "on", "for", "with", "by",
    "is", "are", "was", "were", "be", "been", "being", "as", "at", "from", "that", "this", "it",
    "you", "your", "we", "our", "their", "they", "i", "can", "will", "should", "may", "not", "no",
}


@dataclass(frozen=True)
class GuardrailPolicy:
    """Tightening-only guardrail policy.

    Guardrails are always enabled. These options can only add stricter checks.
    """

    always_enabled: bool = True
    allow_disable: bool = False  # ignored/forbidden by design
    extra_disallowed_patterns: Tuple[str, ...] = ()
    require_citations_for_answer_actions: bool = True
    min_claim_overlap_ratio: float = 0.08
    min_claim_overlap_tokens: int = 2

    def __post_init__(self) -> None:
        # Enforce non-bypassable guardrails regardless of caller input.
        object.__setattr__(self, "always_enabled", True)
        object.__setattr__(self, "allow_disable", False)

    @classmethod
    def tightened(cls, base: Optional["GuardrailPolicy"] = None, **kwargs: Any) -> "GuardrailPolicy":
        b = base or cls()
        merged = {
            "extra_disallowed_patterns": tuple(
                dict.fromkeys(list(b.extra_disallowed_patterns) + list(kwargs.pop("extra_disallowed_patterns", ())))
            ),
            "require_citations_for_answer_actions": bool(
                b.require_citations_for_answer_actions or kwargs.pop("require_citations_for_answer_actions", False)
            ),
            "min_claim_overlap_ratio": max(float(b.min_claim_overlap_ratio), float(kwargs.pop("min_claim_overlap_ratio", b.min_claim_overlap_ratio))),
            "min_claim_overlap_tokens": max(int(b.min_claim_overlap_tokens), int(kwargs.pop("min_claim_overlap_tokens", b.min_claim_overlap_tokens))),
        }
        # Any unknown kwargs treated as tightening intent ignored except explicit deny patterns above.
        return cls(**merged)


def _ticket_id(ticket: Any, answer: Optional[Answer]) -> str:
    if answer and getattr(answer, "ticket_id", None):
        return str(answer.ticket_id)
    if ticket is None:
        return "unknown-ticket"
    if isinstance(ticket, dict):
        return str(ticket.get("ticket_id") or ticket.get("id") or "unknown-ticket")
    return str(getattr(ticket, "ticket_id", None) or getattr(ticket, "id", None) or "unknown-ticket")


def _iter_answer_texts(answer: Answer) -> Iterable[str]:
    if answer.answer_text:
        yield answer.answer_text
    for claim in answer.claims or []:
        if isinstance(claim, dict):
            for k in ("text", "claim", "value", "content", "statement"):
                v = claim.get(k)
                if isinstance(v, str) and v.strip():
                    yield v
        elif isinstance(claim, str) and claim.strip():
            yield claim
    raw = answer.raw_output or {}
    if isinstance(raw, dict):
        for k in ("answer", "answer_text", "response", "escalation_summary", "recommended_next_action", "customer_safe_update", "summary"):
            v = raw.get(k)
            if isinstance(v, str) and v.strip():
                yield v
        for list_key in ("facts", "key_facts", "unknowns", "actions_taken", "uncertainty_factors", "open_questions", "missing_information"):
            v = raw.get(list_key)
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, str) and item.strip():
                        yield item


def _tokenize(text: str) -> Set[str]:
    tokens = re.findall(r"[a-z0-9][a-z0-9_-]*", (text or "").lower())
    return {t for t in tokens if len(t) > 2 and t not in _STOPWORDS}


def _chunk_map(retrieval: Optional[RetrievalResult]) -> Dict[str, RetrievedChunk]:
    out: Dict[str, RetrievedChunk] = {}
    if not retrieval:
        return out
    for hit in retrieval.hits or []:
        if hit.chunk_id:
            out[hit.chunk_id] = hit
        # also allow doc_id#chunk_id form
        if hit.doc_id and hit.chunk_id:
            if "#" in hit.chunk_id:
                out[hit.chunk_id] = hit
            else:
                out[f"{hit.doc_id}#{hit.chunk_id}"] = hit
    return out


def _is_citation_resolvable(citation: Citation, cmap: Dict[str, RetrievedChunk]) -> bool:
    cid = citation.chunk_id or ""
    if cid in cmap:
        return True
    if citation.doc_id and cid and f"{citation.doc_id}#{cid}" in cmap:
        return True
    # fallback: any chunk for doc_id
    return any(h.doc_id == citation.doc_id for h in cmap.values()) if citation.doc_id else False


def _resolve_citation_text(citation: Citation, cmap: Dict[str, RetrievedChunk]) -> str:
    cid = citation.chunk_id or ""
    chunk = cmap.get(cid) or cmap.get(f"{citation.doc_id}#{cid}")
    if chunk:
        return chunk.text or ""
    # doc-level fallback: concatenate chunks from same doc
    if citation.doc_id:
        parts = [h.text for h in cmap.values() if h.doc_id == citation.doc_id and h.text]
        if parts:
            return "\n".join(parts)
    return ""


class ResponseValidator:
    """Always-on pre-release validator (T22)."""

    def __init__(self, policy: Optional[GuardrailPolicy] = None, provider: Any = None):
        # Never accept a policy that disables checks.
        self.policy = policy or GuardrailPolicy()
        if getattr(self.policy, "allow_disable", False) or not getattr(self.policy, "always_enabled", True):
            self.policy = GuardrailPolicy(
                extra_disallowed_patterns=getattr(self.policy, "extra_disallowed_patterns", ()),
                require_citations_for_answer_actions=getattr(self.policy, "require_citations_for_answer_actions", True),
                min_claim_overlap_ratio=getattr(self.policy, "min_claim_overlap_ratio", 0.08),
                min_claim_overlap_tokens=getattr(self.policy, "min_claim_overlap_tokens", 2),
            )
        self.provider = provider  # optional LLM judge hook (not required)

    def validate(
        self,
        answer: Answer,
        ticket: Optional[Any] = None,
        classification: Optional[Classification] = None,
        retrieval: Optional[RetrievalResult] = None,
        route: Optional[RouteDecision] = None,
        *,
        provider: Any = None,
        llm_judge: bool = False,
    ) -> ValidationResult:
        tid = _ticket_id(ticket, answer)
        texts = list(_iter_answer_texts(answer))
        joined = "\n".join(texts)

        checks: List[GuardrailCheck] = []
        findings: List[Dict[str, Any]] = []

        pii_check, pii_findings, pii_detected = self._check_pii_private_data(joined)
        checks.append(pii_check)
        findings.extend(pii_findings)

        grounded_check, grounded_findings, unsupported = self._check_groundedness_claim_support(
            answer=answer,
            retrieval=retrieval,
            texts=texts,
            provider=provider or self.provider,
            llm_judge=llm_judge,
        )
        checks.append(grounded_check)
        findings.extend(grounded_findings)

        tone_check, tone_findings = self._check_tone_policy(joined)
        checks.append(tone_check)
        findings.extend(tone_findings)

        failed = [c.name for c in checks if not c.passed]
        passed = len(failed) == 0
        blocked = not passed
        action: str = "allow" if passed else "escalate"  # blocked + escalated on any failure

        result = ValidationResult(
            ticket_id=tid,
            passed=passed,
            blocked=blocked,
            action=action,  # type: ignore[arg-type]
            checks=checks,
            findings=findings,
            pii_detected=pii_detected,
            unsupported_claims_detected=unsupported,
            validator_version=VALIDATOR_VERSION,
        )

        # Structured per-check logging (no PII values logged)
        for c in checks:
            logger.info(
                "guardrail_check",
                extra={
                    "ticket_id": tid,
                    "check": c.name,
                    "passed": c.passed,
                    "severity": c.severity,
                    "blocked": blocked,
                    "evidence_counts": {k: (len(v) if isinstance(v, list) else v) for k, v in (c.evidence or {}).items()},
                },
            )
        if blocked:
            logger.warning(
                "guardrail_blocked",
                extra={"ticket_id": tid, "failed_checks": failed, "action": action},
            )
        return result

    # --- (a) PII/private data scan ---
    def _check_pii_private_data(self, text: str) -> Tuple[GuardrailCheck, List[Dict[str, Any]], bool]:
        findings: List[Dict[str, Any]] = []
        evidence: Dict[str, Any] = {"match_types": [], "counts": {}}

        def add(match_type: str, severity: str, detail: str, count: int = 1) -> None:
            findings.append({
                "check": "pii_scan",
                "type": match_type,
                "severity": severity,
                "detail": detail,
                "count": count,
            })
            evidence["match_types"].append(match_type)
            evidence["counts"][match_type] = evidence["counts"].get(match_type, 0) + count

        emails = _EMAIL_RE.findall(text or "")
        if emails:
            add("email", "high", "Email address detected in outgoing response", len(emails))
        phones = [m.group(0) for m in _PHONE_RE.finditer(text or "") if len(re.sub(r"\D", "", m.group(0))) >= 7]
        if phones:
            add("phone", "high", "Phone-number-like value detected in outgoing response", len(phones))
        for name, pat in _SECRET_PATTERNS:
            matches = pat.findall(text or "")
            if matches:
                sev = "critical" if name in {"labeled_secret", "openai_like_key", "bearer_token", "jwt_like"} else "high"
                add(name, sev, "Potential secret/token/credential detected in outgoing response", len(matches))
        if _OTHER_CUSTOMER_RE.search(text or ""):
            add("other_customer_data", "high", "Potential cross-customer/private log data reference detected", 1)
        if _SYSTEM_PROMPT_LEAK_RE.search(text or ""):
            add("system_prompt_leak", "high", "Potential system/internal prompt disclosure content detected", 1)
        # Tightening-only extra patterns
        for i, pat_str in enumerate(self.policy.extra_disallowed_patterns):
            try:
                if re.search(pat_str, text or "", re.IGNORECASE):
                    add(f"extra_disallowed_{i}", "high", "Disallowed pattern matched (tightened policy)", 1)
            except re.error:
                continue

        detected = len(findings) > 0
        check = GuardrailCheck(
            name="pii_scan",
            passed=not detected,
            severity="critical" if detected else "info",
            details="PII/private data detected" if detected else "No PII/private data detected",
            evidence=evidence,
        )
        return check, findings, detected

    # --- (b) Groundedness / claim-support ---
    def _check_groundedness_claim_support(
        self,
        answer: Answer,
        retrieval: Optional[RetrievalResult],
        texts: Sequence[str],
        provider: Any = None,
        llm_judge: bool = False,
    ) -> Tuple[GuardrailCheck, List[Dict[str, Any]], bool]:
        findings: List[Dict[str, Any]] = []
        evidence: Dict[str, Any] = {"issues": [], "counts": {}}
        cmap = _chunk_map(retrieval)
        has_retrieval = bool(retrieval and retrieval.hits)

        def add(issue: str, severity: str, detail: str) -> None:
            findings.append({"check": "groundedness_claim_support", "type": issue, "severity": severity, "detail": detail})
            evidence["issues"].append(issue)
            evidence["counts"][issue] = evidence["counts"].get(issue, 0) + 1

        citations = list(answer.citations or [])
        valid_citations = [c for c in citations if _is_citation_resolvable(c, cmap)]
        invalid_citations = [c for c in citations if not _is_citation_resolvable(c, cmap)]
        if invalid_citations:
            add("unresolvable_citation", "high", f"{len(invalid_citations)} citation(s) do not resolve to retrieved evidence")

        action = getattr(answer, "action", "abstain")
        substantive = action in {"answer", "assist_draft"} and bool((answer.answer_text or "").strip() or answer.claims)

        # Require valid citations for substantive grounded actions when evidence is present/required.
        if substantive and self.policy.require_citations_for_answer_actions and has_retrieval and not valid_citations:
            add("missing_citation", "high", "Substantive answer/assist_draft lacks valid citations to retrieved evidence")
        if substantive and not has_retrieval and (citations or (answer.answer_text or "").strip()):
            add("no_evidence_support", "high", "Substantive response produced without retrieved evidence")

        # Claim-level support (rule-based overlap)
        claims = list(answer.claims or [])
        for idx, claim in enumerate(claims):
            claim_text = ""
            claim_citation_ids: List[str] = []
            if isinstance(claim, dict):
                claim_text = str(claim.get("text") or claim.get("claim") or claim.get("value") or "")
                cits = claim.get("citations") or claim.get("citation_ids") or claim.get("chunk_ids") or []
                if isinstance(cits, list):
                    claim_citation_ids = [str(x) for x in cits if x is not None]
                elif isinstance(cits, str):
                    claim_citation_ids = [cits]
            elif isinstance(claim, str):
                claim_text = claim
            if not claim_text.strip():
                continue
            # Determine support text: cited chunks for this claim, else all valid cited chunks, else none
            support_texts: List[str] = []
            if claim_citation_ids:
                for cid in claim_citation_ids:
                    cobj = next((c for c in citations if c.citation_id == cid or c.chunk_id == cid), None)
                    if cobj:
                        st = _resolve_citation_text(cobj, cmap)
                        if st:
                            support_texts.append(st)
            if not support_texts and valid_citations:
                for c in valid_citations:
                    st = _resolve_citation_text(c, cmap)
                    if st:
                        support_texts.append(st)
            support = "\n".join(support_texts)
            if not support:
                add("unsupported_claim", "high", f"Claim {idx} has no resolvable supporting evidence")
                continue
            c_tokens = _tokenize(claim_text)
            s_tokens = _tokenize(support)
            overlap = c_tokens & s_tokens
            ratio = (len(overlap) / len(c_tokens)) if c_tokens else 0.0
            if len(overlap) < self.policy.min_claim_overlap_tokens or ratio < self.policy.min_claim_overlap_ratio:
                add("weak_claim_support", "medium", f"Claim {idx} has weak lexical overlap with cited evidence")

        # If no structured claims but substantive answer text exists, require at least lexical grounding to some evidence
        if substantive and not claims and has_retrieval and valid_citations and (answer.answer_text or "").strip():
            support = "\n".join(_resolve_citation_text(c, cmap) for c in valid_citations)
            a_tokens = _tokenize(answer.answer_text)
            s_tokens = _tokenize(support)
            overlap = a_tokens & s_tokens
            ratio = (len(overlap) / len(a_tokens)) if a_tokens else 0.0
            if len(overlap) < max(3, self.policy.min_claim_overlap_tokens) or ratio < self.policy.min_claim_overlap_ratio:
                add("weak_answer_support", "medium", "Answer text has weak lexical support from cited evidence")

        # Optional LLM judge hook (tightening/secondary signal only when explicitly requested and provider available)
        if llm_judge and provider is not None and substantive and not findings:
            # Keep deterministic-safe: if judge call fails, do not weaken/block solely on infra failure.
            try:
                # Minimal hook; concrete prompt/judging can be wired in T23+ if needed.
                pass
            except Exception:
                logger.info("llm_judge_skipped", extra={"ticket_id": answer.ticket_id, "reason": "judge_error"})

        unsupported = any(f.get("type") in {"unsupported_claim", "unresolvable_citation", "missing_citation", "no_evidence_support", "weak_claim_support", "weak_answer_support"} for f in findings)
        passed = not unsupported
        check = GuardrailCheck(
            name="groundedness_claim_support",
            passed=passed,
            severity="high" if not passed else "info",
            details="Groundedness/claim-support check failed" if not passed else "Groundedness/claim-support check passed",
            evidence=evidence,
        )
        return check, findings, unsupported

    # --- (c) Tone/policy ---
    def _check_tone_policy(self, text: str) -> Tuple[GuardrailCheck, List[Dict[str, Any]]]:
        findings: List[Dict[str, Any]] = []
        evidence: Dict[str, Any] = {"issues": [], "counts": {}}

        def add(issue: str, severity: str, detail: str, count: int = 1) -> None:
            findings.append({"check": "tone_policy", "type": issue, "severity": severity, "detail": detail, "count": count})
            evidence["issues"].append(issue)
            evidence["counts"][issue] = evidence["counts"].get(issue, 0) + count

        if _PROMISE_SLA_REFUND_RE.search(text or ""):
            m = _PROMISE_SLA_REFUND_RE.findall(text or "")
            add("promise_sla_refund", "high", "Response contains promise/SLA/refund commitment language", len(m) if isinstance(m, list) else 1)
        if _BLAME_RE.search(text or ""):
            m = _BLAME_RE.findall(text or "")
            add("blame_language", "medium", "Response contains blame/shaming language", len(m) if isinstance(m, list) else 1)

        passed = len(findings) == 0
        check = GuardrailCheck(
            name="tone_policy",
            passed=passed,
            severity="high" if not passed else "info",
            details="Tone/policy check failed" if not passed else "Tone/policy check passed",
            evidence=evidence,
        )
        return check, findings


def validate_before_release(
    answer: Answer,
    ticket: Optional[Any] = None,
    classification: Optional[Classification] = None,
    retrieval: Optional[RetrievalResult] = None,
    route: Optional[RouteDecision] = None,
    *,
    provider: Any = None,
    policy: Optional[GuardrailPolicy] = None,
) -> ValidationResult:
    """Always-on release validation entrypoint (no disable flag)."""
    validator = ResponseValidator(policy=policy, provider=provider)
    return validator.validate(answer=answer, ticket=ticket, classification=classification, retrieval=retrieval, route=route, provider=provider)


def build_blocked_escalation_answer(
    ticket_id: str,
    validation: ValidationResult,
    base_answer: Optional[Answer] = None,
    reason_prefix: str = "Blocked by pre-release guardrails",
) -> Answer:
    """Create an escalation-safe answer artifact when validation blocks release."""
    failed = [c.name for c in (validation.checks or []) if not c.passed]
    reasons = [f"{f.get('type')}: {f.get('detail')}" for f in (validation.findings or [])[:8] if isinstance(f, dict)]
    text_lines = [
        f"{reason_prefix}. The draft response was not released.",
        f"Failed checks: {', '.join(failed) if failed else 'unknown'}.",
    ]
    if reasons:
        text_lines.append("Findings: " + " | ".join(reasons))
    text_lines.append("Action: escalate for human/agent review with safe context only.")
    return Answer(
        ticket_id=ticket_id,
        action="escalate_recommendation",
        answer_text="\n".join(text_lines),
        claims=[],
        citations=[],
        confidence=0.0,
        unknown_or_insufficient_evidence=True,
        prompt_version=(base_answer.prompt_version if base_answer else None),
        model_name=(base_answer.model_name if base_answer else None),
        raw_output={
            "blocked": True,
            "guardrail_failed_checks": failed,
            "validation": validation.model_dump(mode="json"),
        },
    )
