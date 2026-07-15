# 正式產出地圖

MedPaper Assistant 不把所有任務都塞進 IMRaD。Canonical registry 定義 13 種 output profiles，每一種有自己的 writing order、concept prerequisites、hook applicability 與 constraints。

![Thirteen output profiles](../assets/wiki-output-landscape.svg){ loading=lazy }

## 選擇 profile

```mermaid
flowchart TD
    Start([預期交付物]) --> ProjectDoc{專案文件？}
    ProjectDoc -->|研究尚未執行| Proposal[Research proposal]
    ProjectDoc -->|專案已完成| Closeout[Project closeout report]
    ProjectDoc -->|否| Synthesis{整合既有證據？}
    Synthesis -->|可重現檢索| Sys[Systematic review]
    Synthesis -->|統計合併| Meta[Meta-analysis]
    Synthesis -->|敘事整合| Narrative[Narrative review]
    Synthesis -->|否| Empirical{有原始資料/病例？}
    Empirical -->|完整研究| Original[Original research]
    Empirical -->|短篇結果| Letter[Research letter]
    Empirical -->|單一病例| Case[Case report]
    Empirical -->|會議格式| Conf[Conference paper]
    Empirical -->|學位成果| Thesis[Thesis / dissertation]
    Empirical -->|否| Audience{主要情境？}
    Audience -->|課程/學生研究| Student[Student paper]
    Audience -->|評論/通訊| Corr[Letter / correspondence]
    Audience -->|repository-first| Preprint[arXiv / preprint]
```

## 四個 family

| Family                   | Profiles                                            | 主要差異                                             |
| ------------------------ | --------------------------------------------------- | ---------------------------------------------------- |
| Empirical / clinical     | original、research letter、case、conference、thesis | Results 客觀性、效果量、N 值、方法時態               |
| Evidence synthesis       | systematic、meta-analysis、narrative                | search strategy、selection、heterogeneity、synthesis |
| Project documents        | proposal、closeout                                  | 未來式 objectives vs 已完成 deliverables/outcomes    |
| Educational / positional | student paper、correspondence、preprint             | audience、篇幅、repository metadata、scope           |

## Profile 如何驅動系統

```mermaid
flowchart LR
    Profile[Selected profile] --> Order[Writing order]
    Profile --> Concept[Concept requirements]
    Profile --> Template[Concept template]
    Profile --> Hooks[Applicable hooks]
    Profile --> Constraints[Domain constraints]
    Order & Concept & Template --> Draft[Draft workflow]
    Hooks & Constraints --> Quality[Quality result]
    Draft & Quality --> Export[Formal output]
```

例如 proposal 不應被迫提供已完成 Results；closeout 不應用 novelty 分數取代 deliverable accountability；conference 與 thesis 仍屬 empirical family，應執行資料與效果量 hooks。

## Concept gate 差異

```mermaid
flowchart TB
    Validate[Concept validation] --> Common[Core required sections]
    Validate --> Specific[Profile-specific sections]
    Validate --> Novelty{Profile requires novelty?}
    Novelty -->|yes| Score[Novelty rounds + threshold]
    Novelty -->|no| Skip[Auditable skip]
    Common & Specific & Score & Skip --> Ready{Ready for target section?}
```

Validation cache 包含 enabled validation flags，避免先做 structure-only 檢查後，完整驗證錯誤命中舊 cache。

## 13 profiles

1. Original research
2. Systematic review
3. Meta-analysis
4. Case report
5. Research letter
6. Narrative review
7. Letter / correspondence
8. Research proposal
9. Project closeout report
10. Student paper
11. Conference paper
12. Thesis / dissertation
13. arXiv / repository preprint

每一種 profile 的 section、必要內容與 integrity rules 詳見 [13 種產出規格](../harness/output-profiles.md)。

!!! note "不同格式，不同 gate；不是不同誠信標準"

    學生小論文篇幅可以較短，proposal 可以沒有 Results，但所有輸出仍不能捏造資料、誤用引用或把範文當成證據。
