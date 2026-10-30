#!/usr/bin/env python3
"""Deterministic evidence scoring for a JSON object or array; never a probability."""
import argparse
import json
import sys
from pathlib import Path

SOURCE_SCORES = {"A1": 25, "P1": 25, "A2": 20, "B": 12, "C": 5}
CHECK_METHODS = {
    "grounded", "quote_match", "extraction_agreement", "independent_source",
    "formula_recalculation", "scope_match", "version_match", "unit_check",
}
COMPARISON_METHODS = {"quote_match", "extraction_agreement"}


def _yes(item, key):
    """Do not let strings such as 'unknown' or 'false' satisfy a gate."""
    return item.get(key) is True


def _ids(value):
    if not isinstance(value, list):
        return set()
    return {entry for entry in value if isinstance(entry, str) and entry.strip()}


def _verification(item):
    """Check audit-link integrity, not the truth of remote pages or OCR itself."""
    known_refs = set()
    for key in ("source_ids", "record_ids", "screenshot_ids"):
        known_refs.update(_ids(item.get(key)))
    evidence = item.get("evidence", [])
    if isinstance(evidence, list):
        for entry in evidence:
            if not isinstance(entry, dict):
                continue
            evidence_id = entry.get("evidence_id")
            if isinstance(evidence_id, str) and evidence_id.strip() and any(
                entry.get(key) for key in ("path", "url", "local_copy_path", "image_path", "raw_text_path")
            ):
                known_refs.add(evidence_id)

    checks = item.get("verification_checks", [])
    if not isinstance(checks, list):
        return set(), [], ["verification_checks 必须是数组"], False, True
    accepted_ids, methods, problems, seen = [], set(), [], set()
    failed = unknown = False
    for index, check in enumerate(checks, 1):
        if not isinstance(check, dict):
            problems.append(f"核验记录 {index} 不是对象")
            unknown = True
            continue
        check_id = check.get("check_id")
        label = check_id if isinstance(check_id, str) and check_id.strip() else f"#{index}"
        method = check.get("method")
        refs = _ids(check.get("evidence_refs"))
        valid = True
        if not isinstance(check_id, str) or not check_id.strip() or check_id in seen:
            problems.append(f"核验 {label} 缺少唯一 check_id")
            valid = False
        else:
            seen.add(check_id)
        if not isinstance(method, str) or method not in CHECK_METHODS:
            problems.append(f"核验 {label} 的 method 未被支持")
            valid = False
        if not refs or not refs.issubset(known_refs):
            problems.append(f"核验 {label} 未引用已登记的证据 ID")
            valid = False
        if method == "extraction_agreement" and len(refs) < 2:
            problems.append(f"核验 {label} 的独立提取比对至少需要两份证据")
            valid = False
        if check.get("passed") is False:
            problems.append(f"核验 {label} 未通过")
            failed = True
        elif check.get("passed") is not True:
            problems.append(f"核验 {label} 结果未知")
            valid = False
        if valid and check.get("passed") is True:
            methods.add(method)
            accepted_ids.append(check_id)
        elif not failed or check.get("passed") is not False:
            unknown = True
    return methods, accepted_ids, problems, failed, unknown


def score(item):
    if not isinstance(item, dict):
        raise ValueError("每条主张必须是 JSON 对象")
    claim_type = item.get("claim_type", "interpretive")
    if not isinstance(claim_type, str):
        claim_type = "unknown"
    tier = item.get("source_tier")
    if not isinstance(tier, str):
        tier = None
    methods, accepted_ids, check_problems, failed_check, unknown_check = _verification(item)
    grounded = "grounded" in methods
    extraction_verified = grounded and bool(methods & COMPARISON_METHODS)
    formula_verified = grounded and "formula_recalculation" in methods
    human = _yes(item, "human_verified")
    raw = _yes(item, "raw_material")
    locator = _yes(item, "exact_locator")
    effective = _yes(item, "effective_at_claim_time")
    applicable = _yes(item, "scope_applicable")
    reproducible = _yes(item, "reproducible_formula")
    complete = _yes(item, "complete_inputs")
    auto_verified = (
        raw and locator and extraction_verified if claim_type in {"observed", "normative"}
        else complete and reproducible and formula_verified if claim_type == "computed"
        else False
    )

    source_score = SOURCE_SCORES.get(tier, 0)
    locator_score = 25 if locator and (claim_type != "normative" or effective) else 15 if item.get("url") else 5 if _yes(item, "summary_only") else 0
    cross_score = 25 if _yes(item, "independent_crosscheck") else 15 if raw else 5 if _yes(item, "model_extraction_only") else 0
    verify_score = 25 if auto_verified or human and reproducible else 15 if human or reproducible or grounded else 5 if _yes(item, "model_extraction_only") else 0
    total = source_score + locator_score + cross_score + verify_score

    gate_reasons = []
    if claim_type == "normative":
        if tier != "A1":
            gate_reasons.append("规范性主张缺少主管机构 A1 原文")
        if not effective:
            gate_reasons.append("未确认标准在主张时间点已生效")
        if not locator:
            gate_reasons.append("缺少精确条款定位")
        if not applicable:
            gate_reasons.append("未确认地区、对象和条件的适用范围")
        if _yes(item, "negative_search_only"):
            gate_reasons.append("查无条款只能说明检索结果，不能推出违法或不合规")
    elif claim_type == "observed":
        if not raw:
            gate_reasons.append("观察性主张缺少原始材料")
        if not human and not auto_verified:
            gate_reasons.append("观察字段尚未完成带证据的自动核验或人工核验")
    elif claim_type == "computed":
        if not complete or not reproducible:
            gate_reasons.append("计算主张缺少完整输入、单位或可复算公式")
    elif claim_type == "interpretive":
        if not _ids(item.get("source_ids")) or not item.get("premises"):
            gate_reasons.append("解释性主张缺少支撑来源或明确前提")
    else:
        gate_reasons.append("未知 claim_type")

    gate_passed = not gate_reasons
    conflict = _yes(item, "unresolved_conflict") or item.get("status") == "conflict"
    flag_keys = (
        "human_verified", "raw_material", "exact_locator", "effective_at_claim_time",
        "scope_applicable", "reproducible_formula", "complete_inputs", "independent_crosscheck",
        "summary_only", "model_extraction_only", "unresolved_conflict", "negative_search_only",
        "interpretation_disputed", "strong_allegation",
    )
    invalid_flags = [key for key in flag_keys if key in item and not isinstance(item[key], bool)]
    unknown = bool(item.get("unknown_fields")) or item.get("status") == "unknown" or unknown_check or bool(invalid_flags)
    review_reasons = list(gate_reasons)
    if conflict:
        review_reasons.append("存在未解决冲突，人工确认标记不能覆盖冲突")
    if unknown:
        review_reasons.append("存在未知字段或无法核实的核验记录")
    if invalid_flags:
        review_reasons.append("布尔字段结果未知或格式无效：" + ", ".join(invalid_flags))
    review_reasons.extend(check_problems)
    if _yes(item, "interpretation_disputed"):
        review_reasons.append("存在语义或适用解释争议")
    if _yes(item, "strong_allegation"):
        review_reasons.append("涉及违法、欺诈等强指控，需要专业复核")
    if not human and not auto_verified:
        review_reasons.append("尚无充分的自动核验记录；可补齐证据，无需默认全量人审")
    if claim_type == "interpretive" and not human:
        review_reasons.append("解释性结论需要人工确认推理前提与边界")

    review_reasons = list(dict.fromkeys(review_reasons))
    review_status = "needs_review" if review_reasons else "human_verified" if human else "auto_verified"
    if conflict or failed_check:
        level = "low"
    elif total >= 80 and gate_passed and review_status != "needs_review":
        level = "high"
    elif total >= 55:
        level = "medium"
    else:
        level = "low"

    return {
        "score": total,
        "level": level,
        "gate_passed": gate_passed,
        "review_status": review_status,
        "review_reasons": review_reasons,
        "accepted_check_ids": accepted_ids,
        "reasons": [
            f"来源权威性 {source_score}/25",
            f"原文定位与版本 {locator_score}/25",
            f"交叉或原始材料 {cross_score}/25",
            f"可追溯核验与可复算 {verify_score}/25",
        ],
        "gaps": review_reasons,
        "next_check": "只处理列出的异常、缺口或解释争议" if review_reasons else "归档自动核验记录；按项目计划抽样复查",
    }


def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="计算带自动核验记录的证据分数（不是概率）")
    parser.add_argument("input", nargs="?", help="JSON 对象或数组文件；不填则从 stdin 读")
    args = parser.parse_args()
    try:
        raw = Path(args.input).read_text(encoding="utf-8-sig") if args.input else sys.stdin.read()
        payload = json.loads(raw)
        output = [score(item) for item in payload] if isinstance(payload, list) else score(payload)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
