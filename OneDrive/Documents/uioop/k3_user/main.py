"""
K3's Floating Cottage - User Portal
Entry point: python main.py
"""

import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import K3App


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-file", default="")
    parser.add_argument("--integrated", action="store_true")
    return parser.parse_args()


def _load_session(session_file: str) -> dict | None:
    if not session_file:
        return None
    path = Path(session_file)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as source:
        return json.load(source)


if __name__ == "__main__":
    args = _parse_args()
    session_user = _load_session(args.session_file)
    if args.integrated and session_user is None:
        raise SystemExit("Integrated user portal launch requires a valid session file.")
    app = K3App(
        session_user=session_user,
        integrated_auth=args.integrated,
    )
    app.mainloop()
