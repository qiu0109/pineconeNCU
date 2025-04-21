from ..model.gemini import Gemini
import os
import csv
import time
from .summarizer import (
    ConversationBuffer,
    Summarizer,
    need_topic_summary
)

from utils.database import MySQLManager


class MultiUserSummaryManager:
    """
    用來同時管理多個 user 的會話buffer以及摘要流程。
    每個 user_id 會有：
      - 一個 ConversationBuffer
      - 一個 partial_summaries 列表
    """
    
    def __init__(self, token_limit=250, model="gpt-4", temperature=0.0):
        self.token_limit = token_limit
        self.model = model
        self.temperature = temperature
        self.sql = MySQLManager()
        
        # 紀錄每個 user 的對話buffer: user_id -> ConversationBuffer
        self.user_buffers = {}
        # 紀錄每個 user 的多段小摘要: user_id -> list of partial summaries
        self.user_partial_summaries = {}
        self.user_summary_times = {}
        
        # Summarizer 用於生成小摘要 / 大摘要
        self.summarizer = Summarizer(model=self.model, temperature=self.temperature)
        
    def add_message(self, user_id, role, message, memory=""):
        """
        新增一則訊息到指定 user_id 的對話緩衝區。
        若該 user_id 尚未建立 buffer，就在此初始化。
        """
        if user_id not in self.user_buffers:
            self.user_buffers[user_id] = ConversationBuffer(token_limit=self.token_limit, model=self.model)
            self.user_partial_summaries[user_id] = []
            self.user_summary_times[user_id] = time.time()
            
        # 將訊息加入 buffer
        self.user_buffers[user_id].add_message(role, message)
        
        # 檢查是否需要「小摘要」
        return self._maybe_summarize(user_id, memory)

    def _maybe_summarize(self, user_id, memory):
        """
        檢查該 user 的 ConversationBuffer 是否超過 token_limit，若超過則做小摘要。
        然後檢查需不需要大摘要。
        """
        buffer = self.user_buffers[user_id]
        
        if buffer.should_summarize():
            # 取出整段對話文本
            conversation_text = buffer.get_conversation_text()
            small_summary = self.summarizer.summarize_chunk(conversation_text)
            print(f"[User {user_id}] 小摘要: {small_summary}")
            self._store_small_summary(user_id,small_summary)

            # 把這段小摘要存到 partial_summaries
            self.user_partial_summaries[user_id].append(small_summary)
            
            # 清空 buffer，等後續對話重新累積
            buffer.clear_buffer()
            
            # 接著檢查是否要做「大摘要」
            if need_topic_summary(self.user_partial_summaries[user_id], max_partial_count=4):
                # 更新時間差
                time_decay = time.time() - self.user_summary_times[user_id]/3600
                self.user_summary_times[user_id] = time.time()
                
                # 製造大摘要
                big_summary = self.summarizer.summarize_topic(self.user_partial_summaries[user_id])
                print(f"[User {user_id}] 大摘要: {big_summary}")

                mode = self.get_sql_hos(user_id)
                
                # 這邊示範：把大摘要印出或存到資料庫
                self._store_big_summary(user_id, big_summary)
                
                # 產生完大摘要後，就可以清空 partial_summaries 或保留視需求
                self.user_partial_summaries[user_id].clear()

                return {
                    'uid': user_id, 
                    'mode': mode, 
                    'memory': memory, 
                    'summary': big_summary, 
                    'time': self.user_summary_times[user_id],
                    'time_decay': time_decay
                }
            
        return None
    
    def get_sql_hos(self, uid: str):
        uid = uid.strip("'")
        table = "user"
        properties = ['hostility']
        condition = f"user_id = '{uid}'"
        hos = self.sql.fetch(table, properties, condition)[0][0]
        if hos==1:
            return "negative"
        else:
            return "positive"
    
    def _store_small_summary(self, user_id, small_summary):
        """
        把小摘要寫入 CSV 檔：
          summary/small_summary/<user_id>.csv
        一行一則小摘要。
        """
        folder_path = os.path.join("summary", "small_summary")
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, f"{user_id}.csv")
        
        # 以 append 模式打開檔案，寫入新的摘要
        with open(file_path, mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # 這裡僅示範直接把摘要放第一欄，可自行改成多欄結構
            writer.writerow([small_summary])

    def _store_big_summary(self, user_id, big_summary):
        """
        寫入大摘要到:
          summary/topic_summary/<user_id>.csv
        一行一則大摘要。
        """
        folder_path = os.path.join("summary", "topic_summary")
        os.makedirs(folder_path, exist_ok=True)
        
        file_path = os.path.join(folder_path, f"{user_id}.csv")
        
        with open(file_path, mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            # 這裡也可以加上其他資訊或時間戳
            writer.writerow([big_summary])
        
        print(f"[User {user_id}] 已將大摘要存入 {file_path}")

