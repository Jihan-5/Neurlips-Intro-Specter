# Real-X benchmark pattern

How the existing `Real-HotpotQA`, `Real-TruthfulQA`, `Real-StrategyQA`, and
`Real-TravelPlanner` benchmarks are structured. Mirror this pattern when
adding new Real-X benchmarks; do not modify these files directly.

## File layout

Each benchmark lives in `intro_specter/benchmarks/<short>_real.py` and exports
a single dataclass with a `name` property and `__iter__` that yields
`BenchmarkExample` instances.

## Dataset loading

Lazy module-level cache:

```python
_HF_DATASET = None  # cached after first access

def _load(split: str) -> Any:
    global _HF_DATASET
    if _HF_DATASET is None or _HF_DATASET[0] != split:
        from datasets import load_dataset
        ds = load_dataset("hotpot_qa", "distractor", split=split)
        _HF_DATASET = (split, ds)
    return _HF_DATASET[1]
```

The cache persists for the lifetime of the Python process; subsequent
`__iter__` calls reuse it. HuggingFace handles its own on-disk cache
under `~/.cache/huggingface/datasets/`.

## Profile + fault injection

Both come from `intro_specter/profiles`:

```python
from ..profiles import inject_fault, inject_profile

profile_dict = inject_profile(task_id=task_id, seed=self.seed, dataset="hotpotqa")
profile = _profile_to_userprofile(profile_dict)  # converts spec-shape dict → UserProfile pydantic

fr = inject_fault(
    task_id=task_id, seed=self.seed,
    profile=profile_dict, gold_answer=answer,
)
gold_fault = fr.target_node_id if fr else None
```

`inject_profile` uses the 28-template bank with deterministic
`hash(task_id, seed)` selection. `inject_fault` is Bernoulli-rate=0.30
deterministic per (task_id, seed) and produces a `FaultRecord`
declaratively for the runner.

## Profile→UserProfile helper

Each loader currently has its own copy of this 9-line helper. Future
refactor candidate; for now just copy it:

```python
def _profile_to_userprofile(profile_dict: dict[str, Any]) -> UserProfile:
    spans = []
    for c in profile_dict["constraints"]:
        spans.append(ProfileSpan(
            id=c["id"],
            text=c["text"],
            kind="constraint" if c["type"] == "hard" else "preference",
            is_hard=(c["type"] == "hard"),
            contradicts=[],
        ))
    return UserProfile(user_id=profile_dict["user_id"], spans=spans)
```

## Verifier rule

A closure factory builds the verifier rule from the dataset's gold:

```python
def _make_rule(meta: dict[str, Any]):
    answer = (meta["answer"] or "").lower()
    banned_substrings = [b.lower() for b in meta.get("banned_substrings", [])]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        out: list[ViolationEvent] = []
        if answer and answer not in text:
            out.append(ViolationEvent(
                violation_id="v_real_factual_miss", ...))
        for b in banned_substrings:
            if b and b in text:
                out.append(ViolationEvent(
                    violation_id="v_real_profile_violation", ...))
                break
        return out

    rule.__name__ = "real_<short>_rule"
    return rule
```

`banned_substrings` is built from the user profile (e.g.,
`"english only"` constraint → ban `["hola", "bonjour", ...]`). Add a
new banned-substring rule per profile category as needed.

## Example schema

```python
return BenchmarkExample(
    task_id=task_id,                              # f"real_<short>_{idx:05d}_{hf_id}"
    dataset=self.name,                            # f"<short>_real"
    profile=profile,                              # UserProfile pydantic
    task=task,                                    # dict with prompt, condition_meta, etc.
    trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
    dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
    gold=GoldLabels(success=None, correct_final_output=answer, fault_node_id=gold_fault),
    rules=[rule],
    split=self.split_of(idx),
)
```

The `trajectory` and `dag` fields start empty; the runner fills them via
the agent priming pass plus the IS pipeline's Layer-1 extraction.

## Runner integration

In `intro_specter/runner.py::_build_benchmark()`:

```python
if spec.benchmark == "hotpotqa_real":
    return HotpotQAReal(
        n_examples=spec.n_examples,
        seed=seed,
        split=spec.split,
    )
```

Add a parallel branch per new benchmark. Benchmark string-id is the
same as the file stem (without `.py`).

## Sample-ID determinism (paired comparisons)

The deterministic sample mapping is the linchpin of paired statistical
tests. Each loader implements:

```python
def _hf_index(self, idx: int) -> int:
    """Deterministic mapping from local idx → row index in the HF split."""
    ds = _load(self.hf_split)
    rng = random.Random(self.seed * <prime> + idx)
    return rng.randint(0, len(ds) - 1)
```

The `<prime>` constant is benchmark-specific (e.g., `1_000_019` for
HotpotQA, `1_000_023` for TruthfulQA) so different benchmarks get
different sub-samples but the same idx within one benchmark always
maps to the same HF row regardless of which run-config asks for it.
**This guarantees**: if seed=42 yields `task_id=real_hotpotqa_00000_5a8fab8c…`
on Direct, the same task_id appears on Self-Refine, Reflexion, ToT,
SelfCheckGPT, and IS — making the paired McNemar / paired-bootstrap
tests valid.

The runner additionally pairs across (task_id, seed): each method runs
on the same trial set, so when it writes JSONL rows, the (task_id, seed)
keys align across methods inside a cell.

## Conditions / verifier metadata

The benchmark stores per-example metadata in `task["condition_meta"]`:

```python
condition_meta = {
    "answer": answer,
    "hotpot_id": ex["id"],
    "hotpot_type": ex["type"],
    "banned_substrings": banned,
    "profile_constraints": profile_dict["constraints"],
    "gold_fault_node": gold_fault,
    "fault_record": (fr.__dict__ if fr else None),
}
```

The aggregator and the manual-error-analysis bundle reach into this
dict to surface profile/fault metadata downstream.

## Output convention

The runner writes one JSONL per (benchmark, model, method, seed):

```
outputs/<tier>/<dataset>__<model_slug>/
  <benchmark>__<split>__seed<n>__<method>.jsonl
  <benchmark>__<split>__results_long.csv
  <benchmark>__<split>__results_wide.csv
  <benchmark>__<split>__summary.json
```

Each JSONL row schema (verified, do NOT change field names):

```json
{"task_id": str, "dataset": str, "method": str, "model": str, "seed": int,
 "success": bool, "constraint_satisfied": bool, "violation_rate": float,
 "profile_violation": bool, "repair_status": str | null,
 "fault_node_predicted": str | null, "posterior": [...] | null,
 "final_output": str, "tokens_input": int, "tokens_output": int,
 "tool_calls": int, "latency_ms": float, "extra": dict}
```

## Smoke-test recipe (Phase 0 sanity check)

Before launching the full matrix, verify the pipeline end-to-end on
n=2 examples on the cheapest model:

```yaml
# configs/real/_smoke_<short>_qwen.yaml
benchmark: <short>_real
split: test
n_examples: 10                # test split = 20% = 2 examples
seeds: [42]
output_dir: outputs/real/_smoke_<short>__qwen-2.5-7b
methods:
  - {name: direct, provider_name: openrouter, model: qwen/qwen-2.5-7b-instruct}
  - {name: intro_specter_llm, provider_name: openrouter, model: qwen/qwen-2.5-7b-instruct,
     temperature: 0.0, extra: {tau_abstain: 0.0, n_counterfactual_trials: 1}}
```

Then `intro-specter run --config <config>` and confirm the JSONL has
2 rows per method and the summary table renders.
