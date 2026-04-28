"""Command-line entry point for Intro-Specter experiments.

Examples:

    # Tier-C synthetic, single_fault mode, test split, 3 seeds
    intro-specter run --config configs/synthetic_single_fault_test.yaml

    # Quick sanity ping
    intro-specter run --benchmark synthetic_dag --mode single_fault --split test \\
        --n 30 --seeds 0 1 2 \\
        --method direct --method intro_specter --method oracle_repair \\
        --method oracle_detector --method full_regen \\
        --output outputs/dryrun
"""

from __future__ import annotations

import json
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

from .runner import MethodConfig, RunSpec, run

console = Console()


@click.group()
def main() -> None:
    """Intro-Specter experiment runner."""


@main.command("run")
@click.option("--config", type=click.Path(exists=True), default=None, help="YAML config path.")
@click.option("--benchmark", default="synthetic_dag")
@click.option(
    "--mode",
    default=None,
    type=click.Choice(["single_fault", "multi_valid"]),
    help="Synthetic-only mode flag.",
)
@click.option(
    "--split",
    default="all",
    type=click.Choice(["train", "val", "test", "all"]),
)
@click.option("--n", "n_examples", default=50, type=int)
@click.option("--seeds", multiple=True, type=int, default=(0,))
@click.option(
    "--method",
    "methods",
    multiple=True,
    default=(
        "direct",
        "full_regen",
        "oracle_repair",
        "oracle_detector",
        "intro_specter",
    ),
)
@click.option("--provider", default="none", help="Default provider for LLM-using methods.")
@click.option("--model", default="", help="Default model id.")
@click.option("--output", "output_dir", default="outputs/dryrun")
@click.option("--cache", "cache_path", default="cache/completions.sqlite")
@click.option("--verifier-provider", default=None)
@click.option("--verifier-model", default="")
def run_cmd(
    config: str | None,
    benchmark: str,
    mode: str | None,
    split: str,
    n_examples: int,
    seeds: tuple[int, ...],
    methods: tuple[str, ...],
    provider: str,
    model: str,
    output_dir: str,
    cache_path: str,
    verifier_provider: str | None,
    verifier_model: str,
) -> None:
    if config:
        spec = _spec_from_yaml(Path(config))
    else:
        spec = RunSpec(
            benchmark=benchmark,
            mode=mode,
            split=split,
            n_examples=n_examples,
            seeds=list(seeds),
            output_dir=output_dir,
            cache_path=cache_path,
            verifier_provider=verifier_provider,
            verifier_model=verifier_model,
            methods=[
                MethodConfig(
                    name=m,
                    provider_name=provider if m not in {"direct", "full_regen", "oracle_repair", "oracle_detector", "intro_specter"} else "none",
                    model=model,
                )
                for m in methods
            ],
        )

    summary = run(spec)
    _render_summary(summary, spec.output_dir)


def _spec_from_yaml(path: Path) -> RunSpec:
    data = yaml.safe_load(path.read_text())
    methods = [MethodConfig(**m) for m in data.pop("methods", [])]
    return RunSpec(methods=methods, **data)


def _render_summary(summary: dict, output_dir: str) -> None:
    methods = summary.get("methods", {})
    if not methods:
        console.print("[yellow]No method results to summarize.[/yellow]")
        return

    n_total = summary.get("n_total_rows", "?")
    n_examples = summary.get("n_examples", "?")
    seeds = summary.get("seeds", [])
    label = summary.get("benchmark", "?")
    table = Table(
        title=f"Summary — {label}  (examples={n_examples} × seeds={len(seeds)} = {n_total} rows)",
    )
    table.add_column("method")
    table.add_column("success", justify="right")
    table.add_column("violation", justify="right")
    table.add_column("tokens", justify="right")
    table.add_column("Δsuccess vs direct", justify="right")
    table.add_column("McNemar p", justify="right")
    table.add_column("Holm-adj", justify="right")

    for name, m in methods.items():
        delta = m.get("delta_success")
        ci_low = m.get("delta_success_ci_low")
        ci_high = m.get("delta_success_ci_high")
        mc_p = m.get("mcnemar_success_p")
        holm_p = m.get("holm_success_p_adj")
        ci_str = "—" if ci_low is None else f"[{ci_low:+.3f}, {ci_high:+.3f}]"
        delta_str = "—" if delta is None else f"{delta:+.3f} {ci_str}"
        table.add_row(
            name,
            f"{m['success_rate']:.3f}",
            f"{m['violation_rate']:.3f}",
            f"{m['tokens_input_mean'] + m['tokens_output_mean']:.0f}",
            delta_str,
            "—" if mc_p is None else f"{mc_p:.3g}",
            "—" if holm_p is None else f"{holm_p:.3g}",
        )
    console.print(table)
    console.print(f"\nDetailed outputs: [cyan]{output_dir}[/cyan]")


@main.command("show")
@click.argument("output_dir", type=click.Path(exists=True))
@click.option("--label", default=None, help="Optional benchmark label prefix.")
def show_cmd(output_dir: str, label: str | None) -> None:
    """Render the summary for a previous run."""
    out = Path(output_dir)
    pattern = f"{label}__summary.json" if label else "*__summary.json"
    candidates = sorted(out.glob(pattern))
    if not candidates:
        console.print(f"[red]no summary.json under {output_dir}[/red]")
        raise SystemExit(1)
    for p in candidates:
        summary = json.loads(p.read_text())
        _render_summary(summary, output_dir)


if __name__ == "__main__":  # pragma: no cover
    main()
