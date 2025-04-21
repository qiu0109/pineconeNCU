# tasks.py
from datetime import datetime
from redis import Redis
from rq import Queue
from utils.database.manager import MySQLManager
from service.Engagement.base import EngagementManager

# 1) 在檔案頂部「全域」建立 DB & EngagementManager
db_manager = MySQLManager(reset_database=False)  
eng_manager = EngagementManager()

# 2) 建立 Redis & RQ Queue 物件 
redis_conn = Redis(host='localhost', port=6379, db=0)
queue = Queue('my_queue', connection=redis_conn)

def rq_engagement_loss(user_id: str, msg_time_str: str):
    """
    在 RQ Worker 中被呼叫；但不需要重複建立 manager。
    直接使用全域 eng_manager 進行 engagement_loss。
    """
    print(f"[RQ] Start engagement_loss(user={user_id}) at {datetime.now()}")

    eng_manager.engagement_loss(user_id, datetime.now())
