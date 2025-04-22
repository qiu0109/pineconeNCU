import math
import json
import statistics
from datetime import datetime

from .base import Memory, TopicMemory
from ..model import GPT4O,Gemini
from ..intention import Intention
from utils.database.manager import MySQLManager  # 你自己的 manager, 調整 import 路徑

class Memory_Manager:
    def __init__(self, topic_threshold=0.8, forget_threshold=0.1):
        self.gemini = Gemini()
        self.it = Intention()
        self.db = MySQLManager(reset_database=False)

        # 主題相似度門檻
        self.topic_similarity_threshold = topic_threshold
        # 遺忘分數門檻
        self.forget_threshold = forget_threshold

    def store_memory(
        self,
        user_id: str,
        text: str,
        importance: float,
        frequency: int = 1
    ):
        """
        將一段文字存入 memories 表格，並自動歸屬到對應的 topic:
        - 根據意圖偵測判斷 topic_name
        - 若找不到相似 topic，則新建 topic
        """
        # 計算 embedding
        embedding = self.gemini.call_embedding(text)
        user_id=user_id.strip("'")

        # 意圖偵測 (若無明顯意圖則不儲存)
        intention_result = self.it.multiIntention(text)
        print(intention_result)
        if not intention_result:
            print("[store_memory] 偵測不到意圖 => 捨棄")
            return None

        detected_topic_name = intention_result[0]['intention'].split(':')[0]
        if detected_topic_name == '無明顯意圖':
            print("[store_memory] 偵測到『無明顯意圖』 => 捨棄資料")
            return None

        # 找出最相似的 Topic (同一個 user_id)
        all_topics = self._fetch_all_topics(user_id=user_id)
        best_topic = None
        best_sim = -1

        for t in all_topics:
            sim = self.cosine_similarity(t.topic_embedding, embedding)
            if sim > best_sim:
                best_sim = sim
                best_topic = t

        topic_id = None
        if best_topic and best_sim >= self.topic_similarity_threshold:
            # 歸屬到最相似的 topic
            topic_id = best_topic.id
        else:
            # 嘗試找是否已有同名 topic
            existing_topic = self._find_topic_by_name(user_id, detected_topic_name)
            if existing_topic:
                topic_id = existing_topic.id
            else:
                # 新建一個 topic
                new_topic = TopicMemory(
                    user_id=user_id,
                    topic_name=detected_topic_name,
                    topic_embedding=self.gemini.call_embedding(detected_topic_name)
                )
                self._insert_topic(new_topic)
                topic_id = new_topic.id

        # 建立 Memory 物件
        mem_obj = Memory(
            user_id=user_id,
            text=text,
            embedding=embedding,
            importance=importance,
            frequency=frequency,
            topic_id=topic_id
        )

        # 寫進資料庫
        self._insert_memory(mem_obj)
        print(f"[store_memory] 已插入 memory: {mem_obj}")
        return mem_obj

    def retrieve_memory(self, user_id: str, query: str, top_k: int = 3, top_mem_per_topic: int = 3):
        """
        從資料庫中撈出該 user_id 下的 topic 與 memories，並選出最相近的主題及記憶。
        不再使用 decay_factor, 但仍保留 importance / frequency。
        """
        query_vec = self.gemini.call_embedding(query)
        user_id=user_id.strip("'")

        # 1) 抓該 user_id 的所有 Topics
        all_topics = self._fetch_all_topics(user_id)
        if not all_topics:
            return [], []

        # 2) 計算 topic 與 query 的相似度
        topic_with_sims = []
        for t in all_topics:
            sim = self.cosine_similarity(t.topic_embedding, query_vec)
            topic_with_sims.append((t, sim))
            print(f"[retrieve_memory] Topic={t.topic_name}, similarity={sim:.4f}")

        # 統計(可省略)
        sim_values = [x[1] for x in topic_with_sims]
        if sim_values:
            print("=== Topic-level Similarity ===")
            print(f"min={min(sim_values):.4f}, max={max(sim_values):.4f}, mean={statistics.mean(sim_values):.4f}")

        # 3) 取前 top_k
        topic_with_sims.sort(key=lambda x: x[1], reverse=True)
        selected_topics = [item[0] for item in topic_with_sims[:top_k]]

        now = datetime.now()
        final_memories = []

        # 4) 每個 topic 撈出所有 memory，計算綜合分數
        for top_topic in selected_topics:
            mem_list = self._fetch_memories_by_topic(top_topic.id)
            memory_scores = []

            for mem_obj in mem_list:
                mem_sim = self.cosine_similarity(mem_obj.embedding, query_vec)

                # 加權分數 (不再含 decay_factor)
                # 可依需求自行修改
                # 例如 importance 與 frequency 的影響:
                freq_factor = math.log1p(mem_obj.frequency + 1) ** 0.5

                # (b) 時間衰減
                def piecewise_decay(x):
                    """
                    先取ln
                    在 x<=8 幾乎不衰減, 
                    8<x<16 之間線性從1.0降到0.2,
                    x>=16 收斂到0.2。
                    """
                    x=math.log1p(x)
                    if x <= 8:
                        return 1.0
                    elif x >= 16:
                        return 0.2
                    else:
                        # 線性插值：從 1.0 到 0.2
                        return 1.0 - 0.8 * (x - 8) / (16 - 8)
            
                time_diff = (now - mem_obj.created_at).total_seconds()
                time_decay_factor = piecewise_decay(time_diff) 


                # (c) importance
                imp = mem_obj.importance

                # Step C: 綜合計算加權分數 (以下公式可依需求調整)
                weighted_score = (
                    imp
                    * freq_factor
                    * time_decay_factor
                )

                # 判斷是否需要遺忘
                if weighted_score < self.forget_threshold:
                    print(f"[forget_memory] memory={mem_obj}")
                    self._delete_memory(mem_obj.id)
                    continue

                # 最終排序分數
                final_score = mem_sim * weighted_score
                memory_scores.append((mem_obj, final_score))

            # 取前 top_mem_per_topic
            memory_scores.sort(key=lambda x: x[1], reverse=True)
            best_mem_in_topic = memory_scores[:top_mem_per_topic]
            final_memories.extend(best_mem_in_topic)

        # 5) 更新 frequency、last_called_from_memory
        for mem_obj, _ in final_memories:
            mem_obj.frequency += 1
            mem_obj.last_called_from_memory = now
            self._update_memory(mem_obj)

        return selected_topics, final_memories

    # ----------------- SQL 輔助方法 -----------------

    def _fetch_all_topics(self, user_id: str):
        condition = f"user_id = '{user_id}'"
        rows = self.db.fetch(table="topics", condition=condition)
        topics = []
        for r in rows:
            # 假設資料表欄位順序: id, user_id, topic_name, topic_embedding, created_at
            t = TopicMemory(
                topic_id=r[0],
                user_id=r[1],
                topic_name=r[2],
                topic_embedding=r[3],
                created_at=r[4]
            )
            topics.append(t)
        return topics

    def _find_topic_by_name(self, user_id: str, topic_name: str):
        condition = f"user_id = '{user_id}' AND topic_name = '{topic_name}'"
        rows = self.db.fetch(table="topics", condition=condition)
        if not rows:
            return None
        r = rows[0]
        t = TopicMemory(
            topic_id=r[0],
            user_id=r[1],
            topic_name=r[2],
            topic_embedding=r[3],
            created_at=r[4]
        )
        return t

    def _insert_topic(self, topic_obj: TopicMemory):
        properties = ["`id`", "`user_id`", "`topic_name`", "`topic_embedding`"]
        data = [
            f"'{topic_obj.id}'",
            f"'{topic_obj.user_id}'",
            f"'{topic_obj.topic_name}'",
            f"'{json.dumps(topic_obj.topic_embedding)}'"
        ]
        self.db.push(table="topics", data=data, properties=properties)

    def _fetch_memories_by_topic(self, topic_id: str):
        condition = f"topic_id = '{topic_id}'"
        rows = self.db.fetch(table="memories", condition=condition)
        mem_list = []
        for r in rows:
            # 欄位順序: id, user_id, text, embedding, importance, frequency,
            #           created_at, last_called_from_memory, topic_id
            mem_obj = Memory(
                memory_id=r[0],
                user_id=r[1],
                text=r[2],
                embedding=r[3],
                importance=r[4],
                frequency=r[5],
                created_at=r[6],
                last_called_from_memory=r[7],
                topic_id=r[8]
            )
            mem_list.append(mem_obj)
        return mem_list

    def _insert_memory(self, mem_obj: Memory):
        properties = [
            "`id`", "`user_id`", "`text`", "`embedding`",
            "`importance`", "`frequency`", "`topic_id`"
        ]
        data = [
            f"'{mem_obj.id}'",
            f"'{mem_obj.user_id}'",
            f"'{mem_obj.text}'",
            f"'{json.dumps(mem_obj.embedding)}'",
            f"{mem_obj.importance}",
            f"{mem_obj.frequency}",
            f"'{mem_obj.topic_id}'" if mem_obj.topic_id else "NULL"
        ]

        # created_at、last_called_from_memory 欄位在資料庫端有預設值
        # 如果你想手動指定，也可加上：
        # properties += ["`created_at`", "`last_called_from_memory`"]
        # data += [f"'{mem_obj.created_at}'", f"'{mem_obj.last_called_from_memory}'"]

        self.db.push(table="memories", data=data, properties=properties)

    def _update_memory(self, mem_obj: Memory):
        condition = {"id": f"'{mem_obj.id}'"}
        # 同樣，如果想更新 created_at，就得手動加上
        data = {
            "frequency": f"{mem_obj.frequency}",
            "last_called_from_memory": f"'{mem_obj.last_called_from_memory}'"
        }
        self.db.update(table="memories", data=data, condition=condition)

    def _delete_memory(self, mem_id: str):
        condition = f"id = '{mem_id}'"
        self.db.delete(table="memories", condition=condition)

    def cosine_similarity(self, vec1, vec2):
        # 如果 embedding 是 JSON string，要先 loads
        if isinstance(vec1, str):
            vec1 = json.loads(vec1)
        if isinstance(vec2, str):
            vec2 = json.loads(vec2)
        if not vec1 or not vec2:
            return 0.0

        dot = sum((v1 * v2) for v1, v2 in zip(vec1, vec2))
        norm1 = math.sqrt(sum((v1 * v1) for v1 in vec1))
        norm2 = math.sqrt(sum((v2 * v2) for v2 in vec2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
