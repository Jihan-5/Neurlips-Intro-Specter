"""Command-line entry point for Intro-Specter experiments.

Examples:
    intro-specter run --benchmark synthetic_dag --n 50 \\
        --method direct --method intro_specter --method oracle_repair --method full_regen \\
        --output outputs/dryrun

    intro-specter run --config configs/synthetic_dag.yaml
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
@click.option("--n", "n_examples", default=50, type=int)
@click.option("--seed", default=0, type=int)
@click.option(
    "--method",
    "methods",
    multiple=True,
    default=("direct", "full_regen", "oracle_repair", "intro_specter"),
)
@click.option("--provider", default="mock", help="Default provider for LLM-using methods.")
@click.option("--model", default="", help="Default model id.")
@click.option("--output", "output_dir", default="outputs/dryrun")
@click.option("--cache", "cache_path", default="cache/completions.sqlite")
@click.option("--verifier-provider", default=None)
@click.option("--verifier-model", default="")
def run_cmd(
    config: str | None,
    benchmark: str,
    n_examples: int,
    seed: int,
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
            n_examples=n_examples,
            seed=seed,
            output_dir=output_dir,
            cache_path=cache_path,
            verifier_provider=verifier_provider,
            verifier_model=verifier_model,
            methods=[
                MethodConfig(
                    name=m,
                    provider_name=provider if m != "direct" else "none",
                    model=model,
                    seed=seed,
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

    table = Table(title=f"Summary — {summary.get('benchmark')} (n={summary.get('n')})")
    table.add_column("method")
    table.add_column("success", justify="right")
    table.add_column("violation", justify="right")
    table.add_column("Δsuccess vs direct", justify="right")
    table.add_column("95% CI", justify="right")
    table.add_column("tokens_in", justify="right")
    table.add_column("tokens_out", justify="right")

    for name, m in methods.items():
        delta = m.get("delta_success_vs_direct")
        ci_low = m.get("delta_success_ci_low")
        ci_high = m.get("delta_success_ci_high")
        table.add_row(
            name,
            f"{m['success_rate']:.3f}",
            f"{m['violation_rate']:.3f}",
            "—" if delta is None else f"{delta:+.3f}",
            "—" if ci_low is None else f"[{ci_low:+.3f}, {ci_high:+.3f}]",
            f"{m['tokens_input_mean']:.0f}",
            f"{m['tokens_output_mean']:.0f}",
        )
    console.print(table)
    console.print(f"\nDetailed outputs: [cyan]{output_dir}[/cyan]")


@main.command("show")
@click.argument("output_dir", type=click.Path(exists=True))
def show_cmd(output_dir: str) -> None:
    """Render the summary for a previous run."""
    out = Path(output_dir)
    candidates = list(out.glob("*__summary.json"))
    if not candidates:
        console.print(f"[red]no summary.json under {output_dir}[/red]")
        raise SystemExit(1)
    summary = json.loads(candidates[0].read_text())
    _render_summary(summary, output_dir)


if __name__ == "__main__":  # pragma: no cover
    main()
