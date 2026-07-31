"""Physics verification helpers."""

from __future__ import annotations

import re
from typing import Optional

from app.verification.math_verifier import compare_numeric, extract_numbers
from app.verification.schemas import ToolCallRecord

_UNIT_ALIASES = {
    "m/s": "meter/second",
    "m/s2": "meter/second**2",
    "m s-1": "meter/second",
    "kg": "kilogram",
    "n": "newton",
    "j": "joule",
    "w": "watt",
    "pa": "pascal",
    "atm": "atmosphere",
    "l": "liter",
    "mol": "mole",
}


def validate_numeric_tolerance(
    submitted: float, official: float, *, rel_tol: float = 0.02, abs_tol: float = 0.5
) -> tuple[bool, ToolCallRecord]:
    ok, detail = compare_numeric(submitted, official, rel_tol=rel_tol, abs_tol=abs_tol)
    return ok, ToolCallRecord(
        tool="physics.validate_numeric_tolerance",
        input_summary=f"{submitted} vs {official}",
        output_summary=detail,
        success=ok,
    )


def match_option(submitted: str, official: str) -> tuple[bool, ToolCallRecord]:
    sub = submitted.strip().upper()
    off = official.strip().upper()
    ok = sub == off
    return ok, ToolCallRecord(
        tool="physics.match_option",
        input_summary=f"{sub} vs {off}",
        output_summary="match" if ok else "mismatch",
        success=ok,
    )


def check_dimensions(expression: str, expected_unit: Optional[str] = None) -> tuple[bool, ToolCallRecord]:
    """Basic dimensional check when pint is available."""
    try:
        import pint

        ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
        _ = ureg.parse_expression(expression)
        return True, ToolCallRecord(
            tool="physics.check_dimensions",
            input_summary=expression[:60],
            output_summary="parseable",
            success=True,
        )
    except Exception as exc:
        return False, ToolCallRecord(
            tool="physics.check_dimensions",
            input_summary=expression[:60],
            output_summary="skipped",
            success=False,
            error=str(exc),
        )


def extract_physics_answer(message: str) -> Optional[float]:
    nums = extract_numbers(message)
    return nums[-1] if nums else None
