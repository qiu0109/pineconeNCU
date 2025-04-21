import utils.database as db
import service.intention as it
from datetime import datetime, timedelta
import utils.random_reply as rr
import service.phase1 as p1
import time

# 保留摘要與記憶功能
from service.summarizer import MultiUserSummaryManager
from service.memory import Memory_Manager
from service.model import Gemini


class ModuleManager():

    def __init__(self):
        # 資料庫連線
        self.sql = db.MySQLManager(True)

        # 意圖分析
        self.intention = it.Intention()

        # 回覆時間模擬
        self.reply = rr.ExponentialGrowthSimulator()
        # 回應生成主體
        self.phase1 = p1.FinalPromptGenerator()
        # 保留摘要系統
        self.summary_manager = MultiUserSummaryManager(
            token_limit=120,   # 可依需求調整 token 門檻
            temperature=0.0
        )
        # 保留記憶系統
        self.memory_manager = Memory_Manager()


        # Buffer 設定 (可視需要保留或移除)
        self.buffer = 5
        self.last_received_times = {}
        self.pending_users = set()
        self.model = Gemini()


    def main(self) -> str:
        print("正在接收訊息...")
        while True:
            self.sql.sql.reconnect()

            # 檢查有無新訊息
            uids = self.check_update()
            current_time = time.time()

            # 檢查 buffer
            if uids:
                for uid in uids:
                    self.update_user_table(uid[0])
                    uid_str = f"'{uid[0]}'"

                    if uid_str not in self.last_received_times:
                        self.last_received_times[uid_str] = current_time
                        self.pending_users.add(uid_str)

                    elapsed_time = current_time - self.last_received_times[uid_str]
                    if elapsed_time < self.buffer:
                        print(f"用戶【{uid_str}】進入 buffer 模式（剩餘 {self.buffer - elapsed_time:.1f} 秒）...")
                        self.update_temp_dialogue(uid_str)
                        continue

            # 若超過 buffer 時間，開始處理訊息
            expired_users = []
            for uid_str in self.pending_users:
                elapsed_time = current_time - self.last_received_times[uid_str]
                if elapsed_time >= self.buffer:
                    expired_users.append(uid_str)

            for uid_str in expired_users:
                print(f"用戶【{uid_str}】的 Buffer 時間結束，開始處理訊息...")
                del self.last_received_times[uid_str]
                self.pending_users.remove(uid_str)
                self.process_user_message(uid_str)

            time.sleep(1)


    def process_user_message(self, uid):
        # 取得訊息
        messages, messages_id, reply_id, msg_timestamps = self.get_message(uid)
        history = self.get_history(uid)
        reply_message = self.get_reply_message(uid, reply_id)


        user_input = ' '.join(messages)
        print(f"\nmessage:【{user_input}】\nhistory:【{history}】\nreply:【{reply_message}】")


        # 取得記憶
        topic, mem = self.memory_manager.retrieve_memory(user_id=uid, query=user_input)
        topic_names = [t.topic_name for t in topic]
        topics = ','.join(topic_names)
        print("[retrieve_memory] 查詢結果, Topic:", topic, "Memory:", mem)

        # 意圖分析 
        intent = self.intention.multiIntention(user_input, reply_message)

        intent_discript = []
        for item in intent:
            intent_discript.append(item.get('intention'))

        # Summary Manager處理使用者訊息 
        user_summary = self.summary_manager.add_message(user_id=uid, role="user", message=user_input, memory=topics)
        if user_summary is not None:
            # 做摘要
            summary = user_summary['summary']
            # 視需求將其寫入 memory
            self.memory_manager.store_memory(user_id=uid, text=summary, importance=0.5, frequency=1 )

        # 單次生成回應 (不再多次檢查ReplyChecker)
        phase1_response = self.phase1.generate_final_prompt(
            user_input=user_input,
            context=[intent_discript],
            history=history,
            check_result=None,
            ph1_emotion_tone=None
        )
        print(f"\nAI 回應: {phase1_response}")

        # 可視需要進行 split_message 或 str 改寫
        answer = phase1_response

        # 處理 bot 端摘要
        bot_summary = self.summary_manager.add_message(user_id=uid, role="bot", message=answer, memory=topics)
        if bot_summary is not None:
            sum2 = bot_summary['summary']
            self.memory_manager.store_memory(user_id=uid, text=sum2, importance=0.5, frequency=1 )

        # 新增到 dialogue
        self.delete_temp_dialogue(uid)
        self.add_dialogue(uid, messages, messages_id, answer, reply_id)

        print("\n處理完畢繼續接受訊息...")
        return


    # ======= 下方輔助函式 =======
    def check_update(self, table="temp_dialogue"):
        data = self.sql.fetch(table, ["user_id"], "`state` = 'False' ")
        return data

    def update_user_table(self, uid: str):
        table = "user"
        data = [f"'{uid}'"]
        properties = ['user_id']
        condition = f"user_id = '{uid}'"
        appear = self.sql.fetch(table, properties, condition)
        if appear == []:
            self.sql.push(table, data, properties)

    def get_message(self, uid: str, table="temp_dialogue"):
        message, message_id, reply_id, timestamps = [], [], [], []
        data = self.sql.fetch(table, ["content", "message_id", "reply_id", "timestamp"], f"`user_id` = {uid}")
        for item in data:
            message.append(item[0])
            message_id.append(item[1])
            reply_id.append(item[2])
            timestamps.append(item[3])
        return message, message_id, reply_id, timestamps

    def get_reply_message(self, uid: str, reply_id: list, table="temp_dialogue"):
        answer = []
        for rpid in reply_id:
            if rpid:
                rid = f"'{rpid}'"
                data = self.sql.fetch(table, ["content"], f"`user_id` = {uid} AND `message_id` = {rid}")
                for item in data:
                    answer.append(item[0])
        return answer

    def get_history(self, uid: str, table="dialogue"):
        history_data = self.sql.fetch(table, ["role", "content"], f"user_id = {uid}", "dialogue_id DESC", size=50)
        if not history_data:
            return "尚未與系統對話"

        turns = 0
        temp_msg = ""
        last_10_history = []
        for i in range(len(history_data)):
            role = history_data[i][0]
            content = history_data[i][1]
            temp_msg += content + "<^>"
            if i == len(history_data) - 1 or role != history_data[i+1][0]:
                temp_msg = " ".join(temp_msg.strip().split("<^>")[::-1])
                if role == "assistant":
                    temp_msg = f"<使用者>{temp_msg}</使用者>"
                else:
                    temp_msg = f"<柔伊>{temp_msg}</柔伊>"
                last_10_history.append(temp_msg)
                temp_msg = ""
                turns += 1
                if turns == 10:
                    break
        last_10_history.reverse()
        return "\n".join(last_10_history)

    def update_temp_dialogue(self, uid: str, table="temp_dialogue"):
        self.sql.update(table, {"`state`": "'True'"}, {"user_id": uid})

    def delete_temp_dialogue(self, uid: str, table="temp_dialogue"):
        self.sql.delete(table, f"`user_id` = {uid} ")

    def add_dialogue(self, uid: str, assistants: list, assistant_id: list, bots: list,
                     assistant_reply_id: list = None, table="dialogue"):
        # 寫入使用者訊息
        for i in range(len(assistants)):
            content = f"'{assistants[i]}'"
            msg_id = f"'{assistant_id[i]}'"
            if assistant_reply_id[i]:
                rpid = f"'{assistant_reply_id[i]}'"
            else:
                rpid = "'None'"
            embedding = f"'{str(self.model.call_embedding(content))}'"
            data = [uid, "'assistant'", content, embedding, "'True'", msg_id, rpid]
            props = ["`user_id`", "`role`", "`content`", "`embedding_vector`", "`state`", "`message_id`", "`reply_id`"]
            self.sql.push(table, data, props)

        # 寫入機器人訊息
        receive_time = datetime.now()
        reply_time = self.reply.get_random_reply_time()
        reply_datetime = receive_time + timedelta(minutes=reply_time)

        for bot in bots:
            bot_str = f"'{bot}'"
            bot_embedding = f"'{str(self.model.call_embedding(bot_str))}'"
            # 加一點時間模擬
            reply_datetime += timedelta(seconds=int(len(bot)*1.3))
            data = [uid, "'bot'", bot_str, bot_embedding, "'False'", reply_datetime.strftime("'%Y-%m-%d %H:%M:%S'")]
            props = ["`user_id`", "`role`", "`content`", "`embedding_vector`", "`state`", "`reply_time`"]
            self.sql.push(table, data, props)

        # 如不需要互動度計算，eg.bot_send_message(uid, reply_datetime) 也可刪除


if __name__ == "__main__":
    try:
        print("🔧 啟動 ModuleManager 中...")
        mm = ModuleManager()
        print("✅ 初始化完成，進入主循環")
        mm.main()
    except Exception as e:
        print(f"❌ 啟動時發生錯誤：{e}")