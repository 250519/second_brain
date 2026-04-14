"""
Entry point for running the Second Brain API server.

Usage:
    uv run python backend/server.py                   # default: 0.0.0.0:8000
    uv run python backend/server.py --port 9000
    uv run python backend/server.py --reload          # dev mode
    uv run second-brain serve                         # same via CLI
"""

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Second Brain API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Auto-reload (dev only)")
    args = parser.parse_args()

    print(f"Starting Second Brain API → http://{args.host}:{args.port}")
    print(f"  Swagger UI : http://localhost:{args.port}/docs")
    print(f"  ReDoc      : http://localhost:{args.port}/redoc")

    uvicorn.run(
        "second_brain.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
