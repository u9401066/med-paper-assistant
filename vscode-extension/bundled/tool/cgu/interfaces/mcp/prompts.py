"""Prompts: condensed skills for clients that do not load skills."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from cgu.interfaces.mcp.deps import Deps

FRAME_AUDIT = """請對下面的問題做「框架稽核」，目的是找出值得質疑的假設，而不是替使用者決定。
問題：{problem}
步驟：
1. cgu_session(action="open", topic=問題)；cgu_frame(action="create", problem=問題, ...) 寫出目前的目標、利害關係人、假設、準則。
2. cgu_diverge(action="typical_set") 取得典型答案，回交為 kind=typical。
3. cgu_frame(action="operate", operator="explicate", target="assumption") 把典型答案背後的假設浮現出來，commit 回去。
4. cgu_frame(action="doubt")：只在有僵局、異常、衝突、高風險或使用者要求時才啟動；用 0–1 估計四個因子，取前幾名，列出尚未檢驗的承重假設。
5. 對挑出的假設用 negate／bracket 等算子產生子框架；改寫目標、利害關係人、準則前必須取得使用者同意。
6. 每個子框架都要附至少一個具體點子（cgu_ideas(action="add", frame_id=...)），沒有具體點子的框架不算數。
護欄：候選假設需使用者確認；不替使用者決定誰重要；停損——再質疑也不會改變決策就停。"""

ANTI_TYPICAL_SESSION = """請用「反典型」流程為下面的主題發想。
主題：{topic}
步驟：
1. cgu_session(action="open", topic=主題)。
2. cgu_diverge(action="typical_set")：先不看任何素材，寫下最直覺的回答，回交為 kind=typical。
3. cgu_diverge(action="anti_typical")：避開 avoid 清單，每個點子標明改寫了哪個框架元素，回交為 kind=candidate。
4. cgu_ideas(action="measure")：看相對 typical 的相似度與多樣性；若 embedding.semantic=false，只當作詞面重疊。
5. cgu_judge(action="plan")、record、rank：用至少兩個不同家族的模型做 AB／BA 比較。
6. 讓使用者決定，並用 cgu_feedback(action="record") 記下採用、修改或放棄。
護欄：不要自己給新穎度分數；先由使用者自己想過再看你的點子，避免錨定。"""

MAIEUTIC_SESSION = """請用助產式提問陪使用者釐清下面的主題，你提問，使用者回答。
主題：{topic}
步驟：
1. cgu_session(action="open", topic=主題)。
2. 先請使用者說出他目前的想法，不要先給答案。
3. 準備 3–5 個候選問題；每個用 cgu_question_gate(action="check", question=..., decision_context=...) 取得工單並作答，再 record。
4. 只問通過的問題（決策相關、可操作、承重、非口頭）；non_typical 只是加分。
5. 使用者的回答若揭露假設，用 cgu_frame(action="create") 或 operate 記下來。
護欄：一次只問一題；不要把使用者的答案改寫成你的版本；沒有決策情境的問題不要問。"""

PAIRWISE_JUDGE = """請對 session {session_id} 的點子做成對比較。
步驟：
1. cgu_judge(action="plan", session_id=..., idea_ids=[...])，會得到每個配對的 AB 與 BA 兩張工單。
2. 每張工單用獨立 context 執行（最好交給不同家族的模型），依工單回交 cgu_judge(action="record")。
3. cgu_judge(action="rank")：回報 win_rate 與 Wilson 95% 區間、AB／BA 一致率、warnings，以及 Pareto 前緣。
護欄：win_rate 依賴評審，不是品質；一致率低表示評審受位置影響；準則不可通約時看前緣，不要加權成單一分數。"""


def register(server: MCPServer[Deps]) -> None:
    @server.prompt(name="frame_audit", description="框架稽核：浮現假設、啟動懷疑的經濟學。")
    def frame_audit(problem: str) -> str:
        return FRAME_AUDIT.format(problem=problem)

    @server.prompt(
        name="anti_typical_session", description="反典型發想：先列典型答案，再避開並量測。"
    )
    def anti_typical_session(topic: str) -> str:
        return ANTI_TYPICAL_SESSION.format(topic=topic)

    @server.prompt(name="maieutic_session", description="助產式提問：用提問閘門篩出值得問的問題。")
    def maieutic_session(topic: str) -> str:
        return MAIEUTIC_SESSION.format(topic=topic)

    @server.prompt(name="pairwise_judge", description="成對比較：位置交換、多家族評審、誠實排名。")
    def pairwise_judge(session_id: str) -> str:
        return PAIRWISE_JUDGE.format(session_id=session_id)
