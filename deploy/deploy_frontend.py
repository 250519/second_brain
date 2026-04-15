"""
Deploy second-brain React frontend to TrueFoundry.

Usage:
    python deploy/deploy_frontend.py

Reads credentials from .env in the project root.
The frontend Dockerfile bakes in VITE_API_URL at build time so the
browser knows where to reach the backend.
"""
import logging
from pathlib import Path

from dotenv import load_dotenv
from truefoundry.deploy import (
    Build,
    DockerFileBuild,
    LocalSource,
    NodeSelector,
    Port,
    Resources,
    Service,
)

import os

load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO)

os.environ.setdefault("TFY_HOST", "https://internal.devtest.truefoundry.tech")

WORKSPACE_FQN  = "tfy-usea1-devtest:harsh-ws"
SERVICE_HOST   = "second-brain-frontend.tfy-usea1-ctl.devtest.truefoundry.tech"
BACKEND_URL    = "https://second-brain-backend.tfy-usea1-ctl.devtest.truefoundry.tech"
FRONTEND_ROOT  = str(Path(__file__).parent.parent.resolve() / "frontend")

service = Service(
    name="second-brain-frontend",
    image=Build(
        build_source=LocalSource(
            project_root_path=FRONTEND_ROOT,
            local_build=True,
        ),
        build_spec=DockerFileBuild(
            dockerfile_path="Dockerfile",
            build_context_path="./",
            build_args={"VITE_API_URL": BACKEND_URL},
        ),
    ),
    ports=[
        Port(
            port=80,
            protocol="TCP",
            expose=True,
            app_protocol="http",
            host=SERVICE_HOST,
        )
    ],
    resources=Resources(
        cpu_request=0.1,
        cpu_limit=0.5,
        memory_request=128,
        memory_limit=256,
        ephemeral_storage_request=500,
        ephemeral_storage_limit=1000,
        node=NodeSelector(capacity_type="spot_fallback_on_demand"),
    ),
    replicas=1,
)

service.deploy(workspace_fqn=WORKSPACE_FQN, wait=True)
