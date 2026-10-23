"""把 tag-normalizer 的歸併提議合併進跨批次標籤字典 library/tags.json，只接受新增。

用法：uv run scripts/merge_tags.py reviews/<slug> [--library library]
讀 reviews/<slug>/tag-proposals.json，寫回 <library>/tags.json，並寫 reviews/<slug>/tag-merge-report.json。
字典由本人與 agent 共用：agent 只能新增類別、或替 agent 建的類別加同義詞；
已在字典裡的寫法、本人管理（source=user）的類別一律拒絕，本人的修改不會被 agent 改回去。
"""
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


def merge(library, proposals):
    """回傳 (新字典, 接受清單, 拒絕清單)；不修改傳入的 library。"""
    tags = {
        name: {**entry, "synonyms": list(entry.get("synonyms", []))}
        for name, entry in library.get("tags", {}).items()
    }
    known = {name.casefold() for name in tags} | {s.casefold() for e in tags.values() for s in e["synonyms"]}
    accepted, rejected = [], []
    for proposal in proposals:
        raw = (proposal.get("raw") or "").strip()
        canonical = (proposal.get("canonical") or "").strip()
        reason = _rejection(tags, known, raw, canonical, proposal.get("new"))
        if reason:
            rejected.append({**proposal, "rejected": reason})
            continue
        if proposal.get("new") is True:
            tags[canonical] = {"synonyms": [] if raw.casefold() == canonical.casefold() else [raw], "source": "agent"}
            known.add(canonical.casefold())
        else:
            tags[canonical]["synonyms"].append(raw)
        known.add(raw.casefold())
        accepted.append(proposal)
    return {"tags": tags}, accepted, rejected


def main(argv=None):
    args = _parse_args(argv)
    review = Path(args.review_dir)
    proposals_path = review / "tag-proposals.json"
    if not proposals_path.exists():
        print(f"找不到 {proposals_path}", file=sys.stderr)
        return 1
    library_dir = Path(args.library)
    library_path = library_dir / "tags.json"
    library = json.loads(library_path.read_text(encoding="utf-8")) if library_path.exists() else {"tags": {}}
    proposals = json.loads(proposals_path.read_text(encoding="utf-8")).get("proposals", [])

    tags, accepted, rejected = merge(library, proposals)

    if accepted:
        library_dir.mkdir(parents=True, exist_ok=True)
        _write_atomic(library_path, json.dumps(tags, ensure_ascii=False, indent=2) + "\n")
    report = {"accepted": accepted, "rejected": rejected}
    (review / "tag-merge-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"接受 {len(accepted)}、拒絕 {len(rejected)}")
    for item in rejected:
        print(f"- 拒絕 {item.get('raw')} → {item.get('canonical')}：{item['rejected']}")
    return 0


def _rejection(tags, known, raw, canonical, new):
    if not raw or not canonical:
        return "raw 或 canonical 是空的"
    if raw.casefold() in known:
        return "這個寫法已在字典裡"
    if new is True:
        return "標成新類別，但類別名已在字典裡" if canonical.casefold() in known else None
    if canonical not in tags:
        return "標成歸入既有類別，但字典沒有這個類別"
    if tags[canonical].get("source") != "agent":
        return "本人管理的類別，不由 agent 擴充"
    return None


def _write_atomic(path, text):
    """先寫同目錄的暫存檔再 os.replace，避免寫到一半留下壞掉的字典。"""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="把標籤歸併提議只增不改地併入標籤字典")
    parser.add_argument("review_dir")
    parser.add_argument("--library", default="library")
    return parser.parse_args(argv)


if __name__ == "__main__":
    sys.exit(main())
