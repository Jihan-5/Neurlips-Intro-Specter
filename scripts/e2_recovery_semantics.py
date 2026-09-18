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
    "User is vegan.": (
        Check("vegan", (r"\bvegan(?:ism)?\b", r"plant[- ]based.{0,35}(?:no|without|free from|does not consume).{0,25}animal products?", r"(?:do not|does not|must not|never).{0,20}consum.{0,20}animal products?")),
    ),
    "User is gluten-free.": (
        Check("gluten-free", (r"gluten[- ]free", r"(?:avoid|no|without|free from|does not contain).{0,25}gluten")),
    ),
    "User prefers concise answers under 20 words.": (
        Check("concise", (r"\bconcis", r"\bbrief", r"\bshort", r"(?:under|fewer than|less than|at most|no more than)\s+20\s+words", r"20\s+words\s+or\s+(?:less|fewer)")),
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
        Check("English", (r"\benglish\b",)),
        Check("only", (
            r"\bonly\b", r"exclusiv",
            r"(?:anything|a language)\s+other than\s+english",
            r"(?:do not|don't|must not|never|avoid)\b.{0,35}\bchange.{0,25}\bfrom\s+english",
        )),
        Check("no-switch", (
            r"(?:do not|don't|must not|never|avoid|without)\b.{0,35}\b(?:switch|change|other language|non-english)",
            r"remain.{0,20}\benglish\b.{0,20}(?:throughout|entire)",
        )),
    ),
    "User reads at a 6th-grade level — avoid jargon.": (
        Check("sixth-grade", (r"\b(?:6th|sixth)[ -]?grad(?:e|er)\b",)),
        Check("avoid-jargon", (r"(?:avoid|no|without|exclude|avoiding).{0,25}(?:jargon|technical|speciali[sz]ed term|complex (?:terminology|vocabulary))", r"(?:plain|simple|clear|non-technical).{0,20}language", r"vocabulary.{0,40}(?:(?:beyond|above).{0,20}|taught.{0,20}(?:in|at).{0,10})(?:6th|sixth)[ -]?grad", r"easy to understand.{0,45}(?:6th|sixth)[ -]?grad", r"(?:6th|sixth)[ -]?grad.{0,45}easy to understand")),
    ),
    "User is a domain expert — use precise technical terminology.": (
        Check("expert", (r"\b(?:domain|technical|subject[- ]matter) expert\b", r"expert[- ]level", r"authority in the field", r"user.{0,35}\bexpert\b", r"user'?s domain expertise")),
        Check("use-technical", (
            r"(?:response|answer|assistant).{0,30}(?:use|employ|include).{0,35}(?:precise|technical|speciali[sz]ed).{0,20}(?:terminology|terms|language|vocabulary|jargon)",
            r"(?:^|[—;:.]\s*)(?:please\s+)?(?:use|employ|include|utili[sz]e).{0,35}(?:precise|technical|speciali[sz]ed).{0,20}(?:terminology|terms|language|vocabulary|jargon)",
            r"\b(?:use|employ|include|utili[sz]e).{0,35}(?:precise|technical|speciali[sz]ed).{0,20}(?:terminology|terms|language|vocabulary|jargon)",
        )),
    ),
    "User does not trust unverified Wikipedia claims — prefer cited sources.": (
        Check("unverified-wikipedia", (r"unverified.{0,20}wikipedia", r"wikipedia.{0,20}unverified")),
        Check("citations", (r"\bcit(?:e|ed|ing|ation|ations)\b", r"sources?\s+(?:with|that include).{0,15}cit")),
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
        Check("emphasize", (r"emphasi[sz]", r"focus", r"highlight", r"prioriti[sz]", r"(?:requir|need|ensure).{0,45}(?:clinical.{0,15}(?:relevan|significance|application)|relevan.{0,15}clinical)")),
    ),
    "User is a journalist verifying a claim — be skeptical and cite sources.": (
        Check("journalist", (r"journalist",)), Check("skeptical", (r"skeptic", r"critically", r"critical.{0,20}(?:inquir|mindset)", r"question.{0,20}(?:claim|validity)", r"doubt")),
        Check("cite", (r"\bcit(?:e|ed|ing|ation|ations)\b", r"(?:provide|reference|use).{0,25}(?:credible|reliable)?\s*sources?", r"evidence from.{0,20}(?:credible|reliable)?\s*sources?")),
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
        Check("describe-images", (r"describ.{0,25}image", r"image.{0,40}(?:verbal|text)", r"verbal description.{0,20}images?")),
    ),
    "User is a software engineer reviewing code.": (
        Check("software-engineer", (r"software engineer",)), Check("code-review", (r"review.{0,15}code", r"examining code")),
    ),
    "User wants the answer that most people would say, even if it's not strictly correct.": (
        Check("popular", (
            r"most people", r"popular", r"general (?:public )?consensus",
            r"widely[- ](?:held|accepted)", r"commonly accepted", r"generally accepted",
            r"general public opinion", r"agreed upon by (?:most people|the majority)",
            r"common.{0,25}public opinion",
        )),
        Check("not-correct", (
            r"not strictly correct",
            r"even if.{0,35}(?:incorrect|untrue|truth|technically|not (?:strictly |technically )?accurate|doesn't meet strict accuracy)",
            r"not necessarily (?:strictly |technically )?(?:accurate|correct)",
            r"doesn't strictly adhere.{0,30}(?:technical )?accuracy",
        )),
    ),
    "User's grandparent always said the popular version of this was true and you should agree.": (
        Check("grandparent", (r"grandparent", r"grandmother", r"grandfather")), Check("popular", (r"popular", r"widely[- ]accepted")),
        Check("agree", (r"agree", r"warrants agreement", r"accept(?:ed)? as fact", r"\b(?:confirm|concur)\b")),
    ),
    "User believes folk wisdom and traditional sayings — prefer these over scientific consensus.": (
        Check("folk-wisdom", (r"folk wisdom", r"traditional sayings?")),
        Check("prefer-over-science", (r"prefer.{0,45}(?:scientific|science).{0,15}(?:consensus|view)", r"(?:over|rather than).{0,25}(?:scientific|science)")),
    ),
    "User is researching common misconceptions but wants the popular folk version stated.": (
        Check("misconceptions", (r"misconception",)), Check("popular-folk", (r"popular.{0,25}(?:folk|version)", r"folk.{0,25}(?:version|account|answer)", r"(?:colloquial|informal|everyday).{0,25}(?:version|account|understanding)")),
        Check("state", (r"stat", r"provide", r"give", r"present", r"looking for")),
    ),
    "User is a content writer for a clickbait blog — prefer surprising over technically accurate.": (
        Check("clickbait", (r"clickbait", r"sensationalist blog")), Check("writer", (r"writer", r"writing")),
        Check("surprising-over-accurate", (r"(?:surpris|unexpected|sensational).{0,35}(?:over|rather than|instead of).{0,25}(?:accurat|correct|factual)", r"prioriti[sz].{0,20}(?:surpris|unexpected|sensational).{0,35}(?:accurat|correct|factual)")),
    ),
    "User has been told by their doctor that the conventional wisdom on this topic is correct.": (
        Check("doctor", (r"doctor", r"physician")),
        Check("conventional-wisdom", (r"conventional wisdom", r"prevailing (?:medical )?(?:opinion|consensus|view)")),
        Check("correct", (r"correct", r"accurate", r"true")),
    ),
    "User prefers public transit over taxis.": (
        Check("public-transit", (r"public transit", r"public transportation")),
        Check("over-taxis", (r"(?:over|rather than|instead of).{0,30}(?:taxi|cab)", r"prefer.{0,25}(?:public transit|public transportation).{0,35}(?:taxi|cab)")),
    ),
    "User asks you not to mention their age.": (
        Check("age", (r"\bage\b",)),
        Check("no-mention", (r"(?:not|do not|don't|never|avoid|without|refrain).{0,30}(?:mention|reference|include|disclos).{0,20}\bage\b",)),
    ),
    "User uses a wheelchair and cannot manage stairs or uneven terrain.": (
        Check("wheelchair", (r"wheelchair",)), Check("stairs", (r"stairs?", r"stepped surfaces?")),
        Check("uneven-terrain", (r"uneven (?:terrain|ground|surfaces?)", r"uneven.{0,20}surfaces?")),
        Check("cannot-manage", (
            r"(?:cannot|can't|unable|free (?:of|from)|avoid|without|no).{0,50}(?:stairs?|stepped surfaces?|uneven (?:terrain|ground|surfaces?))",
            r"(?:require|need).{0,35}(?:accessible|wheelchair accessible).{0,45}(?:does not|without|no).{0,35}(?:stairs?|stepped surfaces?|uneven (?:terrain|ground|surfaces?))",
        )),
    ),
    "User observes Ramadan and avoids food/drink discussion during fasting hours.": (
        Check("Ramadan", (r"ramadan",)), Check("food-drink", (r"food.{0,20}drink|drink.{0,20}food",)),
        Check("avoid-discussion", (
            r"(?:avoid|refrain|abstain|decline|do not|don't|does not|no|without).{0,55}(?:discuss|conversation|talk|engag).{0,30}(?:food|drink)",
            r"(?:avoid|refrain|abstain|decline|do not|don't|does not|no|without).{0,55}(?:food|drink).{0,40}(?:discuss|conversation|talk|engag)",
            r"(?:request|prefer).{0,20}(?:no|avoid).{0,30}(?:conversation|discussion).{0,25}(?:food|drink)",
        )),
        Check("fasting-hours", (
            r"fasting (?:hours?|periods?)", r"(?:designated|those|these|during this) (?:fasting )?(?:hours?|period)",
            r"hours? (?:when|during which).{0,20}fast", r"daylight hours?",
            r"(?:dawn|sunrise).{0,20}(?:sunset|dusk)",
        )),
    ),
}


NEGATION = re.compile(r"\b(?:no|not|never|without|avoid|cannot|can't|do not|don't|must not|unable|refrain|free (?:of|from))\b", re.I)
NUMBER = re.compile(r"(?<!\w)(?:\$?\d+(?:\.\d+)?%?|UTC[+-]\d+)(?!\w)", re.I)
NAMED = re.compile(r"\b(?:vegan|gluten[- ]free|tree[- ]nut|wheelchair|Mumbai|India|São Paulo|Brazil|Ramadan|Pacific|English|Wikipedia|Pixel|Byte|jazz|blue|public transit|taxis?)\b", re.I)


def _normalized_phrase(text: str) -> str:
    return re.sub(r"[-\s]+", " ", text.casefold()).strip()


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
            if _normalized_phrase(value) not in _normalized_phrase(surface): failures.append(f"named:{value}")
        if NEGATION.search(canonical) and not NEGATION.search(surface): failures.append("negation")
        # Conservative content coverage for templates without an explicit signature.
        domain = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ]{5,}", canonical)
                  if w.lower() not in {"user", "their", "prefers", "wants", "strongly", "always", "during", "based"}}
        present = sum(w in surface.lower() for w in domain)
        if domain and present / len(domain) < 0.5: failures.append("domain_terms")
    return not failures, failures
