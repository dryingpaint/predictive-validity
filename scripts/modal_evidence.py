"""Run the evidence steps that read large raw releases on Modal, where their downloads fit.

    modal run scripts/modal_evidence.py                     # every step in STEPS, in order
    modal run scripts/modal_evidence.py --steps "pipeline.chembl activities"

Open Targets evidence and associations, the evidence-date sources and the ChEMBL MySQL dump take tens
of GB on disk. Each step runs as `python -m <step>` in a container holding this checkout, with the
Volume VOLUME mounted as the checkout's .cache, so a release downloaded once is reused by later runs.
The steps write to the database named by the local .env's DATABASE_URL, exactly as they would run
locally; run them in Makefile order, after `make labels` has resolved entity targets.
"""
from __future__ import annotations

import os
import subprocess
import tomllib

import modal
from dotenv import dotenv_values

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOLUME = "pv-evidence-cache"
STEPS = ("pipeline.opentargets fetch", "pipeline.opentargets load", "pipeline.evidence_dates clinvar",
         "pipeline.evidence_dates impc", "pipeline.evidence_dates studies", "pipeline.evidence_dates projectscore",
         "pipeline.opentargets evidence", "pipeline.chembl activities")  # the Makefile evidence steps with raw releases

with open(os.path.join(REPO, "pyproject.toml"), "rb") as f:
    DEPENDENCIES = tomllib.load(f)["project"]["dependencies"]
image = (modal.Image.debian_slim(python_version="3.12")
         .uv_pip_install(*DEPENDENCIES)
         .add_local_dir(REPO, "/repo", ignore=[".venv", ".cache", ".git", ".env", "**/__pycache__", "report/output"]))
volume = modal.Volume.from_name(VOLUME, create_if_missing=True)
env = dotenv_values(os.path.join(REPO, ".env"))
secret = modal.Secret.from_dict({k: env[k] for k in ("DATABASE_URL", "ANTHROPIC_API_KEY") if env.get(k)})
app = modal.App("predictive-validity-evidence")


@app.function(image=image, volumes={"/repo/.cache": volume}, secrets=[secret], cpu=8, memory=65536,
              timeout=24 * 3600)
def run(steps: list[str]) -> None:
    for step in steps:
        print(f"=== {step}", flush=True)
        subprocess.run(["python", "-m", *step.split()], cwd="/repo", env={**os.environ, "PYTHONPATH": "/repo"},
                       check=True)
        volume.commit()


@app.local_entrypoint()
def main(steps: str = ",".join(STEPS)) -> None:
    run.remote([s.strip() for s in steps.split(",") if s.strip()])
