"""FlowEngine — v2 (完整實作)

* 兩個 I/O function ✅  
    - `_load_schedule_from_db()`
    - `_save_schedule_to_db()`
* `handle()` 會：
    1. 若記憶體中沒有 session → 先從 DB 載入
    2. 每一次 state 有變動都呼叫 `_save_schedule_to_db()`
    3. 流程結束時把兩欄位設回 NULL

> ★ 不改動 utils.database 任何程式碼；只呼叫 `fetch` / `update` 方法。
"""

from __future__ import annotations

import json
import utils.database as db
from utils.knowledge_base import KnowledgeBase
from service.intention.base import Intention
from service.knowledge_flow import (
    get_main_intent,
    get_non_schedule_steps,
    get_data_by_link,
    get_data_by_link_database, 
)
from service.phase1.base import FinalPromptGenerator_flowEngine, llm_step_checker


class FlowEngine:
    """多步驟 non‑schedule 流程的狀態機。"""

    # ───────────────────────── internal data class ──────────────────────────

    class SessionState:
        def __init__(self):
            self.current_intent: str | None = None
            self.steps: list[dict] = []
            self.step_index: int = 0
            self.history: list[str] = []  # e.g. "User:... | AI:..."

    # ─────────────────────────────────────────────────────────────────────────

    def __init__(self):
        self.kb = KnowledgeBase()
        self.intention = Intention()
        self.generator = FinalPromptGenerator_flowEngine()
        self.sessions: dict[str, FlowEngine.SessionState] = {}

        # DB 連線（沿用 utils.database 的 MySQLManager）
        self.sql = db.MySQLManager(False)

        # intent → schedule_topic 名稱對照表（避免字面不一致導致找不到流程）
        self.intent_to_schedule: dict[str, str] = {
            "加好友途徑質疑流程": "加好友途徑質疑",
            # 其他需要轉換的 intent 可在此補充
        }

    # ──────────────────────────────── public API ────────────────────────────

    def handle(self, uid: str, user_input: str) -> tuple[str | None, bool]:
        """核心：處理一輪使用者輸入，返回 (reply, in_flow)。"""

        # 0-a 使用 llm_step_checker 套用在「退出流程判斷」
        if uid in self.sessions and self.sessions[uid].current_intent:
            exit_flag, exit_reason = llm_step_checker(
                user_input=user_input,
                ai_reply="",
                step_name="退出詢問",
                step_content="偵測使用者是否想結束/取消目前流程。",
                extra_data="None",
                history=" | ".join(self.sessions[uid].history) or "None",
            )
            if exit_reason == "EXIT_FLOW":
                self.sessions.pop(uid, None)
                self._save_schedule_to_db(uid, None, None)
                return None, False

        # 0) 若記憶體沒有，嘗試從 DB 還原
        if uid not in self.sessions:
            sch, stage = self._load_schedule_from_db(uid)
            if sch:
                s = FlowEngine.SessionState()
                s.current_intent = sch.get("intent")
                s.steps = sch.get("steps", [])
                s.step_index = stage or 0
                self.sessions[uid] = s

        # 確保 session 物件存在
        s = self.sessions.setdefault(uid, FlowEngine.SessionState())

        # 1) 尚未在流程中 — 嘗試根據最新輸入啟動
        if not s.current_intent:
            rough = self.intention.roughLabel(user_input)
            s.current_intent = get_main_intent([rough])
            # 將意圖名稱映射到 knowledge.csv 中的 schedule topic
            schedule_topic = self.intent_to_schedule.get(s.current_intent, s.current_intent)
            s.steps = get_non_schedule_steps(self.kb, schedule_topic)
            s.step_index = 0
            s.history.clear()

            if not s.steps:  # 沒找到流程 → 不啟動
                s.current_intent = None
                self._save_schedule_to_db(uid, None, None)
                return None, False

            # 新流程啟動 → 立即持久化
            self._save_schedule_to_db(
                uid,
                {"intent": s.current_intent, "steps": s.steps},
                s.step_index,
            )

        # 2) 如果流程已完成（保險起見）
        if s.step_index >= len(s.steps):
            self.sessions.pop(uid, None)
            self._save_schedule_to_db(uid, None, None)
            return None, False

        # 3) 解析當前步驟內容
        step = s.steps[s.step_index]
        step_name = step.get("step", step.get("Topic", ""))
        step_content = step["content"]
        extra = ""
        # if step.get("link") and step["link"] != "[]":
        #     if step["link"] == "['event_info']":
        #         extra = get_data_by_link_database(self.sql, step["link"])
        #     else:
        #         rows = get_data_by_link(self.kb, step["link"])
        #         if rows:
        #             extra = "\n".join(f"{d['Topic']}: {d['content']}" for d in rows)
        # print("extra:", extra)

        # 4) 連續檢查：跳過所有已完成的步驟
        final_reply = None
        in_flow = True
        while s.step_index < len(s.steps):
            step = s.steps[s.step_index]
            step_name = step.get("step", step.get("Topic", ""))
            step_content = step["content"]
            if step.get("link") and step["link"] != "[]":
                if step["link"] == "['event_info']":
                    extra = get_data_by_link_database(self.sql, step["link"])
                else:
                    rows = get_data_by_link(self.kb, step["link"])
                    if rows:
                        extra = "\n".join(f"{d['Topic']}: {d['content']}" for d in rows)
            print("extra:", extra)
            print("step:",s.step_index)

            done, reason = llm_step_checker(
                user_input=user_input,
                ai_reply="",
                step_name=step_name,
                step_content=step_content,
                extra_data=extra or "None",
                history=" | ".join(s.history) or "None",
            )
            
            if done:
                # 如果跳完最後一步，流程結束
                if s.step_index >= len(s.steps)-1:
                    final_reply = self.generator.generate_final_prompt(
                        user_input=user_input,
                        main_intent=s.current_intent,
                        step_name=step_name,
                        step_content=step_content,
                        history=" | ".join(s.history) or "None",
                        extra_data=extra or "None",
                        fail_reason=reason,
                    )
                    in_flow = True
                    self._save_schedule_to_db(uid, None, None)
                    self.sessions.pop(uid, None)
                    break
                s.step_index += 1
                continue
            else:
                final_reply = self.generator.generate_final_prompt(
                    user_input=user_input,
                    main_intent=s.current_intent,
                    step_name=step_name,
                    step_content=step_content,
                    history=" | ".join(s.history) or "None",
                    extra_data=extra or "None",
                    fail_reason=reason,
                )
                s.history.append(f"User:{user_input} | AI:{final_reply}")
                self._save_schedule_to_db(
                    uid,
                    {"intent": s.current_intent, "steps": s.steps},
                    s.step_index,
                )
                break

        return final_reply, in_flow

    # ──────────────────────────────── DB I/O ────────────────────────────────

    def _load_schedule_from_db(self, uid: str) -> tuple[dict | None, int | None]:
        """讀取 user.schedule / user.stage。

        任何 NULL 或空值都視為沒有流程資料。"""
        uid=uid.strip("'")
        row = self.sql.fetch("user", ["schedule", "stage"], f"user_id = '{uid}'")
        if not row:
            return None, None

        sch_raw, stage_raw = row[0]
        if sch_raw in (None, "null", "NULL", ""):
            return None, None

        try:
            schedule_dict = json.loads(sch_raw)
        except Exception:
            schedule_dict = None
        try:
            stage = int(stage_raw) if stage_raw is not None else None
        except ValueError:
            stage = None
        return schedule_dict, stage

    def _save_schedule_to_db(self, uid: str, schedule_dict: dict | None, stage: int | None):
        """把 schedule / stage 寫回 user 表。

        * 若 schedule_dict 為 None → schedule, stage 改 NULL
        * 其餘情況用 json.dumps() 儲存
        """
        uid=uid.strip("'")
        if schedule_dict is None:
            self.sql.update(
                "user",
                {"schedule": "NULL", "stage": "NULL"},
                {"user_id": "'"+uid+"'"},
            )
            return

        json_str = json.dumps(schedule_dict, ensure_ascii=False)
        # rudimentary escape of single quotes for SQL literal
        json_str_escaped = json_str.replace("'", "\\'")
        print("[saved]: " + json_str_escaped,"stage: " +str(stage))
        self.sql.update(
            "user",
            {"schedule": f"'{json_str_escaped}'", "stage": stage if stage is not None else "NULL"},
            {"user_id": "'"+uid+"'"},
        )
