"""Pickle-based save/resume for long-running pipeline stages."""

import logging
import pickle
from pathlib import Path

from config.settings import CHECKPOINT_DIR

logger = logging.getLogger(__name__)


def checkpoint_path(name: str) -> Path:
    return CHECKPOINT_DIR / f"{name}.pkl"


def save_checkpoint(name: str, data) -> Path:
    """Save data to a named checkpoint file."""
    path = checkpoint_path(name)
    with open(path, "wb") as f:
        pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
    logger.debug(f"Checkpoint saved: {name} ({path.stat().st_size:,} bytes)")
    return path


def load_checkpoint(name: str):
    """Load data from a named checkpoint. Returns None if not found."""
    path = checkpoint_path(name)
    if not path.exists():
        return None
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
        logger.info(f"Checkpoint loaded: {name}")
        return data
    except (pickle.UnpicklingError, EOFError, OSError) as e:
        logger.warning(f"Failed to load checkpoint {name}: {e}")
        return None


def has_checkpoint(name: str) -> bool:
    return checkpoint_path(name).exists()


def clear_checkpoint(name: str):
    path = checkpoint_path(name)
    if path.exists():
        path.unlink()
        logger.info(f"Checkpoint cleared: {name}")


def clear_all_checkpoints():
    """Remove all checkpoint files."""
    count = 0
    for path in CHECKPOINT_DIR.glob("*.pkl"):
        path.unlink()
        count += 1
    logger.info(f"Cleared {count} checkpoint files")
