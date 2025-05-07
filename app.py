from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage
import datetime
from utils.database import MySQLManager
import json,time,re
import os
from service.model import Gemini
from threading import Thread

# === LINE 金鑰 ===
CHANNEL_ACCESS_TOKEN = 'G8HOp50ZIU22bU/jMAUrd8p9wnghhMHHdmqir4RoRdSTwGRZ4M0LGZoUXBsxatq/tkF3p82y1/rZuRq7gpTrYrCuPBgkGzO3o20qeWEIctzC4EmWIEuImy1lXSh1mGSzinKvFt1n7hdPrE5fzO8XFwdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '4a24eeef056b6ccd9c2a0096422b831a'
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


sql = MySQLManager(False)
app = Flask(__name__)
gm = Gemini()

print("✅ Flask 啟動中...")

@app.route("/")
def home():
    return "✅ Flask 已啟動，請用 /callback 接 webhook"

def async_handle(body, signature):
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽名驗證失敗")

@app.route("/callback", methods=['POST'])
def callback():
    print("📥 有訊息打進 /callback！")
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        abort(400, "Invalid JSON")

    valid_events = []
    for event in payload.get("events", []):
        # 1. 官方「重送」旗標
        if event.get("deliveryContext", {}).get("isRedelivery", False):
            print("🔄  LINE 標記為重送，略過 eventId:", event.get("eventId"))
            continue
        valid_events.append(event)
    
    # 若沒有任何新事件就立即回 200
    if not valid_events:
        return "OK", 200

    # 開新線程處理，主線程立即回應 LINE
    Thread(target=async_handle, args=(body, signature)).start()

    return 'OK', 200

# @app.route("/callback", methods=['POST'])
# def callback():
#     print("📥 有訊息打進 /callback！")
#     signature = request.headers['X-Line-Signature']
#     body = request.get_data(as_text=True)
#     print("body:",body)
#     try:
#         handler.handle(body, signature)
#     except InvalidSignatureError:
#         print("❌ 簽名驗證失敗")
#         abort(400)
#     return 'OK',200

@handler.add(MessageEvent)
def handle_message(event):
    uid = f"'{event.source.user_id}'"
    reply_token = f"'{event.reply_token}'"
    message_id = f"'{event.message.id}'"

    if isinstance(event.message, TextMessage):
        message = "'" + event.message.text + "'"
        table = "temp_dialogue"
        input_data = [uid, message, "'False'", message_id, reply_token]
        properties = ["`user_id`", "`content`", "`state`", "`message_id`", "`reply_token`"]
        sql.push(table, input_data, properties)
    
        print(f"👤 使用者說：{event.message.text}")

    elif isinstance(event.message, ImageMessage):
        print("📷 使用者傳來圖片")

        # 建立資料夾（第一次使用）
        save_dir = "./received"
        os.makedirs(save_dir, exist_ok=True)

        # 儲存圖片
        image_path = os.path.join(save_dir, f"{event.message.id}.jpg")
        image_content = line_bot_api.get_message_content(event.message.id)
        with open(image_path, "wb") as f:
            for chunk in image_content.iter_content():
                f.write(chunk)

        # 呼叫 Gemini 辨識活動資訊
        gm = Gemini()
        try:
            image_info = gm.analyze_image(image_path)
            reply_text = f"✅ 活動資訊如下：\n{image_info}"
        except Exception as e:
            reply_text = f"❌ 解析圖片時發生錯誤：{e}"

        # 回覆使用者
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )


@handler.add(MessageEvent, message=TextMessage)

# ---- SQL 安全轉義小工具 ----
def esc(val):
    """None / 空字串 → NULL，其餘字串做簡易轉義並加引號"""
    if val in (None, "", "null"):
        return "NULL"
    return "'" + str(val).replace("\\", "\\\\").replace("'", "''") + "'"

def handle_message(event):
    user_input = event.message.text
    uid = "'"+event.source.user_id+"'"
    message_id = "'"+event.message.id+"'"
    message = "'" + event.message.text + "'"
    reply_token = "'" + event.reply_token + "'"

    table = "temp_dialogue"
    input_data = [uid, message, "'False'", message_id, reply_token]
    properties = ["`user_id`", "`content`", "`state`", "`message_id`", "`reply_token`"]
    sql.push(table, input_data, properties)
    
    print(f"👤 使用者說：{user_input}")

@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_id = event.message.id
    # 從 LINE 下載圖片內容
    message_content = line_bot_api.get_message_content(message_id)

    # 建立存放路徑
    save_dir = os.path.join('static', 'images')
    os.makedirs(save_dir, exist_ok=True)
    file_path = os.path.join(save_dir, f"{message_id}.jpg")

    # 寫檔
    with open(file_path, 'wb') as f:
        for chunk in message_content.iter_content(chunk_size=1024):
            f.write(chunk)
    print(f"📥 圖片已儲存: {file_path}")

    # 使用 Gemini 多模態模型分析圖片
    description= gm.analyze_image(file_path)
    description = description.split("\n", 1)[1]      # 去掉第一行 ```json
    description = description.rsplit("```", 1)[0]    # 去尾端 ```
    print(f"🔍 圖片分析結果: {description}")

    # 寫入MYSQL
    info = json.loads(description)      
    meta = info.get("metadata", {})              # dict，可 .get()        # 解析成 dict
    metadata_json = json.dumps(meta, ensure_ascii=False)
    table      = "event_info"
    properties = [
        "`event_name`", "`organizer`", "`contact_person`", "`contact_email`",
        "`target_audience`", "`speaker`", "`location`",
        "`registration_period`", "`session_time`",
        "`credit_label`", "`learning_passport_code`", "`event_url`"
    ]
    input_data = [
        esc(meta.get("event_name")),
        esc(meta.get("organizer")),
        esc(meta.get("contact_person")),
        esc(meta.get("contact_email")),
        esc(meta.get("target_audience")),
        esc(meta.get("speaker")),
        esc(meta.get("location")),
        esc(meta.get("registration_period")),
        esc(meta.get("session_time")),
        esc(meta.get("credit_label")),
        esc(meta.get("learning_passport_code")),
        esc(meta.get("event_url"))
    ]
    sql.push(table, input_data, properties)


    # 回覆使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"圖片分析結果：{description}")
    )

    if os.path.exists(file_path):
        os.remove(file_path)


    

def check_mysql_periodically():
    with app.app_context():
        while True:
            try:
                sql.sql.reconnect()

                # 定期從 MySQL 中查詢需要發送的數據
                table = "dialogue"
                rule=" reply_time ASC"
                condition=" state = 'False'"
                properties=['user_id','content','reply_time','dialogue_id', "reply_token"]
                new_messages = sql.fetch(table,properties,condition,rule,1)  # 假設你有這個方法
                #print(new_messages)
                if len(new_messages) > 0:
                    reply_time=new_messages[0][2]
                    if reply_time<datetime.datetime.now():
                        message = new_messages[0][1]
                        uid = new_messages[0][0]
                        reply_token = new_messages[0][4]
                        data = {"state":"'True'"}
                        condi = {"dialogue_id":"'"+str(new_messages[0][3])+"'"}

                        sql.update(table, data, condi)
                        #print("reply_token:",reply_token)
                        
                        #line_bot_api.push_message(uid, TextSendMessage(text=f"{message}"))
                        line_bot_api.reply_message(
                            reply_token,
                            TextSendMessage(text=f"{message.strip('\n')}")
                        )

                time.sleep(1)
            except Exception as e:
                print(f"後台執行緒發生錯誤: {e}")

if __name__ == "__main__":
    Thread(target=check_mysql_periodically, daemon=True).start()
    app.run(port=5000,debug= True)
