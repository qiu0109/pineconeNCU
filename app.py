from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import datetime
from utils.database import MySQLManager

# === LINE 金鑰 ===
CHANNEL_ACCESS_TOKEN = 'G8HOp50ZIU22bU/jMAUrd8p9wnghhMHHdmqir4RoRdSTwGRZ4M0LGZoUXBsxatq/tkF3p82y1/rZuRq7gpTrYrCuPBgkGzO3o20qeWEIctzC4EmWIEuImy1lXSh1mGSzinKvFt1n7hdPrE5fzO8XFwdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '4a24eeef056b6ccd9c2a0096422b831a'
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)


sql = MySQLManager(True)
app = Flask(__name__)
print("✅ Flask 啟動中...")

@app.route("/")
def home():
    return "✅ Flask 已啟動，請用 /callback 接 webhook"

@app.route("/callback", methods=['POST'])
def callback():
    print("📥 有訊息打進 /callback！")
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("❌ 簽名驗證失敗")
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
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
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說的是：「{user_input}」")
    )

if __name__ == "__main__":
    app.run(port=5000,debug= True)