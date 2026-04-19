"""
Deploy second-brain FastAPI backend to TrueFoundry.

Usage:
    python deploy/deploy_backend.py

Reads credentials from .env in the project root.

Storage: A persistent volume is created (or reused) and mounted at /app/data
so that wiki pages, the knowledge graph, and output files survive pod restarts,
spot-instance preemptions, and redeployments.
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from truefoundry.deploy import (
    Build,
    DockerFileBuild,
    DynamicVolumeConfig,
    LocalSource,
    NodeSelector,
    Port,
    Resources,
    Service,
    Volume,
    VolumeMount,
)

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO)

# TFY_HOST is the platform URL (not the LLM gateway URL)
os.environ.setdefault("TFY_HOST", "https://internal.devtest.truefoundry.tech")

WORKSPACE_FQN = "tfy-usea1-devtest:harsh-ws"
SERVICE_HOST   = "second-brain-backend.tfy-usea1-ctl.devtest.truefoundry.tech"
REPO_ROOT      = str(Path(__file__).parent.parent.resolve())
VOLUME_NAME    = "second-brain-data"

# ── Step 1: Create (or update) the persistent volume ─────────────────────────
# This is idempotent — running the script again reuses the existing volume.
# All wiki pages, graph data, and output files live here and survive restarts.
volume = Volume(
    name=VOLUME_NAME,
    config=DynamicVolumeConfig(
        storage_class="efs-sc",
        size=10,                   # GB
    ),
)
volume.deploy(workspace_fqn=WORKSPACE_FQN, wait=True)
volume_fqn = f"tfy-volume://{WORKSPACE_FQN}:{VOLUME_NAME}"
logging.info("Volume FQN: %s", volume_fqn)

# ── Step 2: Deploy the service with the volume mounted at /app/data ───────────
service = Service(
    name="second-brain-backend",
    image=Build(
        build_source=LocalSource(
            project_root_path=REPO_ROOT,
            local_build=True,
        ),
        build_spec=DockerFileBuild(
            dockerfile_path="Dockerfile",
            build_context_path="./",
        ),
    ),
    ports=[
        Port(
            port=8000,
            protocol="TCP",
            expose=True,
            app_protocol="http",
            host=SERVICE_HOST,
        )
    ],
    resources=Resources(
        cpu_request=0.5,
        cpu_limit=1.0,
        memory_request=1024,
        memory_limit=2048,
        ephemeral_storage_request=1000,
        ephemeral_storage_limit=2000,
        node=NodeSelector(capacity_type="spot_fallback_on_demand"),
    ),
    mounts=[
        # All wiki data persists here across restarts and redeployments
        VolumeMount(
            mount_path="/app/data",
            volume_fqn=volume_fqn,
        ),
    ],
    env={
        "TFY_API_KEY":      os.environ["TFY_API_KEY"],
        "TFY_BASE_URL":     os.environ["TFY_BASE_URL"],
        "DEFAULT_MODEL":    os.getenv("DEFAULT_MODEL", "tfy-ai-anthropic/claude-sonnet-4-6"),
        "SUPADATA_API_KEY": os.environ["SUPADATA_API_KEY"],
        "YOUTUBE_COOKIES_FILE": "/etc/cookies.txt",
    },
    replicas=1,
)

service.deploy(workspace_fqn=WORKSPACE_FQN, wait=True)
