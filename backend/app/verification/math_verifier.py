"""SymPy-based math verification — safe parsing, no arbitrary code execution."""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.verification.schemas import ToolCallRecord

logger = logging.getLogger("tutor.verification.math")

_NUMERIC_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def _safe_parse(expr: str):
    from sympy import sympify
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication_application,
        standard_transformations,
    )

    transformations = standard_transformations + (
        implicit_multiplication_application,
        convert_xor,
    )
    cleaned = expr.replace("^", "**")
    return sympify(cleaned, transformations=transformations)


def extract_numbers(text: str) -> list[float]:
    return [float(m.group()) for m in _NUMERIC_RE.finditer(text or "")]


def compare_expressions(a: str, b: str, *, rel_tol: float = 1e-4) -> tuple[bool, str]:
    try:
        from sympy import simplify, sympify

        expr_a = sympify(a.strip())
        expr_b = sympify(b.strip())
        diff = simplify(expr_a - expr_b)
        if diff == 0:
            return True, "Expressions are equivalent."
        try:
            val_a = float(expr_a.evalf())
            val_b = float(expr_b.evalf())
            if abs(val_a - val_b) <= rel_tol * max(1.0, abs(val_a), abs(val_b)):
                return True, f"Numeric values match within tolerance ({val_a} ≈ {val_b})."
        except (TypeError, ValueError):
            pass
        return False, "Expressions differ."
    except Exception as exc:
        return False, f"Expression comparison failed: {exc}"


def evaluate_numeric(expr: str) -> tuple[Optional[float], str]:
    try:
        value = float(_safe_parse(expr).evalf())
        return value, f"Evaluated to {value}"
    except Exception as exc:
        return None, f"Numeric evaluation failed: {exc}"


def compare_numeric(
    submitted: float, official: float, *, rel_tol: float = 0.02, abs_tol: float = 0.5
) -> tuple[bool, str]:
    diff = abs(submitted - official)
    if diff <= abs_tol:
        return True, f"Within absolute tolerance ({submitted} ≈ {official})."
    if official != 0 and diff / abs(official) <= rel_tol:
        return True, f"Within relative tolerance ({submitted} ≈ {official})."
    return False, f"Values differ: submitted={submitted}, official={official}"


def match_mcq_option(submitted: str, official: str) -> tuple[bool, ToolCallRecord]:
    sub = submitted.strip().upper()
    off = official.strip().upper()
    ok = sub == off
    return ok, ToolCallRecord(
        tool="math.match_mcq_option",
        input_summary=f"submitted={sub}, official={off}",
        output_summary="match" if ok else "mismatch",
        success=True,
    )


def verify_numeric_submission(
    message: str, official: str, *, rel_tol: float = 0.02
) -> tuple[bool, list[ToolCallRecord], str]:
    calls: list[ToolCallRecord] = []
    submitted_nums = extract_numbers(message)
    official_nums = extract_numbers(str(official))

    if not official_nums:
        return False, calls, "No official numeric answer to compare."

    official_val = official_nums[0]
    if not submitted_nums:
        calls.append(
            ToolCallRecord(
                tool="math.extract_numbers",
                input_summary=message[:80],
                output_summary="no numbers found",
                success=False,
                error="No numeric value in submission",
            )
        )
        return False, calls, "Could not extract a numeric answer from your message."

    submitted_val = submitted_nums[-1]
    ok, detail = compare_numeric(submitted_val, official_val, rel_tol=rel_tol)
    calls.append(
        ToolCallRecord(
            tool="math.compare_numeric",
            input_summary=f"submitted={submitted_val}, official={official_val}",
            output_summary=detail,
            success=ok,
        )
    )
    return ok, calls, detail
