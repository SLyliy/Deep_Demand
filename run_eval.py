from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CASES_PATH = BASE_DIR / "eval_cases.json"


def normalize_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [normalize_text(item) for item in value if normalize_text(item)]
    if normalize_text(value):
        return [normalize_text(value)]
    return []


USER_VISIBLE_KEYS = {
    "business_domain",
    "business_object",
    "related_systems",
    "candidate_systems",
    "pain_points",
    "system_actions",
    "target_users",
    "current_manual_process",
    "process_breakpoint",
    "passive_consequence",
    "minimum_system_behavior",
    "real_intent",
    "rewritten_request",
    "suggested_request",
    "diagnosis",
    "structured_report",
    "uncertain_items",
}


def flatten_result_text(result: dict[str, Any]) -> str:
    chunks: list[str] = []

    def collect(value: Any, *, top_level: bool = False) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if top_level and key not in USER_VISIBLE_KEYS:
                    continue
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)
        elif value is not None:
            chunks.append(normalize_text(value))

    collect(result, top_level=True)
    return "\n".join(chunk for chunk in chunks if chunk)


def any_expected_hit(actual_values: list[str], expected_values: list[str]) -> bool:
    actual_text = " ".join(actual_values)
    return any(expected and expected in actual_text for expected in expected_values)


def score_case(result: dict[str, Any], case: dict[str, Any]) -> dict[str, Any]:
    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    result_text = flatten_result_text(result)
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": passed, "detail": detail})

    field_map = {
        "business_domain": normalize_list(result.get("business_domain")),
        "business_object": normalize_list(result.get("business_object"))
        + normalize_list((result.get("diagnosis") or {}).get("business_object") if isinstance(result.get("diagnosis"), dict) else ""),
        "related_systems": normalize_list(result.get("related_systems")) + normalize_list(result.get("candidate_systems")),
        "pain_points": normalize_list(result.get("pain_points")),
        "system_actions": normalize_list(result.get("system_actions"))
        + normalize_list((result.get("diagnosis") or {}).get("desired_system_behavior") if isinstance(result.get("diagnosis"), dict) else []),
    }

    for field_name, actual_values in field_map.items():
        expected_values = normalize_list(expected.get(field_name))
        if not expected_values:
            continue
        add_check(
            field_name,
            any_expected_hit(actual_values, expected_values),
            f"actual={actual_values}; expected_any={expected_values}",
        )

    for phrase in normalize_list(expected.get("must_include")):
        add_check(f"must_include:{phrase}", phrase in result_text, phrase)

    for phrase in normalize_list(expected.get("must_not_include")):
        add_check(f"must_not_include:{phrase}", phrase not in result_text, phrase)

    passed_count = sum(1 for check in checks if check["passed"])
    total_count = len(checks)
    return {
        "id": case.get("id"),
        "input": case.get("input"),
        "score": round(passed_count / total_count, 3) if total_count else 0,
        "passed": passed_count == total_count,
        "passed_count": passed_count,
        "total_count": total_count,
        "checks": checks,
        "summary": {
            "business_domain": result.get("business_domain"),
            "business_object": result.get("business_object") or (result.get("diagnosis") or {}).get("business_object") if isinstance(result.get("diagnosis"), dict) else "",
            "related_systems": result.get("related_systems"),
            "candidate_systems": result.get("candidate_systems"),
            "pain_points": result.get("pain_points"),
            "system_actions": result.get("system_actions"),
            "suggested_request": result.get("suggested_request"),
            "mode": result.get("mode"),
        },
    }


def load_cases(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("eval cases file must contain a JSON array")
    return [case for case in data if isinstance(case, dict)]


def run_case(case: dict[str, Any], mode: str) -> dict[str, Any]:
    import app

    user_input = normalize_text(case.get("input"))
    if not user_input:
        raise ValueError(f"case {case.get('id')} has empty input")
    if mode == "fast":
        retrieved_context = app.retrieve_context(user_input)
        fallback = app.build_fast_fallback_from_context(user_input, retrieved_context)
        return app.normalize_fast_analysis_result(
            fallback,
            user_input,
            retrieved_context,
            used_llm=False,
            used_fallback=True,
            elapsed_ms=0,
        )
    return app.run_full_analysis(user_input)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run synthetic evaluation cases for Deep Demand MVP.")
    parser.add_argument("--cases", default=str(DEFAULT_CASES_PATH), help="Path to eval_cases.json")
    parser.add_argument("--mode", choices=["fast", "full"], default="fast", help="Evaluation target")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    if args.mode == "fast":
        os.environ.setdefault("LLM_API_KEY", "")
        os.environ.setdefault("LLM_BASE_URL", "")
        os.environ.setdefault("LLM_MODEL", "")

    cases = load_cases(Path(args.cases))
    results = [score_case(run_case(case, args.mode), case) for case in cases]
    passed = sum(1 for item in results if item["passed"])
    average_score = round(sum(item["score"] for item in results) / len(results), 3) if results else 0
    report = {
        "mode": args.mode,
        "case_count": len(results),
        "passed_count": passed,
        "average_score": average_score,
        "results": results,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"mode={report['mode']} cases={report['case_count']} passed={report['passed_count']} avg={report['average_score']}")
        for item in results:
            status = "PASS" if item["passed"] else "FAIL"
            print(f"{status} {item['id']} score={item['score']} {item['passed_count']}/{item['total_count']}")
            for check in item["checks"]:
                if not check["passed"]:
                    print(f"  - {check['name']}: {check['detail']}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
