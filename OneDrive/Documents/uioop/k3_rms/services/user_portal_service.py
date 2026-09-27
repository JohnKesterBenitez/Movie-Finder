import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UserPortalHandle:
    process: subprocess.Popen
    session_file: Path


def launch_user_portal(session_user: dict) -> UserPortalHandle:
    project_root = Path(__file__).resolve().parent.parent.parent
    user_main = project_root / "k3_user" / "main.py"
    if not user_main.exists():
        raise FileNotFoundError(f"User portal entry point not found: {user_main}")

    session_file = _write_session_file(session_user)
    try:
        process = subprocess.Popen(
            [_python_gui_executable(), str(user_main), "--session-file", str(session_file), "--integrated"],
            cwd=str(project_root),
        )
    except Exception:
        session_file.unlink(missing_ok=True)
        raise
    return UserPortalHandle(process=process, session_file=session_file)


def cleanup_user_portal(handle: UserPortalHandle | None) -> None:
    if handle is None:
        return
    try:
        handle.session_file.unlink(missing_ok=True)
    except OSError:
        pass


def _write_session_file(session_user: dict) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".json",
        prefix="k3_user_session_",
        delete=False,
    ) as session_file:
        json.dump(session_user, session_file)
        return Path(session_file.name)


def _python_gui_executable() -> str:
    executable = Path(sys.executable)
    if executable.name.lower() == "python.exe":
        pythonw = executable.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return str(executable)
