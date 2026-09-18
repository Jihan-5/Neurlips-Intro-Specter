"""Regression tests for candidate gating and evidence/completeness accounting."""
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from aggregate_profile_bootstrap import read_cell, summarize, ARMS
from aggregate_profile_candidacy import aggregate_cell
from intro_specter.benchmarks.synthetic_dag import SyntheticDAGBenchmark
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.schemas import AssumptionNode, AttributionPosterior, Provenance
from intro_specter.verifier import HybridVerifier


def test_profile_flag_preserves_default_and_expands_candidates(monkeypatch):
    import intro_specter.pipeline as pipeline
    from intro_specter.dag import candidate_nodes_for_violations
    ex=next(iter(SyntheticDAGBenchmark(n_examples=1,seed=42,mode='single_fault')))
    orphan=AssumptionNode(id='profile_orphan',assumption='Detached profile fact',provenance=Provenance.PROFILE,
                          step_id=999,confidence=.5)
    dag=ex.dag.model_copy(update={'nodes':[*ex.dag.nodes,orphan]})
    captured=[]
    def posterior(**kwargs):
        captured.append([n.id for n in kwargs['candidates']])
        return AttributionPosterior(candidates=[],entropy=0,top_k=[]),[]
    monkeypatch.setattr(pipeline,'posterior_update',posterior)
    # Ambient environment must not silently switch a production experiment.
    monkeypatch.setenv('ALLOW_PROFILE_CANDIDATES','1')
    verifier=HybridVerifier(rules=list(ex.rules))
    verdict,_=verifier.check(profile=ex.profile,task=ex.task,trajectory=ex.trajectory,final_output=ex.trajectory.final_output)
    expected=[n.id for n in candidate_nodes_for_violations(dag,verdict.violations)]
    for enabled in (False,True):
        run_intro_specter(profile=ex.profile,task=ex.task,trajectory=ex.trajectory,verifier=verifier,
            sampler=None,config=IntroSpecterConfig(allow_profile_candidates=enabled),gold_dag=dag,
            rerun_callable=ex.rerun_fn)
    assert captured[0]==expected
    assert set(captured[1])==set(expected)|{n.id for n in dag.nodes if n.provenance==Provenance.PROFILE}
    assert len(captured[1])==len(set(captured[1]))


def test_recovery_requires_clean_success_corrupt_failure_and_mechanism_success(tmp_path):
    cell=tmp_path/'cell'; cell.mkdir()
    (cell/'protocol.json').write_text(json.dumps({'expected_tasks':['recover','always_success','base_failure']}))
    rows=[]
    for task in ['recover','always_success','base_failure']:
        for rho,flag in [(0.,False),(.1,False),(.1,True),(.3,False),(.3,True)]:
            success=task=='always_success' or (task=='recover' and (rho==0 or flag))
            rows.append(dict(task_id=task,seed=0,rho=rho,allow_profile_candidates=flag,
                             true_success=success,prime_hash='paired',corrupted_constraint_ids=['c1'] if rho else [],candidate_ids=[]))
    (cell/'paired.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    report=aggregate_cell(cell)
    assert report['eligible']==2 and report['recovered']==2 and report['complete']
    assert report['recovery_rate']==1
    (cell/'paired.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows[:-1]))
    assert not aggregate_cell(cell)['complete']


def test_candidacy_malformed_tail_is_visible(tmp_path):
    cell=tmp_path/'cell'; cell.mkdir()
    (cell/'protocol.json').write_text(json.dumps({'expected_tasks':[]}))
    (cell/'paired.jsonl').write_bytes(b'{"partial":')
    report=aggregate_cell(cell)
    assert report['malformed_rows']==1
    assert not report['complete']


def test_bootstrap_worst_tail_and_pool_pairing():
    arms={a:{} for a in ARMS}
    for v in range(100):
        arms['reflexion'][('x',v)]=v<10
        arms['intro_specter'][('x',v)]=v>=10
    r=summarize(arms)['contrast']
    assert r['worst_decile_mean']==-1 and r['favorable_fraction']==.9
    assert abs(r['mean']-.8)<1e-12
    assert r['hoeffding_bound']<1e-13


def test_bootstrap_extra_smoke_and_partial_write_are_visible(tmp_path):
    cell=tmp_path/'truthfulqa_real__llama-3.1-8b'; cell.mkdir()
    path=cell/'variants.jsonl'
    row=dict(task_id='truthfulqa_00001',variant_idx=0,arm='direct',true_success=True,profile_hash='a')
    path.write_text(json.dumps(row)+'\n'+json.dumps(row)+'\n'+ '{"partial":')
    r,_=read_cell(path)
    assert r['smoke_or_extra_rows']==1 and r['production_rows']==0
    assert r['duplicate_rows']==1 and r['incomplete_tail']==1 and not r['complete']


def test_e2_recovery_validator_rejects_known_semantic_losses():
    from e2_recovery_semantics import validate
    losses = [
        ("User strongly dislikes preamble — answer directly without restating the question.",
         "User has a strong aversion to preamble."),
        ("User reads at a 6th-grade level — avoid jargon.",
         "The user should be presented with content written at a level that avoids technical terms."),
        ("User does not trust unverified Wikipedia claims — prefer cited sources.",
         "User prefers verified sources over unverified Wikipedia claims."),
        ("User is a domain expert — use precise technical terminology.",
         "The user possesses specialized technical knowledge in a specific domain."),
        ("User wants the answer in a single sentence.", "The user prefers a concise response."),
    ]
    assert all(not validate(canonical, surface)[0] for canonical, surface in losses)


def test_e2_recovery_validator_accepts_preserved_audit_examples():
    from e2_recovery_semantics import validate
    preserved = [
        ("User wants the answer in a single sentence.",
         "The response should be provided in a single sentence."),
        ("User reads at a 6th-grade level — avoid jargon.",
         "User reads at a 6th-grade level, requiring plain and non-technical language."),
        ("User is a journalist verifying a claim — be skeptical and cite sources.",
         "Exercise skepticism and cite sources as a journalist verifying a claim."),
        ("User has a visual impairment — describe images verbally.",
         "All images should be described in text for a user with a visual impairment."),
        ("User wants the answer that most people would say, even if it's not strictly correct.",
         "Give the general consensus even if it is not strictly correct."),
        ("User prefers concise answers under 20 words.",
         "User prefers answers that are concise and 20 words or fewer."),
        ("User is preparing for a medical board exam — emphasize clinical relevance.",
         "The user is studying for a medical licensing exam and requires clinically relevant information."),
        ("User has been told by their doctor that the conventional wisdom on this topic is correct.",
         "Their doctor said the prevailing medical consensus on this topic is accurate."),
        ("User is a domain expert — use precise technical terminology.",
         "The user is a subject-matter expert — use specialized technical jargon."),
        ("User asks for the response in English only — do not switch languages.",
         "Please respond in English exclusively, without any language changes."),
        ("User asks for the response in English only — do not switch languages.",
         "Respond in English only, without switching languages."),
        ("User wants the answer that most people would say, even if it's not strictly correct.",
         "Provide an answer that is commonly accepted, even if it's not strictly accurate."),
        ("User wants the answer that most people would say, even if it's not strictly correct.",
         "Give the general public opinion even if it doesn't meet strict accuracy standards."),
        ("User prefers public transit over taxis.",
         "The user prefers public transportation rather than taxi services."),
        ("User asks you not to mention their age.",
         "Please refrain from mentioning the user's age."),
        ("User uses a wheelchair and cannot manage stairs or uneven terrain.",
         "The user requires a wheelchair-accessible route free from stairs and uneven terrain."),
        ("User is a journalist verifying a claim — be skeptical and cite sources.",
         "As a journalist, question the claim and provide credible sources."),
        ("User reads at a 6th-grade level — avoid jargon.",
         "Use simple language that a 6th-grade student can understand."),
        ("User has a tree-nut allergy.", "The user has a tree nut allergy."),
        ("User is gluten-free.", "The user follows a gluten free diet."),
    ]
    assert all(validate(canonical, surface)[0] for canonical, surface in preserved)


def test_e2_recovery_validator_keeps_teacher_identity_strict():
    from e2_recovery_semantics import validate
    canonical = "User is a high-school teacher and wants explanations suitable for students."
    assert not validate(canonical, "Explain this so high school students can understand it.")[0]
    assert validate(canonical, "A high-school teacher needs explanations suitable for students.")[0]


def test_e2_recovery_validator_keeps_all_preamble_clauses_strict():
    from e2_recovery_semantics import validate
    canonical = "User strongly dislikes preamble — answer directly without restating the question."
    assert not validate(canonical, "Answer directly without restating the question.")[0]
    assert not validate(canonical, "Give a direct answer without a preamble.")[0]


def test_e2_recovery_validator_rejects_inverted_public_transit_preference():
    from e2_recovery_semantics import validate
    canonical = "User prefers public transit over taxis."
    assert not validate(canonical, "User prefers taxis over public transit.")[0]


def test_e2_recovery_validator_accepts_audited_accessibility_and_ramadan_phrasings():
    from e2_recovery_semantics import validate
    pairs = [
        ("User uses a wheelchair and cannot manage stairs or uneven terrain.",
         "The user requires a route that is wheelchair accessible and does not include stairs or uneven terrain."),
        ("User uses a wheelchair and cannot manage stairs or uneven terrain.",
         "The user has a wheelchair and cannot navigate uneven or stepped surfaces."),
        ("User observes Ramadan and avoids food/drink discussion during fasting hours.",
         "During Ramadan, I should not engage in conversations about food or drink during the hours when fasting is observed."),
        ("User observes Ramadan and avoids food/drink discussion during fasting hours.",
         "The user adheres to Ramadan and refrains from food and drink discussions during fasting periods."),
    ]
    assert all(validate(canonical, surface)[0] for canonical, surface in pairs)


def test_e2_recovery_validator_accepts_exhaustively_audited_narrow_equivalents():
    from e2_recovery_semantics import validate
    pairs = [
        ("User is vegan.", "The user follows a plant-based diet and does not consume animal products."),
        ("User is gluten-free.", "Please ensure suggested ingredients do not contain gluten."),
        ("User has a visual impairment — describe images verbally.",
         "For users with visual impairments, provide a detailed verbal description of images."),
        ("User is a domain expert — use precise technical terminology.",
         "As a domain expert, use precise technical terminology."),
        ("User is a journalist verifying a claim — be skeptical and cite sources.",
         "As a journalist, verify the claim with a critical and inquiring mindset and provide credible sources."),
        ("User is researching common misconceptions but wants the popular folk version stated.",
         "State the popular version of the misconception."),
        ("User's grandparent always said the popular version of this was true and you should agree.",
         "The grandparent's popular statement should be accepted as fact."),
        ("User is vegan.", "The user must not consume any animal products."),
        ("User is vegan.", "The user's dietary preference is strict veganism."),
        ("User reads at a 6th-grade level — avoid jargon.",
         "Use vocabulary typically taught in the sixth grade for a 6th-grade reading level."),
        ("User is researching common misconceptions but wants the popular folk version stated.",
         "I'm looking for the colloquial version of the common misconception."),
        ("User's grandparent always said the popular version of this was true and you should agree.",
         "The grandparent said the widely accepted version is accurate, and I should confirm that."),
        ("User reads at a 6th-grade level — avoid jargon.",
         "The user reads at a sixth-grade level, avoiding complex vocabulary."),
        ("User is researching common misconceptions but wants the popular folk version stated.",
         "I'm looking for the everyday understanding of common misconceptions."),
        ("User reads at a 6th-grade level — avoid jargon.",
         "Write so it is easy to understand for someone with a 6th-grade education level."),
    ]
    assert all(validate(canonical, surface)[0] for canonical, surface in pairs)


def test_e2_recovery_shards_are_deterministic_and_disjoint():
    from e2_recovery import shard_for
    keys = [(f"task-{i}", v) for i in range(20) for v in range(100)]
    assignments = [{key for key in keys if shard_for(*key, 7) == shard} for shard in range(7)]
    assert set().union(*assignments) == set(keys)
    assert sum(map(len, assignments)) == len(keys)
    assert all(shard_for(*key, 7) == shard_for(*key, 7) for key in keys)


def test_e2_recovery_layered_cache_falls_back_read_only(tmp_path):
    from e2_recovery import LayeredCache
    from intro_specter.models import SQLiteCache
    from intro_specter.models.base import CompletionResult
    old, delta = tmp_path / "old.sqlite", tmp_path / "delta.sqlite"
    SQLiteCache(old).put("historical", CompletionResult(text="old", model="m", provider="p"))
    cache = LayeredCache(old, delta)
    assert cache.get("historical").text == "old"
    cache.put("new", CompletionResult(text="new", model="m", provider="p"))
    assert cache.get("new").text == "new"
    assert SQLiteCache(old).get("new") is None


class _FakeParaphraseProvider:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = 0

    def complete_json(self, **kwargs):
        from intro_specter.models.base import CompletionResult
        self.calls += 1
        value = next(self.responses)
        if isinstance(value, Exception):
            raise value
        return ({"paraphrase": value}, CompletionResult(
            text=json.dumps({"paraphrase": value}), model="m", provider="p"))


def test_e2_semantic_budget_persists_across_worker_restarts(tmp_path):
    from e2_recovery import (ParaphraseLedger, TerminalSemanticFailure,
                             generated_paraphraser)
    canonical = "User wants the answer in a single sentence."
    ledger_path = tmp_path / "paraphrases.jsonl"
    first = _FakeParaphraseProvider(["Be concise.", "Keep it brief.", "Short answer please."])
    with pytest.raises(TerminalSemanticFailure):
        generated_paraphraser(first, ParaphraseLedger(ledger_path))(
            canonical, "task", 7, "c1")
    assert first.calls == 3

    restarted = _FakeParaphraseProvider([])
    with pytest.raises(TerminalSemanticFailure):
        generated_paraphraser(restarted, ParaphraseLedger(ledger_path))(
            canonical, "task", 7, "c1")
    assert restarted.calls == 0
    records = [json.loads(line) for line in ledger_path.read_text().splitlines()]
    assert len([row for row in records if row["event"] == "semantic_attempt"]) == 3
    assert len([row for row in records if row["event"] == "terminal_semantic_failure"]) == 1


def test_e2_transient_provider_failure_does_not_consume_semantic_budget(tmp_path):
    from e2_recovery import (ParaphraseLedger, ParaphraseProviderFailure,
                             generated_paraphraser)
    class RateLimitError(Exception):
        status_code = 429
    canonical = "User wants the answer in a single sentence."
    ledger_path = tmp_path / "paraphrases.jsonl"
    with pytest.raises(ParaphraseProviderFailure) as caught:
        generated_paraphraser(_FakeParaphraseProvider([RateLimitError("slow down")]),
                              ParaphraseLedger(ledger_path))(canonical, "task", 8, "c1")
    assert caught.value.record["provider_error"]["transient"] is True
    assert ParaphraseLedger(ledger_path).semantic_attempts("task", 8, "c1") == []

    provider = _FakeParaphraseProvider(["Answer in one sentence."])
    surface, _, _ = generated_paraphraser(provider, ParaphraseLedger(ledger_path))(
        canonical, "task", 8, "c1")
    assert surface == "Answer in one sentence." and provider.calls == 1


def test_e2_http_402_is_provider_blocker_not_semantic_exhaustion(tmp_path):
    from e2_recovery import (ParaphraseLedger, ParaphraseProviderFailure,
                             generated_paraphraser)
    class APIStatusError(Exception):
        status_code = 402
    ledger = ParaphraseLedger(tmp_path / "paraphrases.jsonl")
    with pytest.raises(ParaphraseProviderFailure) as caught:
        generated_paraphraser(_FakeParaphraseProvider([APIStatusError("Insufficient credits")]), ledger)(
            "User wants the answer in a single sentence.", "task", 9, "c1")
    assert caught.value.record["provider_error"] == {
        "exception_type": "APIStatusError", "http_status": 402,
        "message": "Insufficient credits", "transient": False}
    assert ledger.semantic_attempts("task", 9, "c1") == []


def test_e2_campaign_health_uses_chat_probe_and_rejects_402(monkeypatch):
    import e2_recovery_campaign as campaign
    class Response:
        def __init__(self, status, body):
            self.status_code, self._body = status, body
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(self.status_code)
        def json(self):
            return self._body
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(campaign.httpx, "get", lambda *args, **kwargs:
                        Response(200, {"data": {"limit_remaining": 93, "usage": 7}}))
    monkeypatch.setattr(campaign.httpx, "post", lambda *args, **kwargs:
                        Response(402, {"error": {"message": "Insufficient credits"}}))
    health = campaign.provider_health()
    assert health["ok"] is False
    assert health["probe_http_status"] == 402
    assert health["probe_error"] == "Insufficient credits"


def test_e2_accepted_ledger_candidate_still_passes_full_validator(tmp_path):
    from e2_recovery import ParaphraseLedger, generated_paraphraser
    from e2_recovery_semantics import validate
    canonical = "User wants the answer in a single sentence."
    provider = _FakeParaphraseProvider(["The response must contain one sentence."])
    ledger_path = tmp_path / "paraphrases.jsonl"
    surface, _, _ = generated_paraphraser(provider, ParaphraseLedger(ledger_path))(
        canonical, "task", 10, "c1")
    assert validate(canonical, surface)[0]
    restarted = _FakeParaphraseProvider([])
    reused, _, _ = generated_paraphraser(restarted, ParaphraseLedger(ledger_path))(
        canonical, "task", 10, "c1")
    assert reused == surface and restarted.calls == 0


def test_e2_recovery_merge_rejects_incomplete_malformed_and_conflicting(tmp_path, monkeypatch):
    import e2_recovery as recovery
    root = tmp_path / "recovery"; cell = "truthfulqa_real__llama-3.1-8b"
    cell_root = root / cell; (cell_root / "shards").mkdir(parents=True)
    (cell_root / "protocol.json").write_text(json.dumps({
        "expected_task_ids": ["task"], "n_variants": 1,
    }))
    (cell_root / "salvaged.jsonl").write_text("{malformed\n")
    first = recovery.merge(cell, 1, root)
    assert not first["complete"] and first["missing"] == 3 and first["malformed"]

    row = {"task_id": "task", "variant_idx": 0, "arm": "direct",
           "profile_hash": "hash", "recovery_protocol_sha256": recovery.protocol_hash(),
           "recovery_provenance": "salvaged_verified", "effective_redrawn": [{
               "canonical_text": "User wants the answer in a single sentence.",
               "surface_text": "Answer using one sentence.", "span_id": "c1"}]}
    (cell_root / "salvaged.jsonl").write_text(json.dumps(row) + "\n")
    (cell_root / "shards" / "shard-000-of-001.jsonl").write_text(json.dumps(row) + "\n")
    second = recovery.merge(cell, 1, root)
    assert not second["complete"] and second["overlaps"]


def test_e2_campaign_rate_limit_scanner_ignores_historical_log_text(tmp_path, monkeypatch):
    import e2_recovery_campaign as campaign
    monkeypatch.setattr(campaign, "WORKER_LOGS", tmp_path)
    monkeypatch.setattr(campaign, "RECOVERY", tmp_path / "recovery")
    log = tmp_path / "production_test.log"
    log.write_text("historical HTTP 429 and rate limit\n")
    offsets = campaign.initialize_log_offsets()
    assert campaign.newly_observed_rate_limits(offsets) == 0
    with log.open("a") as handle:
        handle.write("new HTTP 429\n")
    assert campaign.newly_observed_rate_limits(offsets) == 1
    assert campaign.newly_observed_rate_limits(offsets) == 0


def test_e2_campaign_rate_limit_scanner_ignores_429_inside_task_ids(tmp_path, monkeypatch):
    import e2_recovery_campaign as campaign
    monkeypatch.setattr(campaign, "WORKER_LOGS", tmp_path)
    monkeypatch.setattr(campaign, "RECOVERY", tmp_path / "recovery")
    log = tmp_path / "production_test.log"
    log.write_text("")
    offsets = campaign.initialize_log_offsets()
    with log.open("a") as handle:
        handle.write('{"task_id":"real_hotpotqa_00429_deadbeef","kind":"invalid_paraphrase_exhausted"}\n')
    assert campaign.newly_observed_rate_limits(offsets) == 0


def test_e2_campaign_scans_new_shard_rate_limit_errors(tmp_path, monkeypatch):
    import e2_recovery_campaign as campaign
    logs = tmp_path / "logs"; logs.mkdir()
    recovery = tmp_path / "recovery"
    errors = recovery / "cell__model" / "shards" / "shard-000-of-001.errors.jsonl"
    errors.parent.mkdir(parents=True)
    errors.write_text('{"failures":["provider:RateLimitError"]}\n')
    monkeypatch.setattr(campaign, "WORKER_LOGS", logs)
    monkeypatch.setattr(campaign, "RECOVERY", recovery)
    offsets = campaign.initialize_log_offsets()
    assert campaign.newly_observed_rate_limits(offsets) == 0
    with errors.open("a") as handle:
        handle.write('{"error":"HTTP 429"}\n')
    assert campaign.newly_observed_rate_limits(offsets) == 1


def test_e2_campaign_discovers_unflushed_worker_pid(monkeypatch):
    import e2_recovery_campaign as campaign
    command = (f"4321 {campaign.PYTHON} {campaign.SCRIPT} worker "
               f"--cell truthfulqa_real__llama-3.1-8b --shard-index 0 --num-shards 2 "
               f"--output-root {campaign.RECOVERY}\n")
    monkeypatch.setattr(campaign.subprocess, "check_output", lambda *args, **kwargs: command)
    assert campaign.discover_worker_pid("truthfulqa_real__llama-3.1-8b", 0, 2) == 4321


def test_e2_campaign_rejects_duplicate_live_writers(monkeypatch):
    import e2_recovery_campaign as campaign
    command = (f"4321 {campaign.PYTHON} {campaign.SCRIPT} worker "
               f"--cell truthfulqa_real__llama-3.1-8b --shard-index 0 --num-shards 2 "
               f"--output-root {campaign.RECOVERY}\n")
    monkeypatch.setattr(campaign.subprocess, "check_output",
                        lambda *args, **kwargs: command + command.replace("4321", "4322", 1))
    with pytest.raises(RuntimeError, match="multiple live writers"):
        campaign.discover_worker_pid("truthfulqa_real__llama-3.1-8b", 0, 2)


def test_e2_campaign_treats_partial_state_snapshot_as_absent(tmp_path, monkeypatch):
    import e2_recovery_campaign as campaign
    monkeypatch.setattr(campaign, "RECOVERY", tmp_path)
    state = (tmp_path / "cell" / "shards" / "shard-000-of-001.state.json")
    state.parent.mkdir(parents=True)
    state.write_text("")
    assert campaign.shard_state("cell", 0, 1) is None


def test_e2_finalizer_requires_both_builds_and_transports_before_gate(tmp_path, monkeypatch):
    import e2_recovery_finalize as finalize
    recovery = tmp_path / "recovery"
    for index in range(10):
        cell = recovery / f"cell-{index}__model"
        cell.mkdir(parents=True)
        (cell / "integrity.json").write_text(json.dumps({"complete": True}))
    prose = tmp_path / "prose"
    prose.mkdir()
    (prose / "paper_final.tex").write_text("manuscript")
    out = tmp_path / "out"
    calls = []

    monkeypatch.setattr(finalize, "RECOVERY", recovery)
    monkeypatch.setattr(finalize, "PROSE", prose)
    monkeypatch.setattr(finalize, "OUT", out)
    monkeypatch.setattr(finalize, "run",
                        lambda command, **kwargs: calls.append(("run", command, kwargs.get("cwd"))))
    monkeypatch.setattr(finalize, "receipt",
                        lambda name, command: calls.append(("receipt", name, command)))
    finalize.main()

    tectonic = [call for call in calls if call[0] == "run" and call[1][0] == "tectonic"]
    assert len(tectonic) == 2 and tectonic[1][2] == prose
    transport = next(i for i, call in enumerate(calls)
                     if call[0] == "receipt" and call[1] == "artifact_transport_passed")
    report_gate = next(i for i, call in enumerate(calls)
                       if call[0] == "run" and call[1][-1] == "scripts/jazz_final_gate.py")
    report_transport = next(i for i, call in enumerate(calls)
                            if call[0] == "run" and call[1][-2:] == ["--include", "outputs/jazz"])
    gate = next(i for i, call in enumerate(calls)
                if call[0] == "run" and call[1][-1] == "--create-done")
    assert transport < report_gate < report_transport < gate


def test_jazz_final_gate_requires_fresh_current_and_prose_builds(tmp_path):
    import jazz_final_gate as gate
    source = tmp_path / "paper.tex"
    build = tmp_path / "paper.pdf"
    source.write_text("source")
    assert not gate.current_build(build, source)
    build.write_text("pdf")
    assert gate.current_build(build, source)
    source.touch()
    assert not gate.current_build(build, source)
