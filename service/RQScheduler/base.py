# base.py

from datetime import timedelta, datetime
from .tasks import queue, rq_engagement_loss

class RQScheduler:

    def __init__(self):
        self.user_jobs = {}
        self.queue = queue  # 從 tasks.py 引入的 queue

    def schedule_for_bot(self, user_id: str, msg_time: datetime):
        """
        Bot 傳完 => (訊息時間 + 30 分鐘) 時觸發 engagement_loss
        """
        self._delete_old_job_if_exists(user_id)

        # 要在 (msg_time + 30分) 執行
        scheduled_time = msg_time + timedelta(minutes=30)

        # 轉成字串，之後在 rq_engagement_loss 內可還原
        msg_time_str = msg_time.strftime("%Y-%m-%d %H:%M:%S")

        job = self.queue.enqueue_at(
            scheduled_time,         # 絕對時間
            rq_engagement_loss,     # 要執行的函式
            user_id,
            msg_time_str,
            result_ttl=0,
            delete_on_complete=True
        )
        self.user_jobs[user_id] = job.id
        print(f"[schedule_for_bot] user={user_id}, new_job_id={job.id}, scheduled_time={scheduled_time}")

    def schedule_for_user(self, user_id: str, msg_time: datetime):
        """
        User 傳完 => (訊息時間 + 60 分鐘) 時觸發 engagement_loss
        """
        self._delete_old_job_if_exists(user_id)

        scheduled_time = msg_time + timedelta(minutes=60)
        msg_time_str = msg_time.strftime("%Y-%m-%d %H:%M:%S")

        job = self.queue.enqueue_at(
            scheduled_time,
            rq_engagement_loss,
            user_id,
            msg_time_str,
            result_ttl=0,
            delete_on_complete=True
        )
        self.user_jobs[user_id] = job.id
        print(f"[schedule_for_user] user={user_id}, new_job_id={job.id}, scheduled_time={scheduled_time}")

    def _delete_old_job_if_exists(self, user_id: str):
        """
        若該 user_id 先前已排任務 => 先刪除
        """
        old_job_id = self.user_jobs.pop(user_id, None)
        if old_job_id:
            old_job = self.queue.fetch_job(old_job_id)
            if old_job:
                old_job.delete()
                print(f"  => Deleted old job_id={old_job_id} for user={user_id}")
