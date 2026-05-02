"""
Logging utilities for the FinRL Trading Platform.
"""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level=logging.INFO,
    log_file: Optional[str] = None,
    log_dir: str = "./logs"
) -> None:
    if log_file:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_path = Path(log_dir) / log_file
    else:
        log_path = None

    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)

    handlers = [logging.StreamHandler(sys.stdout)]

    if log_path:
        handlers.append(logging.FileHandler(log_path))

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )
