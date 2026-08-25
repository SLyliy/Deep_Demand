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
        "name": "采购",
        "keywords": ["采购", "供应商", "请购", "交期", "到货", "缺料", "BOM", "物料"],
        "description": "采购执行、供应商协同、交付跟进相关场景",
    },
    {
        "code": "finance",
        "name": "财务",
        "keywords": ["财务", "对账", "关账", "凭证", "预算", "回款", "应收", "应付"],
        "description": "财务核算、对账、预算和回款相关场景",
    },
    {
        "code": "hr",
        "name": "HR",
        "keywords": ["HR", "人力", "员工", "入职", "转正", "离职", "考勤", "招聘", "编制"],
        "description": "员工生命周期和人力流程相关场景",
    },
    {
        "code": "legal",
        "name": "法务",
        "keywords": ["法务", "合同", "盖章", "协议", "审查", "归档", "合规", "到期"],
        "description": "合同、法务审批和合规管理相关场景",
    },
    {
        "code": "warehouse",
        "name": "仓储",
        "keywords": ["仓库", "仓储", "库存", "出入库", "库位", "盘点", "批次", "呆滞", "缺货"],
        "description": "库存、仓储执行和物流现场相关场景",
    },
    {
        "code": "production",
        "name": "生产",
        "keywords": ["生产", "制造", "工单", "排产", "车间", "产线", "设备", "工艺"],
        "description": "生产制造、计划排程和车间执行相关场景",
    },
    {
        "code": "sales",
        "name": "销售",
        "keywords": ["销售", "客户", "商机", "报价", "订单", "线索", "回访", "签约"],
        "description": "客户跟进、商机推进和销售管理相关场景",
    },
    {
        "code": "general",
        "name": "通用",
        "keywords": [],
        "description": "尚未明确业务域的通用场景",
    },
]

PAIN_CONFIG = [
    {
        "code": "timeliness",
        "name": "时效慢",
        "keywords": ["慢", "太慢", "滞后", "不及时", "耗时", "周期长", "等待"],
        "phrase": "响应不及时",
    },
    {
        "code": "omission",
        "name": "容易漏",
        "keywords": ["漏", "遗漏", "忘记", "漏掉", "漏发", "漏批", "漏步骤"],
        "phrase": "容易遗漏",
    },
    {
        "code": "accuracy",
        "name": "数据不准",
        "keywords": ["不准", "错误", "偏差", "对不上", "差异", "口径不一致", "不一致"],
        "phrase": "数据不够准确",
    },
    {
        "code": "manual_heavy",
        "name": "人工太重",
        "keywords": ["人工", "手工", "手动", "重复", "Excel", "表格", "复制粘贴", "人工算", "人工计算"],
        "phrase": "人工处理工作重",
    },
    {
        "code": "workflow_block",
        "name": "流程卡点",
        "keywords": ["卡点", "卡住", "堵点", "退回", "审批慢", "流转慢", "卡在"],
        "phrase": "流程卡点明显",
    },
    {
        "code": "risk_hidden",
        "name": "风险不可见",
        "keywords": ["风险", "异常", "预警", "超期", "到期", "合规", "看不见", "发现没有货", "不透明"],
        "phrase": "风险不够可见",
    },
]

ACTION_CONFIG = [
    {
        "code": "data_view",
        "name": "看数据",
        "keywords": ["报表", "统计", "看板", "查看", "分析", "数据", "进度"],
        "guess_text": "展示关键数据",
    },
    {
        "code": "auto_remind",
        "name": "自动提醒",
        "keywords": ["提醒", "通知", "预警", "催办"],
        "guess_text": "自动提醒相关人员",
    },
    {
        "code": "auto_flow",
        "name": "自动流转",
        "keywords": ["审批", "流程", "流转", "加签", "退回", "入职", "开账号", "办权限", "发设备"],
        "guess_text": "自动流转流程节点",
    },
    {
        "code": "auto_sync",
        "name": "自动同步",
        "keywords": ["同步", "对接", "接口", "打通"],
        "guess_text": "自动同步关键数据",
    },
    {
        "code": "auto_generate",
        "name": "自动生成",
        "keywords": ["生成", "汇总", "计算", "输出", "算好", "自动算"],
        "guess_text": "自动生成关键结果",
    },
    {
        "code": "auto_control",
        "name": "自动控制",
        "keywords": ["控制", "校验", "拦截", "限制", "锁定"],
        "guess_text": "自动控制关键节点",
    },
]

PAIN_INFERENCE_RULES = [
    {
        "pain_code": "manual_heavy",
        "any_keywords": ["自动计算", "自动汇总", "报表", "汇总", "同步", "人工通知"],
        "action_codes": ["auto_generate", "auto_sync"],
    },
    {
        "pain_code": "timeliness",
        "domain_codes": ["procurement"],
        "any_keywords": ["报表", "BOM", "库存", "交期", "缺料"],
    },
    {
        "pain_code": "omission",
        "any_keywords": ["提醒", "通知", "到期", "漏步骤"],
        "action_codes": ["auto_remind"],
    },
    {
        "pain_code": "risk_hidden",
        "any_keywords": ["到期", "预警", "风险", "异常", "发现没有货"],
        "action_codes": ["auto_remind", "auto_control"],
    },
    {
        "pain_code": "workflow_block",
        "any_keywords": ["审批", "流程", "流转", "入职", "开账号", "办权限", "发设备"],
        "action_codes": ["auto_flow"],
    },
    {
        "pain_code": "accuracy",
        "any_keywords": ["对账", "差异", "库存", "校验", "不准", "不一致"],
        "action_codes": ["auto_sync", "auto_control"],
    },
]

QUICK_SELECTION_LIBRARY = {
    "procurement": {
        "affected_roles": ["采购执行", "供应链负责人", "计划人员", "跨部门协作人员", "供应商"],
        "focus_points": ["BOM/用量计算", "缺料风险", "交期响应", "供应商协同", "人工统计太重"],
        "system_expectations": ["展示关键数据", "自动提醒", "自动同步", "自动生成结果", "自动拦截风险"],
    },
    "finance": {
        "affected_roles": ["财务专员", "财务负责人", "业务部门", "跨部门协作人员", "管理层"],
        "focus_points": ["月底对账", "差异汇总", "多系统取数", "人工比对太重", "口径不一致"],
        "system_expectations": ["展示关键数据", "自动同步", "自动生成结果", "自动提醒", "自动拦截风险"],
    },
    "hr": {
        "affected_roles": ["HR专员", "用人部门", "IT支持", "跨部门协作人员", "新员工"],
        "focus_points": ["入职步骤漏项", "账号开通", "设备发放", "权限办理", "流程协同慢"],
        "system_expectations": ["自动流转", "自动提醒", "自动生成结果", "自动控制", "展示关键数据"],
    },
    "legal": {
        "affected_roles": ["法务专员", "业务负责人", "部门负责人", "管理层", "客户/供应商"],
        "focus_points": ["合同到期", "审批超时", "提醒对象不清", "合规风险", "归档缺失"],
        "system_expectations": ["自动提醒", "自动流转", "展示关键数据", "自动控制", "自动生成结果"],
    },
    "warehouse": {
        "affected_roles": ["仓库管理员", "计划人员", "采购执行", "跨部门协作人员", "管理层"],
        "focus_points": ["库存不准", "缺货风险", "人工核对太重", "业务下单受影响", "异常库存发现太晚"],
        "system_expectations": ["展示关键数据", "自动同步", "自动提醒", "自动生成结果", "自动拦截风险"],
    },
    "production": {
        "affected_roles": ["生产计划员", "车间主管", "设备人员", "跨部门协作人员", "管理层"],
        "focus_points": ["排产不及时", "工单流转", "设备异常", "人工跟单", "异常反馈滞后"],
        "system_expectations": ["自动流转", "自动提醒", "展示关键数据", "自动同步", "自动控制"],
    },
    "sales": {
        "affected_roles": ["销售执行", "销售负责人", "客户", "跨部门协作人员", "管理层"],
        "focus_points": ["客户跟进", "商机推进", "报价反馈", "订单协同", "数据分散"],
        "system_expectations": ["展示关键数据", "自动提醒", "自动流转", "自动生成结果", "自动同步"],
    },
    "general": {
        "affected_roles": ["一线执行人员", "部门负责人", "管理层", "跨部门协作人员", "客户/供应商"],
        "focus_points": ["太慢", "容易漏", "数据不准", "人工重复", "流程卡住"],
        "system_expectations": ["展示关键数据", "自动提醒", "自动流转", "自动同步", "自动生成结果"],
    },
}

ACTION_UNCERTAIN_MAP = {
    "data_view": ["数据来源", "关键字段", "查看方式"],
    "auto_remind": ["提醒对象", "提醒时点", "触发规则"],
    "auto_flow": ["发起角色", "审批节点", "异常处理规则"],
    "auto_sync": ["主数据来源", "同步频率", "失败处理方式"],
    "auto_generate": ["生成口径", "输出频率", "发送方式"],
    "auto_control": ["拦截规则", "例外放行机制", "责任人"],
}

DOMAIN_UNCERTAIN_MAP = {
    "procurement": ["BOM/库存数据口径", "使用对象", "触发频率"],
    "finance": ["差异判断口径", "数据源系统", "输出对象"],
    "hr": ["责任分工", "通知对象", "节点顺序"],
    "legal": ["提醒对象", "提前天数", "升级规则"],
    "warehouse": ["库存口径", "异常阈值", "同步时效"],
    "production": ["触发条件", "责任岗位", "异常闭环"],
    "sales": ["跟进对象", "提醒时机", "输出结果"],
    "general": ["影响对象", "触发条件", "成功标准"],
}

ANALYZE_SYSTEM_PROMPT = """
你是企业 ITBP 需求诊断助手，不是单纯文案改写助手。
用户通常只会输入一句不完整的业务描述。

你必须先诊断业务语境、当前处理方式、流程断点、人工动作、痛点根因和业务影响，再生成需求描述。
不要把某个示例场景套用到其他场景。
没有明确依据时，不要写死具体系统、角色、指标、人天、时效。
	任何具体系统、角色、流程、指标，如果不是用户明确提到或 business_context 强相关，都只能作为候选或待确认。
	related_systems 只放用户原话明确提到的系统；candidate_systems 放根据业务域推断、需要确认的候选系统。
	必须保留 source_evidence：从原话中摘取能支撑诊断的短语，例如“只能去问车间”“开会才查”“漏催”“邮件里”。
	不确定内容必须放入 uncertain_items。

输出必须是 JSON，不要输出 Markdown。
不要输出分析过程长文，但要输出 diagnosis 字段作为可审计的诊断摘要。
需求文案要像业务人员能直接提交的表达，不要像咨询报告。

返回字段必须包含：
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
你是企业业务需求提交助手。
用户通常只输入一句不完整的业务描述，你只需要快速生成首页可提交需求和少量澄清项，不生成 ITBP 深度分析报告。

要求：
- 只输出 JSON，不要 Markdown
	- 只能根据 user_input 和 retrieved_context 判断，不要编造事实
	- related_systems 只放用户原话明确提到的系统
	- candidate_systems 放根据业务域推断、需要确认的候选系统
	- source_evidence 必须保留原话中的关键证据短语，例如只能去问、开会才查、漏催、邮件里
- rewritten_request 不超过 80 字
- suggested_request 不超过 120 字
- 不要无依据写死 SAP/MES/WMS/QMS 等系统名
- 不要写人天、百分比、具体承诺指标
- 不要输出空泛表达：提升效率、降低风险、减少人工、及时处理、关键数据、相关人员、当前业务场景
- 如果必须使用泛词，必须绑定具体业务对象、人工动作和业务后果
- uncertain_items 最多 3 条，只放真正需要确认的问题

返回字段必须包含：
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
你是企业 ITBP 需求诊断助手。
你会收到：
1. 用户的一句话原始需求
2. 上一步的需求诊断 JSON
3. 用户在前端点选的快速确认项
4. 上一版 suggested_request

你的任务是基于首页快速分析结果和用户点选项重新生成 refined_request，而不是生成 ITBP 深度分析报告。
要求：
- 输出 JSON
- 不要输出 Markdown
- 用户选择只作为补充信号，不要覆盖原始需求中的明确事实
- 如果用户选择与模型诊断冲突，优先保留用户选择，但在 uncertain_items 中提示需要确认
- refined_request 不超过 120 字，包含触发条件、系统动作、处理对象、业务价值
- rewritten_request 也要返回
- 必须把用户选择自然融合进一句完整需求里
- 禁止在句尾用“重点关注：...”“系统期望：...”“面向对象：...”罗列补充
- 不要写成清单、不要用分号追加要点，表达要像一句业务人员可直接提交的话
- target_users 返回字符串数组
- 不要生成 structured_report 或 ITBP 深度诊断内容；这些内容只在用户点击“生成 ITBP 深度分析”后生成
- uncertain_items 只保留还没有确认、确实重要的点
- 不要编造已经确定的事实
""".strip()

SOLUTION_SYSTEM_PROMPT = """
你是资深企业 ITBP 方案顾问，任务是基于业务需求诊断 JSON 生成“方案建议草案”，不是生成最终立项方案。

要求：
- 只输出 JSON，不要 Markdown。
- 面向 ITBP 内部评估，表达专业、克制、可落地。
- 必须区分已知事实、合理推断、待确认事项。
- 不要承诺百分比、人天、固定收益。
- 不要无依据写死具体系统；如果系统只属于候选，要写成“候选/需确认”。
- 方案要包含最小可行方案、标准方案或长期增强思路，但不要过度扩大范围。
- 如果输入中包含外部参考摘要，只能作为参考经验，不得当成企业内部事实。

返回字段必须包含：
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
        return "自动生成并展示关键数据"
    if "auto_flow" in action_codes:
        return "自动流转流程节点"
    if "auto_sync" in action_codes:
        return "自动同步关键数据"
    if "auto_remind" in action_codes:
        return "自动提醒相关人员"
    if "auto_control" in action_codes:
        return "自动控制关键节点"
    if "auto_generate" in action_codes:
        return "自动生成关键结果"
    if "data_view" in action_codes:
        return "展示关键数据"
    return "支持关键处理动作"


def get_lead_text(text: str, actions: list[dict]) -> str:
    action_codes = [item["code"] for item in actions]
    if "报表" in text or "看板" in text:
        return "你可能不是单纯想要一张报表"
    if "auto_remind" in action_codes:
        return "你可能不是单纯想要一个提醒"
    if "auto_flow" in action_codes:
        return "你可能不是单纯想把流程搬到线上"
    if "auto_sync" in action_codes:
        return "你可能不是单纯想做一个系统对接"
    if "auto_generate" in action_codes:
        return "你可能不是单纯想让系统自动生成结果"
    if "auto_control" in action_codes:
        return "你可能不是单纯想加一个控制点"
    return "你可能不是单纯想要一个功能"


def guess_focus(text: str, domain: dict) -> str:
    mapping = {
        "procurement": [
            ("BOM", "BOM用量与采购执行数据"),
            ("交期", "交期与供应商响应"),
            ("缺料", "缺料风险与库存可用性"),
            ("库存", "库存与缺料风险"),
        ],
        "finance": [
            ("对账", "月底对账与差异汇总"),
            ("差异", "差异识别与核对效率"),
            ("回款", "回款跟踪"),
        ],
        "hr": [
            ("入职", "入职流程协同"),
            ("权限", "账号与权限开通"),
            ("设备", "设备和资源发放"),
        ],
        "legal": [
            ("合同", "合同到期与合规提醒"),
            ("盖章", "盖章与审批进度"),
        ],
        "warehouse": [
            ("库存", "库存准确性与异常发现"),
            ("下单", "下单前库存校验"),
            ("缺货", "缺货风险发现"),
        ],
    }

    for keyword, focus in mapping.get(domain["code"], []):
        if keyword in text:
            return focus

    return f"{domain['name']}场景下的关键业务处理"


def build_confirmation_options(domain: dict, pains: list[dict], actions: list[dict]) -> dict[str, list[str]]:
    base = QUICK_SELECTION_LIBRARY.get(domain["code"], QUICK_SELECTION_LIBRARY["general"])
    options = {
        "affected_roles": list(base["affected_roles"]),
        "focus_points": list(base["focus_points"]),
        "system_expectations": list(base["system_expectations"]),
    }

    pain_names = [item["name"] for item in pains]
    action_names = [item["name"] for item in actions]

    if "风险不可见" in pain_names and "风险预警" not in options["focus_points"]:
        options["focus_points"].insert(0, "风险预警")
    if "数据不准" in pain_names and "数据准确性" not in options["focus_points"]:
        options["focus_points"].insert(0, "数据准确性")
    if "自动提醒" in action_names and "自动提醒" not in options["system_expectations"]:
        options["system_expectations"].insert(0, "自动提醒")
    if "自动流转" in action_names and "自动流转" not in options["system_expectations"]:
        options["system_expectations"].insert(0, "自动流转")

    return {key: unique_keep_order(value)[:5] for key, value in options.items()}


def build_uncertain_items(domain: dict, actions: list[dict]) -> list[str]:
    items: list[str] = []
    for action in actions:
        items.extend(ACTION_UNCERTAIN_MAP.get(action["code"], []))
    items.extend(DOMAIN_UNCERTAIN_MAP.get(domain["code"], []))
    return unique_keep_order(items)[:3]


def build_real_intent(text: str, domain: dict, pains: list[dict], actions: list[dict]) -> str:
    domain_name = "当前业务" if domain["name"] == "通用" else domain["name"]
    pain_text = "、".join(item.get("phrase", item["name"]) for item in pains) if pains else "当前核心痛点"
    action_text = get_action_guess_text(actions)
    return (
        f"{get_lead_text(text, actions)}，而是希望解决{domain_name}场景下{pain_text}的问题，"
        f"通过系统{action_text}，让处理更及时、更准确、更省人工。"
    )


def join_items(values: list[str], fallback: str = "待业务确认") -> str:
    cleaned = unique_keep_order([normalize_text(value) for value in values if normalize_text(value)])
    return "、".join(cleaned) if cleaned else fallback


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
    for part in re.split(r"[/／、]", name):
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
            warnings.append(f"系统 {normalized} 未在原话明确出现，已仅保留为候选或待确认")
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
                cleaned = cleaned.replace(alias, "相关系统")
                replaced = True
        if replaced:
            warnings.append(f"生成文案中出现未确认系统：{system_name}，已替换为相关系统")
    return cleanup_sentence(cleaned)


def cleanup_sentence(text: str) -> str:
    cleaned = normalize_text(text)
    replacements = {
        "待确认解决待确认": "仍需确认具体问题和处理目标",
        "待确认待确认": "待业务确认",
        "相关系统系统": "相关系统",
        "。，": "，",
        "。。": "。",
        "，，": "，",
        "；；": "；",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    return cleaned


def limit_text(text: str, limit: int) -> str:
    cleaned = cleanup_sentence(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip("，、；; ") + "。"


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
        return re.split(r"[，,/／]", description, maxsplit=1)[0].strip() or normalize_text(domain_name)
    return normalize_text(domain_name) or "当前业务"


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
            reason = f"原话明确提到 {name}"
        elif score >= 6:
            confidence = 0.78
            reason = f"原话中多个关键词与 {name} 的业务上下文匹配"
        else:
            confidence = 0.62
            reason = f"原话中部分关键词与 {name} 相关，需要进一步确认"
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
        "IPD": ["研发", "图纸", "BOM", "设计变更", "版本", "试产", "PLM"],
        "IPMS": ["上市", "上市资料", "营销", "销售资料", "售后资料", "服务政策", "客户沟通口径", "政策更新"],
        "MTC": ["经销商", "客户", "商机", "报价", "销售订单", "客户订单", "订单签", "发货", "回款", "DMS"],
        "DSTE": ["战略", "规划", "年度计划", "重点项目", "执行监控", "里程碑", "执行偏差", "管理层"],
        "Manufacturing": ["MES", "工单", "车间", "报工", "工序", "生产进度", "产线"],
        "Supply": ["供应链", "缺料", "物料", "齐套", "计划变更", "交付风险"],
        "Procurement": ["采购", "供应商", "采购订单", "催交", "到货", "交期"],
        "Quality": ["质量", "检验", "整改", "8D", "不良"],
        "SD": ["售后", "报修", "服务单", "维修", "备件", "客户报修"],
        "Warehouse": ["仓储", "库位", "出入库", "盘点", "账实"],
        "Finance": ["财务", "凭证", "结算", "关账", "发票"],
        "MBTIT": ["ITBP", "跨系统", "数据口径", "系统状态", "接口", "SAP", "MES", "WMS", "拉群确认", "人工拉群"],
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
            candidate["reason"] = f"{candidate['reason']}；关键对象更偏向 {domain_name} 场景"
        elif score >= 4:
            candidate = {
                "name": domain_name,
                "confidence": round(0.55 + boost, 2),
                "reason": f"原话中的关键对象更偏向 {domain_name} 场景",
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
        for term in re.split(r"[\s,，、/／;；:：()（）\[\]【】<>《》]+", value):
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
    for term in re.split(r"[\s,，、/／;；:：()（）]+", phrase):
        term = normalize_text(term)
        if len(term) >= 2 and term in text:
            score += len(term)
    skip_fragments = {
        "没有",
        "自动",
        "状态",
        "处理",
        "信息",
        "业务",
        "系统",
        "相关",
        "当前",
        "确认",
        "跟踪",
        "提醒",
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
                fragments = [part for part in re.split(r"[\s,，、/／;；]+", value) if len(part) >= 2 and part in text]
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
                "reason": f"命中：{join_items(match['hit_terms'], '关键词匹配')}",
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
                "reason": "没有匹配到明确业务域，使用 General",
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
        "template_name": "通用需求澄清表",
        "match_reason": "未命中特定业务对象模板，使用通用澄清项。",
        "groups": [
            {
                "key": "trigger",
                "title": "1. 通常在什么情况下触发这个问题？",
                "type": "multi_select",
                "required": True,
                "options": ["状态变化后", "别人催促后", "会议/检查前", "月底/关账前", "人工发现异常时"],
            },
            {
                "key": "current_gap",
                "title": "2. 当前主要卡在哪里？",
                "type": "multi_select",
                "required": True,
                "options": ["数据不准", "状态不透明", "责任人不清", "人工反复询问", "异常没有闭环"],
            },
            {
                "key": "expected_action",
                "title": "3. 你希望系统至少先做什么？",
                "type": "multi_select",
                "required": True,
                "options": ["自动同步状态", "集中展示信息", "自动提醒责任人", "生成待办清单", "跟踪处理闭环"],
            },
        ],
    }


def normalize_scenario_group(group: dict) -> dict:
    return {
        "key": cleanup_sentence(group.get("key")) or "question",
        "title": cleanup_sentence(group.get("title")) or "请补充确认",
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
                reasons.append(f"业务域命中：{domain}")
        for keyword in ensure_string_list(template.get("match_keywords")):
            if keyword and keyword in context_text:
                score += max(2, len(keyword))
                reasons.append(f"关键词命中：{keyword}")
        if score > best_score:
            best_score = score
            best_template = template
            best_reasons = reasons

    if not best_template or best_score < 4:
        return {}

    return {
        "template_code": cleanup_sentence(best_template.get("code")) or "scenario_template",
        "template_name": cleanup_sentence(best_template.get("name")) or "场景化澄清表",
        "match_score": best_score,
        "match_reason": "；".join(unique_keep_order(best_reasons)[:4]),
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
        facts.append(f"原话明确提到系统：{join_items(explicit_systems)}")

    explicit_roles = [item["name"] for item in role_candidates if item["name"] in text]
    if explicit_roles:
        facts.append(f"原话明确提到对象：{join_items(explicit_roles)}")

    business_terms = []
    for keyword in ["BOM", "物料", "库存", "交期", "工单", "质量异常", "客户", "订单", "合同", "报表", "提醒"]:
        if keyword in text:
            business_terms.append(keyword)
    if business_terms:
        facts.append(f"原话明确提到业务对象或动作：{join_items(business_terms)}")

    manual_terms = []
    for keyword in ["人工", "手工", "手动", "导出", "计算", "比对", "催办", "统计", "汇总", "转发"]:
        if keyword in text:
            manual_terms.append(keyword)
    if manual_terms:
        facts.append(f"原话明确提到人工处理动作：{join_items(manual_terms)}")

    if not facts:
        facts.append("原话只提供了初步需求描述，具体业务事实仍需补充。")
    return facts


def build_manual_actions(text: str) -> list[str]:
    action_rules = [
        ("人工", "人工处理或跟进"),
        ("手工", "手工处理数据或流程"),
        ("手动", "手动维护状态或结果"),
        ("导出", "人工导出数据"),
        ("计算", "人工计算或核算结果"),
        ("比对", "人工比对差异"),
        ("催办", "人工催办责任人"),
        ("催", "人工催促或响应催办"),
        ("追", "人工追踪处理进展"),
        ("靠人追", "人工追踪处理进展"),
        ("统计", "人工统计汇总"),
        ("汇总", "人工汇总信息"),
        ("转发", "人工转发结果"),
        ("询问", "跨角色人工询问状态"),
        ("问车间", "人工向车间询问状态"),
        ("来问", "被动等待他人询问后才发现问题"),
        ("去问", "主动向相关人员询问状态"),
        ("不知道", "人工查询或等待他人确认状态"),
        ("才发现", "问题依赖人工询问后才被发现"),
        ("开会", "通过会议追踪进展"),
    ]
    return unique_keep_order([label for keyword, label in action_rules if keyword in text])


def build_current_process(manual_actions: list[str]) -> str:
    if manual_actions:
        return f"当前处理方式看起来依赖{join_items(manual_actions[:3])}，具体流程节点仍需业务确认。"
    return "当前处理方式未在原话中明确，需要确认实际由谁、在什么节点、通过什么系统处理。"


def get_process_chain(domain_name: str) -> list[str]:
    normalized = normalize_text(domain_name)
    for item in context_entries("process_chains"):
        if normalize_text(item.get("name")) == normalized:
            chain = item.get("chain")
            return [normalize_text(value) for value in chain if normalize_text(value)] if isinstance(chain, list) else []
    return []


def build_current_process_from_context(domain_name: str, manual_actions: list[str]) -> str:
    chain = get_process_chain(domain_name)
    chain_text = " → ".join(chain)
    if manual_actions and chain_text:
        return f"当前大概率处在{chain_text}链路中，已暴露出{join_items(manual_actions[:3])}等人工处理动作，具体节点需确认。"
    if chain_text:
        return f"当前大概率处在{chain_text}链路中，实际卡点节点和责任角色仍需确认。"
    return build_current_process(manual_actions)


def build_process_breakpoint(pain_points: list[str], manual_actions: list[str], system_actions: list[str]) -> str:
    manual_text = join_items(manual_actions, "")
    if any(keyword in manual_text for keyword in ["询问", "等待", "才被发现", "确认状态"]):
        return "关键状态或影响范围没有自动同步，风险需要靠人工询问、等待他人反馈后才暴露。"
    if "协同断点" in pain_points:
        return "跨角色或跨部门之间的信息同步和责任闭环存在断点。"
    if "风险不可见" in pain_points:
        return "异常、延期或未闭环事项没有被系统提前暴露。"
    if "流程卡点" in pain_points:
        return "流程状态、卡点节点和责任人不够透明。"
    if manual_actions and ("自动生成" in system_actions or "看数据" in system_actions):
        return "关键结果依赖人工加工和传递，系统没有自动形成可用结果。"
    if manual_actions:
        return "关键处理动作依赖人工完成，缺少系统化触发、提醒或闭环。"
    return "流程断点尚不明确，需要确认当前卡在哪个节点或责任角色。"


def build_pain_root_cause(pain_points: list[str], manual_actions: list[str], process_breakpoint: str) -> str:
    if pain_points:
        explanation_map = {item["name"]: item["description"] for item in context_entries("pain_types")}
        explanations = [explanation_map.get(name, name) for name in pain_points[:2]]
        return f"{join_items(explanations)}；核心断点是：{process_breakpoint}"
    if manual_actions:
        return f"当前依赖{join_items(manual_actions[:3])}，系统触发、状态同步和责任闭环边界仍不清晰。"
    return "痛点根因尚不明确，需要补充当前处理方式、责任人和异常场景。"


def build_business_impact(domain_name: str, pain_points: list[str]) -> str:
    domain_desc = business_domain_label(domain_name) or "当前业务结果"
    if "风险不可见" in pain_points:
        return f"可能影响{domain_desc}中的异常提前发现和风险处置。"
    if "时效慢" in pain_points:
        return f"可能影响{domain_desc}中的响应及时性和交付判断。"
    if "数据不准" in pain_points:
        return f"可能影响{domain_desc}中的数据判断、计划安排和后续处理可信度。"
    if "协同断点" in pain_points:
        return f"可能影响{domain_desc}中的跨角色协同和责任闭环。"
    return f"可能影响{domain_desc}中的处理效率、责任闭环和业务判断。"


def build_desired_system_behavior(system_actions: list[str], pain_points: list[str]) -> list[str]:
    action_desc = {item["name"]: item["description"] for item in context_entries("system_actions")}
    behaviors = [action_desc.get(action, action) for action in system_actions]
    if not behaviors and "风险不可见" in pain_points:
        behaviors.append("自动识别异常、超期或未闭环状态，并提醒责任人处理")
    if not behaviors:
        behaviors.extend(["集中展示关键状态", "把待处理事项推给责任人", "跟踪处理结果是否关闭"])
    return unique_keep_order(behaviors)[:5]


def infer_surface_feature(text: str, system_actions: list[str]) -> str:
    if "报表" in text or "看板" in text:
        return "一张报表"
    if "提醒" in text or "通知" in text:
        return "一个提醒"
    if "审批" in text or "流转" in text:
        return "一个流程功能"
    if "自动" in text or "生成" in text or "计算" in text:
        return "一个自动化功能"
    if system_actions:
        return join_items(system_actions[:2])
    return "一个功能"


def derive_focus_points(diagnosis: dict, pain_points: list[str]) -> list[str]:
    focus: list[str] = []
    for fact in ensure_string_list(diagnosis.get("explicit_facts")):
        for keyword in ["BOM", "物料", "库存", "交期", "工单", "质量异常", "客户", "订单", "合同", "报表"]:
            if keyword in fact:
                focus.append(keyword)
    focus.extend(pain_points)
    if diagnosis.get("process_breakpoint"):
        focus.append(shorten_focus_text(diagnosis["process_breakpoint"]))
    return unique_keep_order(focus)[:5]


def shorten_focus_text(text: str) -> str:
    cleaned = cleanup_sentence(text).rstrip("。")
    return cleaned[:18] + ("..." if len(cleaned) > 18 else "")


def build_confirmation_options_from_diagnosis(diagnosis: dict, pain_points: list[str], system_actions: list[str]) -> dict:
    roles = ensure_string_list(diagnosis.get("target_users"))
    if not roles:
        role_candidates = build_context_candidates(" ".join(ensure_string_list(diagnosis.get("explicit_facts"))), "roles", 5)
        roles = [item["name"] for item in role_candidates]
    if not roles:
        roles = ["一线执行人员", "部门负责人", "跨部门协作人员", "ITBP"]

    focus_points = derive_focus_points(diagnosis, pain_points)
    if not focus_points:
        focus_points = ["流程断点", "人工动作", "业务影响", "数据口径", "责任闭环"]

    expectations = system_actions or ["看数据", "自动提醒", "自动流转", "自动同步", "自动闭环"]
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
        "why": cleanup_sentence(diagnosis.get("pain_root_cause")) or "待业务确认",
        "what": join_items(desired[:2], "待业务确认"),
        "where": cleanup_sentence(diagnosis.get("current_process")) or "待业务确认",
        "who": join_items(target_users, "待业务确认"),
        "input": join_items(systems, "待业务确认"),
        "output": join_items(desired, "待业务确认"),
        "how": [
            "确认触发条件、责任角色和数据来源。",
            "由系统替代已识别的人工动作，并形成待办或结果输出。",
            "跟踪处理结果是否关闭，未闭环事项继续提醒或升级。",
        ],
        "monitor": ["处理时效是否改善", "人工动作是否减少", "问题是否形成闭环"],
        "howmuch": "待业务确认",
    }


def build_diagnostic_texts(original_request: str, diagnosis: dict, pain_points: list[str], system_actions: list[str]) -> dict:
    domain_name = normalize_text(diagnosis.get("primary_business_domain")) or "待业务确认"
    domain_text = business_domain_label(domain_name)
    roles_text = join_items(ensure_string_list(diagnosis.get("target_users")), "相关人员")
    process_breakpoint = cleanup_sentence(diagnosis.get("process_breakpoint")) or "关键流程断点"
    impact = cleanup_sentence(diagnosis.get("business_impact")) or "业务处理结果受影响"
    action_text = build_action_clause(system_actions)
    trigger = "出现异常、状态变化或需要跟进时"
    surface = infer_surface_feature(original_request, system_actions)

    real_intent = (
        f"你可能不是单纯想要{surface}，而是希望系统在{domain_text}场景下帮助{roles_text}"
        f"及时发现、跟进或闭环{process_breakpoint}，避免{impact}"
    )
    rewritten = f"希望系统在{domain_text}场景下，帮助{roles_text}{action_text}，处理{process_breakpoint}。"
    suggested = f"当{trigger}，系统{action_text}，帮助{roles_text}处理{process_breakpoint}，避免{impact}"
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
        domain_candidates = [{"name": "General", "confidence": 0.35, "reason": "原话未提供足够业务域线索"}]

    system_candidates = build_context_candidates(text, "systems", 4)
    role_candidates = build_context_candidates(text, "roles", 5)
    pain_candidates = build_context_candidates(text, "pain_types", 5)
    action_candidates = build_context_candidates(text, "system_actions", 5)

    pain_points = [item["name"] for item in pain_candidates] or ["待业务确认"]
    system_actions = [item["name"] for item in action_candidates]
    target_users = [item["name"] for item in role_candidates if item["confidence"] >= 0.62][:4]
    manual_actions = build_manual_actions(text)
    primary_domain = domain_candidates[0]["name"] if domain_candidates[0]["confidence"] >= 0.55 else "待业务确认"
    process_breakpoint = build_process_breakpoint(pain_points, manual_actions, system_actions)
    uncertain_items: list[str] = []

    for item in system_candidates:
        if item["confidence"] < 0.72:
            uncertain_items.append(f"是否涉及 {item['name']} 需要确认")
    if primary_domain == "待业务确认":
        uncertain_items.append("主业务域需要确认")
    if not target_users:
        uncertain_items.append("主要使用对象需要确认")
    if not system_actions:
        uncertain_items.append("系统需要替代的动作需要确认")

    diagnosis = {
        "explicit_facts": build_explicit_facts(text, system_candidates, role_candidates),
        "inferred_context": [
            f"根据业务上下文，候选业务域为 {domain_candidates[0]['name']}，置信度 {domain_candidates[0]['confidence']}。"
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
    top_domain = domain_candidates[0] if domain_candidates else {"name": "待业务确认", "confidence": 0}
    business_domain = normalize_text(diagnosis.get("primary_business_domain")) or normalize_text(top_domain.get("name"))
    if float(top_domain.get("confidence") or 0) < 0.55:
        business_domain = "待业务确认"

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
        pain_points = ["待业务确认"]

    desired_text = " ".join(ensure_string_list(diagnosis.get("desired_system_behavior")))
    system_actions = [item["name"] for item in build_context_candidates(user_input + " " + desired_text, "system_actions", 5)]
    if not system_actions:
        system_actions = ["待业务确认"]

    texts = build_diagnostic_texts(user_input, diagnosis, pain_points, system_actions)
    uncertain_items = unique_keep_order(
        ensure_string_list(diagnosis.get("uncertain_items"))
        + ["触发条件需要确认"]
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
        return "关键业务处理不够顺畅"
    return "、".join(item.get("phrase", item["name"]) for item in pains)


def build_target_users(text: str, domain: dict, confirmation_options: dict[str, list[str]]) -> list[str]:
    explicit_roles: list[str] = []
    role_keywords = [
        ("采购执行", "采购执行"),
        ("供应链负责人", "供应链负责人"),
        ("计划人员", "计划人员"),
        ("仓库管理员", "仓库管理员"),
        ("车间主管", "车间主管"),
        ("财务专员", "财务专员"),
        ("法务专员", "法务专员"),
        ("业务负责人", "业务负责人"),
        ("HR专员", "HR专员"),
        ("IT支持", "IT支持"),
    ]

    for keyword, role in role_keywords:
        if keyword in text:
            explicit_roles.append(role)

    default_roles = (confirmation_options or {}).get("affected_roles") or []
    return unique_keep_order(explicit_roles + default_roles[:2])[:3]


def build_action_clause(action_names: list[str]) -> str:
    action_aliases = {
        "展示关键数据": "看数据",
        "自动生成结果": "自动生成",
        "自动拦截风险": "自动控制",
        "自动控制": "自动控制",
        "自动同步": "自动同步",
        "自动提醒": "自动提醒",
        "自动流转": "自动流转",
        "自动闭环": "自动闭环",
        "看数据": "看数据",
        "自动生成": "自动生成",
    }
    phrase_map = {
        "看数据": "展示关键数据",
        "自动生成": "自动生成关键结果",
        "自动同步": "自动同步关键数据",
        "自动提醒": "自动提醒相关人员",
        "自动控制": "按规则校验并拦截风险",
        "自动流转": "自动流转关键节点",
        "自动闭环": "跟踪处理闭环",
    }
    normalized = unique_keep_order(
        [action_aliases.get(normalize_text(name), normalize_text(name)) for name in action_names if normalize_text(name)]
    )
    phrases = [phrase_map[name] for name in normalized if name in phrase_map]
    return "、".join(phrases) if phrases else "支持关键处理动作"


def build_focus_metrics(focus_points: list[str]) -> list[str]:
    metric_rules = [
        ("缺料", "缺料风险提前发现率提升"),
        ("交期", "交期响应时效缩短"),
        ("供应商", "供应商响应闭环率提升"),
        ("BOM", "BOM用量计算准确率提升"),
        ("用量", "用量计算准确率提升"),
        ("库存", "库存可用性判断准确率提升"),
        ("人工", "人工统计工时下降"),
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
    roles_text = join_items(target_users, "相关人员")
    focus_text = join_items(focus_points or [], guess_focus(text, domain))
    action_names = system_expectations or [item["name"] for item in actions]
    action_clause = build_action_clause(action_names)
    pain_text = summarize_pains(pains)

    if domain["code"] == "warehouse":
        return (
            f"希望系统能围绕{focus_text}，{action_clause}，及时发现账实不一致和缺货风险，"
            f"并提醒{roles_text}处理，避免业务下单后才发现无货。"
        )
    if domain["code"] == "procurement":
        return (
            f"希望系统能围绕{focus_text}，{action_clause}，"
            f"并及时把结果发送给{roles_text}查看和跟进，减少{pain_text}问题。"
        )
    if domain["code"] == "finance":
        return (
            f"希望系统能围绕{focus_text}，{action_clause}，及时提供给{roles_text}核对，"
            f"减少手工比对和月底结账压力。"
        )
    if domain["code"] == "legal":
        return (
            f"希望系统能围绕{focus_text}，{action_clause}，并及时提醒{roles_text}跟进，"
            f"避免临近到期才发现风险。"
        )
    if domain["code"] == "hr":
        return (
            f"希望系统能围绕{focus_text}，{action_clause}，按节点通知并流转给{roles_text}，"
            f"减少人工跟进和漏步骤。"
        )
    if domain["code"] == "production":
        return (
            f"希望系统能围绕{focus_text}，{action_clause}，并在异常滞后或即将影响计划时提醒{roles_text}，"
            f"减少人工追问，提高生产计划跟进效率。"
        )
    if domain["code"] == "sales":
        return (
            f"希望系统能围绕{focus_text}，{action_clause}，并在关键节点提醒{roles_text}及时处理，"
            f"减少信息分散和漏跟进。"
        )

    return (
        f"希望系统能围绕{focus_text}，{action_clause}，及时支持{roles_text}处理，"
        f"减少{pain_text}。"
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
    roles_text = join_items(target_users, "相关人员")
    focus_text = join_items(focus_points or [], guess_focus(text, domain))
    action_names = system_expectations or [item["name"] for item in actions]
    action_clause = build_action_clause(action_names)

    if domain["code"] == "warehouse":
        return f"仓储团队希望系统围绕{focus_text}，{action_clause}，提前识别异常并提醒{roles_text}处理。"
    if domain["code"] == "procurement":
        return f"采购团队希望系统围绕{focus_text}，{action_clause}，并把结果及时推送给{roles_text}，减少人工统计和交付压力。"
    if domain["code"] == "finance":
        return f"财务团队希望系统围绕{focus_text}，{action_clause}，并及时提供给{roles_text}处理，缩短月底结账时间。"
    if domain["code"] == "legal":
        return f"法务团队希望系统围绕{focus_text}，{action_clause}，并提醒{roles_text}跟进，避免风险临近才被发现。"
    if domain["code"] == "hr":
        return f"HR 希望系统围绕{focus_text}，{action_clause}，按节点通知并流转给{roles_text}。"
    if domain["code"] == "production":
        return f"生产团队希望系统围绕{focus_text}，{action_clause}，并在异常滞后时提醒{roles_text}及时跟进。"
    if domain["code"] == "sales":
        return f"销售团队希望系统围绕{focus_text}，{action_clause}，并在关键节点提醒{roles_text}及时处理。"
    return f"业务团队希望系统围绕{focus_text}，{action_clause}，及时支持{roles_text}处理。"


def build_structured_report(
    text: str,
    domain: dict,
    pains: list[dict],
    actions: list[dict],
    target_users: list[str],
    focus_points: list[str] | None = None,
    system_expectations: list[str] | None = None,
) -> dict:
    roles_text = join_items(target_users, "待业务确认")
    selected_focus = normalize_selected_values(focus_points or [])
    selected_expectations = normalize_selected_values(system_expectations or [])
    focus_text = join_items(selected_focus, guess_focus(text, domain))
    action_names = selected_expectations or [item["name"] for item in actions]
    action_clause = build_action_clause(action_names)
    has_selected_constraints = bool(selected_focus or selected_expectations)

    what_map = {
        "procurement": "采购/供应影响识别与结果推送",
        "finance": "多系统对账差异自动汇总",
        "hr": "入职账号、设备与权限协同",
        "legal": "合同到期提醒与跟进",
        "warehouse": "库存账实差异自动比对与缺货提醒",
        "production": "工单进度透明化与异常提醒",
        "sales": "客户跟进与订单进度提醒",
        "general": "关键数据与待处理动作自动跟进",
    }
    where_map = {
        "procurement": "采购执行 / 供应链协同场景",
        "finance": "财务对账 / 月结处理场景",
        "hr": "员工入职协同场景",
        "legal": "合同管理 / 到期跟进场景",
        "warehouse": "仓储库存管理 / 下单前库存校验场景",
        "production": "生产工单跟踪 / 计划协同场景",
        "sales": "客户跟进 / 订单推进场景",
        "general": "当前业务处理场景",
    }
    owner_map = {
        "procurement": f"采购团队主导，主要使用方：{roles_text}",
        "finance": f"财务团队主导，主要使用方：{roles_text}",
        "hr": f"HR 主导，协同使用方：{roles_text}",
        "legal": f"法务主导，协同使用方：{roles_text}",
        "warehouse": f"仓储团队主导，主要使用方：{roles_text}",
        "production": f"生产计划团队主导，主要使用方：{roles_text}",
        "sales": f"销售团队主导，主要使用方：{roles_text}",
        "general": f"待业务确认，当前主要影响 {roles_text}",
    }
    input_map = {
        "procurement": "采购计划、物料需求、库存和供应相关数据",
        "finance": "多个系统的对账明细、凭证或流水数据",
        "hr": "入职名单、账号申请信息、设备和权限清单",
        "legal": "合同台账、到期时间、负责人信息",
        "warehouse": "库存台账、实际出入库记录、业务下单数据",
        "production": "工单、报工记录、排产计划和异常状态",
        "sales": "客户跟进记录、订单状态、关键节点时间",
        "general": "业务主数据、关键状态、待处理事项",
    }
    output_map = {
        "procurement": "供应影响结果、异常数据提醒、结果推送通知",
        "finance": "对账差异清单、汇总结果、处理提醒",
        "hr": "入职待办清单、节点流转通知、漏项提醒",
        "legal": "合同到期提醒、跟进清单、升级通知",
        "warehouse": "库存差异清单、缺货风险提醒、异常处理通知",
        "production": "工单进度视图、异常提醒、计划影响提示",
        "sales": "客户跟进提醒、订单推进结果、关键节点提醒",
        "general": f"{focus_text}相关结果、提醒通知和处理动作",
    }
    pain_metric_map = {
        "时效慢": "处理时效缩短",
        "容易漏": "漏处理次数下降",
        "数据不准": "关键数据差异率下降",
        "人工太重": "人工处理工时下降",
        "流程卡点": "流程平均流转时长下降",
        "风险不可见": "异常或风险提前发现率提升",
    }

    why = {
        "procurement": "当前 BOM 用量计算和结果传递依赖人工处理，交付压力大时容易响应不及时。",
        "finance": "月底对账需要从多个系统导数并手工比对，耗时长且容易遗漏差异。",
        "hr": "入职账号、设备和权限依赖人工通知和跟进，步骤多时容易漏项。",
        "legal": "合同到期依赖人工记忆和跟踪，容易在临近到期时才发现风险。",
        "warehouse": "库存数据与实际情况不一致时，往往要等到业务下单后才暴露问题，影响响应。",
        "production": "工单进度不透明，异常推进不及时，计划人员需要频繁人工追问。",
        "sales": "客户和订单进度分散在不同环节，关键节点容易漏跟进。",
        "general": f"当前{summarize_pains(pains)}，影响 {roles_text} 的处理效率。",
    }[domain["code"]]

    how_steps = [
        f"先梳理 {input_map[domain['code']]} 的来源和判断规则。",
        f"由系统围绕 {focus_text}，{action_clause}。",
        f"将结果发送给 {roles_text} 跟进，并形成异常处理闭环。",
    ]
    monitor = [pain_metric_map[item["name"]] for item in pains if item["name"] in pain_metric_map][:2]
    if not monitor:
        monitor = ["关键处理时效提升", "人工重复工作下降"]
    monitor = unique_keep_order(build_focus_metrics(selected_focus) + monitor)[:3]

    input_value = input_map[domain["code"]]
    output_value = output_map[domain["code"]]
    what_value = what_map[domain["code"]]

    if selected_focus:
        why = f"{why} 本次优先关注：{focus_text}。"
        input_value = f"{input_value}；重点关注：{focus_text}"
    if selected_expectations:
        output_value = f"{focus_text}相关结果；系统需支持：{action_clause}"
    elif selected_focus:
        output_value = f"{focus_text}相关结果、提醒通知和处理动作"
    if has_selected_constraints:
        what_value = f"{focus_text}处理：{action_clause}"

    return {
        "why": why,
        "what": what_value,
        "where": where_map[domain["code"]],
        "who": owner_map[domain["code"]],
        "input": input_value,
        "output": output_value,
        "how": how_steps,
        "monitor": monitor,
        "howmuch": "建议先按一个重点场景试点推进，具体投入待业务和 IT 确认。",
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
    users_text = join_items(target_users, "相关人员")
    impact = diagnosis["business_impact"]
    trigger = "出现异常、状态变化或需要跟进时"
    previous_request = cleanup_sentence(analysis_result.get("suggested_request")) if isinstance(analysis_result, dict) else ""

    if scenario_values and (domain_name == "Warehouse" or scenario_template_code == "warehouse_inventory_accuracy" or "库存" in user_input):
        scenario_action = scenario_answer_phrase(selected_options, "expected_action", action_clause)
        inventory_scope = scenario_answer_phrase(selected_options, "inventory_definition", "可用库存")
        scenario_owner = scenario_answer_phrase(selected_options, "exception_owner", users_text)
        action_values = scenario_answers_by_key(selected_options, "expected_action")
        action_parts: list[str] = []
        for value in action_values:
            cleaned_value = value.replace("下单前", "", 1).replace(inventory_scope, "库存").strip()
            if "自动校验库存" in cleaned_value:
                cleaned_value = "自动校验"
            if cleaned_value and cleaned_value not in action_parts:
                action_parts.append(cleaned_value)
        action_text = selection_phrase(action_parts, "自动校验并提醒")
        refined = limit_text(
            f"业务下单前，系统对{inventory_scope}{action_text}，并在库存异常时通知{scenario_owner}处理，避免下单后才发现无货。",
            120,
        )
        rewritten = limit_text(f"下单前校验{inventory_scope}并处理库存异常，避免下单后才发现无货。", 80)
    elif scenario_values:
        scenario_focus = selection_phrase(scenario_values[:3], process_breakpoint)
        refined = limit_text(
            f"当{trigger}，系统围绕{scenario_focus}进行识别、提醒和跟踪，帮助{users_text}提前处理，避免{impact}",
            120,
        )
        rewritten = limit_text(f"希望系统围绕{scenario_focus}自动提醒和跟踪处理，避免后续被动发现问题。", 80)
    else:
        refined = limit_text(
            f"当{trigger}，系统围绕{process_breakpoint}，{action_clause}，帮助{users_text}及时处理，避免{impact}",
            120,
        )
        rewritten = limit_text(
            f"希望系统在{domain_name}场景下，帮助{users_text}处理{process_breakpoint}，减少人工跟进和流程断点。",
            80,
        )
    if not scenario_values:
        refined = build_integrated_refine_text(refined, selected_options, diagnosis, domain_name, 120)
        rewritten = build_integrated_refine_text(rewritten, selected_options, diagnosis, domain_name, 80)

    uncertain_items: list[str] = ensure_string_list(base_analysis.get("uncertain_items"))
    confirmation = base_analysis.get("confirmation_options") if isinstance(base_analysis.get("confirmation_options"), dict) else {}
    for label, key, selected_values in [
        ("影响对象", "affected_roles", roles),
        ("关注重点", "focus_points", focus_points),
        ("系统期望", "system_expectations", expectations),
    ]:
        allowed = ensure_string_list(confirmation.get(key))
        for value in selected_values:
            if allowed and value not in allowed:
                uncertain_items.append(f"用户选择的{label}“{value}”与AI诊断候选不一致，需要确认")

    structured_report = ensure_structured_report(base_analysis.get("structured_report"))
    structured_report["what"] = f"围绕{process_breakpoint}，{action_clause}"
    structured_report["who"] = users_text
    structured_report["output"] = f"{process_breakpoint}的处理结果、待办提醒和闭环状态"
    if scenario_values:
        structured_report["input"] = f"业务补充澄清：{join_items(scenario_values[:6])}"
        structured_report["output"] = f"形成{join_items(scenario_values[:4])}相关的处理结果、提醒和闭环状态"
    structured_report["how"] = [
        "确认触发条件、数据来源和责任角色。",
        f"系统围绕{process_breakpoint}，{action_clause}。",
        f"将结果推给{users_text}处理，并跟踪是否关闭。",
    ]
    if previous_request and previous_request not in refined:
        uncertain_items.append("上一版建议已重新生成，请确认是否保留原有表达")

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
        raise ValueError("LLM 返回内容为空")

    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("LLM 返回内容不包含 JSON 对象")

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
        "input": f"请只输出 JSON，不要输出 Markdown。\n\n{user_prompt}",
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
        raise ValueError(f"LLM 返回错误：{payload.get('error')}")
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
        log_llm_event("parse_failed", label=label, reason=f"响应不是 JSON：{exc}")
        raise
    if llm_debug_enabled():
        app.logger.info("[LLM] raw_response | %s", json.dumps({"label": label, "payload": payload}, ensure_ascii=False))
    choices = payload.get("choices") or []
    if not choices:
        log_llm_event("parse_failed", label=label, reason="LLM 返回缺少 choices")
        raise ValueError("LLM 返回缺少 choices")
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
                "reason": normalize_text(value.get("reason")) or "待业务确认",
            }
        )
    result.sort(key=lambda item: item["confidence"], reverse=True)
    return result


def ensure_structured_report(value: object) -> dict:
    source = value if isinstance(value, dict) else {}
    return {
        "why": cleanup_sentence(source.get("why")) or "待业务确认",
        "what": cleanup_sentence(source.get("what")) or "待业务确认",
        "where": cleanup_sentence(source.get("where")) or "待业务确认",
        "who": cleanup_sentence(source.get("who")) or "待业务确认",
        "input": cleanup_sentence(source.get("input")) or "待业务确认",
        "output": cleanup_sentence(source.get("output")) or "待业务确认",
        "how": ensure_string_list(source.get("how")) or ["待业务确认"],
        "monitor": ensure_string_list(source.get("monitor")) or ["待业务确认"],
        "howmuch": cleanup_sentence(source.get("howmuch")) or "待业务确认",
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
        "current_process": cleanup_sentence(source.get("current_process")) or "待业务确认",
        "manual_actions": ensure_string_list(source.get("manual_actions")),
        "process_breakpoint": cleanup_sentence(source.get("process_breakpoint")) or "待业务确认",
        "pain_root_cause": cleanup_sentence(source.get("pain_root_cause")) or "待业务确认",
        "business_impact": cleanup_sentence(source.get("business_impact")) or "待业务确认",
        "desired_system_behavior": ensure_string_list(source.get("desired_system_behavior")),
        "candidate_systems": ensure_string_list(source.get("candidate_systems")),
        "source_evidence": ensure_string_list(source.get("source_evidence")),
        "uncertain_items": ensure_string_list(source.get("uncertain_items")),
    }
    if not diagnosis["explicit_facts"]:
        diagnosis["explicit_facts"] = ["原话只提供了初步需求描述，具体业务事实仍需补充。"]
    if not diagnosis["business_domain_candidates"]:
        diagnosis["business_domain_candidates"] = [
            {"name": "General", "confidence": 0.35, "reason": "缺少明确业务域线索"}
        ]
    if not diagnosis["desired_system_behavior"]:
        diagnosis["desired_system_behavior"] = ["待业务确认"]
    if not diagnosis["source_evidence"]:
        diagnosis["source_evidence"] = extract_source_evidence(original_request)
    diagnosis["primary_business_domain"] = cleanup_sentence(source.get("primary_business_domain")) or diagnosis["business_domain_candidates"][0]["name"]
    return diagnosis


def collect_low_confidence_uncertain(diagnosis: dict) -> list[str]:
    items: list[str] = []
    domain_candidates = ensure_candidate_list(diagnosis.get("business_domain_candidates"))
    if domain_candidates and domain_candidates[0]["confidence"] < 0.55:
        items.append("主业务域需要确认")
    for candidate in ensure_candidate_list(diagnosis.get("related_system_candidates")):
        if candidate["confidence"] < 0.72:
            items.append(f"是否涉及 {candidate['name']} 需要确认")
    return items


def validate_analysis_result(result: dict, original_request: str) -> dict:
    source = result if isinstance(result, dict) else {}
    fallback = build_analysis_from_diagnosis(original_request, build_fallback_diagnosis(original_request)) if not source.get("diagnosis") else {}
    diagnosis = ensure_diagnosis_schema(source.get("diagnosis") or fallback.get("diagnosis"), original_request)
    warnings = ensure_string_list(source.get("warnings"))

    top_domain = diagnosis["business_domain_candidates"][0]
    business_domain = cleanup_sentence(source.get("business_domain")) or diagnosis.get("primary_business_domain") or top_domain["name"]
    if top_domain["confidence"] < 0.55:
        business_domain = "待业务确认"

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
            matched_objects[0] if matched_objects else "待确认业务对象",
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
        pain_points = ["待业务确认"]

    system_actions = ensure_string_list(source.get("system_actions"))
    if not system_actions:
        behavior_context = " ".join(diagnosis["desired_system_behavior"])
        system_actions = [item["name"] for item in build_context_candidates(behavior_context, "system_actions", 5)]
    if not system_actions:
        system_actions = ["待业务确认"]

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
        uncertain_items = ["触发条件、数据来源和责任角色需要确认"]

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
    if structured_report["why"] == "待业务确认":
        structured_report["why"] = diagnosis["pain_root_cause"]
    if structured_report["what"] == "待业务确认":
        structured_report["what"] = join_items(diagnosis["desired_system_behavior"], "待业务确认")
    if structured_report["where"] == "待业务确认":
        structured_report["where"] = diagnosis["current_process"]
    if structured_report["who"] == "待业务确认":
        structured_report["who"] = join_items(target_users, "待业务确认")
    if structured_report["input"] == "待业务确认" and related_systems:
        structured_report["input"] = join_items(related_systems)
    if structured_report["output"] == "待业务确认":
        structured_report["output"] = join_items(diagnosis["desired_system_behavior"], "待业务确认")
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
    "DSTE": ["计划系统", "BI/经营看板"],
    "Supply": ["SAP", "APS", "WMS", "计划系统"],
    "Manufacturing": ["MES", "SAP"],
    "Procurement": ["SAP", "SRM", "采购系统"],
    "Quality": ["QMS", "MES", "DMS"],
    "MBTIT": ["SAP", "MES", "WMS", "PLM", "SRM", "DMS"],
    "Warehouse": ["WMS", "SAP"],
}


def infer_candidate_systems(domain_name: str, user_input: str, retrieved_context: dict, related_systems: list[str]) -> list[str]:
    candidates: list[str] = []
    candidates.extend(related_systems)
    candidates.extend(DOMAIN_CANDIDATE_SYSTEMS.get(domain_name, []))

    if "计划" in user_input and domain_name in ["Supply", "DSTE"]:
        candidates.append("计划系统")
    if "APS" in user_input:
        candidates.append("APS")
    if any(keyword in user_input for keyword in ["缺料", "物料", "库存", "采购在途"]):
        candidates.extend(["SAP", "WMS"])
    if any(keyword in user_input for keyword in ["供应商", "交期", "采购订单"]):
        candidates.extend(["SRM", "SAP"])
    if any(keyword in user_input for keyword in ["质量", "整改", "验证", "关闭"]):
        candidates.append("QMS")
    if any(keyword in user_input for keyword in ["经销商", "售后", "维修", "索赔", "配件"]):
        candidates.append("DMS")

    return unique_keep_order(candidates)[:6]


def concise_business_object(business_object: str) -> str:
    text = cleanup_sentence(business_object)
    replacements = {
        "生产计划影响的物料、库存和采购到货/缺料风险": "受影响物料和缺料风险",
        "工单状态和生产进度": "工单进度",
        "供应商交期和快延期采购订单": "快延期采购订单",
        "质量异常整改和验证关闭": "质量异常整改闭环",
        "跨系统订单状态和数据口径": "跨系统订单状态",
        "年度重点项目执行进度和延期风险": "重点项目执行风险",
        "售后维修单备件准备和库存状态": "备件准备和库存状态",
        "上市资料和服务政策口径": "上市资料和政策口径",
        "经销商订单发货进度和交付风险": "经销商订单交付风险",
        "图纸/BOM版本和变更影响范围": "图纸/BOM版本影响",
    }
    return replacements.get(text, text)


def infer_specific_business_object(user_input: str, domain_name: str, fallback_object: str) -> str:
    text = normalize_text(user_input)
    if domain_name == "Supply" and any(keyword in text for keyword in ["计划", "物料", "缺料"]):
        return "生产计划影响的物料、库存和采购到货/缺料风险"
    if domain_name == "Manufacturing" and any(keyword in text for keyword in ["工单", "报工", "车间"]):
        return "工单状态和生产进度"
    if domain_name == "Procurement" and any(keyword in text for keyword in ["供应商", "交期", "采购订单", "漏催"]):
        return "供应商交期和快延期采购订单"
    if domain_name == "Quality" and any(keyword in text for keyword in ["质量", "整改", "验证", "关闭"]):
        return "质量异常整改和验证关闭"
    if domain_name == "MBTIT" and any(keyword in text for keyword in ["跨系统", "口径", "状态不一致"]):
        return "跨系统订单状态和数据口径"
    if domain_name == "DSTE" and any(keyword in text for keyword in ["年度", "重点项目", "延期", "执行"]):
        return "年度重点项目执行进度和延期风险"
    if domain_name == "SD" and any(keyword in text for keyword in ["维修", "备件", "售后"]):
        return "售后维修单备件准备和库存状态"
    if domain_name == "IPMS" and any(keyword in text for keyword in ["上市", "资料", "政策", "口径"]):
        return "上市资料和服务政策口径"
    if domain_name == "MTC" and any(keyword in text for keyword in ["经销商", "订单", "发货", "交付"]):
        return "经销商订单发货进度和交付风险"
    if domain_name == "IPD" and any(keyword in text for keyword in ["图纸", "BOM", "版本", "变更"]):
        return "图纸/BOM版本和变更影响范围"
    return fallback_object


def extract_source_evidence(user_input: str) -> list[str]:
    evidence: list[str] = []
    patterns = [
        "客户报修",
        "客户一催我们就要到处问维修和备件情况",
        "到处问维修和备件情况",
        "采购和生产",
        "管理层",
        "排产",
        "责任部门",
        "等采购或者车间来问才发现可能缺料",
        "等采购或车间来问才发现缺料",
        "只能去问车间",
        "快延期的订单没有系统提醒",
        "容易漏催",
        "开会的时候才想起来查",
        "会议前才临时追查",
        "人工拉群确认口径",
        "客户催了才发现交付风险",
        "邮件",
        "微信",
    ]
    for pattern in patterns:
        if pattern in user_input:
            evidence.append(pattern)
    for keyword in ["客户报修", "客户一催", "到处问", "采购和生产", "管理层", "排产", "责任部门", "来问才发现", "只能去问", "没人盯", "开会", "漏催", "邮件", "微信", "状态不一致"]:
        if keyword in user_input:
            evidence.append(keyword)
    return unique_keep_order(evidence)[:4]


def infer_supplemental_pain_points(user_input: str) -> list[str]:
    points: list[str] = []
    if any(keyword in user_input for keyword in ["客户一催", "催促后", "才知道", "才发现", "不及时"]):
        points.extend(["时效慢", "风险不可见"])
    if any(keyword in user_input for keyword in ["到处问", "只能去问", "人工问", "人工查", "手动跟进"]):
        points.extend(["人工太重", "协同断点"])
    if any(keyword in user_input for keyword in ["没人盯", "漏", "想起来才"]):
        points.append("容易漏")
    return unique_keep_order(points)


def build_contextual_current_manual_process(user_input: str, retrieved_context: dict, business_object: str) -> str:
    domain = top_relevant_context_item(retrieved_context, "domain_context")
    patterns = normalize_context_list(retrieved_context.get("matched_manual_actions"))
    manual_actions = patterns + choose_relevant_phrases(user_input, normalize_context_list(domain.get("common_manual_actions")), 2)
    manual_actions = unique_keep_order(manual_actions)
    object_status_suffix = "" if business_object.endswith("状态") else "状态"
    if manual_actions:
        return cleanup_sentence(
            f"当前主要靠{join_items(manual_actions[:3])}来确认{business_object}{object_status_suffix}，具体责任节点仍需业务确认。"
        )
    return cleanup_sentence(
        f"当前{business_object}处理方式需要业务人员人工查询、确认或催办，实际责任人和处理节点仍需确认。"
    )


def build_contextual_process_breakpoint(user_input: str, retrieved_context: dict, business_object: str) -> str:
    domain = top_relevant_context_item(retrieved_context, "domain_context")
    process = top_relevant_context_item(retrieved_context, "process_context", normalize_text(domain.get("name")))
    candidates = normalize_context_list(domain.get("common_breakpoints")) + normalize_context_list(process.get("typical_breakpoints"))
    selected = choose_relevant_phrases(user_input, candidates, 2)
    if selected:
        return cleanup_sentence(join_items(selected[:2]))
    return cleanup_sentence(f"{business_object}的状态、责任人或关闭结果没有被系统持续跟踪。")


def build_contextual_passive_consequence(user_input: str, retrieved_context: dict, business_object: str) -> str:
    domain = top_relevant_context_item(retrieved_context, "domain_context")
    if "开会" in user_input:
        return cleanup_sentence(f"开会时才想起来查{business_object}是否处理完，问题容易长期未闭环。")
    if "来问才发现" in user_input:
        return cleanup_sentence(f"等采购、车间或相关人员来问时才暴露{business_object}。")
    if "只能去问车间" in user_input:
        return cleanup_sentence(f"计划人员只能反复问车间，难以及时判断{business_object}是否影响交付。")
    if "漏催" in user_input:
        return cleanup_sentence(f"快延期事项容易漏催，可能影响后续生产交付。")
    candidates = normalize_context_list(domain.get("common_consequences"))
    selected = choose_relevant_phrases(user_input, candidates, 2)
    if selected:
        return cleanup_sentence(join_items(selected[:2]))
    if any(keyword in user_input for keyword in ["催", "来问", "才发现", "开会", "月底"]):
        return cleanup_sentence(f"等别人追问或集中检查时才发现{business_object}没有处理完。")
    return cleanup_sentence(f"{business_object}风险容易到后续业务受影响时才暴露。")


def expand_minimum_behavior(behavior: str, business_object: str, manual_process: str, breakpoint: str) -> str:
    cleaned = cleanup_sentence(behavior)
    if not cleaned:
        return ""
    replacement = "人工查询和跟进"
    if "问" in manual_process:
        replacement = "人工逐个询问状态"
    elif "催" in manual_process:
        replacement = "人工催办"
    elif "会议" in manual_process or "开会" in manual_process:
        replacement = "会议前临时追查"
    elif "手动" in manual_process:
        replacement = "手动维护状态"
    elif "Excel" in manual_process:
        replacement = "Excel手工汇总"

    if any(keyword in cleaned for keyword in ["提醒", "预警", "告警"]):
        return cleanup_sentence(f"在{business_object}超期、停滞或未关闭时提醒责任人，替代{replacement}")
    if any(keyword in cleaned for keyword in ["同步", "更新"]):
        object_status_suffix = "" if business_object.endswith("状态") else "状态"
        return cleanup_sentence(f"自动同步{business_object}{object_status_suffix}，替代{replacement}")
    if any(keyword in cleaned for keyword in ["展示", "看", "查询"]):
        return cleanup_sentence(f"集中展示{business_object}进度、责任人和异常状态，替代{replacement}")
    if any(keyword in cleaned for keyword in ["生成", "待办", "分派", "派发", "汇总", "清单"]):
        return cleanup_sentence(f"自动生成{business_object}待办并分派责任人，替代{replacement}")
    if any(keyword in cleaned for keyword in ["跟踪", "关闭", "闭环", "验证"]):
        return cleanup_sentence(f"自动跟踪{business_object}处理到关闭，替代{replacement}")
    if any(keyword in cleaned for keyword in ["识别", "计算", "判断"]):
        return cleanup_sentence(f"自动识别{business_object}影响和风险，替代{replacement}")
    if len(cleaned) <= 6 or cleaned in ["自动提醒", "自动同步", "看数据", "自动流转", "自动生成"]:
        return cleanup_sentence(f"{cleaned}{business_object}状态，替代{replacement}")
    if business_object not in cleaned and len(cleaned) < 18:
        return cleanup_sentence(f"{cleaned}{business_object}，用于处理{breakpoint}")
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
            f"自动识别{business_object}状态变化或超期风险",
            f"自动形成{business_object}待办并提醒责任人",
            f"自动跟踪{business_object}处理结果是否关闭",
        ]
    return unique_keep_order(expanded)[:4]


def build_fast_uncertain_items(user_input: str, retrieved_context: dict, related_systems: list[str]) -> list[str]:
    items: list[str] = []
    system_candidates = ensure_string_list(retrieved_context.get("matched_systems"))
    if system_candidates and not related_systems:
        items.append("数据来源来自哪个系统？")
    if any(keyword in user_input for keyword in ["提醒", "催", "没人盯", "超期", "延期", "待办"]):
        items.append("提醒对象是谁？")
    if any(keyword in user_input for keyword in ["超期", "延期", "快延", "不及时"]):
        items.append("什么条件算超期或延期？")
    if any(keyword in user_input for keyword in ["关闭", "完成", "闭环", "处理完"]):
        items.append("什么状态算关闭或完成？")
    if any(keyword in user_input for keyword in ["同步", "状态", "到哪一步", "进度"]):
        items.append("状态更新的来源和频率是什么？")
    if len(items) < 3:
        items.append("是否需要形成待办闭环？")
    return unique_keep_order(items)[:3]


def build_fast_fallback_from_context(user_input: str, retrieved_context: dict | None = None) -> dict:
    retrieved_context = retrieved_context or retrieve_context(user_input)
    text = normalize_text(user_input)
    domain_name = ensure_string_list(retrieved_context.get("matched_domains"))[0] if ensure_string_list(retrieved_context.get("matched_domains")) else "General"
    fallback_business_object = ensure_string_list(retrieved_context.get("matched_business_objects"))[0] if ensure_string_list(retrieved_context.get("matched_business_objects")) else "待确认业务对象"
    business_object = infer_specific_business_object(text, domain_name, fallback_business_object)
    text_business_object = concise_business_object(business_object)
    related_systems = explicit_system_names(text)
    candidate_systems = infer_candidate_systems(domain_name, text, retrieved_context, related_systems)
    pain_points = unique_keep_order(
        ensure_string_list(retrieved_context.get("matched_pain_types"))
        + infer_supplemental_pain_points(text)
    ) or ["待业务确认"]
    system_actions = ensure_string_list(retrieved_context.get("matched_system_actions")) or ["自动提醒", "看数据"]
    target_users = ensure_string_list(retrieved_context.get("matched_roles"))[:4]
    if not target_users:
        target_users = ["业务责任人"]

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
    roles_text = join_items(target_users[:2], "责任人")
    first_behavior = minimum_system_behavior[0]
    real_intent = limit_text(
        f"用户不是单纯想要一个功能，而是希望{roles_text}在{business_domain_label(domain_name)}场景下提前发现、跟进或闭环{text_business_object}问题，避免{passive_consequence}。",
        120,
    )
    rewritten_request = limit_text(
        f"希望系统围绕{text_business_object}自动形成跟踪和提醒，处理{process_breakpoint}，避免{passive_consequence}。",
        80,
    )
    suggested_request = limit_text(
        f"当{text_business_object}发生或状态变化后，系统{first_behavior}，帮助{roles_text}跟踪处理进度，避免{passive_consequence}。",
        120,
    )

    diagnosis = {
        "business_object": business_object,
        "current_process": current_manual_process,
        "current_manual_process": current_manual_process,
        "manual_actions": ensure_string_list(retrieved_context.get("matched_manual_actions")),
        "process_breakpoint": process_breakpoint,
        "passive_consequence": passive_consequence,
        "pain_root_cause": f"{process_breakpoint}，导致{passive_consequence}",
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
        {"related_system_candidates": [{"name": item, "confidence": 0.6, "reason": "检索候选"} for item in retrieved_context.get("matched_systems", [])]},
        user_input,
        warnings=[],
    )

    warnings: list[str] = []
    related_systems = filter_supported_related_systems(
        related_systems,
        {"related_system_candidates": [{"name": item, "confidence": 0.6, "reason": "检索候选"} for item in retrieved_context.get("matched_systems", [])]},
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
            "pain_root_cause": cleanup_sentence(diagnosis.get("pain_root_cause")) or f"{process_breakpoint}，导致{passive_consequence}",
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
    for term in re.split(r"[\s,，、/／;；]+", object_text):
        if len(term) >= 2 and term in text:
            return True
    return False


def vague_without_specifics(text: str, business_object: str) -> bool:
    cleaned = cleanup_sentence(text)
    vague_terms = [
        "提升效率",
        "降低风险",
        "减少人工",
        "及时处理",
        "关键数据",
        "相关人员",
        "当前业务场景",
        "自动同步关键信息",
    ]
    if not any(term in cleaned for term in vague_terms):
        return False
    return not has_business_object(cleaned, business_object)


def is_vague_behavior(values: list[str], business_object: str) -> bool:
    if not values:
        return True
    vague_labels = {"自动提醒", "自动同步", "看数据", "自动流转", "自动生成", "自动处理"}
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
    vague_business_objects = {"业务问题", "需求", "系统功能", "功能", "待确认业务对象", "业务对象"}

    if not business_object or business_object in vague_business_objects:
        issues.append("business_object 为空或过于泛化")
    current_manual_process = cleanup_sentence(result.get("current_manual_process"))
    if not current_manual_process or current_manual_process in ["人工处理", "人工跟进", "效率低"] or len(current_manual_process) < 10:
        issues.append("current_manual_process 没有说明具体人工做法")
    process_breakpoint = cleanup_sentence(result.get("process_breakpoint"))
    if not process_breakpoint or process_breakpoint in ["流程卡点", "流程不顺"] or len(process_breakpoint) < 8:
        issues.append("process_breakpoint 没有说明具体流程断点")
    passive_consequence = cleanup_sentence(result.get("passive_consequence"))
    if not passive_consequence or passive_consequence in ["影响效率", "降低风险"] or len(passive_consequence) < 8:
        issues.append("passive_consequence 没有说明具体被动后果")
    if is_vague_behavior(ensure_string_list(result.get("minimum_system_behavior")), business_object):
        issues.append("minimum_system_behavior 没有说明系统替代哪一步人工动作")

    rewritten = cleanup_sentence(result.get("rewritten_request"))
    if not has_business_object(rewritten, business_object):
        issues.append("rewritten_request 没有包含具体业务对象")
    if len(rewritten) > 80:
        issues.append("rewritten_request 超过 80 字")

    suggested = cleanup_sentence(result.get("suggested_request"))
    has_trigger = any(keyword in suggested for keyword in ["当", "发生", "后", "如果", "在"])
    has_action = any(action in suggested for action in ensure_string_list(result.get("system_actions")) + ["系统", "自动", "提醒", "展示", "跟踪", "生成", "同步"])
    has_value = any(keyword in suggested for keyword in ["避免", "防止", "减少", "提前", "闭环", "影响"])
    if not (has_trigger and has_action and has_business_object(suggested, business_object) and has_value):
        issues.append("suggested_request 没有同时包含触发条件、系统动作、处理对象和业务价值")
    if len(suggested) > 120:
        issues.append("suggested_request 超过 120 字")

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
        issues.append("输出包含空泛表达但没有绑定具体业务对象、动作和后果")
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
                "识别业务对象",
                "还原当前人工做法",
                "判断流程断点",
                "说明被动后果",
                "给出系统最小替代动作",
                "生成前台短版结果",
            ],
            "response_schema": {
                "original_request": "string",
                "business_domain": "string",
                "business_object": "string",
                "related_systems": ["string；仅用户原话明确提到系统名才填入，否则留空"],
                "candidate_systems": ["string；根据业务域推断的候选系统，可包含未在原话明确出现但需要确认的系统"],
                "pain_points": ["string"],
                "system_actions": ["string"],
                "target_users": ["string"],
                "current_manual_process": "string；必须具体说明人工做法",
                "process_breakpoint": "string；必须具体说明断点",
                "passive_consequence": "string；必须具体说明被动后果",
                "minimum_system_behavior": ["string；说明系统替代哪一步人工动作"],
                "source_evidence": ["string；保留原话中的关键证据短语，如只能去问、开会才查、漏催"],
                "real_intent": "string <= 120 chars",
                "rewritten_request": "string <= 80 chars",
                "suggested_request": "string <= 120 chars",
                "confirmation_options": {
                    "affected_roles": ["2-8字短标签"],
                    "focus_points": ["2-8字短标签"],
                    "system_expectations": ["2-8字短标签"],
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
                "上一次结果过于泛化。请基于原始需求和检索到的业务上下文，补充具体业务对象、"
                "当前人工做法、流程断点、被动后果和系统最小动作。不要增加无依据系统名，"
                "不要输出空泛表达，只返回 JSON。"
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
    if report["output"] != "待业务确认":
        items.append({"stage": "Output", "title": shorten_focus_text(report["output"])})
    if monitor_items:
        items.append({"stage": "Monitor", "title": shorten_focus_text(monitor_items[0])})
    return items[:8]


def build_process_map_from_structured_report(structured_report: dict) -> dict:
    report = ensure_structured_report(structured_report)
    return {
        "nodes": [
            {"label": "触发前提", "value": report["input"]},
            {"label": "活动名称", "value": report["what"]},
            {"label": "执行步骤", "value": " → ".join(ensure_string_list(report["how"]))},
            {"label": "需求背景", "value": report["why"]},
            {"label": "所属流程", "value": report["where"]},
            {"label": "主导方", "value": report["who"]},
            {"label": "最终输出", "value": report["output"]},
            {"label": "监控指标", "value": " · ".join(ensure_string_list(report["monitor"]))},
        ]
    }


def build_deep_response(analysis: dict, fast_analysis: dict | None = None) -> dict:
    diagnosis = analysis.get("diagnosis") if isinstance(analysis.get("diagnosis"), dict) else {}
    fast = fast_analysis if isinstance(fast_analysis, dict) else {}
    structured_report = ensure_structured_report(analysis.get("structured_report"))
    business_object = cleanup_sentence(
        diagnosis.get("business_object")
        or fast.get("business_object")
        or "待业务确认"
    )
    current_manual_process = cleanup_sentence(
        diagnosis.get("current_manual_process")
        or diagnosis.get("current_process")
        or fast.get("current_manual_process")
        or "待业务确认"
    )
    passive_consequence = cleanup_sentence(
        diagnosis.get("passive_consequence")
        or fast.get("passive_consequence")
        or diagnosis.get("business_impact")
        or "待业务确认"
    )
    minimum_system_behavior = (
        ensure_string_list(diagnosis.get("minimum_system_behavior"))
        or ensure_string_list(fast.get("minimum_system_behavior"))
        or ensure_string_list(diagnosis.get("desired_system_behavior"))
    )
    return {
        "diagnosis": {
            "business_object": business_object,
            "current_process": cleanup_sentence(diagnosis.get("current_process")) or "待业务确认",
            "current_manual_process": current_manual_process,
            "manual_actions": ensure_string_list(diagnosis.get("manual_actions")),
            "process_breakpoint": cleanup_sentence(diagnosis.get("process_breakpoint")) or "待业务确认",
            "passive_consequence": passive_consequence,
            "pain_root_cause": cleanup_sentence(diagnosis.get("pain_root_cause")) or "待业务确认",
            "business_impact": cleanup_sentence(diagnosis.get("business_impact")) or "待业务确认",
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
        "待业务确认",
        "提升效率",
        "降低风险",
        "提高效率",
        "减少风险",
        "效率低",
        "风险高",
        "人工多",
        "流程优化",
        "业务处理不顺畅",
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
            issues.append(f"出现无依据系统名：{system_name}")

    for pattern, label in [
        (r"\d+\s*%", "百分比指标"),
        (r"\d+\s*(?:人天|小时|天|分钟)", "具体投入或时效数字"),
    ]:
        for match in re.findall(pattern, generated_text):
            matched_text = match
            if matched_text and matched_text not in original_request:
                issues.append(f"出现无依据{label}：{matched_text}")
    return unique_keep_order(issues)


def quality_check_analysis(result: dict) -> dict:
    diagnosis = result.get("diagnosis") if isinstance(result.get("diagnosis"), dict) else {}
    reasons: list[str] = []
    original_request = normalize_text(result.get("original_request"))

    if is_generic_text(diagnosis.get("current_process"), 10):
        reasons.append("diagnosis.current_process 为空或太泛")
    if not ensure_string_list(diagnosis.get("manual_actions")):
        reasons.append("diagnosis.manual_actions 为空")
    if is_generic_text(diagnosis.get("process_breakpoint"), 8):
        reasons.append("diagnosis.process_breakpoint 为空或太泛")
    if is_generic_text(diagnosis.get("pain_root_cause"), 12):
        reasons.append("diagnosis.pain_root_cause 只写了泛词")
    if is_generic_text(diagnosis.get("business_impact"), 12):
        reasons.append("diagnosis.business_impact 为空或太泛")
    if not ensure_string_list(diagnosis.get("desired_system_behavior")):
        reasons.append("diagnosis.desired_system_behavior 为空")
    if not ensure_string_list(diagnosis.get("source_evidence")):
        reasons.append("diagnosis.source_evidence 为空，未保留原话证据")

    rewritten = cleanup_sentence(result.get("rewritten_request"))
    if len(rewritten) < 18 or not any(action in rewritten for action in context_names("system_actions")):
        reasons.append("rewritten_request 缺少系统动作、对象或业务价值")

    suggested = cleanup_sentence(result.get("suggested_request"))
    if len(suggested) > 120:
        reasons.append("suggested_request 超过 120 字")

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
    cleaned = base.rstrip("。；; ")
    if not cleaned:
        return f"{label}：{join_items(missing)}。"
    return f"{cleaned}；{label}：{join_items(missing)}。"


def selection_phrase(values: list[str], fallback: str = "") -> str:
    cleaned = normalize_selected_values(values)
    if not cleaned:
        return fallback
    if len(cleaned) == 1:
        return cleaned[0]
    return "、".join(cleaned[:-1]) + "和" + cleaned[-1]


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

    users_text = selection_phrase(roles, join_items(ensure_string_list(diagnosis.get("target_users")), "相关人员"))
    focus_text = selection_phrase(focus_points, cleanup_sentence(diagnosis.get("process_breakpoint")) or "关键风险")
    action_text = selection_phrase(expectations)
    if action_text:
        action_clause = f"通过{action_text}"
    else:
        action_clause = build_action_clause(ensure_string_list(diagnosis.get("desired_system_behavior")))
    domain_text = business_domain_label(business_domain) if business_domain else "当前业务"

    if roles or focus_points or expectations:
        sentence = (
            f"生产或业务状态变化后，系统应在{domain_text}场景下帮助{users_text}"
            f"{action_clause}，及时处理{focus_text}，减少人工追问和风险遗漏。"
        )
        return limit_text(sentence, max_len)

    return limit_text(base_text, max_len)


def has_appended_selection_list(text: str) -> bool:
    cleaned = normalize_text(text)
    return any(marker in cleaned for marker in ["重点关注：", "系统期望：", "面向对象：", "主要使用方：", "输出围绕："])


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
        structured_report["input"] = f"围绕{selection_phrase(focus_points)}触发分析或提醒"
        structured_report["what"] = f"处理{selection_phrase(focus_points)}"
    if expectations:
        structured_report["output"] = f"形成{selection_phrase(expectations)}后的处理结果"
        if focus_points:
            structured_report["what"] = f"通过{selection_phrase(expectations)}处理{selection_phrase(focus_points)}"
        else:
            structured_report["what"] = f"实现{selection_phrase(expectations)}"

    how_steps = ensure_string_list(structured_report.get("how"))
    if roles or focus_points or expectations:
        focus_text = selection_phrase(focus_points, "已确认的关键风险")
        expectation_text = selection_phrase(expectations, "系统动作")
        role_text = selection_phrase(roles, "相关人员")
        integrated_step = f"系统围绕{focus_text}{expectation_text}，并推送给{role_text}处理。"
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
            "howmuch": normalize_text(structured_report.get("howmuch")) or mock["structured_report"].get("howmuch") or "待业务确认",
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
                "必须包含具体 current_process，不要只写待确认或流程优化",
                "必须列出 manual_actions；如果用户未明说，也要基于上下文标注为合理推断",
                "必须列出 source_evidence；从原话保留关键证据短语，不要只写推断结论",
                "必须指出 process_breakpoint、pain_root_cause、business_impact",
                "desired_system_behavior 必须说明系统替代哪些人工动作",
                "related_systems 只放用户原话明确提到的系统；candidate_systems 放候选系统",
                "suggested_request 不超过 120 字",
                "confirmation_options 是给业务人员快速点选的按钮，每项必须是 2-8 个字的短标签",
                "confirmation_options 必须针对当前原始需求动态生成，不要输出完整问句，不要写“是否需要...”",
                "不要增加无依据系统名、指标、人天、百分比",
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
                    "affected_roles": ["2-8字短标签，如：计划、采购、车间"],
                    "focus_points": ["2-8字短标签，如：晚发现、范围不清、靠人问"],
                    "system_expectations": ["2-8字短标签，如：分析影响、推送待办、跟踪闭环"],
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
                "上一次输出过于泛化，请基于原始需求和 retrieved_context 补充具体的当前处理方式、"
                "人工动作、流程断点、痛点根因、业务影响和系统替代动作。不要增加无依据事实。"
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
                "如果 scenario_answers 不为空，必须优先把这些业务补充自然融合进 refined_request。",
                "不要把 scenario_answers 机械罗列在句尾，要转成一句完整可提交需求。",
                "仍需确认的数据源、口径、拦截规则或责任人要保留到 uncertain_items。",
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
    if any(keyword in text for keyword in ["库存", "仓库", "缺货", "账实", "可用库存", "下单"]):
        return "inventory"
    if any(keyword in text for keyword in ["BOM", "图纸", "版本", "变更", "试产", "物料影响"]):
        return "bom"
    if any(keyword in text for keyword in ["订单", "发货", "交付", "经销商", "客户催", "交期"]):
        return "order_delivery"
    return "generic"


def build_solution_fallback(user_input: str, analysis_result: dict, settings: dict | None = None, reference_summary: str = "") -> dict:
    settings = settings if isinstance(settings, dict) else {}
    base = analysis_result if isinstance(analysis_result, dict) else {}
    scenario = infer_solution_scenario(user_input, base)
    diagnosis = base.get("diagnosis") if isinstance(base.get("diagnosis"), dict) else {}
    business_object = cleanup_sentence(base.get("business_object") or diagnosis.get("business_object")) or "当前业务对象"
    suggested = cleanup_sentence(base.get("suggested_request") or base.get("rewritten_request") or user_input)
    pending = ensure_string_list(base.get("uncertain_items")) or ensure_string_list(diagnosis.get("uncertain_items"))

    if scenario == "inventory":
        solution = {
            "executive_summary": "建议建设“下单前库存可用性校验与缺货预警能力”：整合库存、订单占用和差异状态，在业务下单前校验可用库存，并对缺货或账实差异形成提醒与核查闭环。",
            "entry_point": "业务下单入口 / 销售订单创建页面",
            "data_systems": "WMS库存、ERP/SAP库存账、订单占用、预留库存、出入库流水",
            "modules": ["下单前可用库存校验", "库存不足提醒或拦截规则", "账实差异展示", "仓库核查任务生成", "异常责任人通知与闭环跟踪", "库存校验日志和查询报表"],
            "stages": [
                {"name": "阶段1", "description": "确认库存口径、数据源、提醒或拦截规则。"},
                {"name": "阶段2", "description": "梳理 WMS/ERP 库存字段与可用库存计算逻辑。"},
                {"name": "阶段3", "description": "实现下单前校验、缺货提醒和差异展示。"},
                {"name": "阶段4", "description": "选择仓库或业务线试点，跟踪误报和漏报。"},
            ],
            "risks": ["库存数据本身不准时，单纯前端提醒效果有限。", "WMS 与 ERP 同步时延会影响可用库存判断。", "直接拦截下单可能影响紧急订单，需要设计例外流程。", "账实差异责任人和关闭标准需要先确认。"],
            "confirmations": pending or ["库存口径是总库存还是可用库存？", "缺货时提醒、拦截还是允许提交但标记风险？", "库存数据以哪个系统为准？"],
        }
    elif scenario == "bom":
        solution = {
            "executive_summary": "建议建设“BOM/图纸变更影响识别与下游确认能力”：在版本变更后自动识别受影响物料、订单、库存和生产计划，并推动采购、生产等责任方确认闭环。",
            "entry_point": "BOM/图纸版本变更发布节点",
            "data_systems": "PLM、ERP/SAP、采购订单、生产计划、库存数据",
            "modules": ["变更影响范围识别", "新旧版本差异展示", "受影响物料清单", "采购/生产确认待办", "版本一致性校验", "变更处理闭环看板"],
            "stages": [
                {"name": "阶段1", "description": "确认变更触发点和影响对象范围。"},
                {"name": "阶段2", "description": "梳理 PLM、ERP、采购和生产数据映射关系。"},
                {"name": "阶段3", "description": "实现影响识别、差异展示和确认待办。"},
                {"name": "阶段4", "description": "试点关键产品线，优化影响规则。"},
            ],
            "risks": ["BOM层级和替代料规则复杂，影响范围规则需业务确认。", "图纸与BOM版本如果不同步，会影响识别准确性。", "待办过多可能造成信息噪音，需要分级提醒。"],
            "confirmations": pending or ["变更发布的权威触发点在哪里？", "需要识别哪些下游对象？", "哪些角色必须确认变更影响？"],
        }
    elif scenario == "order_delivery":
        solution = {
            "executive_summary": "建议建设“订单交付进度可视化与风险预警能力”：集中展示订单从签订、排产、库存齐套、发货到签收的状态，并对延期、缺货和责任节点停滞进行提醒。",
            "entry_point": "销售订单 / 经销商订单跟踪入口",
            "data_systems": "订单系统、ERP/SAP、WMS、MES/计划系统、物流状态",
            "modules": ["订单全链路状态看板", "发货与物流状态同步", "延期/缺货预警", "责任人待办生成", "客户反馈口径输出", "异常关闭跟踪"],
            "stages": [
                {"name": "阶段1", "description": "确认订单关键节点和责任部门。"},
                {"name": "阶段2", "description": "打通订单、计划、仓库和物流状态。"},
                {"name": "阶段3", "description": "实现进度看板、风险预警和待办推送。"},
                {"name": "阶段4", "description": "按业务线试点，校验状态准确性和提醒有效性。"},
            ],
            "risks": ["跨系统状态口径可能不一致，需要先定义主口径。", "客户可见信息和内部处理信息需要权限隔离。", "预警阈值过松或过紧都会影响使用体验。"],
            "confirmations": pending or ["订单关键状态节点如何定义？", "哪个系统是订单状态主口径？", "异常提醒对象和升级规则是什么？"],
        }
    else:
        solution = {
            "executive_summary": f"建议先按“最小可行方案”推进：围绕{business_object}的当前业务断点，明确触发条件、数据来源、责任人和闭环标准，再建设提醒、展示、待办和跟踪能力。",
            "entry_point": "当前业务操作入口",
            "data_systems": "业务主数据、状态数据、责任人数据、处理结果数据",
            "modules": ["业务状态集中展示", "异常识别和提醒", "责任人待办", "处理结果跟踪", "管理查询报表"],
            "stages": [
                {"name": "阶段1", "description": "确认业务对象、触发条件和成功标准。"},
                {"name": "阶段2", "description": "梳理数据来源和系统承载边界。"},
                {"name": "阶段3", "description": "实现最小闭环功能并试点。"},
                {"name": "阶段4", "description": "根据试点反馈扩展规则和场景。"},
            ],
            "risks": ["需求边界不清会导致方案过大。", "数据源和责任人未确认会影响落地。", "需要区分系统功能问题和流程管理问题。"],
            "confirmations": pending or ["触发条件是什么？", "数据来源来自哪个系统？", "责任人和关闭标准是什么？"],
        }

    solution.update(
        {
            "scenario": scenario,
            "known_request": suggested,
            "settings": settings,
            "reference_summary": reference_summary or "当前未接入外部搜索，方案基于需求诊断与内置业务场景模板生成。",
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
                stages.append({"name": name or f"阶段{len(stages)+1}", "description": description or "待补充"})
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
                    result.setdefault("warnings", []).append(f"LLM retry 失败：{retry_exc}")
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
        return jsonify({"error": "user_input 不能为空"}), 400

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
                    result["warnings"].append(f"快速模式 retry 失败：{retry_exc}")
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
        return jsonify({"error": "user_input 不能为空"}), 400

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
        return jsonify({"error": "user_input 不能为空"}), 400

    result = run_full_analysis(user_input)
    return jsonify(result)


@app.post("/api/refine")
def api_refine() -> object:
    payload = request.get_json(silent=True) or {}
    user_input = normalize_text(payload.get("user_input"))
    analysis_result = payload.get("analysis_result") if isinstance(payload.get("analysis_result"), dict) else {}
    selected_options = payload.get("selected_options") if isinstance(payload.get("selected_options"), dict) else {}

    if not user_input:
        return jsonify({"error": "user_input 不能为空"}), 400

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
        return jsonify({"error": "user_input 不能为空"}), 400

    reference_summary = ""
    if settings.get("web_search"):
        reference_summary = "已选择联网搜索；当前后端未配置搜索服务，先基于需求诊断和内置经验生成方案草案。"

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




