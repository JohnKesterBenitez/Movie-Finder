import sys
from pathlib import Path

# Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from k3_rms.app import build_context_from_env

def init():
    try:
        print("Initializing schema...")
        build_context_from_env()
        print("Schema initialization complete.")
    except Exception as e:
        print(f"Error initializing schema: {e}")

if __name__ == "__main__":
    init()
