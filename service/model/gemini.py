import google.generativeai as genai
import os
from PIL import Image



class Gemini():
    def __init__(self):
        google_api=os.getenv("GOOGLE_API_KEY")

        # 設定 API Key
        genai.configure(api_key=google_api)

        # 指定要使用的模型（示例名稱，實際需使用平台提供的模型ID）
        self.MODEL_NAME = "gemini-2.0-flash"
       


    # 呼叫 gpt 模型協助生成回復
    def call(self, prompt:list[dict], system_instruction = ''):
        """
        :param prompt: list[dict], 例如：[{"role":"user", "parts":["text"]}, ...]
        """
        try:
            self.model = genai.GenerativeModel(
                model_name = self.MODEL_NAME,
                system_instruction = system_instruction
            )
            response = self.model.generate_content(
                contents = prompt
            )
            candidate = response.candidates[0]
            reply_text = candidate.content.parts[0].text
            return reply_text
        except Exception as e:
            return f"[Error] gemini 呼叫失敗: {e}"
        
    def call_embedding(
        self,
        content: str | list[str],
        model_name: str = "models/gemini-embedding-exp-03-07",
        task_type: str = "RETRIEVAL_DOCUMENT",
    ):
        """
        :param content: 一段文字或文字 list
        :param model_name: 預設為 3072 維 SOTA。需低成本可換 text-embedding-004 (768 維)
        :param task_type: 依需求改成 SEMANTIC_SIMILARITY / CLASSIFICATION … 等
        :return: list[float] 或 list[list[float]]
        """
        try:
            # 直接呼叫官方 embed_content API
            resp = genai.embed_content(
                model=model_name,
                content=content,
                task_type=task_type,
            )
            return resp["embedding"]
        except Exception as e:
            return f"[Error] Gemini Embedding 失敗: {e}"



    def analyze_image(self, image_path: str, system_instruction: str = '') -> str:
        """
        利用 Gemini 多模態模型分析圖片內容，並回傳文字描述。
        :param image_path: 本地圖片檔案路徑
        :param system_instruction: 選填，提供額外上下文或分析指令
        """
        try:
            # 讀取二進位圖片資料
            # with open(image_path, 'rb') as img_f:
            #     image_bytes = img_f.read()
            default_prompt= '''你是一個 「活動海報資訊抽取與摘要助理」。
            當使用者上傳含有活動海報的圖片，請根據海報畫面中的文字與版面，完成下列任務並以 JSON 物件 回傳結果：
            1.**精準擷取下列欄位（若海報缺漏，請以 null 填值）**：
            {
                "event_name": null,
                "organizer": null,
                "contact_person": null,
                "contact_email": null,
                "target_audience": null,
                "speaker": null,
                "location": null,
                "registration_period": null,
                "session_time": null,
                "credit_label": null,
                "learning_passport_code": null,
                "event_url": null
            }
            2.**圖片摘要**
            以 1-2 句中文概述海報重點（活動核心、時間、地點）。
            不要重複 JSON 中已列出的欄位值，僅補充整體印象或亮點。
            格式規範
            最外層固定回傳一個物件，包含 metadata 與 summary 兩鍵：
            {
            "metadata": { ...欄位清單... },
            "summary": "..."
            }
            所有日期時間請保持原格式；若為範圍，用「起—迄」連寫。
            僅回傳 JSON，不要加入額外說明、標題或 markdown。
            3.**解析原則**
            優先以版面上醒目大字判斷「活動名稱」。
            如有多個時間段，將首段視為主要「場次時間」，其他可用分號 ; 分隔。
            電子郵件與網址須符合標準格式；若海報將網址縮短或使用 QR Code 而無明文字串，可填 null。
            若海報包含 QR Code，且能辨識出嵌入的連結，再填入「活動網址」。
            遵循以上規格，確保輸出可直接被程式解析。'''

            # 若沒有提供 system_instruction，使用預設提示
            system_prompt = system_instruction or default_prompt

            self.model = genai.GenerativeModel(
                model_name = self.MODEL_NAME,
                system_instruction = system_prompt
            )

            with Image.open(image_path) as img:
                response = self.model.generate_content(
                    [
                        img                  # Part 2：PIL.Image 物件即可
                    ]
                )

            print(response.text)          # Gemini 會依 system/user prompt 輸出

            # 呼叫通用的 call() 進行多模態分析
            return response.text
        except Exception as e:
            return f"[Error] gemini analyze_image 失敗: {e}"


if __name__ == "__main__":
    gm = Gemini()
    # 取得句子向量
    vec = gm.call_embedding("校園哪裡可以借打印機？")

    # 批次轉多句
    batch_vecs = gm.call_embedding(
        ["圖書館幾點關門？", "體育館開放時間？"],
        task_type="RETRIEVAL_QUERY"
    )
    print(len(batch_vecs), len(batch_vecs[0]))
    print(batch_vecs)
