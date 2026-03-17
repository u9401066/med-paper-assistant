# Anesthesiology Journal Profiles (Top 20)

> 自動生成於 2026-03-17。使用前請務必對照各期刊最新投稿指南 URL 驗證。

## 使用方式

### 搭配 Copilot（推薦）

直接告訴 Copilot 你的目標期刊，例如：

- 「我要投 BJA」
- 「幫我套用 Anesthesiology 的設定」
- 「用 RAPM 的投稿格式」

Copilot 會自動讀取對應的 YAML 設定檔並產生 `journal-profile.yaml`。

### 手動複製

```bash
# 複製 profile 到專案
cp templates/journal-profiles/bja.yaml projects/my-project/journal-profile.yaml

# 或用 MCP tool (Phase 0)
# setup_project_interactive 會引導選擇期刊
```

## 期刊列表

| #   | 期刊                                                                                                                                                                   | 縮寫                       | 全文字數 | 摘要字數 | 參考文獻上限 | 驗證狀態 |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- | -------- | -------- | ------------ | -------- |
| 1   | [British Journal of Anaesthesia](https://academic.oup.com/bja/pages/general-instructions)                                                                              | Br J Anaesth               | 3000     | 250      | 30           | 📋       |
| 2   | [Anesthesiology](https://pubs.asahq.org/anesthesiology/pages/instructions-for-authors)                                                                                 | Anesthesiology             | 4500     | 350      | 50           | 📋       |
| 3   | [Anaesthesia](https://anaesthesia.onlinelibrary.wiley.com/hub/journal/13652044/homepage/ForAuthors)                                                                    | Anaesthesia                | 3000     | 200      | 30           | 📋       |
| 4   | [Regional Anesthesia & Pain Medicine](https://rapm.bmj.com/pages/authors/)                                                                                             | Reg Anesth Pain Med        | 3000     | 250      | 30           | ✅       |
| 5   | [Anesthesia & Analgesia](https://journals.lww.com/anesthesia-analgesia/pages/informationforauthors.aspx)                                                               | Anesth Analg               | 3000     | 400      | 50           | 📋       |
| 6   | [European Journal of Anaesthesiology](http://edmgr.ovid.com/eja/accounts/ifauth.htm)                                                                                   | Eur J Anaesthesiol         | 3500     | 300      | 40           | ✅       |
| 7   | [Canadian Journal of Anesthesia / Journal canadien d'anesthésie](https://www.springer.com/journal/12630/submission-guidelines)                                         | Can J Anaesth              | 3000     | 250      | 40           | 📋       |
| 8   | [Journal of Clinical Anesthesia](https://www.sciencedirect.com/journal/journal-of-clinical-anesthesia/publish/guide-for-authors)                                       | J Clin Anesth              | 3000     | 250      | 40           | 📋       |
| 9   | [Current Opinion in Anaesthesiology](https://journals.lww.com/co-anesthesiology/pages/informationforauthors.aspx)                                                      | Curr Opin Anaesthesiol     | 3500     | 200      | 50           | 📋       |
| 10  | [Minerva Anestesiologica](https://www.minervamedica.it/en/journals/minerva-anestesiologica/notice-to-authors.php)                                                      | Minerva Anestesiol         | 4000     | 250      | 40           | 📋       |
| 11  | [Journal of Neurosurgical Anesthesiology](https://journals.lww.com/jnsa/pages/informationforauthors.aspx)                                                              | J Neurosurg Anesthesiol    | 3000     | 250      | 35           | 📋       |
| 12  | [Acta Anaesthesiologica Scandinavica](https://onlinelibrary.wiley.com/page/journal/13996576/homepage/forauthors.html)                                                  | Acta Anaesthesiol Scand    | 3000     | 250      | 30           | 📋       |
| 13  | [Paediatric Anaesthesia](https://onlinelibrary.wiley.com/page/journal/14609592/homepage/forauthors.html)                                                               | Paediatr Anaesth           | 3000     | 250      | 40           | 📋       |
| 14  | [Journal of Cardiothoracic and Vascular Anesthesia](https://www.sciencedirect.com/journal/journal-of-cardiothoracic-and-vascular-anesthesia/publish/guide-for-authors) | J Cardiothorac Vasc Anesth | 3000     | 250      | 40           | 📋       |
| 15  | [International Journal of Obstetric Anesthesia](https://www.sciencedirect.com/journal/international-journal-of-obstetric-anesthesia/publish/guide-for-authors)         | Int J Obstet Anesth        | 3000     | 250      | 30           | 📋       |
| 16  | [BMC Anesthesiology](https://bmcanesthesiol.biomedcentral.com/submission-guidelines)                                                                                   | BMC Anesthesiol            | 5000     | 350      | 60           | 📋       |
| 17  | [Journal of Anesthesia](https://www.springer.com/journal/540/submission-guidelines)                                                                                    | J Anesth                   | 3000     | 250      | 30           | 📋       |
| 18  | [Anaesthesia and Intensive Care](https://journals.sagepub.com/author-instructions/AIC)                                                                                 | Anaesth Intensive Care     | 3000     | 200      | 30           | 📋       |
| 19  | [Korean Journal of Anesthesiology](https://ekja.org/authors/authors.php)                                                                                               | Korean J Anesthesiol       | 3000     | 250      | 30           | ✅       |
| 20  | [Brazilian Journal of Anesthesiology](https://www.sciencedirect.com/journal/brazilian-journal-of-anesthesiology/publish/guide-for-authors)                             | Braz J Anesthesiol         | 3000     | 250      | 30           | 📋       |

## 驗證狀態

- ✅ = 已從官方投稿指南網頁驗證 (2026-03)
- 📋 = 基於已知投稿指南編譯，建議使用前驗證

## 資料欄位說明

每個 `.yaml` 檔案包含以下結構（與 `journal-profile.template.yaml` 相容）：

- `journal` — 期刊基本資訊（名稱、ISSN、投稿系統 URL、指南 URL）
- `authors` — 空白（專案特定）
- `paper` — 論文類型和章節結構
- `word_limits` — 字數限制
- `abstract` — 摘要格式（結構化/非結構化、標題）
- `assets` — 圖表限制和格式要求
- `references` — 引用格式和數量限制（含各論文類型）
- `required_documents` — 必要附件
- `reporting_guidelines` — 報告指引要求
- `other_article_types` — 其他文章類型的限制
- `pipeline` — MedPaper 系統預設設定

## 貢獻

如果某期刊的指南有更新，請修改對應的 `.yaml` 檔案或更新 `scripts/generate_journal_profiles.py` 中的資料源。
