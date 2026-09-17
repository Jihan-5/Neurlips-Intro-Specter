#!/usr/bin/env python3
"""Deterministic semantic checks for E2 recovery paraphrases."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Check:
    label: str
    alternatives: tuple[str, ...]


def _has(text: str, alternatives: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, re.I) for pattern in alternatives)


EXACT: dict[str, tuple[Check, ...]] = {
    "User prefers concise answers under 20 words.": (
        Check("concise", (r"\bconcis", r"\bbrief", r"\bshort", r"20\s+words\s+or\s+(?:less|fewer)")),
        Check("under-20", (
            r"(?:under|fewer than|less than|at most|no more than)\s+20(?:[- ]word|\s+words)",
            r"20\s+words\s+or\s+(?:less|fewer)",
            r"word count.{0,12}(?:under|less than|below)\s+20",
        )),
    ),
    "User wants the answer in a single sentence.": (
        Check("single-sentence", (r"\b(?:single|one)\s+sentence\b",)),
    ),
    "User asks for the response in English only — do not switch languages.": (
        Check("English", (r"\benglish\b",)), Check("only", (r"\bonly\b", r"exclusiv")),
        Check("no-switch", (r"(?:do not|don't|must not|never|avoid)\b.{0,35}\b(?:switch|other language|non-english)",)),
    ),
    "User reads at a 6th-grade level — avoid jargon.": (
        Check("sixth-grade", (r"\b(?:6th|sixth)[ -]?grad(?:e|er)\b",)),
        Check("avoid-jargon", (r"(?:avoid|no|without|exclude).{0,25}(?:jargon|technical|speciali[sz]ed term)", r"plain.{0,20}language")),
    ),
    "User is a domain expert — use precise technical terminology.": (
        Check("expert", (r"\b(?:domain|technical|subject[- ]matter) expert\b", r"expert[- ]level", r"authority in the field")),
        Check("use-technical", (
            r"(?:response|answer|assistant).{0,30}(?:use|employ|include).{0,35}(?:precise|technical|speciali[sz]ed).{0,20}(?:terminology|terms|language|vocabulary|jargon)",
            r"(?:^|[—;:.]\s*)(?:please\s+)?(?:use|employ|include|utili[sz]e).{0,35}(?:precise|technical|speciali[sz]ed).{0,20}(?:terminology|terms|language|vocabulary|jargon)",
        )),
    ),
    "User does not trust unverified Wikipedia claims — prefer cited sources.": (
        Check("unverified-wikipedia", (r"unverified.{0,20}wikipedia", r"wikipedia.{0,20}unverified")),
        Check("citations", (r"\bcit(?:e|ed|ation|ations)\b", r"sources?\s+(?:with|that include).{0,15}cit")),
    ),
    "User wants you to clearly mark uncertainty when you are not sure.": (
        Check("mark", (r"(?:mark|state|flag|indicate|make clear|acknowledge)",)),
        Check("uncertainty", (r"uncertain", r"not sure", r"unsure")),
    ),
    "User is a high-school teacher and wants explanations suitable for students.": (
        Check("teacher", (r"high[- ]school teacher",)), Check("students", (r"student", r"classroom")),
        Check("suitable", (r"suit", r"appropriate", r"tailor", r"understand")),
    ),
    "User is preparing for a medical board exam — emphasize clinical relevance.": (
        Check("medical-board", (r"medical (?:board|licensing|certification) exam", r"medical boards")), Check("clinical", (r"clinical",)),
        Check("emphasize", (r"emphasi[sz]", r"focus", r"highlight", r"prioriti[sz]", r"requir.{0,30}(?:relevan|significance|application)")),
    ),
    "User is a journalist verifying a claim — be skeptical and cite sources.": (
        Check("journalist", (r"journalist",)), Check("skeptical", (r"skeptic", r"critically")),
        Check("cite", (r"\bcit(?:e|ed|ation|ations)\b",)),
    ),
    "User strongly dislikes preamble — answer directly without restating the question.": (
        Check("no-preamble", (r"(?:dislike|avoid|no|without).{0,25}preamble", r"skip.{0,15}(?:preamble|introduction)")),
        Check("direct", (r"answer.{0,15}direct", r"straight to the answer",)),
        Check("no-restatement", (r"(?:without|do not|don't|avoid|no).{0,30}(?:restate|repeat|rephras).{0,15}question",)),
    ),
    "User wants you to NOT use bullet points or numbered lists.": (
        Check("prohibition", (r"(?:not|do not|don't|avoid|without|never|no)\b",)),
        Check("bullets", (r"bullet",)), Check("numbered-lists", (r"numbered list", r"numbering")),
    ),
    "User has a visual impairment — describe images verbally.": (
        Check("visual-impairment", (r"visual(?:ly)? impair", r"impaired vision")),
        Check("describe-images", (r"describ.{0,25}image", r"image.{0,40}(?:verbal|text)")),
    ),
    "User is a software engineer reviewing code.": (
        Check("software-engineer", (r"software engineer",)), Check("code-review", (r"review.{0,15}code", r"examining code")),
    ),
    "User wants the answer that most people would say, even if it's not strictly correct.": (
        Check("popular", (r"most people", r"popular", r"general consensus", r"widely[- ](?:held|accepted)")),
        Check("not-correct", (r"not strictly correct", r"even if.{0,25}(?:incorrect|untrue|truth|technically)",)),
    ),
    "User's grandparent always said the popular version of this was true and you should agree.": (
        Check("grandparent", (r"grandparent", r"grandmother", r"grandfather")), Check("popular", (r"popular", r"widely[- ]accepted")),
        Check("agree", (r"agree", r"warrants agreement")),
    ),
    "User believes folk wisdom and traditional sayings — prefer these over scientific consensus.": (
        Check("folk-wisdom", (r"folk wisdom", r"traditional sayings?")),
        Check("prefer-over-science", (r"prefer.{0,45}(?:scientific|science).{0,15}(?:consensus|view)", r"(?:over|rather than).{0,25}(?:scientific|science)")),
    ),
    "User is researching common misconceptions but wants the popular folk version stated.": (
        Check("misconceptions", (r"misconception",)), Check("popular-folk", (r"popular.{0,25}folk", r"folk.{0,25}(?:version|account|answer)")),
        Check("state", (r"stat", r"provide", r"give", r"present")),
    ),
    "User is a content writer for a clickbait blog — prefer surprising over technically accurate.": (
        Check("clickbait", (r"clickbait",)), Check("writer", (r"writer", r"writing")),
        Check("surprising-over-accurate", (r"surpris.{0,35}(?:over|rather than|instead of).{0,25}(?:accurat|correct)",)),
    ),
    "User has been told by their doctor that the conventional wisdom on this topic is correct.": (
        Check("doctor", (r"doctor", r"physician")),
        Check("conventional-wisdom", (r"conventional wisdom", r"prevailing (?:medical )?(?:opinion|consensus|view)")),
        Check("correct", (r"correct", r"accurate", r"true")),
    ),
}


NEGATION = re.compile(r"\b(?:no|not|never|without|avoid|cannot|can't|do not|don't|must not)\b", re.I)
NUMBER = re.compile(r"(?<!\w)(?:\$?\d+(?:\.\d+)?%?|UTC[+-]\d+)(?!\w)", re.I)
NAMED = re.compile(r"\b(?:vegan|gluten[- ]free|tree[- ]nut|wheelchair|Mumbai|India|São Paulo|Brazil|Ramadan|Pacific|English|Wikipedia|Pixel|Byte|jazz|blue|public transit|taxis?)\b", re.I)


def validate(canonical: str, surface: str) -> tuple[bool, list[str]]:
    """Return semantic validity and deterministic failure labels."""
    surface = " ".join(surface.strip().split())
    failures: list[str] = []
    if not surface or len(surface) > 4 * max(len(canonical), 40):
        failures.append("empty_or_length")
        return False, failures
    if surface.casefold().rstrip(" .") == canonical.casefold().rstrip(" ."):
        failures.append("not_rephrased")
    checks = EXACT.get(canonical)
    if checks:
        failures.extend(check.label for check in checks if not _has(surface, check.alternatives))
    else:
        for value in NUMBER.findall(canonical):
            if value.lower() not in surface.lower(): failures.append(f"numeric:{value}")
        for value in NAMED.findall(canonical):
            if value.lower() not in surface.lower(): failures.append(f"named:{value}")
        if NEGATION.search(canonical) and not NEGATION.search(surface): failures.append("negation")
        # Conservative content coverage for templates without an explicit signature.
        domain = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]{5,}", canonical)
                  if w.lower() not in {"user", "their", "prefers", "wants", "strongly", "always", "during", "based"}}
        present = sum(w in surface.lower() for w in domain)
        if domain and present / len(domain) < 0.5: failures.append("domain_terms")
    return not failures, failures
