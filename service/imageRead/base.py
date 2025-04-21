import requests
from PIL import Image
from io import BytesIO
import base64
import openai
import os
from utils.database.manager import MySQLManager

class LineStickerAnalyzer:
    def __init__(self, sticker_id: str):
        self.sql = MySQLManager(False)

        self.sticker_id = sticker_id
        self.image_url = f"https://stickershop.line-scdn.net/stickershop/v1/sticker/{self.sticker_id}/android/sticker.png"
        self.image = self._fetch_image()

    def _fetch_image(self):
        """下載貼圖圖片"""
        response = requests.get(self.image_url)
        if response.status_code == 200:
            return Image.open(BytesIO(response.content))
        else:
            raise Exception(f"貼圖圖片載入失敗，HTTP Status: {response.status_code}")

    def _encode_image_base64(self):
        """把圖片轉成 base64，用於 GPT Vision"""
        if not self.image:
            raise Exception("圖片尚未下載")
        buffered = BytesIO()
        self.image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")

    def get_message(self) -> str:
        table = "sticker"
        properties = ["message"]
        conditions = f"sticker_id = {self.sticker_id}"

        message = self.sql.fetch(table, properties, conditions)
        
        if message == []:
            message.append( (self.gpt_analyze_meaning(), ) )

            properties.append("sticker_id")
            datas = ["'"+message[0][0]+"'", self.sticker_id]
            self.sql.push(table, datas, properties)
        
        return message[0][0]


    def gpt_analyze_meaning(self):
        """呼叫 GPT-4V 模型分析貼圖含意"""
        base64_image = self._encode_image_base64()
        print("呼叫 GPT-4V 進行貼圖語意分析...")

        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "你是一位熟悉貼圖與表情包語意的 AI 分析師，請判斷貼圖代表的情緒與情境。"},
                {"role": "user", "content": [
                    {"type": "text", "text": "請幫我用一句話形容情緒、代表的行為"},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }}
                ]}
            ],
            max_tokens=300
        )

        result = response['choices'][0]['message']['content']
        return result

