"""Layer 2 (detection half): profile-grounded verifier.

The plan PDF specifies a hybrid verifier: a deterministic rule layer for hard
constraints (e.g., dietary class, accessibility, currency) plus an LLM layer for
soft / open-ended checks. We expose three modes: ``rule``, ``llm``, ``combined``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .models import ChatProvider
from .prompts import VERIFIER_SYSTEM, verifier_user
from .schemas import Severity, Trajectory, UserProfile, VerifierResult, ViolationEvent

RuleFn = Callable[[UserProfile, dict[str, Any], Trajectory, str | None], list[ViolationEvent]]


@dataclass
class HybridVerifier:
    """Combines rule-based and LLM-based checks.

    * ``rules`` is a list of pure-Python functions; each returns a (possibly empty)
      list of `ViolationEvent`s for a (profile, task, trajectory, final_output) tuple.
    * If `provider` is set, the LLM verifier prompt is also called and the unions
      of violations is returned (deduplicated by step_id × violated span).
    """

    rules: list[RuleFn]
    provider: ChatProvider | None = None
    model: str = ""
    temperature: float = 0.0
    seed: int | None = None

    def check(
        self,
        *,
        profile: UserProfile,
        task: dict[str, Any],
        trajectory: Trajectory,
        final_output: str | None = None,
    ) -> tuple[VerifierResult, dict[str, Any]]:
        violations: list[ViolationEvent] = []
        meta: dict[str, Any] = {"sources": []}

        for fn in self.rules:
            v = fn(profile, task, trajectory, final_output)
            if v:
                meta["sources"].append({"rule": fn.__name__, "n": len(v)})
                violations.extend(v)

        if self.provider is not None and self.model:
            user = verifier_user(
                profile=profile.model_dump(mode="json"),
                task=task,
                trajectory=trajectory.model_dump(mode="json"),
                final_output=final_output,
            )
            payload, completion = self.provider.complete_json(
                system=VERIFIER_SYSTEM,
                user=user,
                model=self.model,
                temperature=self.temperature,
                seed=self.seed,
            )
            try:
                llm_result = VerifierResult.model_validate(payload)
            except Exception as e:  # pragma: no cover - logged for debugging
                meta["llm_parse_error"] = str(e)
                llm_result = VerifierResult(**{"pass": True, "violations": []})  # type: ignore[arg-type]
            meta["llm_tokens_input"] = completion.tokens_input
            meta["llm_tokens_output"] = completion.tokens_output
            meta["sources"].append({"rule": "llm", "n": len(llm_result.violations)})
            violations.extend(llm_result.violations)

        violations = _dedupe(violations)
        passed = len(violations) == 0
        return VerifierResult(**{"pass": passed, "violations": violations}), meta  # type: ignore[arg-type]


def _dedupe(violations: list[ViolationEvent]) -> list[ViolationEvent]:
    seen: set[tuple[int, str | None, str]] = set()
    out: list[ViolationEvent] = []
    for v in violations:
        key = (v.step_id, v.violated_profile_span_id, v.violated_constraint)
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    # Re-id sequentially so downstream code does not see duplicates.
    for i, v in enumerate(out):
        v.violation_id = f"v{i + 1}"
    return out


# ---------------------------------------------------------------------------
# A small kit of generic deterministic rules. Benchmarks can append their own.
# ---------------------------------------------------------------------------


def hard_constraint_keyword_rule(
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    final_output: str | None,
) -> list[ViolationEvent]:
    """Cheap default rule: any hard-constraint span that is contradicted by a
    keyword in the final output (or any step text) is reported as a violation.

    Each `ProfileSpan.contradicts` lists banned substrings. This is intentionally
    blunt; it exists so that the synthetic benchmark needs no LLM verifier.
    """
    violations: list[ViolationEvent] = []
    haystacks: list[tuple[int, str]] = [(s.step_id, s.text) for s in trajectory.steps]
    if final_output:
        last_step_id = trajectory.steps[-1].step_id if trajectory.steps else 0
        haystacks.append((last_step_id, final_output))

    for span in profile.spans:
        if not span.is_hard or not span.contradicts:
            continue
        for step_id, text in haystacks:
            text_lower = text.lower()
            for banned in span.contradicts:
                if banned.lower() in text_lower:
                    violations.append(
                        ViolationEvent(
                            violation_id=f"v_rule_{len(violations) + 1}",
                            step_id=step_id,
                            violated_profile_span_id=span.id,
                            violated_constraint=span.text,
                            trajectory_text=text,
                            severity=Severity.HIGH,
                            confidence=1.0,
                            explanation=(
                                f"Trajectory mentions {banned!r} which contradicts hard"
                                f" profile constraint {span.id} ({span.text!r})."
                            ),
                        )
                    )
                    break
    return violations
