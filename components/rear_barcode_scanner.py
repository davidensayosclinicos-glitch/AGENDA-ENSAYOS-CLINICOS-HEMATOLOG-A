from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

_COMPONENT_DIR = Path(__file__).resolve().parent / "rear_barcode_scanner_frontend"
_rear_scanner = components.declare_component(
    "rear_barcode_scanner",
    path=str(_COMPONENT_DIR),
)


def rear_barcode_scanner(label: str, key: str, height: int = 300):
    """Render a rear-camera scanner and return detected barcode/text payload.

    Returns:
        dict: {"code": str, "text": str, "source": str} when available.
    """
    value = _rear_scanner(label=label, key=key, default={}, height=height)
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    # Compatibilidad con versiones antiguas del frontend que devuelven string.
    return {"code": str(value).strip(), "text": "", "source": "legacy"}
