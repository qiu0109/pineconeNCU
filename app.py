from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# === 填入你的 LINE 金鑰 ===
CHANNEL_ACCESS_TOKEN = 'G8HOp50ZIU22bU/jMAUrd8p9wnghhMHHdmqir4RoRdSTwGRZ4M0LGZoUXBsxatq/tkF3p82y1/rZuRq7gpTrYrCuPBgkGzO3o20qeWEIctzC4EmWIEuImy1lXSh1mGSzinKvFt1n7hdPrE5fzO8XFwdB04t89/1O/w1cDnyilFU='
CHANNEL_SECRET = '4a24eeef056b6ccd9c2a0096422b831a'

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    reply_text = "🌰 松果大使為您服務中～請問想查詢什麼校園資訊呢？"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(port=5000)
