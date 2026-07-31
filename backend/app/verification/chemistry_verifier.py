"""Chemistry verification helpers."""

from __future__ import annotations

import re
from typing import Optional

from app.verification.math_verifier import compare_numeric, extract_numbers
from app.verification.schemas import ToolCallRecord

_ATOMIC_MASS = {
    "H": 1.008,
    "C": 12.011,
    "N": 14.007,
    "O": 15.999,
    "S": 32.06,
    "P": 30.974,
    "Cl": 35.45,
    "Br": 79.904,
    "I": 126.904,
    "Na": 22.99,
    "K": 39.098,
    "Ca": 40.078,
    "Fe": 55.845,
    "Cu": 63.546,
    "Ba": 137.327,
}


def compute_molar_mass(formula: str) -> tuple[Optional[float], ToolCallRecord]:
    """Parse simple chemical formulas like H2O, CO2."""
    pattern = re.compile(r"([A-Z][a-z]?)(\d*)")
    total = 0.0
    try:
        for elem, count in pattern.findall(formula):
            if not elem:
                continue
            if elem not in _ATOMIC_MASS:
                raise ValueError(f"Unknown element: {elem}")
            mult = int(count) if count else 1
            total += _ATOMIC_MASS[elem] * mult
        return total, ToolCallRecord(
            tool="chemistry.compute_molar_mass",
            input_summary=formula,
            output_summary=f"{total:.3f} g/mol",
            success=True,
        )
    except Exception as exc:
        return None, ToolCallRecord(
            tool="chemistry.compute_molar_mass",
            input_summary=formula,
            output_summary="failed",
            success=False,
            error=str(exc),
        )


def verify_numeric_answer(message: str, official: str) -> tuple[bool, list[ToolCallRecord], str]:
    calls: list[ToolCallRecord] = []
    submitted = extract_numbers(message)
    official_nums = extract_numbers(str(official))
    if not official_nums:
        return False, calls, "No official numeric answer."
    if not submitted:
        return False, calls, "No numeric value submitted."
    ok, detail = compare_numeric(submitted[-1], official_nums[0], rel_tol=0.03, abs_tol=1.0)
    calls.append(
        ToolCallRecord(
            tool="chemistry.validate_numeric",
            input_summary=f"{submitted[-1]} vs {official_nums[0]}",
            output_summary=detail,
            success=ok,
        )
    )
    return ok, calls, detail
