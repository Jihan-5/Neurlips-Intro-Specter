#!/usr/bin/env python3
"""Launch the frozen deterministic A1/A2 shard manifest in detached screens."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "outputs/rebuttal/profile_bootstrap_a1_a2_final"


def live_screens() -> str:
    return subprocess.run(["screen", "-ls"], text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT).stdout


def main() -> None:
    manifest = json.loads((RUN / "sharding_manifest.json").read_text())
    before = live_screens()
    launched = []
    for cell in manifest["cells"]:
        conflict = RUN / cell["cell"] / "a1_conflict_keys.json"
        log_dir = RUN / cell["cell"] / "shards_v1/logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        for shard in cell["shards"]:
            screen = shard["screen"]
            if f".{screen}\t" in before or f".{screen} " in before:
                raise RuntimeError(f"screen already active: {screen}")
            log = log_dir / f"shard-{shard['index']:03d}.log"
            command = (
                f"cd {ROOT} && set -a && source .env.local && set +a && "
                "export HF_DATASETS_OFFLINE=1 && exec caffeinate -i "
                f".venv/bin/python -u scripts/profile_bootstrap_study.py "
                f"--dataset {cell['dataset']} --model {cell['model']} --n-variants 100 "
                f"--cache-read-only-base {cell['base_cache']} --cache-path {shard['cache']} "
                f"--base-output {cell['base_output']} --output-file {shard['output']} "
                f"--assignment-file {shard['assignment']} --conflict-file {conflict.relative_to(ROOT)} "
                f">> {log.relative_to(ROOT)} 2>&1"
            )
            subprocess.run(["screen", "-dmS", screen, "/bin/zsh", "-lc", command],
                           cwd=ROOT, check=True)
            launched.append(screen)
            time.sleep(0.15)
    after = live_screens()
    missing = [name for name in launched
               if f".{name}\t" not in after and f".{name} " not in after]
    if missing:
        raise RuntimeError(f"shard screens failed to stay active: {missing}")
    print(json.dumps({"launched": len(launched), "screens": launched}, indent=2))


if __name__ == "__main__":
    main()
