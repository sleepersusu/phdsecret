---
name: lit-refs
description: 流水線的參考文獻合併段（自動）：每篇派 subagent 逐筆抽出參考文獻、另一個 subagent 獨立數條數，腳本核對每筆原文、去重並標出被幾篇引用，產出 references.csv；再用 citation-management 為本批論文產 papers.bib。完成後自動進入 lit-gaps。state.json 的 stage 是 auto:refs，或使用者說「合併參考文獻」時使用。
---

# lit-refs（參考文獻合併）

你是主控：只派工、跑腳本、看結果。自動段不問本人，例外記下來，到停 2 一次呈現。

## 0. 開工檢查

照 `CLAUDE.md`「開工檢查」的「參考文獻合併」列。

## 1. 抽與數

讀 `state.json`、`progress.md`、`protocol.md`（執行設定）、`papers.json`。`refs/<key>.json` 與 `refs/<key>.count.json` 都已存在的篇跳過。

一次處理執行設定指定的篇數。每篇**同時**派兩個 general-purpose subagent，彼此不知道對方的存在：

- 抽的（`model` 用乙模型）：「讀 `.claude/skills/lit-refs/ref-extractor.md` 照做。slug：`<slug>`，key：`<key>`。」
- 數的（`model` 用乙模型）：「讀 `.claude/skills/lit-refs/ref-counter.md` 照做。slug：`<slug>`，key：`<key>`。」

回 `BLOCKED` 的篇記成例外。

## 2. 合併

1. `uv run scripts/merge_refs.py reviews/<slug>`。
2. 看 `refs-report.json`：
   - `countMismatch` 或 `unverified` 有某篇 → 對那篇再派一次抽的 subagent，prompt 附上該篇的問題（筆數差多少、哪幾筆 raw 對不上）。重跑第 1 步。**只修一輪**，還是不過就記成例外。
3. `references.csv` 標 `uncertain` 的是模糊合併，不用修，停 2 讓本人看。

## 3. 本批論文的 BibTeX

撰寫時引用要用。用 `citation-management` 為 `papers.json` 的每篇產生 BibTeX，**citekey 一律用該篇的 key**，存成 `reviews/<slug>/papers.bib`。有 DOI 就用 DOI 驗證後設資料；查不到的記成例外，不要自己編欄位。

## 4. 收尾

1. `progress.md` 追加：原始筆數、去重後筆數、被 2 篇以上引用的筆數、模糊合併筆數、raw 對不上的筆數、條數不符的篇、BibTeX 成功與失敗篇數。
2. `state.json` 改成 `auto:gaps`，`note` 寫「參考文獻合併完成」，接著執行 `/lit-gaps`。
