# phd-lit-pipeline

用 Claude Code 跑的文獻研究流水線：一個主 session 派多個 subagent 分頭讀論文，結構化欄位由兩個 agent 各自萃取再比對，敘述欄位附逐字引文和頁碼由腳本核對。本人只在定方向、看缺口、寫作時出手。

設計說明（流程圖、卡片欄位、可以調的旋鈕）：https://claude.ai/artifact/9eK6XFknn3W16zyWLtcYcd

## 流程

| 階段 | skill | 誰 | 產出 |
|---|---|---|---|
| 停 1 定方向 | `/lit-protocol` | 本人在場 | `protocol.md`、`papers.json`、`text/` |
| 萃取 | `/lit-extract` | 自動 | `cards/<key>/card.md`、`matrix.md` |
| 參考文獻合併 | `/lit-refs` | 自動 | `references.csv`、`papers.bib` |
| 對照提案 | `/lit-gaps` | 自動 | `proposal-gaps.md` |
| 停 2 看缺口 | `/lit-gaps` 最後一步 | 本人在場 | — |
| 撰寫 | `/lit-draft` | 本人在場 | `drafts/<文件>/` |

停 1 點頭後，萃取到對照提案會一路自動跑完。

## 開始用

這個 repo 就是你整個研究的工作區：每一批文獻是 `reviews/` 底下一個資料夾，`CONTEXT.md` 與 `docs/adr/` 跨所有 review 累積。Claude Code 要在 repo 根目錄開，才會載入 `CLAUDE.md` 與 `.claude/skills/`。

1. 在 GitHub 建一個空的 private repo（不要用 fork 或 template：fork 不能設成私有，template 跟這裡沒有共同歷史，之後拉不到更新），然後：

   ```bash
   git clone https://github.com/Darren901/phd-lit-pipeline.git my-phd
   cd my-phd
   git remote rename origin upstream
   git remote add origin <你的 private repo 網址>
   git push -u origin main
   ```

2. 裝 [uv](https://docs.astral.sh/uv/)，在 repo 根目錄跑 `uv run pytest`，看到全部通過。
3. 在 repo 根目錄開 Claude Code，打 `/lit-protocol`。缺哪些 skill，它會列出來並給安裝指令（完整清單在 `CLAUDE.md`「開工檢查」）。
4. 照它的指示把 PDF 放進 `reviews/<slug>/pdfs/`、提案放進 `proposal/`。

之後這裡有更新時：`git pull upstream main`。你改過的 skill 跟更新撞到時，照一般 merge 衝突處理。

## 怎麼確保沒抄錯

- 每則關於論文的陳述都附 `"原文" [key, p.N]`，`scripts/quote_check.py` 逐則核對原文那一頁真的有這句。
- 結構化欄位（研究類型、資料來源、樣本數、方法、數字）由兩個不同模型的 agent 各自萃取，`scripts/diff_cards.py` 比對，對不上才派 judge 回原文裁決。
- 參考文獻由一個 agent 逐筆抽、另一個 agent 數條數，每筆原文都要在論文裡找得到。
- 缺口清單寫完，另派一個 agent 專門試著推翻每一條。

## 資料夾

```
CONTEXT.md              研究脈絡：名詞、研究問題（停 1 時建立）
docs/adr/               決策紀錄（需要時建立）
proposal/               你的提案原稿，agent 不改
reviews/<slug>/
  protocol.md           停 1 定案
  papers.json           本批論文的 key、id、標題
  state.json            跑到哪一段
  progress.md           做過什麼、驗證數字、例外
  pdfs/                 論文 PDF（不進版控）
  text/                 論文與提案的純文字（引文從這裡抄）
  cards/<key>/          a.json、b.json、diff.json、judge.json、card.md
  matrix.md             比較矩陣
  refs/                 每篇的參考文獻
  references.csv        合併去重後的參考文獻
  papers.bib            本批論文的 BibTeX
  proposal-gaps.md      對照提案的缺口
  drafts/               草稿
scripts/                輔助腳本（uv run scripts/<name>.py）
.claude/skills/         流水線各段的 skill
```
