import uuid
from typing import List
from datetime import datetime

class Memory:
    def __init__(
        self,
        user_id: str,
        text: str,
        embedding,
        importance: float,
        frequency: int,
        memory_id: str = None,
        topic_id: str = None,
        created_at: datetime = None,
        last_called_from_memory: datetime = None
    ):
        self.id = memory_id if memory_id else str(uuid.uuid4())
        self.user_id = user_id
        self.text = text
        self.embedding = embedding
        self.importance = importance
        self.frequency = frequency

        # 這裡的 created_at、last_called 都是 Python 端的時間
        # 預設用 datetime.now()，也可使用 datetime.utcnow()
        now = datetime.now()
        self.created_at = created_at if created_at else now
        self.last_called_from_memory = last_called_from_memory if last_called_from_memory else now

        self.topic_id = topic_id

    def __repr__(self):
        return f"<Memory id={self.id[0:]}, user_id={self.user_id}, text={self.text[:10]}...>"


class TopicMemory:
    def __init__(
        self,
        user_id: str,
        topic_name: str,
        topic_embedding=None,
        topic_id: str = None,
        created_at: datetime = None
    ):
        self.id = topic_id if topic_id else str(uuid.uuid4())
        self.user_id = user_id
        self.topic_name = topic_name
        self.topic_embedding = topic_embedding
        self.created_at = created_at if created_at else datetime.now()

    def __repr__(self):
        return f"<TopicMemory id={self.id[0:]}, user_id={self.user_id}, topic={self.topic_name}>"
    
