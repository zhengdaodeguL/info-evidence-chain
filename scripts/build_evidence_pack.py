#!/usr/bin/env python3
"""Build a portable, offline evidence viewer from real browser captures."""
import argparse
import hashlib
import html
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote, urlsplit


def escape(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else hashlib.sha256(stream.read()).hexdigest()


def copy_asset(value, base, output, folder):
    source = Path(value)
    if not source.is_absolute():
        source = base / source
    source = source.resolve(strict=True)
    if not source.is_file():
        raise ValueError(f"Not a file: {source}")
    digest = file_hash(source)
    relative = Path(folder) / (digest + source.suffix.lower())
    target = output / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if file_hash(target) != digest:
            raise ValueError(f"Existing asset has different content: {target}")
    else:
        shutil.copyfile(source, target)
    return relative.as_posix(), digest


def build(manifest_path, output):
    payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    for key in ("conclusions", "limitations"):
        if key in payload and (not isinstance(payload[key], list) or any(not isinstance(value, str) for value in payload[key])):
            raise ValueError(f"{key} must be an array of strings")
    entries = payload.get("evidence", [])
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest.evidence must be a nonempty array")
    ids = [entry.get("evidence_id") for entry in entries]
    if any(not isinstance(value, str) or not value.strip() for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Each evidence_id must be a unique nonempty string")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be a new or empty directory; use a new run folder")
    # Validate input references before writing output.
    for entry in entries:
        status = entry.get("verification_status", "unverified")
        if status not in {"auto_verified", "human_verified", "needs_review", "unverified", "blocked"}:
            raise ValueError(f"Unknown verification_status: {status}")
        if not entry.get("screenshot_path"):
            raise ValueError(f"{entry['evidence_id']}: screenshot_path is required")
        for key in ("screenshot_path", "annotated_path", "annotations_path", "text_path"):
            if entry.get(key):
                source = Path(entry[key])
                if not source.is_absolute():
                    source = manifest_path.parent / source
                if not source.is_file():
                    raise ValueError(f"Missing {key}: {source}")
    output.mkdir(parents=True, exist_ok=True)
    cards = []
    counts = Counter()
    for entry in entries:
        hashes = {}
        for key, folder in (("screenshot_path", "raw"), ("annotated_path", "annotated"), ("annotations_path", "annotations"), ("text_path", "text")):
            if entry.get(key):
                entry[key], hashes[key] = copy_asset(entry[key], manifest_path.parent, output, folder)
        entry["sha256"] = hashes
        status = entry.get("verification_status", "unverified")
        counts[status] += 1
        source_url = str(entry.get("url", ""))
        source_link = f'<a href="{escape(source_url)}" target="_blank" rel="noreferrer">打开来源网页 ↗</a>' if urlsplit(source_url).scheme in {"http", "https"} else '<span>未提供可打开的来源 URL</span>'
        image_path = entry.get("annotated_path") or entry["screenshot_path"]
        links = [f'<a href="{quote(entry["screenshot_path"])}" target="_blank">原始截图</a>']
        for key, label in (("annotated_path", "标注大图"), ("annotations_path", "标注坐标"), ("text_path", "提取正文")):
            if entry.get(key):
                links.append(f'<a href="{quote(entry[key])}" target="_blank">{label}</a>')
        confidence = entry.get("confidence")
        confidence_text = "尚未评分" if confidence is None else json.dumps(confidence, ensure_ascii=False)
        cards.append(f'''<article class="card" data-search="{escape(json.dumps(entry, ensure_ascii=False))}">
<header><span class="id">{escape(entry['evidence_id'])}</span><span class="status {escape(status)}">{escape(status)}</span></header>
<h2>{escape(entry.get('title', entry['evidence_id']))}</h2>
<dl><dt>检索式</dt><dd>{escape(entry.get('query'))}</dd><dt>采集时间</dt><dd>{escape(entry.get('captured_at'))}</dd><dt>页面定位</dt><dd>{escape(entry.get('locator'))}</dd><dt>页面结果</dt><dd>{escape(entry.get('result_status', 'captured'))}</dd></dl>
<blockquote>{escape(entry.get('excerpt'))}</blockquote>
<p>{escape(entry.get('finding'))}</p>
<a class="image-link" href="{quote(image_path)}" target="_blank"><img src="{quote(image_path)}" alt="{escape(entry.get('title'))} 的证据截图" loading="lazy"></a>
<nav>{source_link} {' '.join(links)}</nav>
<details><summary>核验记录、置信度与文件校验值</summary><p>证据评分不等于概率；截图和标注本身不提升分数。</p><pre>{escape(confidence_text)}</pre><pre>{escape(json.dumps(entry.get('verification_checks', []), ensure_ascii=False, indent=2))}</pre><p>待办：{escape(entry.get('review_reason', '未记录'))}</p><pre>{escape(json.dumps(hashes, ensure_ascii=False, indent=2))}</pre></details></article>''')
    payload["summary"] = dict(counts)
    (output / "manifest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log = payload.get("search_log", [])
    log_table = ''.join(f'<tr><td>{escape(row.get("at"))}</td><td>{escape(row.get("action"))}</td><td>{escape(row.get("query"))}</td><td>{escape(row.get("outcome"))}</td></tr>' for row in log)
    overview = ''
    for key, label in (("conclusions", "本次结论"), ("limitations", "适用范围与限制")):
        if payload.get(key):
            overview += f'<h2>{label}</h2><ul>' + ''.join(f'<li>{escape(value)}</li>' for value in payload[key]) + '</ul>'
    pending = [entry for entry in entries if entry.get("verification_status", "unverified") in {"needs_review", "blocked", "unverified"}]
    overview += '<h2>待处理条目</h2>'
    if pending:
        overview += '<ul>' + ''.join(f'<li><strong>{escape(entry["evidence_id"])}</strong> {escape(entry.get("title"))}：{escape(entry.get("review_reason", "尚未完成核验"))}</li>' for entry in pending) + '</ul>'
    else:
        overview += '<p>当前记录没有待处理条目；这不表示已覆盖全部研究问题。</p>'
    if overview:
        overview = '<section class="intro">' + overview + '</section>'
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title><style>
:root{--blue:#1F5AA6;--ink:#1F2937;--muted:#6B7280;--bg:#F3F4F6;--green:#177245;--amber:#A15C00;--red:#A33A3A}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.7 system-ui,"Microsoft YaHei",sans-serif}main{max-width:1100px;margin:auto;padding:40px 24px}h1{font-size:32px;line-height:1.3;margin:8px 0 16px}h2{font-size:22px}a{color:var(--blue);text-underline-offset:3px}input{width:100%;padding:14px;border:1px solid #bac5d2;border-radius:8px;font:inherit;margin:20px 0}nav{display:flex;flex-wrap:wrap;gap:16px;padding:12px 0}header{display:flex;gap:12px;align-items:center}.card,.intro{background:white;border:1px solid #dce2ea;padding:24px;border-radius:12px;margin-bottom:24px;overflow-wrap:anywhere}.id{font-family:monospace;color:var(--blue);font-weight:bold}.status{font-size:14px;padding:2px 10px;border-radius:20px;background:#eef1f5}.auto_verified,.human_verified{color:var(--green);background:#eaf5ee}.needs_review{color:var(--amber);background:#fff4de}.blocked{color:var(--red);background:#fbeeed}dl{display:grid;grid-template-columns:96px 1fr;gap:6px 16px}dt{color:var(--muted)}dd{margin:0}blockquote{margin:16px 0;border-left:4px solid var(--blue);padding:10px 16px;background:#f5f8fc;white-space:pre-wrap}.image-link{display:block}img{display:block;max-width:100%;height:auto;border:1px solid #e4e8ed}summary{cursor:pointer;color:var(--blue);padding-top:8px}pre{font-size:14px;white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:10px;text-align:left;border-bottom:1px solid #dde3eb;vertical-align:top}.table-wrap{overflow:auto}.muted{color:var(--muted)}@media(max-width:600px){main{padding:20px 12px}.card,.intro{padding:18px}h1{font-size:26px}dl{grid-template-columns:1fr;gap:2px}dd{margin-bottom:10px}}
</style><main><section class="intro"><div class="muted">信息证据链 · 本地证据包</div><h1>__TITLE__</h1><p>__SCOPE__</p><p>__COUNTS__</p><p>先看原文和标注，再看核验记录。auto_verified 表示自动核验通过；不表示人工已审阅。</p><a href="manifest.json">下载完整证据清单 JSON</a></section><label for="filter">按检索式、来源、关键点或状态筛选</label><input id="filter" type="search" placeholder="输入 GB 28050、needs_review 等"><div id="cards">__CARDS__</div><section class="card"><h2>检索动作记录</h2><div class="table-wrap"><table><thead><tr><th>时间</th><th>动作</th><th>检索式</th><th>结果</th></tr></thead><tbody>__LOG__</tbody></table></div></section></main><script>document.getElementById('filter').addEventListener('input',function(){const q=this.value.toLocaleLowerCase();document.querySelectorAll('article.card').forEach(card=>{card.hidden=!card.dataset.search.toLocaleLowerCase().includes(q)})})</script></html>'''
    document = document.replace('<label for="filter">', '__OVERVIEW__<label for="filter">')
    values = {"__TITLE__": escape(payload.get("title", "浏览器检索证据")), "__SCOPE__": escape(payload.get("scope", "")), "__COUNTS__": escape(' · '.join(f'{key}: {count}' for key, count in counts.items())), "__CARDS__": '\n'.join(cards), "__LOG__": log_table, "__OVERVIEW__": overview}
    # One pass avoids interpreting replacement tokens embedded in evidence text.
    import re
    document = re.sub(r'__(?:TITLE|SCOPE|COUNTS|CARDS|LOG|OVERVIEW)__', lambda match: values[match.group()], document)
    (output / "index.html").write_text(document, encoding="utf-8")
    return {"index_path": str((output / "index.html").resolve()), "manifest_path": str((output / "manifest.json").resolve()), "counts": dict(counts)}


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="从真实截图和 manifest 生成离线证据索引；不替代核验")
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="新的或空的输出目录")
    args = parser.parse_args()
    try:
        result = build(args.manifest.resolve(), args.output.resolve())
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
