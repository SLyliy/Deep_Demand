from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path

import requests
from flask import Flask, jsonify, request, send_file


BASE_DIR = Path(__file__).resolve().parent


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from a .env file without extra dependencies."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and os.getenv(key) is None:
            os.environ[key] = value


load_env_file(BASE_DIR / ".env")

app = Flask(__name__, static_folder="assets", static_url_path="/assets")
app.config["JSON_AS_ASCII"] = False
app.logger.setLevel(logging.INFO)


def load_business_context() -> dict:
    context_path = BASE_DIR / "business_context.json"
    with context_path.open("r", encoding="utf-8") as file:
        return json.load(file)


BUSINESS_CONTEXT = load_business_context()


DOMAIN_CONFIG = [
    {
        "code": "procurement",
        "name": "??",
        "keywords": ["??", "???", "??", "??", "??", "??", "BOM", "??"],
        "description": "???????????????????",
    },
    {
        "code": "finance",
        "name": "??",
        "keywords": ["??", "??", "??", "??", "??", "??", "??", "??"],
        "description": "?????????????????",
    },
    {
        "code": "hr",
        "name": "HR",
        "keywords": ["HR", "??", "??", "??", "??", "??", "??", "??", "??"],
        "description": "???????????????",
    },
    {
        "code": "legal",
        "name": "??",
        "keywords": ["??", "??", "??", "??", "??", "??", "??", "??"],
        "description": "????????????????",
    },
    {
        "code": "warehouse",
        "name": "??",
        "keywords": ["??", "??", "??", "???", "??", "??", "??", "??", "??"],
        "description": "????????????????",
    },
    {
        "code": "production",
        "name": "??",
        "keywords": ["??", "??", "??", "??", "??", "??", "??", "??"],
        "description": "??????????????????",
    },
    {
        "code": "sales",
        "name": "??",
        "keywords": ["??", "??", "??", "??", "??", "??", "??", "??"],
        "description": "??????????????????",
    },
    {
        "code": "general",
        "name": "??",
        "keywords": [],
        "description": "????????????",
    },
]

PAIN_CONFIG = [
    {
        "code": "timeliness",
        "name": "???",
        "keywords": ["?", "??", "??", "???", "??", "???", "??"],
        "phrase": "?????",
    },
    {
        "code": "omission",
        "name": "???",
        "keywords": ["?", "??", "??", "??", "??", "??", "???"],
        "phrase": "????",
    },
    {
        "code": "accuracy",
        "name": "????",
        "keywords": ["??", "??", "??", "???", "??", "?????", "???"],
        "phrase": "??????",
    },
    {
        "code": "manual_heavy",
        "name": "????",
        "keywords": ["??", "??", "??", "??", "Excel", "??", "????", "???", "????"],
        "phrase": "???????",
    },
    {
        "code": "workflow_block",
        "name": "????",
        "keywords": ["??", "??", "??", "??", "???", "???", "??"],
        "phrase": "??????",
    },
    {
        "code": "risk_hidden",
        "name": "?????",
        "keywords": ["??", "??", "??", "??", "??", "??", "???", "?????", "???"],
        "phrase": "??????",
    },
]

ACTION_CONFIG = [
    {
        "code": "data_view",
        "name": "???",
        "keywords": ["??", "??", "??", "??", "??", "??", "??"],
        "guess_text": "??????",
    },
    {
        "code": "auto_remind",
        "name": "????",
        "keywords": ["??", "??", "??", "??"],
        "guess_text": "????????",
    },
    {
        "code": "auto_flow",
        "name": "????",
        "keywords": ["??", "??", "??", "??", "??", "??", "???", "???", "???"],
        "guess_text": "????????",
    },
    {
        "code": "auto_sync",
        "name": "????",
        "keywords": ["??", "??", "??", "??"],
        "guess_text": "????????",
    },
    {
        "code": "auto_generate",
        "name": "????",
        "keywords": ["??", "??", "??", "??", "??", "???"],
        "guess_text": "????????",
    },
    {
        "code": "auto_control",
        "name": "????",
        "keywords": ["??", "??", "??", "??", "??"],
        "guess_text": "????????",
    },
]

PAIN_INFERENCE_RULES = [
    {
        "pain_code": "manual_heavy",
        "any_keywords": ["????", "????", "??", "??", "??", "????"],
        "action_codes": ["auto_generate", "auto_sync"],
    },
    {
        "pain_code": "timeliness",
        "domain_codes": ["procurement"],
        "any_keywords": ["??", "BOM", "??", "??", "??"],
    },
    {
        "pain_code": "omission",
        "any_keywords": ["??", "??", "??", "???"],
        "action_codes": ["auto_remind"],
    },
    {
        "pain_code": "risk_hidden",
        "any_keywords": ["??", "??", "??", "??", "?????"],
        "action_codes": ["auto_remind", "auto_control"],
    },
    {
        "pain_code": "workflow_block",
        "any_keywords": ["??", "??", "??", "??", "???", "???", "???"],
        "action_codes": ["auto_flow"],
    },
    {
        "pain_code": "accuracy",
        "any_keywords": ["??", "??", "??", "??", "??", "???"],
        "action_codes": ["auto_sync", "auto_control"],
    },
]

QUICK_SELECTION_LIBRARY = {
    "procurement": {
        "affected_roles": ["????", "??????", "????", "???????", "???"],
        "focus_points": ["BOM/????", "????", "????", "?????", "??????"],
        "system_expectations": ["??????", "????", "????", "??????", "??????"],
    },
    "finance": {
        "affected_roles": ["????", "?????", "????", "???????", "???"],
        "focus_points": ["????", "????", "?????", "??????", "?????"],
        "system_expectations": ["??????", "????", "??????", "????", "??????"],
    },
    "hr": {
        "affected_roles": ["HR??", "????", "IT??", "???????", "???"],
        "focus_points": ["??????", "????", "????", "????", "?????"],
        "system_expectations": ["????", "????", "??????", "????", "??????"],
    },
    "legal": {
        "affected_roles": ["????", "?????", "?????", "???", "??/???"],
        "focus_points": ["????", "????", "??????", "????", "????"],
        "system_expectations": ["????", "????", "??????", "????", "??????"],
    },
    "warehouse": {
        "affected_roles": ["?????", "????", "????", "???????", "???"],
        "focus_points": ["????", "????", "??????", "???????", "????????"],
        "system_expectations": ["??????", "????", "????", "??????", "??????"],
    },
    "production": {
        "affected_roles": ["?????", "????", "????", "???????", "???"],
        "focus_points": ["?????", "????", "????", "????", "??????"],
        "system_expectations": ["????", "????", "??????", "????", "????"],
    },
    "sales": {
        "affected_roles": ["????", "?????", "??", "???????", "???"],
        "focus_points": ["????", "????", "????", "????", "????"],
        "system_expectations": ["??????", "????", "????", "??????", "????"],
    },
    "general": {
        "affected_roles": ["??????", "?????", "???", "???????", "??/???"],
        "focus_points": ["??", "???", "????", "????", "????"],
        "system_expectations": ["??????", "????", "????", "????", "??????"],
    },
}

ACTION_UNCERTAIN_MAP = {
    "data_view": ["????", "????", "????"],
    "auto_remind": ["????", "????", "????"],
    "auto_flow": ["????", "????", "??????"],
    "auto_sync": ["?????", "????", "??????"],
    "auto_generate": ["????", "????", "????"],
    "auto_control": ["????", "??????", "???"],
}

DOMAIN_UNCERTAIN_MAP = {
    "procurement": ["BOM/??????", "????", "????"],
    "finance": ["??????", "?????", "????"],
    "hr": ["????", "????", "????"],
    "legal": ["????", "????", "????"],
    "warehouse": ["????", "????", "????"],
    "production": ["????", "????", "????"],
    "sales": ["????", "????", "????"],
    "general": ["????", "????", "????"],
}

ANALYZE_SYSTEM_PROMPT = """
???? ITBP ??????????????????
???????????????????

??????????????????????????????????????????????
?????????????????
?????????????????????????????
	??????????????????????????? business_context ????????????????
	related_systems ??????????????candidate_systems ???????????????????
	???? source_evidence??????????????????????????????????????????
	????????? uncertain_items?

????? JSON????? Markdown?
??????????????? diagnosis ?????????????
???????????????????????????

?????????
- original_request
	- diagnosis
	- business_domain
	- related_systems
	- candidate_systems
	- pain_points
- system_actions
- target_users
- real_intent
- rewritten_request
- suggested_request
- confirmation_options
	- structured_report
	- uncertain_items
""".strip()

ANALYZE_FAST_SYSTEM_PROMPT = """
?????????????
??????????????????????????????????????????? ITBP ???????

???
- ??? JSON??? Markdown
	- ???? user_input ? retrieved_context ?????????
	- related_systems ?????????????
	- candidate_systems ??????????????????
	- source_evidence ?????????????????????????????????
- rewritten_request ??? 80 ?
- suggested_request ??? 120 ?
- ??????? SAP/MES/WMS/QMS ????
- ????????????????
- ?????????????????????????????????????????????
- ?????????????????????????????
- uncertain_items ?? 3 ?????????????

?????????
- original_request
- business_domain
	- business_object
	- related_systems
	- candidate_systems
	- pain_points
- system_actions
- target_users
- real_intent
- rewritten_request
- suggested_request
- confirmation_options
- uncertain_items
""".strip()

REFINE_SYSTEM_PROMPT = """
???? ITBP ???????
?????
1. ??????????
2. ???????? JSON
3. ?????????????
4. ??? suggested_request

????????????????????????? refined_request?????? ITBP ???????
???
- ?? JSON
- ???? Markdown
- ??????????????????????????
- ????????????????????????? uncertain_items ???????
- refined_request ??? 120 ???????????????????????
- rewritten_request ????
- ???????????????????
- ????????????...???????...???????...?????
- ??????????????????????????????????
- target_users ???????
- ???? structured_report ? ITBP ???????????????????? ITBP ????????
- uncertain_items ???????????????
- ???????????
""".strip()

SOLUTION_SYSTEM_PROMPT = """
?????? ITBP ???????????????? JSON ??????????????????????

???
- ??? JSON??? Markdown?
- ?? ITBP ?????????????????
- ????????????????????
- ????????????????
- ????????????????????????????/?????
- ??????????????????????????????????
- ??????????????????????????????????

?????????
- executive_summary: string
- entry_point: string
- data_systems: string
- modules: string[]
- stages: [{"name": string, "description": string}]
- risks: string[]
- confirmations: string[]
- reference_summary: string
""".strip()


def normalize_text(value: object) -> str:
    return str(value or "").strip()


def score_keywords(text: str, keywords: list[str]) -> int:
    return sum(len(keyword) for keyword in keywords if keyword and keyword in text)


def find_config_by_code(config_list: list[dict], code: str, fallback_code: str | None = None) -> dict | None:
    for item in config_list:
        if item["code"] == code:
            return item
    if fallback_code is None:
        return None
    for item in config_list:
        if item["code"] == fallback_code:
            return item
    return None


def find_config_by_name(config_list: list[dict], name: str, fallback_code: str | None = None) -> dict | None:
    for item in config_list:
        if item["name"] == name:
            return item
    return find_config_by_code(config_list, fallback_code, fallback_code)


def detect_single(text: str, config_list: list[dict], fallback_code: str) -> dict:
    best = find_config_by_code(config_list, fallback_code, fallback_code)
    best_score = 0

    for item in config_list:
        score = score_keywords(text, item.get("keywords", []))
        if score > best_score:
            best = item
            best_score = score

    return best or find_config_by_code(config_list, fallback_code, fallback_code)


def detect_multi(text: str, config_list: list[dict]) -> list[dict]:
    scored = []
    for item in config_list:
        score = score_keywords(text, item.get("keywords", []))
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda entry: entry[0], reverse=True)
    return [item for _, item in scored]


def unique_keep_order(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def map_codes_to_configs(codes: list[str], config_list: list[dict]) -> list[dict]:
    return [item for code in unique_keep_order(codes) if (item := find_config_by_code(config_list, code))]


def rule_matches(rule: dict, text: str, domain: dict, actions: list[dict]) -> bool:
    action_codes = [item["code"] for item in actions]

    if rule.get("domain_codes") and domain["code"] not in rule["domain_codes"]:
        return False
    if rule.get("action_codes") and not any(code in action_codes for code in rule["action_codes"]):
        return False
    if rule.get("any_keywords") and not any(keyword in text for keyword in rule["any_keywords"]):
        return False
    if rule.get("all_keywords") and not all(keyword in text for keyword in rule["all_keywords"]):
        return False
    return True


def infer_pains(text: str, domain: dict, actions: list[dict]) -> list[dict]:
    pain_codes: list[str] = []
    for rule in PAIN_INFERENCE_RULES:
        if rule_matches(rule, text, domain, actions):
            pain_codes.append(rule["pain_code"])
    return map_codes_to_configs(pain_codes, PAIN_CONFIG)


def get_action_guess_text(actions: list[dict]) -> str:
    action_codes = [item["code"] for item in actions]
    if "auto_generate" in action_codes and "data_view" in action_codes:
        return "???????????"
    if "auto_flow" in action_codes:
        return "????????"
    if "auto_sync" in action_codes:
        return "????????"
    if "auto_remind" in action_codes:
        return "????????"
    if "auto_control" in action_codes:
        return "????????"
    if "auto_generate" in action_codes:
        return "????????"
    if "data_view" in action_codes:
        return "??????"
    return "????????"


def get_lead_text(text: str, actions: list[dict]) -> str:
    action_codes = [item["code"] for item in actions]
    if "??" in text or "??" in text:
        return "?????????????"
    if "auto_remind" in action_codes:
        return "?????????????"
    if "auto_flow" in action_codes:
        return "???????????????"
    if "auto_sync" in action_codes:
        return "???????????????"
    if "auto_generate" in action_codes:
        return "?????????????????"
    if "auto_control" in action_codes:
        return "??????????????"
    return "?????????????"


def guess_focus(text: str, domain: dict) -> str:
    mapping = {
        "procurement": [
            ("BOM", "BOM?????????"),
            ("??", "????????"),
            ("??", "??????????"),
            ("??", "???????"),
        ],
        "finance": [
            ("??", "?????????"),
            ("??", "?????????"),
            ("??", "????"),
        ],
        "hr": [
            ("??", "??????"),
            ("??", "???????"),
            ("??", "???????"),
        ],
        "legal": [
            ("??", "?????????"),
            ("??", "???????"),
        ],
        "warehouse": [
            ("??", "??????????"),
            ("??", "???????"),
            ("??", "??????"),
        ],
    }

    for keyword, focus in mapping.get(domain["code"], []):
        if keyword in text:
            return focus

    return f"{domain['name']}??????????"


def build_confirmation_options(domain: dict, pains: list[dict], actions: list[dict]) -> dict[str, list[str]]:
    base = QUICK_SELECTION_LIBRARY.get(domain["code"], QUICK_SELECTION_LIBRARY["general"])
    options = {
        "affected_roles": list(base["affected_roles"]),
        "focus_points": list(base["focus_points"]),
        "system_expectations": list(base["system_expectations"]),
    }

    pain_names = [item["name"] for item in pains]
    action_names = [item["name"] for item in actions]

    if "?????" in pain_names and "????" not in options["focus_points"]:
        options["focus_points"].insert(0, "????")
    if "????" in pain_names and "?????" not in options["focus_points"]:
        options["focus_points"].insert(0, "?????")
    if "????" in action_names and "????" not in options["system_expectations"]:
        options["system_expectations"].insert(0, "????")
    if "????" in action_names and "????" not in options["system_expectations"]:
        options["system_expectations"].insert(0, "????")

    return {key: unique_keep_order(value)[:5] for key, value in options.items()}


def build_uncertain_items(domain: dict, actions: list[dict]) -> list[str]:
    items: list[str] = []
    for action in actions:
        items.extend(ACTION_UNCERTAIN_MAP.get(action["code"], []))
    items.extend(DOMAIN_UNCERTAIN_MAP.get(domain["code"], []))
    return unique_keep_order(items)[:3]


def build_real_intent(text: str, domain: dict, pains: list[dict], actions: list[dict]) -> str:
    domain_name = "????" if domain["name"] == "??" else domain["name"]
    pain_text = "?".join(item.get("phrase", item["name"]) for item in pains) if pains else "??????"
    action_text = get_action_guess_text(actions)
    return (
        f"{get_lead_text(text, actions)}???????{domain_name}???{pain_text}????"
        f"????{action_text}?????????????????"
    )


def join_items(values: list[str], fallback: str = "?????") -> str:
    cleaned = unique_keep_order([normalize_text(value) for value in values if normalize_text(value)])
    return "?".join(cleaned) if cleaned else fallback


def normalize_selected_values(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return unique_keep_order([normalize_text(value) for value in values if normalize_text(value)])


def context_entries(section: str) -> list[dict]:
    values = BUSINESS_CONTEXT.get(section, [])
    return values if isinstance(values, list) else []


def context_names(section: str) -> list[str]:
    return [normalize_text(item.get("name")) for item in context_entries(section) if normalize_text(item.get("name"))]


def system_aliases(system_name: str) -> list[str]:
    name = normalize_text(system_name)
    if not name:
        return []
    aliases = [name]
    for part in re.split(r"[/??]", name):
        part = normalize_text(part)
        if part:
            aliases.append(part)
    return unique_keep_order(aliases)


def system_explicitly_mentioned(system_name: str, text: str) -> bool:
    normalized_text = normalize_text(text)
    return any(alias and alias in normalized_text for alias in system_aliases(system_name))


def explicit_system_names(text: str) -> list[str]:
    return [
        system_name
        for system_name in context_names("systems")
        if system_explicitly_mentioned(system_name, text)
    ]


def filter_supported_related_systems(
    requested_systems: list[str],
    diagnosis: dict,
    original_request: str,
    warnings: list[str],
) -> list[str]:
    supported = explicit_system_names(original_request)
    candidate_names = [
        item["name"]
        for item in ensure_candidate_list(diagnosis.get("related_system_candidates"))
        if item["confidence"] >= 0.72 and system_explicitly_mentioned(item["name"], original_request)
    ]
    allowed = set(supported + candidate_names)

    filtered: list[str] = []
    for system_name in unique_keep_order(requested_systems + candidate_names):
        normalized = normalize_text(system_name)
        if not normalized:
            continue
        if normalized in allowed or system_explicitly_mentioned(normalized, original_request):
            filtered.append(normalized)
        else:
            warnings.append(f"?? {normalized} ????????????????????")
    return unique_keep_order(filtered)


def sanitize_unconfirmed_system_text(
    text: object,
    original_request: str,
    related_systems: list[str],
    warnings: list[str],
) -> str:
    cleaned = cleanup_sentence(text)
    if not cleaned:
        return cleaned

    allowed = set(related_systems + explicit_system_names(original_request))
    for system_name in context_names("systems"):
        if not system_name:
            continue
        if system_name in allowed or system_explicitly_mentioned(system_name, original_request):
            continue
        replaced = False
        for alias in system_aliases(system_name):
            if alias and alias in cleaned:
                cleaned = cleaned.replace(alias, "????")
                replaced = True
        if replaced:
            warnings.append(f"?????????????{system_name}?????????")
    return cleanup_sentence(cleaned)


def cleanup_sentence(text: str) -> str:
    cleaned = normalize_text(text)
    replacements = {
        "????????": "?????????????",
        "??????": "?????",
        "??????": "????",
        "??": "?",
        "??": "?",
        "??": "?",
        "??": "?",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def limit_text(text: str, limit: int) -> str:
    cleaned = cleanup_sentence(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip("???; ") + "?"


def item_keyword_score(text: str, item: dict) -> int:
    keywords = [normalize_text(item.get("name"))] + [
        normalize_text(keyword) for keyword in item.get("keywords", []) if normalize_text(keyword)
    ]
    return score_keywords(text, keywords)


def find_context_item(section: str, name: str) -> dict | None:
    normalized = normalize_text(name)
    for item in context_entries(section):
        if normalize_text(item.get("name")) == normalized:
            return item
    return None


def business_domain_label(domain_name: str) -> str:
    item = find_context_item("business_domains", domain_name)
    description = normalize_text(item.get("description")) if item else ""
    if description:
        return re.split(r"[?,/?]", description, maxsplit=1)[0].strip() or normalize_text(domain_name)
    return normalize_text(domain_name) or "????"


def build_context_candidates(text: str, section: str, limit: int = 3) -> list[dict]:
    candidates: list[dict] = []
    for item in context_entries(section):
        name = normalize_text(item.get("name"))
        if not name:
            continue
        exact_name = bool(name and name in text)
        score = item_keyword_score(text, item)
        if not score:
            continue
        if exact_name:
            confidence = 0.92
            reason = f"?????? {name}"
        elif score >= 6:
            confidence = 0.78
            reason = f"????????? {name} ????????"
        else:
            confidence = 0.62
            reason = f"????????? {name} ??????????"
        candidates.append(
            {
                "name": name,
                "confidence": round(confidence, 2),
                "reason": reason,
            }
        )
    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    return candidates[:limit]


def apply_business_domain_tie_breakers(text: str, candidates: list[dict]) -> list[dict]:
    rules = {
        "IPD": ["??", "??", "BOM", "????", "??", "??", "PLM"],
        "IPMS": ["??", "????", "??", "????", "????", "????", "??????", "????"],
        "MTC": ["???", "??", "??", "??", "????", "????", "???", "??", "??", "DMS"],
        "DSTE": ["??", "??", "????", "????", "????", "???", "????", "???"],
        "Manufacturing": ["MES", "??", "??", "??", "??", "????", "??"],
        "Supply": ["???", "??", "??", "??", "????", "????"],
        "Procurement": ["??", "???", "????", "??", "??", "??"],
        "Quality": ["??", "??", "??", "8D", "??"],
        "SD": ["??", "??", "???", "??", "??", "????"],
        "Warehouse": ["??", "??", "???", "??", "??"],
        "Finance": ["??", "??", "??", "??", "??"],
        "MBTIT": ["ITBP", "???", "????", "????", "??", "SAP", "MES", "WMS", "????", "????"],
    }
    adjusted = [dict(item) for item in candidates]
    by_name = {item["name"]: item for item in adjusted}

    for domain_name, keywords in rules.items():
        score = score_keywords(text, keywords)
        if not score:
            continue
        boost = 0.16 if score >= 4 else 0.08
        candidate = by_name.get(domain_name)
        if candidate:
            candidate["confidence"] = round(min(0.9, float(candidate["confidence"]) + boost), 2)
            candidate["reason"] = f"{candidate['reason']}???????? {domain_name} ??"
        elif score >= 4:
            candidate = {
                "name": domain_name,
                "confidence": round(0.55 + boost, 2),
                "reason": f"??????????? {domain_name} ??",
            }
            adjusted.append(candidate)
            by_name[domain_name] = candidate

    adjusted.sort(key=lambda item: item["confidence"], reverse=True)
    return adjusted


def flatten_context_strings(value: object) -> list[str]:
    strings: list[str] = []
    if isinstance(value, str):
        cleaned = normalize_text(value)
        if cleaned:
            strings.append(cleaned)
    elif isinstance(value, list):
        for item in value:
            strings.extend(flatten_context_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            strings.extend(flatten_context_strings(item))
    return strings


def context_field_values(item: dict, fields: list[str]) -> list[str]:
    values: list[str] = []
    for field in fields:
        values.extend(flatten_context_strings(item.get(field)))
    return unique_keep_order(values)


def context_hit_terms(text: str, values: list[str]) -> list[str]:
    hit_terms: list[str] = []
    for value in values:
        for term in re.split(r"[\s,??/?;?:?()??\[\]??<>??]+", value):
            cleaned = normalize_text(term)
            if len(cleaned) < 2:
                continue
            if cleaned in text:
                hit_terms.append(cleaned)
    return unique_keep_order(hit_terms)


def score_context_item(text: str, item: dict, fields: list[str]) -> tuple[int, list[str]]:
    name = normalize_text(item.get("name"))
    values = [name] + context_field_values(item, fields)
    hits = context_hit_terms(text, values)
    score = sum(len(term) for term in hits)
    if name and name in text:
        score += max(8, len(name) * 2)
    return score, hits


def retrieve_section_matches(text: str, section: str, fields: list[str], limit: int = 5) -> list[dict]:
    matches: list[dict] = []
    for item in context_entries(section):
        score, hits = score_context_item(text, item, fields)
        if score <= 0:
            continue
        name = normalize_text(item.get("name"))
        matches.append(
            {
                "name": name,
                "score": score,
                "hit_terms": hits[:8],
                "item": item,
            }
        )
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches[:limit]


def compact_context_item(item: dict, fields: list[str]) -> dict:
    compact: dict[str, object] = {}
    for field in fields:
        value = item.get(field)
        if value in (None, "", [], {}):
            continue
        compact[field] = value
    return compact


def scored_names(matches: list[dict], limit: int = 5) -> list[str]:
    return [normalize_text(item.get("name")) for item in matches[:limit] if normalize_text(item.get("name"))]


def score_phrase(text: str, phrase: str) -> int:
    phrase = normalize_text(phrase)
    if not phrase:
        return 0
    score = len(phrase) if phrase in text else 0
    for term in re.split(r"[\s,??/?;?:?()??]+", phrase):
        term = normalize_text(term)
        if len(term) >= 2 and term in text:
            score += len(term)
    skip_fragments = {
        "??",
        "??",
        "??",
        "??",
        "??",
        "??",
        "??",
        "??",
        "??",
        "??",
        "??",
        "??",
    }
    fragment_hits: list[str] = []
    for chunk in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", phrase):
        if len(chunk) < 4:
            continue
        for size in [4, 3, 2]:
            for index in range(0, len(chunk) - size + 1):
                fragment = chunk[index : index + size]
                if fragment in skip_fragments:
                    continue
                if fragment in text:
                    fragment_hits.append(fragment)
    score += sum(len(fragment) for fragment in unique_keep_order(fragment_hits)[:8])
    return score


def choose_relevant_phrases(text: str, phrases: list[str], limit: int = 3) -> list[str]:
    scored: list[tuple[int, int, str]] = []
    for index, phrase in enumerate(unique_keep_order([normalize_text(item) for item in phrases if normalize_text(item)])):
        score = score_phrase(text, phrase)
        scored.append((score, -index, phrase))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    positive = [phrase for score, _, phrase in scored if score > 0]
    if positive:
        return positive[:limit]
    return [phrase for _, _, phrase in scored[:limit]]


def infer_business_objects(text: str, domain_matches: list[dict], system_matches: list[dict], limit: int = 5) -> list[str]:
    objects: list[str] = []
    scored: list[tuple[int, int, str]] = []
    sources = [match["item"] for match in domain_matches] + [match["item"] for match in system_matches]
    for index, item in enumerate(sources):
        candidates = flatten_context_strings(item.get("common_objects")) + flatten_context_strings(item.get("usage_scope"))
        for value in unique_keep_order(candidates):
            score = score_phrase(text, value)
            if score <= 0:
                fragments = [part for part in re.split(r"[\s,??/?;?]+", value) if len(part) >= 2 and part in text]
                score = sum(len(part) for part in fragments)
            if score > 0:
                scored.append((score, -index, value))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    objects.extend([value for _, _, value in scored])
    if not objects and domain_matches:
        objects.extend(flatten_context_strings(domain_matches[0]["item"].get("common_objects"))[:3])
    return unique_keep_order(objects)[:limit]


def match_manual_action_patterns(text: str) -> list[str]:
    patterns = BUSINESS_CONTEXT.get("manual_action_patterns", [])
    matched: list[str] = []
    for pattern in flatten_context_strings(patterns):
        if pattern and pattern in text:
            matched.append(pattern)
    matched.extend(build_manual_actions(text))
    return unique_keep_order(matched)


def retrieve_context(user_input: str) -> dict:
    text = normalize_text(user_input)
    domain_fields = [
        "name",
        "chinese_name",
        "description",
        "plain_description",
        "keywords",
        "common_objects",
        "common_manual_actions",
        "common_breakpoints",
        "common_consequences",
        "typical_system_behaviors",
    ]
    system_fields = ["name", "description", "keywords", "usage_scope", "caution"]
    role_fields = ["name", "description", "keywords", "focus", "common_pains"]
    pain_fields = ["name", "description", "keywords", "bad_expression"]
    action_fields = ["name", "description", "keywords", "examples"]
    process_fields = ["name", "chain", "typical_breakpoints"]

    raw_domain_matches = retrieve_section_matches(text, "business_domains", domain_fields, 6)
    adjusted_domains = apply_business_domain_tie_breakers(
        text,
        [
            {
                "name": match["name"],
                "confidence": min(0.95, max(0.35, match["score"] / 20)),
                "reason": f"???{join_items(match['hit_terms'], '?????')}",
                "score": match["score"],
            }
            for match in raw_domain_matches
        ],
    )
    domain_by_name = {match["name"]: match for match in raw_domain_matches}
    domain_matches: list[dict] = []
    for candidate in adjusted_domains[:3]:
        name = normalize_text(candidate.get("name"))
        item = domain_by_name.get(name, {}).get("item") or find_context_item("business_domains", name)
        if item:
            domain_matches.append(
                {
                    "name": name,
                    "score": int(float(candidate.get("confidence", 0)) * 100),
                    "hit_terms": domain_by_name.get(name, {}).get("hit_terms", []),
                    "item": item,
                    "confidence": candidate.get("confidence"),
                    "reason": candidate.get("reason"),
                }
            )
    if not domain_matches:
        general = find_context_item("business_domains", "General") or {}
        domain_matches = [
            {
                "name": "General",
                "score": 0,
                "hit_terms": [],
                "item": general,
                "confidence": 0.35,
                "reason": "????????????? General",
            }
        ]

    system_matches = retrieve_section_matches(text, "systems", system_fields, 5)
    role_matches = retrieve_section_matches(text, "roles", role_fields, 5)
    pain_matches = retrieve_section_matches(text, "pain_types", pain_fields, 5)
    action_matches = retrieve_section_matches(text, "system_actions", action_fields, 5)
    process_matches = retrieve_section_matches(text, "process_chains", process_fields, 5)
    if not process_matches:
        process_matches = [
            {
                "name": match["name"],
                "score": match["score"],
                "hit_terms": [],
                "item": find_context_item("process_chains", match["name"]) or {},
            }
            for match in domain_matches
            if find_context_item("process_chains", match["name"])
        ]

    matched_business_objects = infer_business_objects(text, domain_matches, system_matches)
    matched_manual_actions = match_manual_action_patterns(text)
    for match in domain_matches[:2]:
        matched_manual_actions.extend(
            choose_relevant_phrases(text, flatten_context_strings(match["item"].get("common_manual_actions")), 2)
        )

    relevant_context = {
        "domain_context": [
            compact_context_item(match["item"], domain_fields)
            for match in domain_matches[:3]
            if match.get("item")
        ],
        "system_context": [
            compact_context_item(match["item"], system_fields)
            for match in system_matches[:4]
            if match.get("item")
        ],
        "role_context": [
            compact_context_item(match["item"], role_fields)
            for match in role_matches[:5]
            if match.get("item")
        ],
        "process_context": [
            compact_context_item(match["item"], process_fields)
            for match in process_matches[:4]
            if match.get("item")
        ],
        "pain_context": [
            compact_context_item(match["item"], pain_fields)
            for match in pain_matches[:5]
            if match.get("item")
        ],
        "action_context": [
            compact_context_item(match["item"], action_fields)
            for match in action_matches[:5]
            if match.get("item")
        ],
        "manual_action_patterns": unique_keep_order(matched_manual_actions)[:8],
        "expression_rules": BUSINESS_CONTEXT.get("expression_rules", []),
        "forbidden_vague_expressions": BUSINESS_CONTEXT.get("forbidden_vague_expressions", []),
    }

    return {
        "matched_domains": scored_names(domain_matches, 3),
        "matched_systems": scored_names(system_matches, 5),
        "matched_roles": scored_names(role_matches, 5),
        "matched_pain_types": scored_names(pain_matches, 5),
        "matched_system_actions": scored_names(action_matches, 5),
        "matched_process_chains": scored_names(process_matches, 5),
        "matched_business_objects": matched_business_objects,
        "matched_manual_actions": unique_keep_order(matched_manual_actions)[:8],
        "relevant_context": relevant_context,
        "debug": {
            "domain_matches": [
                {
                    "name": match["name"],
                    "score": match["score"],
                    "hit_terms": match.get("hit_terms", []),
                    "reason": match.get("reason", ""),
                }
                for match in domain_matches
            ],
            "system_matches": [
                {
                    "name": match["name"],
                    "score": match["score"],
                    "hit_terms": match.get("hit_terms", []),
                    "explicit": system_explicitly_mentioned(match["name"], text),
                }
                for match in system_matches
            ],
            "role_matches": [
                {"name": match["name"], "score": match["score"], "hit_terms": match.get("hit_terms", [])}
                for match in role_matches
            ],
            "pain_matches": [
                {"name": match["name"], "score": match["score"], "hit_terms": match.get("hit_terms", [])}
                for match in pain_matches
            ],
            "action_matches": [
                {"name": match["name"], "score": match["score"], "hit_terms": match.get("hit_terms", [])}
                for match in action_matches
            ],
            "explicit_systems": explicit_system_names(text),
        },
    }


def retrieved_context_summary(retrieved_context: dict) -> dict:
    return {
        "matched_domains": retrieved_context.get("matched_domains", []),
        "matched_systems": retrieved_context.get("matched_systems", []),
        "matched_roles": retrieved_context.get("matched_roles", []),
        "matched_pain_types": retrieved_context.get("matched_pain_types", []),
        "matched_system_actions": retrieved_context.get("matched_system_actions", []),
        "matched_process_chains": retrieved_context.get("matched_process_chains", []),
        "matched_business_objects": retrieved_context.get("matched_business_objects", []),
        "matched_manual_actions": retrieved_context.get("matched_manual_actions", []),
        "debug": retrieved_context.get("debug", {}),
    }


def build_generic_scenario_form() -> dict:
    return {
        "template_code": "generic_requirement_clarification",
        "template_name": "???????",
        "match_reason": "????????????????????",
        "groups": [
            {
                "key": "trigger",
                "title": "1. ???????????????",
                "type": "multi_select",
                "required": True,
                "options": ["?????", "?????", "??/???", "??/???", "???????"],
            },
            {
                "key": "current_gap",
                "title": "2. ?????????",
                "type": "multi_select",
                "required": True,
                "options": ["????", "?????", "?????", "??????", "??????"],
            },
            {
                "key": "expected_action",
                "title": "3. ????????????",
                "type": "multi_select",
                "required": True,
                "options": ["??????", "??????", "???????", "??????", "??????"],
            },
        ],
    }


def normalize_scenario_group(group: dict) -> dict:
    return {
        "key": cleanup_sentence(group.get("key")) or "question",
        "title": cleanup_sentence(group.get("title")) or "?????",
        "type": cleanup_sentence(group.get("type")) or "multi_select",
        "required": bool(group.get("required")),
        "options": ensure_string_list(group.get("options"))[:8],
    }


def match_clarification_template(user_input: str, retrieved_context: dict, business_domain: str = "", business_object: str = "") -> dict:
    text = normalize_text(user_input)
    templates = BUSINESS_CONTEXT.get("clarification_templates", [])
    if not isinstance(templates, list):
        return {}

    matched_domains = ensure_string_list(retrieved_context.get("matched_domains"))
    matched_objects = ensure_string_list(retrieved_context.get("matched_business_objects"))
    context_text = " ".join([text, business_domain, business_object, *matched_domains, *matched_objects])
    best_template: dict = {}
    best_score = 0
    best_reasons: list[str] = []

    for template in templates:
        if not isinstance(template, dict):
            continue
        score = 0
        reasons: list[str] = []
        for domain in ensure_string_list(template.get("match_domains")):
            if domain and (domain == business_domain or domain in matched_domains or domain in context_text):
                score += 8
                reasons.append(f"??????{domain}")
        for keyword in ensure_string_list(template.get("match_keywords")):
            if keyword and keyword in context_text:
                score += max(2, len(keyword))
                reasons.append(f"??????{keyword}")
        if score > best_score:
            best_score = score
            best_template = template
            best_reasons = reasons

    if not best_template or best_score < 4:
        return {}

    return {
        "template_code": cleanup_sentence(best_template.get("code")) or "scenario_template",
        "template_name": cleanup_sentence(best_template.get("name")) or "??????",
        "match_score": best_score,
        "match_reason": "?".join(unique_keep_order(best_reasons)[:4]),
        "groups": [
            normalize_scenario_group(group)
            for group in best_template.get("groups", [])
            if isinstance(group, dict) and ensure_string_list(group.get("options"))
        ],
    }


def build_scenario_form(user_input: str, retrieved_context: dict, business_domain: str = "", business_object: str = "") -> dict:
    form = match_clarification_template(user_input, retrieved_context, business_domain, business_object)
    if form and form.get("groups"):
        return form
    return build_generic_scenario_form()


def flatten_scenario_answers(selected_options: dict) -> list[str]:
    answers = selected_options.get("scenario_answers") if isinstance(selected_options, dict) else {}
    if not isinstance(answers, dict):
        return []
    flattened: list[str] = []
    for value in answers.values():
        flattened.extend(normalize_selected_values(value))
    return unique_keep_order(flattened)


def scenario_answers_by_key(selected_options: dict, key: str) -> list[str]:
    answers = selected_options.get("scenario_answers") if isinstance(selected_options, dict) else {}
    if not isinstance(answers, dict):
        return []
    return normalize_selected_values(answers.get(key))


def scenario_answer_phrase(selected_options: dict, key: str, fallback: str = "") -> str:
    return selection_phrase(scenario_answers_by_key(selected_options, key), fallback)


def build_explicit_facts(text: str, system_candidates: list[dict], role_candidates: list[dict]) -> list[str]:
    facts: list[str] = []
    explicit_systems = [item["name"] for item in system_candidates if system_explicitly_mentioned(item["name"], text)]
    if explicit_systems:
        facts.append(f"?????????{join_items(explicit_systems)}")

    explicit_roles = [item["name"] for item in role_candidates if item["name"] in text]
    if explicit_roles:
        facts.append(f"?????????{join_items(explicit_roles)}")

    business_terms = []
    for keyword in ["BOM", "??", "??", "??", "??", "????", "??", "??", "??", "??", "??"]:
        if keyword in text:
            business_terms.append(keyword)
    if business_terms:
        facts.append(f"??????????????{join_items(business_terms)}")

    manual_terms = []
    for keyword in ["??", "??", "??", "??", "??", "??", "??", "??", "??", "??"]:
        if keyword in text:
            manual_terms.append(keyword)
    if manual_terms:
        facts.append(f"?????????????{join_items(manual_terms)}")

    if not facts:
        facts.append("????????????????????????")
    return facts


def build_manual_actions(text: str) -> list[str]:
    action_rules = [
        ("??", "???????"),
        ("??", "?????????"),
        ("??", "?????????"),
        ("??", "??????"),
        ("??", "?????????"),
        ("??", "??????"),
        ("??", "???????"),
        ("?", "?????????"),
        ("?", "????????"),
        ("???", "????????"),
        ("??", "??????"),
        ("??", "??????"),
        ("??", "??????"),
        ("??", "?????????"),
        ("???", "?????????"),
        ("??", "??????????????"),
        ("??", "???????????"),
        ("???", "?????????????"),
        ("???", "?????????????"),
        ("??", "????????"),
    ]
    return unique_keep_order([label for keyword, label in action_rules if keyword in text])


def build_current_process(manual_actions: list[str]) -> str:
    if manual_actions:
        return f"???????????{join_items(manual_actions[:3])}??????????????"
    return "??????????????????????????????????????"


def get_process_chain(domain_name: str) -> list[str]:
    normalized = normalize_text(domain_name)
    for item in context_entries("process_chains"):
        if normalize_text(item.get("name")) == normalized:
            chain = item.get("chain")
            return [normalize_text(value) for value in chain if normalize_text(value)] if isinstance(chain, list) else []
    return []


def build_current_process_from_context(domain_name: str, manual_actions: list[str]) -> str:
    chain = get_process_chain(domain_name)
    chain_text = " ? ".join(chain)
    if manual_actions and chain_text:
        return f"???????{chain_text}????????{join_items(manual_actions[:3])}????????????????"
    if chain_text:
        return f"???????{chain_text}????????????????????"
    return build_current_process(manual_actions)


def build_process_breakpoint(pain_points: list[str], manual_actions: list[str], system_actions: list[str]) -> str:
    manual_text = join_items(manual_actions, "")
    if any(keyword in manual_text for keyword in ["??", "??", "????", "????"]):
        return "?????????????????????????????????????"
    if "????" in pain_points:
        return "????????????????????????"
    if "?????" in pain_points:
        return "?????????????????????"
    if "????" in pain_points:
        return "??????????????????"
    if manual_actions and ("????" in system_actions or "???" in system_actions):
        return "???????????????????????????"
    if manual_actions:
        return "???????????????????????????"
    return "???????????????????????????"


def build_pain_root_cause(pain_points: list[str], manual_actions: list[str], process_breakpoint: str) -> str:
    if pain_points:
        explanation_map = {item["name"]: item["description"] for item in context_entries("pain_types")}
        explanations = [explanation_map.get(name, name) for name in pain_points[:2]]
        return f"{join_items(explanations)}???????{process_breakpoint}"
    if manual_actions:
        return f"????{join_items(manual_actions[:3])}??????????????????????"
    return "?????????????????????????????"


def build_business_impact(domain_name: str, pain_points: list[str]) -> str:
    domain_desc = business_domain_label(domain_name) or "??????"
    if "?????" in pain_points:
        return f"????{domain_desc}??????????????"
    if "???" in pain_points:
        return f"????{domain_desc}?????????????"
    if "????" in pain_points:
        return f"????{domain_desc}????????????????????"
    if "????" in pain_points:
        return f"????{domain_desc}?????????????"
    return f"????{domain_desc}?????????????????"


def build_desired_system_behavior(system_actions: list[str], pain_points: list[str]) -> list[str]:
    action_desc = {item["name"]: item["description"] for item in context_entries("system_actions")}
    behaviors = [action_desc.get(action, action) for action in system_actions]
    if not behaviors and "?????" in pain_points:
        behaviors.append("????????????????????????")
    if not behaviors:
        behaviors.extend(["????????", "???????????", "??????????"])
    return unique_keep_order(behaviors)[:5]


def infer_surface_feature(text: str, system_actions: list[str]) -> str:
    if "??" in text or "??" in text:
        return "????"
    if "??" in text or "??" in text:
        return "????"
    if "??" in text or "??" in text:
        return "??????"
    if "??" in text or "??" in text or "??" in text:
        return "???????"
    if system_actions:
        return join_items(system_actions[:2])
    return "????"


def derive_focus_points(diagnosis: dict, pain_points: list[str]) -> list[str]:
    focus: list[str] = []
    for fact in ensure_string_list(diagnosis.get("explicit_facts")):
        for keyword in ["BOM", "??", "??", "??", "??", "????", "??", "??", "??", "??"]:
            if keyword in fact:
                focus.append(keyword)
    focus.extend(pain_points)
    if diagnosis.get("process_breakpoint"):
        focus.append(shorten_focus_text(diagnosis["process_breakpoint"]))
    return unique_keep_order(focus)[:5]


def shorten_focus_text(text: str) -> str:
    cleaned = cleanup_sentence(text).rstrip("?")
    return cleaned[:18] + ("..." if len(cleaned) > 18 else "")


def build_confirmation_options_from_diagnosis(diagnosis: dict, pain_points: list[str], system_actions: list[str]) -> dict:
    roles = ensure_string_list(diagnosis.get("target_users"))
    if not roles:
        role_candidates = build_context_candidates(" ".join(ensure_string_list(diagnosis.get("explicit_facts"))), "roles", 5)
        roles = [item["name"] for item in role_candidates]
    if not roles:
        roles = ["??????", "?????", "???????", "ITBP"]

    focus_points = derive_focus_points(diagnosis, pain_points)
    if not focus_points:
        focus_points = ["????", "????", "????", "????", "????"]

    expectations = system_actions or ["???", "????", "????", "????", "????"]
    return {
        "affected_roles": unique_keep_order(roles)[:5],
        "focus_points": unique_keep_order(focus_points)[:5],
        "system_expectations": unique_keep_order(expectations)[:5],
    }


def build_structured_report_from_diagnosis(diagnosis: dict) -> dict:
    target_users = ensure_string_list(diagnosis.get("target_users"))
    systems = [
        item["name"]
        for item in diagnosis.get("related_system_candidates", [])
        if isinstance(item, dict) and float(item.get("confidence") or 0) >= 0.72
    ]
    desired = ensure_string_list(diagnosis.get("desired_system_behavior"))
    return {
        "why": cleanup_sentence(diagnosis.get("pain_root_cause")) or "?????",
        "what": join_items(desired[:2], "?????"),
        "where": cleanup_sentence(diagnosis.get("current_process")) or "?????",
        "who": join_items(target_users, "?????"),
        "input": join_items(systems, "?????"),
        "output": join_items(desired, "?????"),
        "how": [
            "?????????????????",
            "?????????????????????????",
            "????????????????????????",
        ],
        "monitor": ["????????", "????????", "????????"],
        "howmuch": "?????",
    }


def build_diagnostic_texts(original_request: str, diagnosis: dict, pain_points: list[str], system_actions: list[str]) -> dict:
    domain_name = normalize_text(diagnosis.get("primary_business_domain")) or "?????"
    domain_text = business_domain_label(domain_name)
    roles_text = join_items(ensure_string_list(diagnosis.get("target_users")), "????")
    process_breakpoint = cleanup_sentence(diagnosis.get("process_breakpoint")) or "??????"
    impact = cleanup_sentence(diagnosis.get("business_impact")) or "?????????"
    action_text = build_action_clause(system_actions)
    trigger = "???????????????"
    surface = infer_surface_feature(original_request, system_actions)

    real_intent = (
        f"?????????{surface}????????{domain_text}?????{roles_text}"
        f"??????????{process_breakpoint}???{impact}"
    )
    rewritten = f"?????{domain_text}??????{roles_text}{action_text}???{process_breakpoint}?"
    suggested = f"?{trigger}???{action_text}???{roles_text}??{process_breakpoint}???{impact}"
    return {
        "real_intent": cleanup_sentence(real_intent),
        "rewritten_request": limit_text(rewritten, 80),
        "suggested_request": limit_text(suggested, 120),
    }


def build_fallback_diagnosis(user_input: str) -> dict:
    text = normalize_text(user_input)
    domain_candidates = apply_business_domain_tie_breakers(
        text,
        build_context_candidates(text, "business_domains", 5),
    )[:3]
    if not domain_candidates:
        domain_candidates = [{"name": "General", "confidence": 0.35, "reason": "????????????"}]

    system_candidates = build_context_candidates(text, "systems", 4)
    role_candidates = build_context_candidates(text, "roles", 5)
    pain_candidates = build_context_candidates(text, "pain_types", 5)
    action_candidates = build_context_candidates(text, "system_actions", 5)

    pain_points = [item["name"] for item in pain_candidates] or ["?????"]
    system_actions = [item["name"] for item in action_candidates]
    target_users = [item["name"] for item in role_candidates if item["confidence"] >= 0.62][:4]
    manual_actions = build_manual_actions(text)
    primary_domain = domain_candidates[0]["name"] if domain_candidates[0]["confidence"] >= 0.55 else "?????"
    process_breakpoint = build_process_breakpoint(pain_points, manual_actions, system_actions)
    uncertain_items: list[str] = []

    for item in system_candidates:
        if item["confidence"] < 0.72:
            uncertain_items.append(f"???? {item['name']} ????")
    if primary_domain == "?????":
        uncertain_items.append("????????")
    if not target_users:
        uncertain_items.append("??????????")
    if not system_actions:
        uncertain_items.append("?????????????")

    diagnosis = {
        "explicit_facts": build_explicit_facts(text, system_candidates, role_candidates),
        "inferred_context": [
            f"?????????????? {domain_candidates[0]['name']}???? {domain_candidates[0]['confidence']}?"
        ],
        "business_domain_candidates": domain_candidates,
        "related_system_candidates": system_candidates,
        "target_users": target_users,
        "current_process": build_current_process_from_context(primary_domain, manual_actions),
        "manual_actions": manual_actions,
        "process_breakpoint": process_breakpoint,
        "pain_root_cause": build_pain_root_cause(pain_points, manual_actions, process_breakpoint),
        "business_impact": build_business_impact(primary_domain, pain_points),
        "desired_system_behavior": build_desired_system_behavior(system_actions, pain_points),
        "uncertain_items": unique_keep_order(uncertain_items)[:6],
        "primary_business_domain": primary_domain,
    }
    return diagnosis


def build_analysis_from_diagnosis(user_input: str, diagnosis: dict) -> dict:
    domain_candidates = [
        item for item in diagnosis.get("business_domain_candidates", []) if isinstance(item, dict)
    ]
    top_domain = domain_candidates[0] if domain_candidates else {"name": "?????", "confidence": 0}
    business_domain = normalize_text(diagnosis.get("primary_business_domain")) or normalize_text(top_domain.get("name"))
    if float(top_domain.get("confidence") or 0) < 0.55:
        business_domain = "?????"

    related_systems = [
        item["name"]
        for item in diagnosis.get("related_system_candidates", [])
        if isinstance(item, dict) and float(item.get("confidence") or 0) >= 0.72
    ]
    pain_context_text = " ".join(
        [
            cleanup_sentence(diagnosis.get("pain_root_cause")),
            cleanup_sentence(diagnosis.get("process_breakpoint")),
            " ".join(ensure_string_list(diagnosis.get("manual_actions"))),
        ]
    )
    pain_points = [item["name"] for item in build_context_candidates(pain_context_text, "pain_types", 5)]
    if not pain_points:
        pain_points = [
            item["name"]
            for item in build_context_candidates(" ".join(ensure_string_list(diagnosis.get("explicit_facts"))), "pain_types", 5)
        ]
    if not pain_points:
        pain_points = ["?????"]

    desired_text = " ".join(ensure_string_list(diagnosis.get("desired_system_behavior")))
    system_actions = [item["name"] for item in build_context_candidates(user_input + " " + desired_text, "system_actions", 5)]
    if not system_actions:
        system_actions = ["?????"]

    texts = build_diagnostic_texts(user_input, diagnosis, pain_points, system_actions)
    uncertain_items = unique_keep_order(
        ensure_string_list(diagnosis.get("uncertain_items"))
        + ["????????"]
    )[:8]

    result = {
        "original_request": user_input,
        "diagnosis": diagnosis,
        "business_domain": business_domain,
        "related_systems": related_systems,
        "pain_points": pain_points,
        "system_actions": system_actions,
        "target_users": ensure_string_list(diagnosis.get("target_users")),
        "real_intent": texts["real_intent"],
        "rewritten_request": texts["rewritten_request"],
        "suggested_request": texts["suggested_request"],
        "confirmation_options": build_confirmation_options_from_diagnosis(diagnosis, pain_points, system_actions),
        "structured_report": build_structured_report_from_diagnosis(diagnosis),
        "uncertain_items": uncertain_items,
        "warnings": [],
        "mode": "mock",
    }
    return validate_analysis_result(result, user_input)


def build_context_analysis(user_input: str) -> dict:
    return build_analysis_from_diagnosis(normalize_text(user_input), build_fallback_diagnosis(user_input))


def summarize_pains(pains: list[dict]) -> str:
    if not pains:
        return "??????????"
    return "?".join(item.get("phrase", item["name"]) for item in pains)


def build_target_users(text: str, domain: dict, confirmation_options: dict[str, list[str]]) -> list[str]:
    explicit_roles: list[str] = []
    role_keywords = [
        ("????", "????"),
        ("??????", "??????"),
        ("????", "????"),
        ("?????", "?????"),
        ("????", "????"),
        ("????", "????"),
        ("????", "????"),
        ("?????", "?????"),
        ("HR??", "HR??"),
        ("IT??", "IT??"),
    ]

    for keyword, role in role_keywords:
        if keyword in text:
            explicit_roles.append(role)

    default_roles = (confirmation_options or {}).get("affected_roles") or []
    return unique_keep_order(explicit_roles + default_roles[:2])[:3]


def build_action_clause(action_names: list[str]) -> str:
    action_aliases = {
        "??????": "???",
        "??????": "????",
        "??????": "????",
        "????": "????",
        "????": "????",
        "????": "????",
        "????": "????",
        "????": "????",
        "???": "???",
        "????": "????",
    }
    phrase_map = {
        "???": "??????",
        "????": "????????",
        "????": "????????",
        "????": "????????",
        "????": "??????????",
        "????": "????????",
        "????": "??????",
    }
    normalized = unique_keep_order(
        [action_aliases.get(normalize_text(name), normalize_text(name)) for name in action_names if normalize_text(name)]
    )
    phrases = [phrase_map[name] for name in normalized if name in phrase_map]
    return "?".join(phrases) if phrases else "????????"


def build_focus_metrics(focus_points: list[str]) -> list[str]:
    metric_rules = [
        ("??", "???????????"),
        ("??", "????????"),
        ("???", "??????????"),
        ("BOM", "BOM?????????"),
        ("??", "?????????"),
        ("??", "????????????"),
        ("??", "????????"),
    ]
    metrics: list[str] = []
    for focus in focus_points:
        for keyword, metric in metric_rules:
            if keyword in focus:
                metrics.append(metric)
    return unique_keep_order(metrics)


def build_natural_request(
    text: str,
    domain: dict,
    pains: list[dict],
    actions: list[dict],
    target_users: list[str],
    focus_points: list[str] | None = None,
    system_expectations: list[str] | None = None,
) -> str:
    roles_text = join_items(target_users, "????")
    focus_text = join_items(focus_points or [], guess_focus(text, domain))
    action_names = system_expectations or [item["name"] for item in actions]
    action_clause = build_action_clause(action_names)
    pain_text = summarize_pains(pains)

    if domain["code"] == "warehouse":
        return (
            f"???????{focus_text}?{action_clause}????????????????"
            f"???{roles_text}????????????????"
        )
    if domain["code"] == "procurement":
        return (
            f"???????{focus_text}?{action_clause}?"
            f"?????????{roles_text}????????{pain_text}???"
        )
    if domain["code"] == "finance":
        return (
            f"???????{focus_text}?{action_clause}??????{roles_text}???"
            f"??????????????"
        )
    if domain["code"] == "legal":
        return (
            f"???????{focus_text}?{action_clause}??????{roles_text}???"
            f"????????????"
        )
    if domain["code"] == "hr":
        return (
            f"???????{focus_text}?{action_clause}??????????{roles_text}?"
            f"???????????"
        )
    if domain["code"] == "production":
        return (
            f"???????{focus_text}?{action_clause}?????????????????{roles_text}?"
            f"??????????????????"
        )
    if domain["code"] == "sales":
        return (
            f"???????{focus_text}?{action_clause}?????????{roles_text}?????"
            f"???????????"
        )

    return (
        f"???????{focus_text}?{action_clause}?????{roles_text}???"
        f"??{pain_text}?"
    )


def build_suggested_request(text: str, domain: dict, pains: list[dict], actions: list[dict]) -> str:
    confirmation_options = build_confirmation_options(domain, pains, actions)
    target_users = build_target_users(text, domain, confirmation_options)
    return build_natural_request(text, domain, pains, actions, target_users)


def build_rewritten_request(
    text: str,
    domain: dict,
    pains: list[dict],
    actions: list[dict],
    target_users: list[str],
    focus_points: list[str] | None = None,
    system_expectations: list[str] | None = None,
) -> str:
    roles_text = join_items(target_users, "????")
    focus_text = join_items(focus_points or [], guess_focus(text, domain))
    action_names = system_expectations or [item["name"] for item in actions]
    action_clause = build_action_clause(action_names)

    if domain["code"] == "warehouse":
        return f"??????????{focus_text}?{action_clause}??????????{roles_text}???"
    if domain["code"] == "procurement":
        return f"??????????{focus_text}?{action_clause}??????????{roles_text}?????????????"
    if domain["code"] == "finance":
        return f"??????????{focus_text}?{action_clause}???????{roles_text}????????????"
    if domain["code"] == "legal":
        return f"??????????{focus_text}?{action_clause}????{roles_text}??????????????"
    if domain["code"] == "hr":
        return f"HR ??????{focus_text}?{action_clause}??????????{roles_text}?"
    if domain["code"] == "production":
        return f"??????????{focus_text}?{action_clause}??????????{roles_text}?????"
    if domain["code"] == "sales":
        return f"??????????{focus_text}?{action_clause}?????????{roles_text}?????"
    return f"??????????{focus_text}?{action_clause}?????{roles_text}???"


def build_structured_report(
    text: str,
    domain: dict,
    pains: list[dict],
    actions: list[dict],
    target_users: list[str],
    focus_points: list[str] | None = None,
    system_expectations: list[str] | None = None,
) -> dict:
    roles_text = join_items(target_users, "?????")
    selected_focus = normalize_selected_values(focus_points or [])
    selected_expectations = normalize_selected_values(system_expectations or [])
    focus_text = join_items(selected_focus, guess_focus(text, domain))
    action_names = selected_expectations or [item["name"] for item in actions]
    action_clause = build_action_clause(action_names)
    has_selected_constraints = bool(selected_focus or selected_expectations)

    what_map = {
        "procurement": "??/???????????",
        "finance": "???????????",
        "hr": "????????????",
        "legal": "?????????",
        "warehouse": "???????????????",
        "production": "????????????",
        "sales": "???????????",
        "general": "??????????????",
    }
    where_map = {
        "procurement": "???? / ???????",
        "finance": "???? / ??????",
        "hr": "????????",
        "legal": "???? / ??????",
        "warehouse": "?????? / ?????????",
        "production": "?????? / ??????",
        "sales": "???? / ??????",
        "general": "????????",
    }
    owner_map = {
        "procurement": f"?????????????{roles_text}",
        "finance": f"?????????????{roles_text}",
        "hr": f"HR ?????????{roles_text}",
        "legal": f"???????????{roles_text}",
        "warehouse": f"?????????????{roles_text}",
        "production": f"???????????????{roles_text}",
        "sales": f"?????????????{roles_text}",
        "general": f"???????????? {roles_text}",
    }
    input_map = {
        "procurement": "???????????????????",
        "finance": "?????????????????",
        "hr": "???????????????????",
        "legal": "???????????????",
        "warehouse": "???????????????????",
        "production": "?????????????????",
        "sales": "??????????????????",
        "general": "????????????????",
    }
    output_map = {
        "procurement": "????????????????????",
        "finance": "????????????????",
        "hr": "??????????????????",
        "legal": "????????????????",
        "warehouse": "????????????????????",
        "production": "??????????????????",
        "sales": "????????????????????",
        "general": f"{focus_text}??????????????",
    }
    pain_metric_map = {
        "???": "??????",
        "???": "???????",
        "????": "?????????",
        "????": "????????",
        "????": "??????????",
        "?????": "????????????",
    }

    why = {
        "procurement": "?? BOM ??????????????????????????????",
        "finance": "??????????????????????????????",
        "hr": "?????????????????????????????",
        "legal": "????????????????????????????",
        "warehouse": "???????????????????????????????????",
        "production": "?????????????????????????????",
        "sales": "?????????????????????????",
        "general": f"??{summarize_pains(pains)}??? {roles_text} ??????",
    }[domain["code"]]

    how_steps = [
        f"??? {input_map[domain['code']]} ?????????",
        f"????? {focus_text}?{action_clause}?",
        f"?????? {roles_text} ?????????????",
    ]
    monitor = [pain_metric_map[item["name"]] for item in pains if item["name"] in pain_metric_map][:2]
    if not monitor:
        monitor = ["????????", "????????"]
    monitor = unique_keep_order(build_focus_metrics(selected_focus) + monitor)[:3]

    input_value = input_map[domain["code"]]
    output_value = output_map[domain["code"]]
    what_value = what_map[domain["code"]]

    if selected_focus:
        why = f"{why} ???????{focus_text}?"
        input_value = f"{input_value}??????{focus_text}"
    if selected_expectations:
        output_value = f"{focus_text}???????????{action_clause}"
    elif selected_focus:
        output_value = f"{focus_text}??????????????"
    if has_selected_constraints:
        what_value = f"{focus_text}???{action_clause}"

    return {
        "why": why,
        "what": what_value,
        "where": where_map[domain["code"]],
        "who": owner_map[domain["code"]],
        "input": input_value,
        "output": output_value,
        "how": how_steps,
        "monitor": monitor,
        "howmuch": "??????????????????????? IT ???",
    }


def build_analysis_response(
    user_input: str,
    domain: dict,
    pains: list[dict],
    actions: list[dict],
    selected_roles: list[str] | None = None,
    selected_focus: list[str] | None = None,
    selected_expectations: list[str] | None = None,
) -> dict:
    confirmation_options = build_confirmation_options(domain, pains, actions)
    target_users = unique_keep_order(selected_roles or build_target_users(user_input, domain, confirmation_options))
    return {
        "original_request": user_input,
        "rewritten_request": build_rewritten_request(
            user_input,
            domain,
            pains,
            actions,
            target_users,
            selected_focus,
            selected_expectations,
        ),
        "business_domain": domain["name"],
        "pain_points": [item["name"] for item in pains],
        "system_actions": [item["name"] for item in actions],
        "target_users": target_users,
        "real_intent": build_real_intent(user_input, domain, pains, actions),
        "suggested_request": build_natural_request(
            user_input,
            domain,
            pains,
            actions,
            target_users,
            selected_focus,
            selected_expectations,
        ),
        "uncertain_items": build_uncertain_items(domain, actions),
        "confirmation_options": confirmation_options,
        "structured_report": build_structured_report(
            user_input,
            domain,
            pains,
            actions,
            target_users,
            selected_focus,
            selected_expectations,
        ),
        "mode": "mock",
    }


def build_mock_analysis(user_input: str) -> dict:
    return build_context_analysis(user_input)


def build_mock_refinement(user_input: str, analysis_result: dict, selected_options: dict) -> dict:
    base_analysis = validate_analysis_result(analysis_result or {}, user_input)
    diagnosis = base_analysis["diagnosis"]
    roles = normalize_selected_values(selected_options.get("affected_roles"))
    focus_points = normalize_selected_values(selected_options.get("focus_points"))
    expectations = normalize_selected_values(selected_options.get("system_expectations"))
    scenario_values = flatten_scenario_answers(selected_options)
    target_users = roles or base_analysis["target_users"]
    focus = focus_points or derive_focus_points(diagnosis, base_analysis["pain_points"])
    actions = expectations or base_analysis["system_actions"]
    domain_name = base_analysis["business_domain"]
    scenario_form = analysis_result.get("scenario_form") if isinstance(analysis_result.get("scenario_form"), dict) else {}
    scenario_template_code = cleanup_sentence(scenario_form.get("template_code"))
    process_breakpoint = join_items(focus, diagnosis["process_breakpoint"])
    action_clause = build_action_clause(actions)
    users_text = join_items(target_users, "????")
    impact = diagnosis["business_impact"]
    trigger = "???????????????"
    previous_request = cleanup_sentence(analysis_result.get("suggested_request")) if isinstance(analysis_result, dict) else ""

    if scenario_values and (domain_name == "Warehouse" or scenario_template_code == "warehouse_inventory_accuracy" or "??" in user_input):
        scenario_action = scenario_answer_phrase(selected_options, "expected_action", action_clause)
        inventory_scope = scenario_answer_phrase(selected_options, "inventory_definition", "????")
        scenario_owner = scenario_answer_phrase(selected_options, "exception_owner", users_text)
        action_values = scenario_answers_by_key(selected_options, "expected_action")
        action_parts: list[str] = []
        for value in action_values:
            cleaned_value = value.replace("???", "", 1).replace(inventory_scope, "??").strip()
            if "??????" in cleaned_value:
                cleaned_value = "????"
            if cleaned_value and cleaned_value not in action_parts:
                action_parts.append(cleaned_value)
        action_text = selection_phrase(action_parts, "???????")
        refined = limit_text(
            f"?????????{inventory_scope}{action_text}??????????{scenario_owner}??????????????",
            120,
        )
        rewritten = limit_text(f"?????{inventory_scope}???????????????????", 80)
    elif scenario_values:
        scenario_focus = selection_phrase(scenario_values[:3], process_breakpoint)
        refined = limit_text(
            f"?{trigger}?????{scenario_focus}?????????????{users_text}???????{impact}",
            120,
        )
        rewritten = limit_text(f"??????{scenario_focus}?????????????????????", 80)
    else:
        refined = limit_text(
            f"?{trigger}?????{process_breakpoint}?{action_clause}???{users_text}???????{impact}",
            120,
        )
        rewritten = limit_text(
            f"?????{domain_name}??????{users_text}??{process_breakpoint}?????????????",
            80,
        )
    if not scenario_values:
        refined = build_integrated_refine_text(refined, selected_options, diagnosis, domain_name, 120)
        rewritten = build_integrated_refine_text(rewritten, selected_options, diagnosis, domain_name, 80)

    uncertain_items: list[str] = ensure_string_list(base_analysis.get("uncertain_items"))
    confirmation = base_analysis.get("confirmation_options") if isinstance(base_analysis.get("confirmation_options"), dict) else {}
    for label, key, selected_values in [
        ("????", "affected_roles", roles),
        ("????", "focus_points", focus_points),
        ("????", "system_expectations", expectations),
    ]:
        allowed = ensure_string_list(confirmation.get(key))
        for value in selected_values:
            if allowed and value not in allowed:
                uncertain_items.append(f"?????{label}?{value}??AI????????????")

    structured_report = ensure_structured_report(base_analysis.get("structured_report"))
    structured_report["what"] = f"??{process_breakpoint}?{action_clause}"
    structured_report["who"] = users_text
    structured_report["output"] = f"{process_breakpoint}???????????????"
    if scenario_values:
        structured_report["input"] = f"???????{join_items(scenario_values[:6])}"
        structured_report["output"] = f"??{join_items(scenario_values[:4])}???????????????"
    structured_report["how"] = [
        "?????????????????",
        f"????{process_breakpoint}?{action_clause}?",
        f"?????{users_text}???????????",
    ]
    if previous_request and previous_request not in refined:
        uncertain_items.append("??????????????????????")

    return {
        "refined_request": refined,
        "rewritten_request": rewritten,
        "target_users": target_users,
        "uncertain_items": unique_keep_order(uncertain_items)[:3],
        "structured_report": structured_report,
        "mode": "mock",
    }


def build_chat_completions_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    if cleaned.endswith("/responses"):
        return cleaned[: -len("/responses")] + "/chat/completions"
    if cleaned.endswith("/v1"):
        return f"{cleaned}/chat/completions"
    return f"{cleaned}/v1/chat/completions"


def build_responses_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/responses"):
        return cleaned
    if cleaned.endswith("/chat/completions"):
        return cleaned[: -len("/chat/completions")] + "/responses"
    if cleaned.endswith("/v1"):
        return f"{cleaned}/responses"
    return f"{cleaned}/v1/responses"


def llm_enabled() -> bool:
    return bool(os.getenv("LLM_API_KEY") and os.getenv("LLM_BASE_URL") and os.getenv("LLM_MODEL"))


def llm_wire_api() -> str:
    value = normalize_text(os.getenv("LLM_WIRE_API") or os.getenv("LLM_API_TYPE")).lower()
    if value in {"responses", "response"}:
        return "responses"
    return "chat_completions"


def llm_debug_enabled() -> bool:
    return normalize_text(os.getenv("LLM_DEBUG")).lower() == "true"


def llm_timeout_seconds() -> float:
    raw_value = normalize_text(os.getenv("LLM_TIMEOUT_SECONDS") or os.getenv("LLM_TIMEOUT"))
    if not raw_value:
        return 90.0
    try:
        return max(10.0, float(raw_value))
    except ValueError:
        return 90.0


def log_llm_event(message: str, **fields: object) -> None:
    safe_fields = {
        key: value
        for key, value in fields.items()
        if "key" not in key.lower() and "token" not in key.lower() and "secret" not in key.lower()
    }
    if safe_fields:
        app.logger.info("[LLM] %s | %s", message, json.dumps(safe_fields, ensure_ascii=False))
        return
    app.logger.info("[LLM] %s", message)


def extract_json_payload(content: object) -> dict:
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )

    text = normalize_text(content)
    if not text:
        raise ValueError("LLM ??????")

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("LLM ??????? JSON ??")

    return json.loads(match.group(0))


def extract_responses_text(payload: dict) -> str:
    output_text = normalize_text(payload.get("output_text"))
    if output_text:
        return output_text

    texts: list[str] = []
    for item in payload.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if text is not None:
                texts.append(str(text))
    return "".join(texts)


def call_llm_json_responses(system_prompt: str, user_prompt: str, label: str = "llm", model_override: str = "", timeout_override: float | None = None, reasoning_effort: str = "", max_output_tokens: int | None = None) -> dict:
    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "")
    model = model_override or os.getenv("LLM_MODEL", "")

    timeout_seconds = timeout_override if timeout_override is not None else llm_timeout_seconds()
    log_llm_event("request_start", label=label, model=model, base_url=base_url, wire_api="responses", timeout_seconds=timeout_seconds, reasoning_effort=reasoning_effort, max_output_tokens=max_output_tokens)
    request_json = {
        "model": model,
        "instructions": system_prompt,
        "input": f"???? JSON ??????????? Markdown ??????\n\n{user_prompt}",
        "text": {"format": {"type": "json_object"}},
    }
    if reasoning_effort:
        request_json["reasoning"] = {"effort": reasoning_effort}
    if max_output_tokens is not None:
        request_json["max_output_tokens"] = max_output_tokens
    response = requests.post(
        build_responses_url(base_url),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=request_json,
        timeout=timeout_seconds,
    )
    if not response.ok:
        error_text = response.text[:1000]
        log_llm_event("request_failed", label=label, status_code=response.status_code, response=error_text)
        response.raise_for_status()
    try:
        payload = response.json()
    except Exception:
        if llm_debug_enabled():
            app.logger.info("[LLM] raw_response_text | %s", response.text)
        raise
    if llm_debug_enabled():
        app.logger.info("[LLM] raw_response | %s", json.dumps({"label": label, "payload": payload}, ensure_ascii=False))
    if payload.get("error"):
        raise ValueError(f"LLM ?????{payload.get('error')}")
    parsed = extract_json_payload(extract_responses_text(payload))
    log_llm_event("parse_success", label=label)
    return parsed


def call_llm_json(system_prompt: str, user_prompt: str, label: str = "llm", model_override: str = "", timeout_override: float | None = None, reasoning_effort: str = "", max_output_tokens: int | None = None) -> dict:
    if llm_wire_api() == "responses":
        return call_llm_json_responses(system_prompt, user_prompt, label, model_override=model_override, timeout_override=timeout_override, reasoning_effort=reasoning_effort, max_output_tokens=max_output_tokens)

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "")
    model = model_override or os.getenv("LLM_MODEL", "")

    timeout_seconds = timeout_override if timeout_override is not None else llm_timeout_seconds()
    log_llm_event("request_start", label=label, model=model, base_url=base_url, wire_api="chat_completions", timeout_seconds=timeout_seconds)
    response = requests.post(
        build_chat_completions_url(base_url),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=timeout_seconds,
    )
    if not response.ok:
        error_text = response.text[:1000]
        log_llm_event("request_failed", label=label, status_code=response.status_code, response=error_text)
        response.raise_for_status()
    try:
        payload = response.json()
    except Exception as exc:
        if llm_debug_enabled():
            app.logger.info("[LLM] raw_response_text | %s", response.text)
        log_llm_event("parse_failed", label=label, reason=f"???? JSON?{exc}")
        raise
    if llm_debug_enabled():
        app.logger.info("[LLM] raw_response | %s", json.dumps({"label": label, "payload": payload}, ensure_ascii=False))
    choices = payload.get("choices") or []
    if not choices:
        log_llm_event("parse_failed", label=label, reason="LLM ???? choices")
        raise ValueError("LLM ???? choices")
    message = choices[0].get("message") or {}
    try:
        parsed = extract_json_payload(message.get("content"))
    except Exception as exc:
        log_llm_event("parse_failed", label=label, reason=str(exc))
        raise
    log_llm_event("parse_success", label=label)
    return parsed


def ensure_string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return unique_keep_order([normalize_text(value) for value in values if normalize_text(value)])


def ensure_candidate_list(values: object) -> list[dict]:
    if not isinstance(values, list):
        return []
    result: list[dict] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        name = normalize_text(value.get("name"))
        if not name:
            continue
        try:
            confidence = float(value.get("confidence", 0))
        except (TypeError, ValueError):
            confidence = 0
        result.append(
            {
                "name": name,
                "confidence": max(0, min(confidence, 1)),
                "reason": normalize_text(value.get("reason")) or "?????",
            }
        )
    result.sort(key=lambda item: item["confidence"], reverse=True)
    return result


def ensure_structured_report(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    return {
        "why": cleanup_sentence(source.get("why")) or "?????",
        "what": cleanup_sentence(source.get("what")) or "?????",
        "where": cleanup_sentence(source.get("where")) or "?????",
        "who": cleanup_sentence(source.get("who")) or "?????",
        "input": cleanup_sentence(source.get("input")) or "?????",
        "output": cleanup_sentence(source.get("output")) or "?????",
        "how": ensure_string_list(source.get("how")) or ["?????"],
        "monitor": ensure_string_list(source.get("monitor")) or ["?????"],
        "howmuch": cleanup_sentence(source.get("howmuch")) or "?????",
    }


def ensure_diagnosis_schema(value: object, original_request: str) -> dict:
    source = value if isinstance(value, dict) else build_fallback_diagnosis(original_request)
    diagnosis = {
        "explicit_facts": ensure_string_list(source.get("explicit_facts")),
        "inferred_context": ensure_string_list(source.get("inferred_context")),
        "business_domain_candidates": ensure_candidate_list(source.get("business_domain_candidates")),
        "related_system_candidates": ensure_candidate_list(source.get("related_system_candidates")),
        "target_users": ensure_string_list(source.get("target_users")),
        "business_object": cleanup_sentence(source.get("business_object")),
        "current_process": cleanup_sentence(source.get("current_process")) or "?????",
        "manual_actions": ensure_string_list(source.get("manual_actions")),
        "process_breakpoint": cleanup_sentence(source.get("process_breakpoint")) or "?????",
        "pain_root_cause": cleanup_sentence(source.get("pain_root_cause")) or "?????",
        "business_impact": cleanup_sentence(source.get("business_impact")) or "?????",
        "desired_system_behavior": ensure_string_list(source.get("desired_system_behavior")),
        "candidate_systems": ensure_string_list(source.get("candidate_systems")),
        "source_evidence": ensure_string_list(source.get("source_evidence")),
        "uncertain_items": ensure_string_list(source.get("uncertain_items")),
    }
    if not diagnosis["explicit_facts"]:
        diagnosis["explicit_facts"] = ["????????????????????????"]
    if not diagnosis["business_domain_candidates"]:
        diagnosis["business_domain_candidates"] = [
            {"name": "General", "confidence": 0.35, "reason": "?????????"}
        ]
    if not diagnosis["desired_system_behavior"]:
        diagnosis["desired_system_behavior"] = ["?????"]
    if not diagnosis["source_evidence"]:
        diagnosis["source_evidence"] = extract_source_evidence(original_request)
    diagnosis["primary_business_domain"] = cleanup_sentence(source.get("primary_business_domain")) or diagnosis["business_domain_candidates"][0]["name"]
    return diagnosis


def collect_low_confidence_uncertain(diagnosis: dict) -> list[str]:
    items: list[str] = []
    domain_candidates = ensure_candidate_list(diagnosis.get("business_domain_candidates"))
    if domain_candidates and domain_candidates[0]["confidence"] < 0.55:
        items.append("????????")
    for candidate in ensure_candidate_list(diagnosis.get("related_system_candidates")):
        if candidate["confidence"] < 0.72:
            items.append(f"???? {candidate['name']} ????")
    return items


def validate_analysis_result(result: dict, original_request: str) -> dict:
    source = result if isinstance(result, dict) else {}
    fallback = build_analysis_from_diagnosis(original_request, build_fallback_diagnosis(original_request)) if not source.get("diagnosis") else {}
    diagnosis = ensure_diagnosis_schema(source.get("diagnosis") or fallback.get("diagnosis"), original_request)
    warnings = ensure_string_list(source.get("warnings"))

    top_domain = diagnosis["business_domain_candidates"][0]
    business_domain = cleanup_sentence(source.get("business_domain")) or diagnosis.get("primary_business_domain") or top_domain["name"]
    if top_domain["confidence"] < 0.55:
        business_domain = "?????"

    requested_related_systems = ensure_string_list(source.get("related_systems"))
    high_conf_systems = [
        item["name"]
        for item in diagnosis["related_system_candidates"]
        if item["confidence"] >= 0.72 and system_explicitly_mentioned(item["name"], original_request)
    ]
    related_systems = filter_supported_related_systems(
        requested_related_systems + high_conf_systems,
        diagnosis,
        original_request,
        warnings,
    )
    candidate_systems = unique_keep_order(
        ensure_string_list(source.get("candidate_systems"))
        + ensure_string_list(diagnosis.get("candidate_systems"))
        + infer_candidate_systems(business_domain, original_request, retrieve_context(original_request), related_systems)
    )[:6]
    business_object = cleanup_sentence(source.get("business_object")) or diagnosis.get("business_object")
    if not business_object:
        matched_objects = ensure_string_list(retrieve_context(original_request).get("matched_business_objects"))
        business_object = infer_specific_business_object(
            original_request,
            business_domain,
            matched_objects[0] if matched_objects else "???????",
        )

    pain_points = ensure_string_list(source.get("pain_points"))
    if not pain_points:
        pain_context = " ".join(
            [
                diagnosis["pain_root_cause"],
                diagnosis["process_breakpoint"],
                " ".join(diagnosis["manual_actions"]),
            ]
        )
        pain_points = [item["name"] for item in build_context_candidates(pain_context, "pain_types", 5)]
    if not pain_points:
        pain_points = ["?????"]

    system_actions = ensure_string_list(source.get("system_actions"))
    if not system_actions:
        behavior_context = " ".join(diagnosis["desired_system_behavior"])
        system_actions = [item["name"] for item in build_context_candidates(behavior_context, "system_actions", 5)]
    if not system_actions:
        system_actions = ["?????"]

    target_users = ensure_string_list(source.get("target_users")) or diagnosis["target_users"]
    text_fields = build_diagnostic_texts(original_request, diagnosis, pain_points, system_actions)
    real_intent = cleanup_sentence(source.get("real_intent")) or text_fields["real_intent"]
    rewritten_request = limit_text(source.get("rewritten_request") or text_fields["rewritten_request"], 80)
    suggested_request = limit_text(source.get("suggested_request") or text_fields["suggested_request"], 120)

    real_intent = sanitize_unconfirmed_system_text(real_intent, original_request, related_systems, warnings)
    rewritten_request = limit_text(
        sanitize_unconfirmed_system_text(rewritten_request, original_request, related_systems, warnings),
        80,
    )
    suggested_request = limit_text(
        sanitize_unconfirmed_system_text(suggested_request, original_request, related_systems, warnings),
        120,
    )

    uncertain_items = unique_keep_order(
        ensure_string_list(source.get("uncertain_items"))
        + diagnosis["uncertain_items"]
        + collect_low_confidence_uncertain(diagnosis)
    )
    if not uncertain_items:
        uncertain_items = ["??????????????????"]

    confirmation = source.get("confirmation_options") if isinstance(source.get("confirmation_options"), dict) else {}
    confirmation_options = {
        "affected_roles": ensure_string_list(confirmation.get("affected_roles")),
        "focus_points": ensure_string_list(confirmation.get("focus_points")),
        "system_expectations": ensure_string_list(confirmation.get("system_expectations")),
    }
    default_confirmation = build_confirmation_options_from_diagnosis(diagnosis, pain_points, system_actions)
    for key, values in default_confirmation.items():
        if not confirmation_options[key]:
            confirmation_options[key] = values

    structured_report = ensure_structured_report(source.get("structured_report"))
    if structured_report["why"] == "?????":
        structured_report["why"] = diagnosis["pain_root_cause"]
    if structured_report["what"] == "?????":
        structured_report["what"] = join_items(diagnosis["desired_system_behavior"], "?????")
    if structured_report["where"] == "?????":
        structured_report["where"] = diagnosis["current_process"]
    if structured_report["who"] == "?????":
        structured_report["who"] = join_items(target_users, "?????")
    if structured_report["input"] == "?????" and related_systems:
        structured_report["input"] = join_items(related_systems)
    if structured_report["output"] == "?????":
        structured_report["output"] = join_items(diagnosis["desired_system_behavior"], "?????")
    for key in ["why", "what", "where", "who", "input", "output", "howmuch"]:
        structured_report[key] = sanitize_unconfirmed_system_text(
            structured_report.get(key),
            original_request,
            related_systems,
            warnings,
        )
    for key in ["how", "monitor"]:
        structured_report[key] = [
            sanitize_unconfirmed_system_text(value, original_request, related_systems, warnings)
            for value in ensure_string_list(structured_report.get(key))
        ]

    return {
        "original_request": original_request,
        "diagnosis": diagnosis,
        "business_domain": business_domain,
        "business_object": business_object,
        "related_systems": related_systems,
        "candidate_systems": candidate_systems,
        "pain_points": pain_points,
        "system_actions": system_actions,
        "target_users": target_users,
        "real_intent": real_intent,
        "rewritten_request": rewritten_request,
        "suggested_request": suggested_request,
        "confirmation_options": confirmation_options,
        "scenario_form": build_scenario_form(original_request, retrieve_context(original_request), business_domain, business_object),
        "structured_report": structured_report,
        "uncertain_items": uncertain_items[:8],
        "warnings": unique_keep_order(warnings),
        "mode": source.get("mode") or "mock",
    }


def top_relevant_context_item(retrieved_context: dict, context_key: str, name: str | None = None) -> dict:
    items = retrieved_context.get("relevant_context", {}).get(context_key, [])
    if not isinstance(items, list):
        return {}
    if name:
        for item in items:
            if isinstance(item, dict) and normalize_text(item.get("name")) == name:
                return item
    for item in items:
        if isinstance(item, dict):
            return item
    return {}


def normalize_context_list(values: object) -> list[str]:
    return unique_keep_order(flatten_context_strings(values))


DOMAIN_CANDIDATE_SYSTEMS = {
    "IPD": ["PLM", "SAP"],
    "IPMS": ["DMS"],
    "MTC": ["DMS", "SAP"],
    "SD": ["DMS", "WMS", "QMS"],
    "DSTE": ["????", "BI/????"],
    "Supply": ["SAP", "APS", "WMS", "????"],
    "Manufacturing": ["MES", "SAP"],
    "Procurement": ["SAP", "SRM", "????"],
    "Quality": ["QMS", "MES", "DMS"],
    "MBTIT": ["SAP", "MES", "WMS", "PLM", "SRM", "DMS"],
    "Warehouse": ["WMS", "SAP"],
}


def infer_candidate_systems(domain_name: str, user_input: str, retrieved_context: dict, related_systems: list[str]) -> list[str]:
    candidates: list[str] = []
    candidates.extend(related_systems)
    candidates.extend(DOMAIN_CANDIDATE_SYSTEMS.get(domain_name, []))

    if "??" in user_input and domain_name in ["Supply", "DSTE"]:
        candidates.append("????")
    if "APS" in user_input:
        candidates.append("APS")
    if any(keyword in user_input for keyword in ["??", "??", "??", "????"]):
        candidates.extend(["SAP", "WMS"])
    if any(keyword in user_input for keyword in ["???", "??", "????"]):
        candidates.extend(["SRM", "SAP"])
    if any(keyword in user_input for keyword in ["??", "??", "??", "??"]):
        candidates.append("QMS")
    if any(keyword in user_input for keyword in ["???", "??", "??", "??", "??"]):
        candidates.append("DMS")

    return unique_keep_order(candidates)[:6]


def concise_business_object(business_object: str) -> str:
    text = cleanup_sentence(business_object)
    replacements = {
        "?????????????????/????": "??????????",
        "?????????": "????",
        "?????????????": "???????",
        "???????????": "????????",
        "????????????": "???????",
        "???????????????": "????????",
        "??????????????": "?????????",
        "???????????": "?????????",
        "??????????????": "?????????",
        "??/BOM?????????": "??/BOM????",
    }
    return replacements.get(text, text)


def infer_specific_business_object(user_input: str, domain_name: str, fallback_object: str) -> str:
    text = normalize_text(user_input)
    if domain_name == "Supply" and any(keyword in text for keyword in ["??", "??", "??"]):
        return "?????????????????/????"
    if domain_name == "Manufacturing" and any(keyword in text for keyword in ["??", "??", "??"]):
        return "?????????"
    if domain_name == "Procurement" and any(keyword in text for keyword in ["???", "??", "????", "??"]):
        return "?????????????"
    if domain_name == "Quality" and any(keyword in text for keyword in ["??", "??", "??", "??"]):
        return "???????????"
    if domain_name == "MBTIT" and any(keyword in text for keyword in ["???", "??", "?????"]):
        return "????????????"
    if domain_name == "DSTE" and any(keyword in text for keyword in ["??", "????", "??", "??"]):
        return "???????????????"
    if domain_name == "SD" and any(keyword in text for keyword in ["??", "??", "??"]):
        return "??????????????"
    if domain_name == "IPMS" and any(keyword in text for keyword in ["??", "??", "??", "??"]):
        return "???????????"
    if domain_name == "MTC" and any(keyword in text for keyword in ["???", "??", "??", "??"]):
        return "??????????????"
    if domain_name == "IPD" and any(keyword in text for keyword in ["??", "BOM", "??", "??"]):
        return "??/BOM?????????"
    return fallback_object


def extract_source_evidence(user_input: str) -> list[str]:
    evidence: list[str] = []
    patterns = [
        "????",
        "??????????????????",
        "??????????",
        "?????",
        "???",
        "??",
        "????",
        "????????????????",
        "?????????????",
        "??????",
        "????????????",
        "????",
        "??????????",
        "????????",
        "????????",
        "???????????",
        "??",
        "??",
    ]
    for pattern in patterns:
        if pattern in user_input:
            evidence.append(pattern)
    for keyword in ["????", "????", "???", "?????", "???", "??", "????", "?????", "????", "???", "??", "??", "??", "??", "?????"]:
        if keyword in user_input:
            evidence.append(keyword)
    return unique_keep_order(evidence)[:4]


def infer_supplemental_pain_points(user_input: str) -> list[str]:
    points: list[str] = []
    if any(keyword in user_input for keyword in ["????", "???", "???", "???", "???"]):
        points.extend(["???", "?????"])
    if any(keyword in user_input for keyword in ["???", "????", "???", "???", "????"]):
        points.extend(["????", "????"])
    if any(keyword in user_input for keyword in ["???", "?", "????"]):
        points.append("???")
    return unique_keep_order(points)


def build_contextual_current_manual_process(user_input: str, retrieved_context: dict, business_object: str) -> str:
    domain = top_relevant_context_item(retrieved_context, "domain_context")
    patterns = normalize_context_list(retrieved_context.get("matched_manual_actions"))
    manual_actions = patterns + choose_relevant_phrases(user_input, normalize_context_list(domain.get("common_manual_actions")), 2)
    manual_actions = unique_keep_order(manual_actions)
    object_status_suffix = "" if business_object.endswith("??") else "??"
    if manual_actions:
        return cleanup_sentence(
            f"?????{join_items(manual_actions[:3])}???{business_object}{object_status_suffix}??????????????"
        )
    return cleanup_sentence(
        f"??{business_object}????????????????????????????????????"
    )


def build_contextual_process_breakpoint(user_input: str, retrieved_context: dict, business_object: str) -> str:
    domain = top_relevant_context_item(retrieved_context, "domain_context")
    process = top_relevant_context_item(retrieved_context, "process_context", normalize_text(domain.get("name")))
    candidates = normalize_context_list(domain.get("common_breakpoints")) + normalize_context_list(process.get("typical_breakpoints"))
    selected = choose_relevant_phrases(user_input, candidates, 2)
    if selected:
        return cleanup_sentence(join_items(selected[:2]))
    return cleanup_sentence(f"{business_object}??????????????????????")


def build_contextual_passive_consequence(user_input: str, retrieved_context: dict, business_object: str) -> str:
    domain = top_relevant_context_item(retrieved_context, "domain_context")
    if "??" in user_input:
        return cleanup_sentence(f"????????{business_object}????????????????")
    if "?????" in user_input:
        return cleanup_sentence(f"?????????????????{business_object}?")
    if "??????" in user_input:
        return cleanup_sentence(f"??????????????????{business_object}???????")
    if "??" in user_input:
        return cleanup_sentence(f"?????????????????????")
    candidates = normalize_context_list(domain.get("common_consequences"))
    selected = choose_relevant_phrases(user_input, candidates, 2)
    if selected:
        return cleanup_sentence(join_items(selected[:2]))
    if any(keyword in user_input for keyword in ["?", "??", "???", "??", "??"]):
        return cleanup_sentence(f"??????????????{business_object}??????")
    return cleanup_sentence(f"{business_object}?????????????????")


def expand_minimum_behavior(behavior: str, business_object: str, manual_process: str, breakpoint: str) -> str:
    cleaned = cleanup_sentence(behavior)
    if not cleaned:
        return ""
    replacement = "???????"
    if "?" in manual_process:
        replacement = "????????"
    elif "?" in manual_process:
        replacement = "????"
    elif "??" in manual_process or "??" in manual_process:
        replacement = "???????"
    elif "??" in manual_process:
        replacement = "??????"
    elif "Excel" in manual_process:
        replacement = "Excel????"

    if any(keyword in cleaned for keyword in ["??", "??", "??"]):
        return cleanup_sentence(f"?{business_object}??????????????????{replacement}")
    if any(keyword in cleaned for keyword in ["??", "??"]):
        object_status_suffix = "" if business_object.endswith("??") else "??"
        return cleanup_sentence(f"????{business_object}{object_status_suffix}???{replacement}")
    if any(keyword in cleaned for keyword in ["??", "?", "??"]):
        return cleanup_sentence(f"????{business_object}??????????????{replacement}")
    if any(keyword in cleaned for keyword in ["??", "??", "??", "??", "??", "??"]):
        return cleanup_sentence(f"????{business_object}???????????{replacement}")
    if any(keyword in cleaned for keyword in ["??", "??", "??", "??"]):
        return cleanup_sentence(f"????{business_object}????????{replacement}")
    if any(keyword in cleaned for keyword in ["??", "??", "??"]):
        return cleanup_sentence(f"????{business_object}????????{replacement}")
    if len(cleaned) <= 6 or cleaned in ["????", "????", "???", "????", "????"]:
        return cleanup_sentence(f"{cleaned}{business_object}?????{replacement}")
    if business_object not in cleaned and len(cleaned) < 18:
        return cleanup_sentence(f"{cleaned}{business_object}?????{breakpoint}")
    return cleaned


def build_contextual_minimum_behaviors(
    user_input: str,
    retrieved_context: dict,
    business_object: str,
    manual_process: str,
    breakpoint: str,
) -> list[str]:
    domain = top_relevant_context_item(retrieved_context, "domain_context")
    action_context = retrieved_context.get("relevant_context", {}).get("action_context", [])
    candidates = normalize_context_list(domain.get("typical_system_behaviors"))
    for item in action_context if isinstance(action_context, list) else []:
        if isinstance(item, dict):
            candidates.extend(normalize_context_list(item.get("examples")))
            candidates.append(normalize_text(item.get("description")))
    selected = choose_relevant_phrases(user_input, candidates, 4)
    expanded = [
        expand_minimum_behavior(item, business_object, manual_process, breakpoint)
        for item in selected
    ]
    expanded = [item for item in expanded if item]
    if not expanded:
        expanded = [
            f"????{business_object}?????????",
            f"????{business_object}????????",
            f"????{business_object}????????",
        ]
    return unique_keep_order(expanded)[:4]


def build_fast_uncertain_items(user_input: str, retrieved_context: dict, related_systems: list[str]) -> list[str]:
    items: list[str] = []
    system_candidates = ensure_string_list(retrieved_context.get("matched_systems"))
    if system_candidates and not related_systems:
        items.append("???????????")
    if any(keyword in user_input for keyword in ["??", "?", "???", "??", "??", "??"]):
        items.append("???????")
    if any(keyword in user_input for keyword in ["??", "??", "??", "???"]):
        items.append("???????????")
    if any(keyword in user_input for keyword in ["??", "??", "??", "???"]):
        items.append("???????????")
    if any(keyword in user_input for keyword in ["??", "??", "????", "??"]):
        items.append("??????????????")
    if len(items) < 3:
        items.append("???????????")
    return unique_keep_order(items)[:3]


def build_fast_fallback_from_context(user_input: str, retrieved_context: dict | None = None) -> dict:
    retrieved_context = retrieved_context or retrieve_context(user_input)
    text = normalize_text(user_input)
    domain_name = ensure_string_list(retrieved_context.get("matched_domains"))[0] if ensure_string_list(retrieved_context.get("matched_domains")) else "General"
    fallback_business_object = ensure_string_list(retrieved_context.get("matched_business_objects"))[0] if ensure_string_list(retrieved_context.get("matched_business_objects")) else "???????"
    business_object = infer_specific_business_object(text, domain_name, fallback_business_object)
    text_business_object = concise_business_object(business_object)
    related_systems = explicit_system_names(text)
    candidate_systems = infer_candidate_systems(domain_name, text, retrieved_context, related_systems)
    pain_points = unique_keep_order(
        ensure_string_list(retrieved_context.get("matched_pain_types"))
        + infer_supplemental_pain_points(text)
    ) or ["?????"]
    system_actions = ensure_string_list(retrieved_context.get("matched_system_actions")) or ["????", "???"]
    target_users = ensure_string_list(retrieved_context.get("matched_roles"))[:4]
    if not target_users:
        target_users = ["?????"]

    current_manual_process = build_contextual_current_manual_process(text, retrieved_context, text_business_object)
    process_breakpoint = build_contextual_process_breakpoint(text, retrieved_context, text_business_object)
    passive_consequence = build_contextual_passive_consequence(text, retrieved_context, text_business_object)
    minimum_system_behavior = build_contextual_minimum_behaviors(
        text,
        retrieved_context,
        text_business_object,
        current_manual_process,
        process_breakpoint,
    )
    roles_text = join_items(target_users[:2], "???")
    first_behavior = minimum_system_behavior[0]
    real_intent = limit_text(
        f"?????????????????{roles_text}?{business_domain_label(domain_name)}?????????????{text_business_object}?????{passive_consequence}?",
        120,
    )
    rewritten_request = limit_text(
        f"??????{text_business_object}????????????{process_breakpoint}???{passive_consequence}?",
        80,
    )
    suggested_request = limit_text(
        f"?{text_business_object}???????????{first_behavior}???{roles_text}?????????{passive_consequence}?",
        120,
    )

    diagnosis = {
        "business_object": business_object,
        "current_process": current_manual_process,
        "current_manual_process": current_manual_process,
        "manual_actions": ensure_string_list(retrieved_context.get("matched_manual_actions")),
        "process_breakpoint": process_breakpoint,
        "passive_consequence": passive_consequence,
        "pain_root_cause": f"{process_breakpoint}???{passive_consequence}",
        "business_impact": passive_consequence,
        "minimum_system_behavior": minimum_system_behavior,
        "desired_system_behavior": minimum_system_behavior,
        "target_users": target_users,
        "candidate_systems": candidate_systems,
        "source_evidence": extract_source_evidence(text),
        "uncertain_items": build_fast_uncertain_items(text, retrieved_context, related_systems),
    }
    return {
        "original_request": text,
        "business_domain": domain_name,
        "business_object": business_object,
        "related_systems": related_systems,
        "candidate_systems": candidate_systems,
        "pain_points": pain_points,
        "system_actions": system_actions,
        "target_users": target_users,
        "current_manual_process": current_manual_process,
        "process_breakpoint": process_breakpoint,
        "passive_consequence": passive_consequence,
        "minimum_system_behavior": minimum_system_behavior,
        "real_intent": real_intent,
        "rewritten_request": rewritten_request,
        "suggested_request": suggested_request,
        "confirmation_options": build_confirmation_options_from_diagnosis(diagnosis, pain_points, system_actions),
        "scenario_form": build_scenario_form(text, retrieved_context, domain_name, business_object),
        "uncertain_items": diagnosis["uncertain_items"],
        "diagnosis": diagnosis,
        "mode": "mock",
    }


def normalize_fast_analysis_result(
    payload: dict,
    user_input: str,
    retrieved_context: dict,
    used_llm: bool,
    used_fallback: bool,
    elapsed_ms: int,
    retry_used: bool = False,
) -> dict:
    source = payload if isinstance(payload, dict) else {}
    fallback = build_fast_fallback_from_context(user_input, retrieved_context)
    diagnosis = source.get("diagnosis") if isinstance(source.get("diagnosis"), dict) else {}

    business_object = cleanup_sentence(
        source.get("business_object")
        or diagnosis.get("business_object")
        or fallback["business_object"]
    )
    current_manual_process = cleanup_sentence(
        source.get("current_manual_process")
        or diagnosis.get("current_manual_process")
        or diagnosis.get("current_process")
        or fallback["current_manual_process"]
    )
    process_breakpoint = cleanup_sentence(
        source.get("process_breakpoint")
        or diagnosis.get("process_breakpoint")
        or fallback["process_breakpoint"]
    )
    passive_consequence = cleanup_sentence(
        source.get("passive_consequence")
        or diagnosis.get("passive_consequence")
        or diagnosis.get("business_impact")
        or fallback["passive_consequence"]
    )
    minimum_system_behavior = (
        ensure_string_list(source.get("minimum_system_behavior"))
        or ensure_string_list(diagnosis.get("minimum_system_behavior"))
        or ensure_string_list(diagnosis.get("desired_system_behavior"))
        or fallback["minimum_system_behavior"]
    )
    related_systems = filter_supported_related_systems(
        ensure_string_list(source.get("related_systems")),
        {"related_system_candidates": [{"name": item, "confidence": 0.6, "reason": "????"} for item in retrieved_context.get("matched_systems", [])]},
        user_input,
        warnings=[],
    )

    warnings: list[str] = []
    related_systems = filter_supported_related_systems(
        related_systems,
        {"related_system_candidates": [{"name": item, "confidence": 0.6, "reason": "????"} for item in retrieved_context.get("matched_systems", [])]},
        user_input,
        warnings,
    )
    candidate_systems = unique_keep_order(
        ensure_string_list(source.get("candidate_systems"))
        + ensure_string_list(diagnosis.get("candidate_systems"))
        + fallback.get("candidate_systems", [])
    )[:6]
    real_intent = sanitize_unconfirmed_system_text(
        source.get("real_intent") or fallback["real_intent"],
        user_input,
        related_systems,
        warnings,
    )
    rewritten_request = limit_text(
        sanitize_unconfirmed_system_text(source.get("rewritten_request") or fallback["rewritten_request"], user_input, related_systems, warnings),
        80,
    )
    suggested_request = limit_text(
        sanitize_unconfirmed_system_text(source.get("suggested_request") or fallback["suggested_request"], user_input, related_systems, warnings),
        120,
    )
    confirmation = source.get("confirmation_options") if isinstance(source.get("confirmation_options"), dict) else {}
    fallback_confirmation = fallback["confirmation_options"]
    confirmation_options = {
        "affected_roles": ensure_string_list(confirmation.get("affected_roles")) or fallback_confirmation["affected_roles"],
        "focus_points": ensure_string_list(confirmation.get("focus_points")) or fallback_confirmation["focus_points"],
        "system_expectations": ensure_string_list(confirmation.get("system_expectations")) or fallback_confirmation["system_expectations"],
    }
    uncertain_items = unique_keep_order(
        ensure_string_list(source.get("uncertain_items"))
        + build_fast_uncertain_items(user_input, retrieved_context, related_systems)
    )[:3]
    debug_source = source.get("debug") if isinstance(source.get("debug"), dict) else {}
    result = {
        "original_request": user_input,
        "business_domain": cleanup_sentence(source.get("business_domain")) or fallback["business_domain"],
        "business_object": business_object,
        "related_systems": related_systems,
        "candidate_systems": candidate_systems,
        "pain_points": ensure_string_list(source.get("pain_points")) or fallback["pain_points"],
        "system_actions": ensure_string_list(source.get("system_actions")) or fallback["system_actions"],
        "target_users": ensure_string_list(source.get("target_users")) or fallback["target_users"],
        "current_manual_process": current_manual_process,
        "process_breakpoint": process_breakpoint,
        "passive_consequence": passive_consequence,
        "minimum_system_behavior": minimum_system_behavior[:4],
        "real_intent": limit_text(real_intent, 120),
        "rewritten_request": rewritten_request,
        "suggested_request": suggested_request,
        "confirmation_options": confirmation_options,
        "scenario_form": source.get("scenario_form") if isinstance(source.get("scenario_form"), dict) else build_scenario_form(user_input, retrieved_context, cleanup_sentence(source.get("business_domain")) or fallback["business_domain"], business_object),
        "uncertain_items": uncertain_items,
        "diagnosis": {
            "business_object": business_object,
            "current_process": current_manual_process,
            "current_manual_process": current_manual_process,
            "manual_actions": ensure_string_list(retrieved_context.get("matched_manual_actions")),
            "process_breakpoint": process_breakpoint,
            "passive_consequence": passive_consequence,
            "pain_root_cause": cleanup_sentence(diagnosis.get("pain_root_cause")) or f"{process_breakpoint}???{passive_consequence}",
            "business_impact": passive_consequence,
            "minimum_system_behavior": minimum_system_behavior[:4],
            "desired_system_behavior": minimum_system_behavior[:4],
            "target_users": ensure_string_list(source.get("target_users")) or fallback["target_users"],
            "candidate_systems": candidate_systems,
            "source_evidence": unique_keep_order(
                ensure_string_list(diagnosis.get("source_evidence")) + extract_source_evidence(user_input)
            )[:4],
            "uncertain_items": uncertain_items,
        },
        "warnings": unique_keep_order(warnings + ensure_string_list(source.get("warnings"))),
        "mode": "llm" if used_llm and not used_fallback else "mock",
        "debug": {
            "used_llm": bool(used_llm and not used_fallback),
            "used_fallback": bool(used_fallback),
            "used_mock": bool(used_fallback or not used_llm),
            "model": os.getenv("LLM_MODEL", "") if used_llm else "",
            "elapsed_ms": elapsed_ms,
            "retrieved_context_summary": retrieved_context_summary(retrieved_context),
            "quality_passed": True,
            "quality_issues": [],
            "llm_retry": bool(retry_used),
            **debug_source,
        },
    }
    return result


def has_business_object(text: str, business_object: str) -> bool:
    object_text = cleanup_sentence(business_object)
    if not object_text:
        return False
    if object_text in text:
        return True
    for term in re.split(r"[\s,??/?;?]+", object_text):
        if len(term) >= 2 and term in text:
            return True
    return False


def vague_without_specifics(text: str, business_object: str) -> bool:
    cleaned = cleanup_sentence(text)
    vague_terms = [
        "????",
        "????",
        "????",
        "????",
        "????",
        "????",
        "??????",
        "????????",
    ]
    if not any(term in cleaned for term in vague_terms):
        return False
    return not has_business_object(cleaned, business_object)


def is_vague_behavior(values: list[str], business_object: str) -> bool:
    if not values:
        return True
    vague_labels = {"????", "????", "???", "????", "????", "????"}
    for value in values:
        cleaned = cleanup_sentence(value)
        if not cleaned or cleaned in vague_labels:
            return True
        if len(cleaned) < 8 and not has_business_object(cleaned, business_object):
            return True
    return False


def quality_check_fast(result: dict, user_input: str, retrieved_context: dict) -> dict:
    issues: list[str] = []
    business_object = cleanup_sentence(result.get("business_object"))
    vague_business_objects = {"????", "??", "????", "??", "???????", "????"}

    if not business_object or business_object in vague_business_objects:
        issues.append("business_object ???????")
    current_manual_process = cleanup_sentence(result.get("current_manual_process"))
    if not current_manual_process or current_manual_process in ["????", "????", "???"] or len(current_manual_process) < 10:
        issues.append("current_manual_process ??????????")
    process_breakpoint = cleanup_sentence(result.get("process_breakpoint"))
    if not process_breakpoint or process_breakpoint in ["????", "????"] or len(process_breakpoint) < 8:
        issues.append("process_breakpoint ??????????")
    passive_consequence = cleanup_sentence(result.get("passive_consequence"))
    if not passive_consequence or passive_consequence in ["????", "????"] or len(passive_consequence) < 8:
        issues.append("passive_consequence ??????????")
    if is_vague_behavior(ensure_string_list(result.get("minimum_system_behavior")), business_object):
        issues.append("minimum_system_behavior ???????????????")

    rewritten = cleanup_sentence(result.get("rewritten_request"))
    if not has_business_object(rewritten, business_object):
        issues.append("rewritten_request ??????????")
    if len(rewritten) > 80:
        issues.append("rewritten_request ?? 80 ?")

    suggested = cleanup_sentence(result.get("suggested_request"))
    has_trigger = any(keyword in suggested for keyword in ["?", "??", "?", "??", "?"])
    has_action = any(action in suggested for action in ensure_string_list(result.get("system_actions")) + ["??", "??", "??", "??", "??", "??", "??"])
    has_value = any(keyword in suggested for keyword in ["??", "??", "??", "??", "??", "??"])
    if not (has_trigger and has_action and has_business_object(suggested, business_object) and has_value):
        issues.append("suggested_request ?????????????????????????")
    if len(suggested) > 120:
        issues.append("suggested_request ?? 120 ?")

    combined_text = " ".join(
        [
            current_manual_process,
            process_breakpoint,
            passive_consequence,
            rewritten,
            suggested,
            cleanup_sentence(result.get("real_intent")),
            " ".join(ensure_string_list(result.get("minimum_system_behavior"))),
        ]
    )
    if vague_without_specifics(combined_text, business_object):
        issues.append("?????????????????????????")
    issues.extend(contains_unsupported_specifics(result, user_input))

    return {"passed": not issues, "issues": unique_keep_order(issues)}


def build_analyze_fast_user_prompt(user_input: str, retrieved_context: dict | None = None) -> str:
    retrieved_context = retrieved_context or retrieve_context(user_input)
    return json.dumps(
        {
            "task": "fast_requirement_clarification",
            "user_input": user_input,
            "retrieved_context": retrieved_context_summary(retrieved_context),
            "workflow": [
                "??????",
                "????????",
                "??????",
                "??????",
                "??????????",
                "????????",
            ],
            "response_schema": {
                "original_request": "string",
                "business_domain": "string",
                "business_object": "string",
                "related_systems": ["string?????????????????????"],
                "candidate_systems": ["string?????????????????????????????????"],
                "pain_points": ["string"],
                "system_actions": ["string"],
                "target_users": ["string"],
                "current_manual_process": "string???????????",
                "process_breakpoint": "string?????????",
                "passive_consequence": "string???????????",
                "minimum_system_behavior": ["string??????????????"],
                "source_evidence": ["string???????????????????????????"],
                "real_intent": "string <= 120 chars",
                "rewritten_request": "string <= 80 chars",
                "suggested_request": "string <= 120 chars",
                "confirmation_options": {
                    "affected_roles": ["2-8????"],
                    "focus_points": ["2-8????"],
                    "system_expectations": ["2-8????"],
                },
                "uncertain_items": ["string"],
            },
        },
        ensure_ascii=False,
    )


def build_analyze_fast_retry_user_prompt(
    user_input: str,
    retrieved_context: dict,
    previous_result: dict,
    quality_check: dict,
) -> str:
    return json.dumps(
        {
            "instruction": (
                "?????????????????????????????????????"
                "???????????????????????????????????"
                "???????????? JSON?"
            ),
            "quality_issues": quality_check.get("issues", []),
            "user_input": user_input,
            "retrieved_context": retrieved_context,
            "previous_result": previous_result,
            "response_schema": json.loads(build_analyze_fast_user_prompt(user_input, retrieved_context))["response_schema"],
        },
        ensure_ascii=False,
    )


def build_roadmap_from_structured_report(structured_report: dict) -> list[dict]:
    report = ensure_structured_report(structured_report)
    how_steps = ensure_string_list(report.get("how"))
    monitor_items = ensure_string_list(report.get("monitor"))
    items = [
        {"stage": "Why", "title": shorten_focus_text(report["why"])},
        {"stage": "What", "title": shorten_focus_text(report["what"])},
        {"stage": "Where", "title": shorten_focus_text(report["where"])},
    ]
    for index, step in enumerate(how_steps[:3], start=1):
        items.append({"stage": f"How-S{index}", "title": shorten_focus_text(step)})
    if report["output"] != "?????":
        items.append({"stage": "Output", "title": shorten_focus_text(report["output"])})
    if monitor_items:
        items.append({"stage": "Monitor", "title": shorten_focus_text(monitor_items[0])})
    return items[:8]


def build_process_map_from_structured_report(structured_report: dict) -> dict:
    report = ensure_structured_report(structured_report)
    return {
        "nodes": [
            {"label": "????", "value": report["input"]},
            {"label": "????", "value": report["what"]},
            {"label": "????", "value": " ? ".join(ensure_string_list(report["how"]))},
            {"label": "????", "value": report["why"]},
            {"label": "????", "value": report["where"]},
            {"label": "???", "value": report["who"]},
            {"label": "????", "value": report["output"]},
            {"label": "????", "value": " ? ".join(ensure_string_list(report["monitor"]))},
        ]
    }


def build_deep_response(analysis: dict, fast_analysis: dict | None = None) -> dict:
    diagnosis = analysis.get("diagnosis") if isinstance(analysis.get("diagnosis"), dict) else {}
    fast = fast_analysis if isinstance(fast_analysis, dict) else {}
    structured_report = ensure_structured_report(analysis.get("structured_report"))
    business_object = cleanup_sentence(
        diagnosis.get("business_object")
        or fast.get("business_object")
        or "?????"
    )
    current_manual_process = cleanup_sentence(
        diagnosis.get("current_manual_process")
        or diagnosis.get("current_process")
        or fast.get("current_manual_process")
        or "?????"
    )
    passive_consequence = cleanup_sentence(
        diagnosis.get("passive_consequence")
        or fast.get("passive_consequence")
        or diagnosis.get("business_impact")
        or "?????"
    )
    minimum_system_behavior = (
        ensure_string_list(diagnosis.get("minimum_system_behavior"))
        or ensure_string_list(fast.get("minimum_system_behavior"))
        or ensure_string_list(diagnosis.get("desired_system_behavior"))
    )
    return {
        "diagnosis": {
            "business_object": business_object,
            "current_process": cleanup_sentence(diagnosis.get("current_process")) or "?????",
            "current_manual_process": current_manual_process,
            "manual_actions": ensure_string_list(diagnosis.get("manual_actions")),
            "process_breakpoint": cleanup_sentence(diagnosis.get("process_breakpoint")) or "?????",
            "passive_consequence": passive_consequence,
            "pain_root_cause": cleanup_sentence(diagnosis.get("pain_root_cause")) or "?????",
            "business_impact": cleanup_sentence(diagnosis.get("business_impact")) or "?????",
            "minimum_system_behavior": minimum_system_behavior,
            "desired_system_behavior": ensure_string_list(diagnosis.get("desired_system_behavior")) or minimum_system_behavior,
            "uncertain_items": ensure_string_list(diagnosis.get("uncertain_items")),
        },
        "structured_report": structured_report,
        "roadmap": build_roadmap_from_structured_report(structured_report),
        "process_map": build_process_map_from_structured_report(structured_report),
    }


def is_generic_text(text: object, min_len: int = 8) -> bool:
    cleaned = cleanup_sentence(text)
    if len(cleaned) < min_len:
        return True
    generic_values = [
        "?????",
        "????",
        "????",
        "????",
        "????",
        "???",
        "???",
        "???",
        "????",
        "???????",
    ]
    return cleaned in generic_values


def contains_unsupported_specifics(result: dict, original_request: str) -> list[str]:
    issues: list[str] = []
    generated_text = " ".join(
        [
            normalize_text(result.get("rewritten_request")),
            normalize_text(result.get("suggested_request")),
            normalize_text(result.get("real_intent")),
        ]
    )
    related_systems = ensure_string_list(result.get("related_systems"))
    for system_name in context_names("systems"):
        if (
            system_name
            and any(alias and alias in generated_text for alias in system_aliases(system_name))
            and not system_explicitly_mentioned(system_name, original_request)
            and system_name not in related_systems
        ):
            issues.append(f"?????????{system_name}")

    for pattern, label in [
        (r"\d+\s*%", "?????"),
        (r"\d+\s*(?:??|??|?|??)", "?????????"),
    ]:
        for match in re.findall(pattern, generated_text):
            matched_text = match
            if matched_text and matched_text not in original_request:
                issues.append(f"?????{label}?{matched_text}")
    return unique_keep_order(issues)


def quality_check_analysis(result: dict) -> dict:
    diagnosis = result.get("diagnosis") if isinstance(result.get("diagnosis"), dict) else {}
    reasons: list[str] = []
    original_request = normalize_text(result.get("original_request"))

    if is_generic_text(diagnosis.get("current_process"), 10):
        reasons.append("diagnosis.current_process ?????")
    if not ensure_string_list(diagnosis.get("manual_actions")):
        reasons.append("diagnosis.manual_actions ??")
    if is_generic_text(diagnosis.get("process_breakpoint"), 8):
        reasons.append("diagnosis.process_breakpoint ?????")
    if is_generic_text(diagnosis.get("pain_root_cause"), 12):
        reasons.append("diagnosis.pain_root_cause ?????")
    if is_generic_text(diagnosis.get("business_impact"), 12):
        reasons.append("diagnosis.business_impact ?????")
    if not ensure_string_list(diagnosis.get("desired_system_behavior")):
        reasons.append("diagnosis.desired_system_behavior ??")
    if not ensure_string_list(diagnosis.get("source_evidence")):
        reasons.append("diagnosis.source_evidence ??????????")

    rewritten = cleanup_sentence(result.get("rewritten_request"))
    if len(rewritten) < 18 or not any(action in rewritten for action in context_names("system_actions")):
        reasons.append("rewritten_request ??????????????")

    suggested = cleanup_sentence(result.get("suggested_request"))
    if len(suggested) > 120:
        reasons.append("suggested_request ?? 120 ?")

    reasons.extend(contains_unsupported_specifics(result, original_request))
    return {
        "shallow_result": bool(reasons),
        "reasons": unique_keep_order(reasons),
    }


def append_missing_values(text: str, label: str, values: list[str]) -> str:
    base = normalize_text(text)
    missing = [value for value in values if value and value not in base]
    if not missing:
        return base
    cleaned = base.rstrip("??; ")
    if not cleaned:
        return f"{label}?{join_items(missing)}?"
    return f"{cleaned}?{label}?{join_items(missing)}?"


def selection_phrase(values: list[str], fallback: str = "") -> str:
    cleaned = normalize_selected_values(values)
    if not cleaned:
        return fallback
    if len(cleaned) == 1:
        return cleaned[0]
    return "?".join(cleaned[:-1]) + "?" + cleaned[-1]


def build_integrated_refine_text(
    base_text: str,
    selected_options: dict,
    diagnosis: dict | None = None,
    business_domain: str = "",
    max_len: int = 120,
) -> str:
    roles = normalize_selected_values(selected_options.get("affected_roles"))
    focus_points = normalize_selected_values(selected_options.get("focus_points"))
    expectations = normalize_selected_values(selected_options.get("system_expectations"))
    diagnosis = diagnosis if isinstance(diagnosis, dict) else {}

    users_text = selection_phrase(roles, join_items(ensure_string_list(diagnosis.get("target_users")), "????"))
    focus_text = selection_phrase(focus_points, cleanup_sentence(diagnosis.get("process_breakpoint")) or "????")
    action_text = selection_phrase(expectations)
    if action_text:
        action_clause = f"??{action_text}"
    else:
        action_clause = build_action_clause(ensure_string_list(diagnosis.get("desired_system_behavior")))
    domain_text = business_domain_label(business_domain) if business_domain else "????"

    if roles or focus_points or expectations:
        sentence = (
            f"???????????????{domain_text}?????{users_text}"
            f"{action_clause}?????{focus_text}?????????????"
        )
        return limit_text(sentence, max_len)

    return limit_text(base_text, max_len)


def has_appended_selection_list(text: str) -> bool:
    cleaned = normalize_text(text)
    return any(marker in cleaned for marker in ["?????", "?????", "?????", "??????", "?????"])


def apply_selected_constraints_to_refine_result(result: dict, selected_options: dict) -> dict:
    roles = normalize_selected_values(selected_options.get("affected_roles"))
    focus_points = normalize_selected_values(selected_options.get("focus_points"))
    expectations = normalize_selected_values(selected_options.get("system_expectations"))

    if roles:
        result["target_users"] = roles

    structured_report = result.get("structured_report") if isinstance(result.get("structured_report"), dict) else {}
    if roles:
        structured_report["who"] = selection_phrase(roles)
    if focus_points:
        structured_report["input"] = f"??{selection_phrase(focus_points)}???????"
        structured_report["what"] = f"??{selection_phrase(focus_points)}"
    if expectations:
        structured_report["output"] = f"??{selection_phrase(expectations)}??????"
        if focus_points:
            structured_report["what"] = f"??{selection_phrase(expectations)}??{selection_phrase(focus_points)}"
        else:
            structured_report["what"] = f"??{selection_phrase(expectations)}"

    how_steps = ensure_string_list(structured_report.get("how"))
    if roles or focus_points or expectations:
        focus_text = selection_phrase(focus_points, "????????")
        expectation_text = selection_phrase(expectations, "????")
        role_text = selection_phrase(roles, "????")
        integrated_step = f"????{focus_text}{expectation_text}?????{role_text}???"
        joined_how = " ".join(how_steps)
        if integrated_step not in joined_how:
            how_steps.insert(1 if how_steps else 0, integrated_step)
        structured_report["how"] = how_steps[:4]

    result["structured_report"] = structured_report
    return result


def sanitize_analysis_payload(payload: dict, user_input: str) -> dict:
    fallback = build_context_analysis(user_input)
    source = payload if isinstance(payload, dict) else {}
    merged = dict(fallback)
    for key in [
        "diagnosis",
        "business_domain",
        "business_object",
        "related_systems",
        "candidate_systems",
        "pain_points",
        "system_actions",
        "target_users",
        "real_intent",
        "rewritten_request",
        "suggested_request",
        "confirmation_options",
        "scenario_form",
        "structured_report",
        "uncertain_items",
        "warnings",
    ]:
        if key in source:
            merged[key] = source[key]
    return validate_analysis_result(merged, user_input)


def sanitize_refine_payload(payload: dict, user_input: str, analysis_result: dict, selected_options: dict) -> dict:
    mock = build_mock_refinement(user_input, analysis_result, selected_options)
    structured_report = payload.get("structured_report") if isinstance(payload.get("structured_report"), dict) else {}
    result = {
        "refined_request": normalize_text(payload.get("refined_request")) or mock["refined_request"],
        "rewritten_request": normalize_text(payload.get("rewritten_request")) or mock["rewritten_request"],
        "target_users": ensure_string_list(payload.get("target_users")) or mock["target_users"],
        "uncertain_items": ensure_string_list(payload.get("uncertain_items")) or mock["uncertain_items"],
        "structured_report": {
            "why": normalize_text(structured_report.get("why")) or mock["structured_report"]["why"],
            "what": normalize_text(structured_report.get("what")) or mock["structured_report"]["what"],
            "where": normalize_text(structured_report.get("where")) or mock["structured_report"]["where"],
            "who": normalize_text(structured_report.get("who")) or mock["structured_report"]["who"],
            "input": normalize_text(structured_report.get("input")) or mock["structured_report"]["input"],
            "output": normalize_text(structured_report.get("output")) or mock["structured_report"]["output"],
            "how": ensure_string_list(structured_report.get("how")) or mock["structured_report"]["how"],
            "monitor": ensure_string_list(structured_report.get("monitor")) or mock["structured_report"]["monitor"],
            "howmuch": normalize_text(structured_report.get("howmuch")) or mock["structured_report"].get("howmuch") or "?????",
        },
    }
    base_analysis = validate_analysis_result(analysis_result or {}, user_input)
    diagnosis = base_analysis.get("diagnosis") if isinstance(base_analysis.get("diagnosis"), dict) else {}
    business_domain = base_analysis.get("business_domain", "")
    if has_appended_selection_list(result["refined_request"]):
        result["refined_request"] = build_integrated_refine_text(
            result["refined_request"],
            selected_options,
            diagnosis,
            business_domain,
            120,
        )
    if has_appended_selection_list(result["rewritten_request"]):
        result["rewritten_request"] = build_integrated_refine_text(
            result["rewritten_request"],
            selected_options,
            diagnosis,
            business_domain,
            80,
        )
    return apply_selected_constraints_to_refine_result(result, selected_options)


def build_analyze_user_prompt(user_input: str) -> str:
    retrieved_context = retrieve_context(user_input)
    return json.dumps(
        {
            "task": "diagnose_and_draft_requirement",
            "user_input": user_input,
            "retrieved_context": retrieved_context,
            "quality_requirements": [
                "?????? current_process?????????????",
                "???? manual_actions???????????????????????",
                "???? source_evidence?????????????????????",
                "???? process_breakpoint?pain_root_cause?business_impact",
                "desired_system_behavior ??????????????",
                "related_systems ??????????????candidate_systems ?????",
                "suggested_request ??? 120 ?",
                "confirmation_options ??????????????????? 2-8 ??????",
                "confirmation_options ????????????????????????????????...?",
                "????????????????????",
            ],
            "response_schema": {
                "original_request": "string",
                "diagnosis": {
                    "explicit_facts": ["string"],
                    "inferred_context": ["string"],
                    "business_domain_candidates": [{"name": "string", "confidence": 0.0, "reason": "string"}],
                    "related_system_candidates": [{"name": "string", "confidence": 0.0, "reason": "string"}],
                    "target_users": ["string"],
                    "business_object": "string",
                    "current_process": "string",
                    "manual_actions": ["string"],
                    "source_evidence": ["string"],
                    "process_breakpoint": "string",
                    "pain_root_cause": "string",
                    "business_impact": "string",
                    "desired_system_behavior": ["string"],
                    "candidate_systems": ["string"],
                    "uncertain_items": ["string"],
                },
                "business_domain": "string",
                "business_object": "string",
                "related_systems": ["string"],
                "candidate_systems": ["string"],
                "pain_points": ["string"],
                "system_actions": ["string"],
                "target_users": ["string"],
                "real_intent": "string",
                "rewritten_request": "string <= 80 chars",
                "suggested_request": "string <= 120 chars",
                "confirmation_options": {
                    "affected_roles": ["2-8???????????????"],
                    "focus_points": ["2-8???????????????????"],
                    "system_expectations": ["2-8?????????????????????"],
                },
                "structured_report": {
                    "why": "string",
                    "what": "string",
                    "where": "string",
                    "who": "string",
                    "input": "string",
                    "output": "string",
                    "how": ["string"],
                    "monitor": ["string"],
                },
                "uncertain_items": ["string"],
            },
        },
        ensure_ascii=False,
    )


def build_analyze_retry_user_prompt(user_input: str, previous_result: dict, quality_check: dict) -> str:
    retrieved_context = retrieve_context(user_input)
    return json.dumps(
        {
            "task": "retry_diagnose_and_draft_requirement",
            "retry_instruction": (
                "?????????????????? retrieved_context ????????????"
                "?????????????????????????????????????"
            ),
            "quality_fail_reasons": quality_check.get("reasons", []),
            "user_input": user_input,
            "retrieved_context": retrieved_context,
            "previous_result": previous_result,
            "response_schema": json.loads(build_analyze_user_prompt(user_input))["response_schema"],
        },
        ensure_ascii=False,
    )


def build_refine_user_prompt(user_input: str, analysis_result: dict, selected_options: dict) -> str:
    previous_suggested_request = normalize_text(analysis_result.get("suggested_request")) if isinstance(analysis_result, dict) else ""
    return json.dumps(
        {
            "task": "refine_requirement",
            "user_input": user_input,
            "analysis_result": analysis_result,
            "selected_options": selected_options,
            "scenario_answers": selected_options.get("scenario_answers") if isinstance(selected_options.get("scenario_answers"), dict) else {},
            "previous_suggested_request": previous_suggested_request,
            "required_response_fields": ["refined_request", "rewritten_request", "target_users", "uncertain_items"],
            "requirements": [
                "?? scenario_answers ???????????????????? refined_request?",
                "??? scenario_answers ?????????????????????",
                "???????????????????????? uncertain_items?",
            ],
        },
        ensure_ascii=False,
    )


def infer_solution_scenario(user_input: str, analysis_result: dict) -> str:
    text = " ".join(
        [
            normalize_text(user_input),
            normalize_text(analysis_result.get("business_domain")),
            normalize_text(analysis_result.get("business_object")),
            normalize_text(analysis_result.get("suggested_request")),
            " ".join(ensure_string_list(analysis_result.get("pain_points"))),
            " ".join(ensure_string_list(analysis_result.get("system_actions"))),
        ]
    )
    if any(keyword in text for keyword in ["??", "??", "??", "??", "????", "??"]):
        return "inventory"
    if any(keyword in text for keyword in ["BOM", "??", "??", "??", "??", "????"]):
        return "bom"
    if any(keyword in text for keyword in ["??", "??", "??", "???", "???", "??"]):
        return "order_delivery"
    return "generic"


def build_solution_fallback(user_input: str, analysis_result: dict, settings: dict | None = None, reference_summary: str = "") -> dict:
    settings = settings if isinstance(settings, dict) else {}
    base = analysis_result if isinstance(analysis_result, dict) else {}
    scenario = infer_solution_scenario(user_input, base)
    diagnosis = base.get("diagnosis") if isinstance(base.get("diagnosis"), dict) else {}
    business_object = cleanup_sentence(base.get("business_object") or diagnosis.get("business_object")) or "??????"
    suggested = cleanup_sentence(base.get("suggested_request") or base.get("rewritten_request") or user_input)
    pending = ensure_string_list(base.get("uncertain_items")) or ensure_string_list(diagnosis.get("uncertain_items"))

    if scenario == "inventory":
        solution = {
            "executive_summary": "???????????????????????????????????????????????????????????????????????",
            "entry_point": "?????? / ????????",
            "data_systems": "WMS???ERP/SAP???????????????????",
            "modules": ["?????????", "???????????", "??????", "????????", "????????????", "???????????"],
            "stages": [
                {"name": "??1", "description": "???????????????????"},
                {"name": "??2", "description": "?? WMS/ERP ??????????????"},
                {"name": "??3", "description": "??????????????????"},
                {"name": "??4", "description": "???????????????????"},
            ],
            "risks": ["?????????????????????", "WMS ? ERP ??????????????", "????????????????????????", "??????????????????"],
            "confirmations": pending or ["???????????????", "????????????????????", "????????????"],
        }
    elif scenario == "bom":
        solution = {
            "executive_summary": "?????BOM/?????????????????????????????????????????????????????????????",
            "entry_point": "BOM/??????????",
            "data_systems": "PLM?ERP/SAP???????????????",
            "modules": ["????????", "????????", "???????", "??/??????", "???????", "????????"],
            "stages": [
                {"name": "??1", "description": "???????????????"},
                {"name": "??2", "description": "?? PLM?ERP?????????????"},
                {"name": "??3", "description": "?????????????????"},
                {"name": "??4", "description": "???????????????"},
            ],
            "risks": ["BOM???????????????????????", "???BOM?????????????????", "????????????????????"],
            "confirmations": pending or ["??????????????", "???????????", "?????????????"],
        }
    elif scenario == "order_delivery":
        solution = {
            "executive_summary": "?????????????????????????????????????????????????????????????????????",
            "entry_point": "???? / ?????????",
            "data_systems": "?????ERP/SAP?WMS?MES/?????????",
            "modules": ["?????????", "?????????", "??/????", "???????", "????????", "??????"],
            "stages": [
                {"name": "??1", "description": "??????????????"},
                {"name": "??2", "description": "????????????????"},
                {"name": "??3", "description": "?????????????????"},
                {"name": "??4", "description": "?????????????????????"},
            ],
            "risks": ["??????????????????????", "????????????????????", "??????????????????"],
            "confirmations": pending or ["?????????????", "?????????????", "???????????????"],
        }
    else:
        solution = {
            "executive_summary": f"?????????????????{business_object}??????????????????????????????????????????????",
            "entry_point": "????????",
            "data_systems": "???????????????????????",
            "modules": ["????????", "???????", "?????", "??????", "??????"],
            "stages": [
                {"name": "??1", "description": "?????????????????"},
                {"name": "??2", "description": "??????????????"},
                {"name": "??3", "description": "????????????"},
                {"name": "??4", "description": "??????????????"},
            ],
            "risks": ["??????????????", "????????????????", "??????????????????"],
            "confirmations": pending or ["????????", "???????????", "????????????"],
        }

    solution.update(
        {
            "scenario": scenario,
            "known_request": suggested,
            "settings": settings,
            "reference_summary": reference_summary or "??????????????????????????????",
            "mode": "mock",
        }
    )
    return solution


def build_solution_user_prompt(user_input: str, analysis_result: dict, deep_analysis: dict, selected_options: dict, settings: dict, reference_summary: str = "") -> str:
    return json.dumps(
        {
            "task": "generate_solution_draft_for_itbp",
            "user_input": user_input,
            "analysis_result": analysis_result,
            "deep_analysis": deep_analysis,
            "selected_options": selected_options,
            "solution_settings": settings,
            "external_reference_summary": reference_summary,
            "response_schema": {
                "executive_summary": "string",
                "entry_point": "string",
                "data_systems": "string",
                "modules": ["string"],
                "stages": [{"name": "string", "description": "string"}],
                "risks": ["string"],
                "confirmations": ["string"],
                "reference_summary": "string",
            },
        },
        ensure_ascii=False,
    )


def sanitize_solution_payload(payload: dict, user_input: str, analysis_result: dict, settings: dict, reference_summary: str = "") -> dict:
    fallback = build_solution_fallback(user_input, analysis_result, settings, reference_summary)
    source = payload if isinstance(payload, dict) else {}
    stages_source = source.get("stages") if isinstance(source.get("stages"), list) else []
    stages: list[dict] = []
    for item in stages_source:
        if isinstance(item, dict):
            name = cleanup_sentence(item.get("name"))
            description = cleanup_sentence(item.get("description"))
            if name or description:
                stages.append({"name": name or f"??{len(stages)+1}", "description": description or "???"})
    return {
        "executive_summary": cleanup_sentence(source.get("executive_summary")) or fallback["executive_summary"],
        "entry_point": cleanup_sentence(source.get("entry_point")) or fallback["entry_point"],
        "data_systems": cleanup_sentence(source.get("data_systems")) or fallback["data_systems"],
        "modules": ensure_string_list(source.get("modules")) or fallback["modules"],
        "stages": stages or fallback["stages"],
        "risks": ensure_string_list(source.get("risks")) or fallback["risks"],
        "confirmations": ensure_string_list(source.get("confirmations")) or fallback["confirmations"],
        "reference_summary": cleanup_sentence(source.get("reference_summary")) or fallback["reference_summary"],
        "scenario": fallback["scenario"],
        "known_request": fallback["known_request"],
        "settings": settings,
    }


@app.get("/")
@app.get("/index.html")
def index() -> object:
    response = send_file(BASE_DIR / "index.html", mimetype="text/html; charset=utf-8")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.get("/intro")
@app.get("/intro.html")
def intro() -> object:
    response = send_file(BASE_DIR / "intro.html", mimetype="text/html; charset=utf-8")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@app.get("/health")
def health() -> object:
    return jsonify({"status": "ok", "llm_enabled": llm_enabled()})


def run_full_analysis(user_input: str) -> dict:
    enabled = llm_enabled()
    log_llm_event("analyze_enter", enabled=enabled, model=os.getenv("LLM_MODEL", ""), debug=llm_debug_enabled())

    if enabled:
        try:
            llm_result = call_llm_json(ANALYZE_SYSTEM_PROMPT, build_analyze_user_prompt(user_input), label="analyze")
            result = sanitize_analysis_payload(llm_result, user_input)
            result["mode"] = "llm"
            quality_check = quality_check_analysis(result)
            result["quality_check"] = quality_check
            if quality_check["shallow_result"]:
                log_llm_event("quality_retry", label="analyze", reasons=quality_check["reasons"])
                try:
                    retry_llm_result = call_llm_json(
                        ANALYZE_SYSTEM_PROMPT,
                        build_analyze_retry_user_prompt(user_input, result, quality_check),
                        label="analyze_retry",
                    )
                    retry_result = sanitize_analysis_payload(retry_llm_result, user_input)
                    retry_result["mode"] = "llm"
                    retry_quality_check = quality_check_analysis(retry_result)
                    retry_result["quality_check"] = retry_quality_check
                    retry_result["llm_retry"] = True
                    log_llm_event(
                        "quality_retry_result",
                        label="analyze_retry",
                        shallow=retry_quality_check["shallow_result"],
                        reasons=retry_quality_check["reasons"],
                    )
                    return retry_result
                except Exception as retry_exc:
                    result.setdefault("warnings", []).append(f"LLM retry ???{retry_exc}")
                    result["llm_retry_error"] = str(retry_exc)
                    log_llm_event("quality_retry_failed", label="analyze_retry", reason=str(retry_exc))
            return result
        except Exception as exc:  # pragma: no cover - fallback path
            result = build_mock_analysis(user_input)
            result["quality_check"] = quality_check_analysis(result)
            result["llm_error"] = str(exc)
            result["fallback_reason"] = str(exc)
            log_llm_event("fallback_entered", label="analyze", reason=str(exc), mode="mock")
            return result

    log_llm_event("mock_entered", label="analyze", reason="llm_disabled", mode="mock")
    result = build_mock_analysis(user_input)
    result["quality_check"] = quality_check_analysis(result)
    return result


@app.post("/api/analyze_fast")
def api_analyze_fast() -> object:
    started = time.monotonic()
    payload = request.get_json(silent=True) or {}
    user_input = normalize_text(payload.get("user_input"))

    if not user_input:
        return jsonify({"error": "user_input ????"}), 400

    retrieved_context = retrieve_context(user_input)
    enabled = llm_enabled()
    log_llm_event("analyze_fast_enter", enabled=enabled, model=os.getenv("LLM_MODEL", ""), debug=llm_debug_enabled())
    if enabled:
        try:
            llm_result = call_llm_json(
                ANALYZE_FAST_SYSTEM_PROMPT,
                build_analyze_fast_user_prompt(user_input, retrieved_context),
                label="analyze_fast",
            )
            elapsed_ms = int((time.monotonic() - started) * 1000)
            result = normalize_fast_analysis_result(
                llm_result,
                user_input,
                retrieved_context,
                used_llm=True,
                used_fallback=False,
                elapsed_ms=elapsed_ms,
            )
            quality_check = quality_check_fast(result, user_input, retrieved_context)

            if not quality_check["passed"]:
                log_llm_event("quality_retry", label="analyze_fast", reasons=quality_check["issues"])
                try:
                    retry_result = call_llm_json(
                        ANALYZE_FAST_SYSTEM_PROMPT,
                        build_analyze_fast_retry_user_prompt(user_input, retrieved_context, result, quality_check),
                        label="analyze_fast_retry",
                    )
                    elapsed_ms = int((time.monotonic() - started) * 1000)
                    result = normalize_fast_analysis_result(
                        retry_result,
                        user_input,
                        retrieved_context,
                        used_llm=True,
                        used_fallback=False,
                        elapsed_ms=elapsed_ms,
                        retry_used=True,
                    )
                    quality_check = quality_check_fast(result, user_input, retrieved_context)
                except Exception as retry_exc:
                    result["warnings"].append(f"???? retry ???{retry_exc}")
                    result["debug"]["llm_retry_error"] = str(retry_exc)
                    log_llm_event("quality_retry_failed", label="analyze_fast_retry", reason=str(retry_exc))

            elapsed_ms = int((time.monotonic() - started) * 1000)
            result["debug"]["elapsed_ms"] = elapsed_ms
            result["debug"]["quality_passed"] = quality_check["passed"]
            result["debug"]["quality_issues"] = quality_check["issues"]
            return jsonify(result)
        except Exception as exc:  # pragma: no cover - fallback path
            log_llm_event("fallback_entered", label="analyze_fast", reason=str(exc), mode="mock")
            elapsed_ms = int((time.monotonic() - started) * 1000)
            fallback = build_fast_fallback_from_context(user_input, retrieved_context)
            result = normalize_fast_analysis_result(
                fallback,
                user_input,
                retrieved_context,
                used_llm=False,
                used_fallback=True,
                elapsed_ms=elapsed_ms,
            )
            quality_check = quality_check_fast(result, user_input, retrieved_context)
            result["debug"]["quality_passed"] = quality_check["passed"]
            result["debug"]["quality_issues"] = quality_check["issues"]
            result["fallback_reason"] = str(exc)
            result["debug"]["fallback_reason"] = str(exc)
            return jsonify(result)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    fallback = build_fast_fallback_from_context(user_input, retrieved_context)
    result = normalize_fast_analysis_result(
        fallback,
        user_input,
        retrieved_context,
        used_llm=False,
        used_fallback=True,
        elapsed_ms=elapsed_ms,
    )
    quality_check = quality_check_fast(result, user_input, retrieved_context)
    result["debug"]["quality_passed"] = quality_check["passed"]
    result["debug"]["quality_issues"] = quality_check["issues"]
    return jsonify(result)


@app.post("/api/analyze_deep")
def api_analyze_deep() -> object:
    payload = request.get_json(silent=True) or {}
    user_input = normalize_text(payload.get("user_input"))
    fast_analysis = payload.get("fast_analysis") if isinstance(payload.get("fast_analysis"), dict) else {}

    if not user_input:
        return jsonify({"error": "user_input ????"}), 400

    analysis = run_full_analysis(user_input)
    result = build_deep_response(analysis, fast_analysis)
    result["debug"] = {
        "used_llm": analysis.get("mode") == "llm" and not analysis.get("fallback_reason"),
        "used_fallback": bool(analysis.get("fallback_reason") or analysis.get("mode") != "llm"),
        "fallback_reason": analysis.get("fallback_reason", ""),
    }
    return jsonify(result)


@app.post("/api/analyze")
def api_analyze() -> object:
    payload = request.get_json(silent=True) or {}
    user_input = normalize_text(payload.get("user_input"))

    if not user_input:
        return jsonify({"error": "user_input ????"}), 400

    result = run_full_analysis(user_input)
    return jsonify(result)


@app.post("/api/refine")
def api_refine() -> object:
    payload = request.get_json(silent=True) or {}
    user_input = normalize_text(payload.get("user_input"))
    analysis_result = payload.get("analysis_result") if isinstance(payload.get("analysis_result"), dict) else {}
    selected_options = payload.get("selected_options") if isinstance(payload.get("selected_options"), dict) else {}

    if not user_input:
        return jsonify({"error": "user_input ????"}), 400

    if llm_enabled():
        try:
            llm_result = call_llm_json(
                REFINE_SYSTEM_PROMPT,
                build_refine_user_prompt(user_input, analysis_result, selected_options),
                label="refine",
            )
            result = sanitize_refine_payload(llm_result, user_input, analysis_result, selected_options)
            result["mode"] = "llm"
            return jsonify(result)
        except Exception as exc:  # pragma: no cover - fallback path
            result = build_mock_refinement(user_input, analysis_result, selected_options)
            result["llm_error"] = str(exc)
            return jsonify(result)

    return jsonify(build_mock_refinement(user_input, analysis_result, selected_options))


@app.post("/api/generate_solution")
def api_generate_solution() -> object:
    payload = request.get_json(silent=True) or {}
    user_input = normalize_text(payload.get("user_input"))
    analysis_result = payload.get("analysis_result") if isinstance(payload.get("analysis_result"), dict) else {}
    deep_analysis = payload.get("deep_analysis") if isinstance(payload.get("deep_analysis"), dict) else {}
    selected_options = payload.get("selected_options") if isinstance(payload.get("selected_options"), dict) else {}
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}

    if not user_input:
        return jsonify({"error": "user_input ????"}), 400

    reference_summary = ""
    if settings.get("web_search"):
        reference_summary = "???????????????????????????????????????"

    if llm_enabled():
        try:
            llm_result = call_llm_json(
                SOLUTION_SYSTEM_PROMPT,
                build_solution_user_prompt(user_input, analysis_result, deep_analysis, selected_options, settings, reference_summary),
                label="generate_solution",
            )
            result = sanitize_solution_payload(llm_result, user_input, analysis_result, settings, reference_summary)
            result["mode"] = "llm"
            return jsonify(result)
        except Exception as exc:  # pragma: no cover - fallback path
            result = build_solution_fallback(user_input, analysis_result, settings, reference_summary)
            result["llm_error"] = str(exc)
            result["fallback_reason"] = str(exc)
            return jsonify(result)

    return jsonify(build_solution_fallback(user_input, analysis_result, settings, reference_summary))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", "8000")), debug=False)




