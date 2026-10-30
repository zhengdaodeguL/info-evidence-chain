#!/usr/bin/env python3
"""Deterministic evidence-score helper; accepts one JSON object or a JSONL file."""
import argparse
import json
import sys
from pathlib import Path

SOURCE_SCORES = {"A1": 25, "P1": 25, "A2": 20, "B": 12, "C": 5}

def score(item):
    tier = item.get("source_tier")
    source_score = SOURCE_SCORES.get(tier, 0)
    locator_score = 25 if item.get("exact_locator") and item.get("effective_at_claim_time") else 15 if item.get("url") else 5 if item.get("summary_only") else 0
    cross_score = 25 if item.get("independent_crosscheck") else 15 if item.get("raw_material") else 5 if item.get("model_extraction_only") else 0
    verify_score = 25 if item.get("human_verified") and item.get("reproducible_formula") else 15 if item.get("human_verified") or item.get("reproducible_formula") else 5 if item.get("model_extraction_only") else 0
    total = source_score + locator_score + cross_score + verify_score
    claim_type = item.get("claim_type", "interpretive")
    gates = {
        "normative": bool(tier == "A1" and item.get("effective_at_claim_time") and item.get("exact_locator")),
        "observed": bool(item.get("raw_material") and item.get("human_verified")),
        "computed": bool(item.get("complete_inputs") and item.get("reproducible_formula")),
        "interpretive": bool(item.get("source_ids") and item.get("premises")),
    }
    gate_passed = gates.get(claim_type, False)
    conflict = bool(item.get("unresolved_conflict"))
    if conflict:
        level = "low"
    elif total >= 80 and gate_passed:
        level = "high"
    elif total >= 55:
        level = "medium"
    else:
        level = "low"
    reasons = [
        f"来源权威性 {source_score}/25",
        f"原文定位与版本 {locator_score}/25",
        f"交叉或原始材料 {cross_score}/25",
        f"人工核验与可复算 {verify_score}/25",
    ]
    gaps = []
    if not gate_passed:
        gaps.append(f"{claim_type} 硬闸门未通过")
    if conflict:
        gaps.append("存在未解决冲突")
    if not item.get("human_verified"):
        gaps.append("缺少人工核验")
    if claim_type == "computed" and not item.get("reproducible_formula"):
        gaps.append("缺少可复算公式")
    return {
        "score": total,
        "level": level,
        "gate_passed": gate_passed,
        "reasons": reasons,
        "gaps": gaps,
        "next_check": "回到原始材料并补齐缺失闸门" if gaps else "按抽样计划再次复核",
    }

def main():
    parser = argparse.ArgumentParser(description="计算可解释证据分数（不是概率）")
    parser.add_argument("input", nargs="?", help="JSON 文件；不填则从 stdin 读")
    args = parser.parse_args()
    raw = Path(args.input).read_text(encoding="utf-8") if args.input else sys.stdin.read()
    payload = json.loads(raw)
    if isinstance(payload, list):
        output = [score(item) for item in payload]
    else:
        output = score(payload)
    print(json.dumps(output, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()


