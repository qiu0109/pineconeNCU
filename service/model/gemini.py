from google import genai
from google.genai import types
import os
from PIL import Image





class Gemini():
    def __init__(self):
        google_api=os.getenv("GOOGLE_API_KEY")

        # 設定 API Key
        self.client = genai.Client(api_key=google_api)

        # 指定要使用的模型（示例名稱，實際需使用平台提供的模型ID）
        self.MODEL_NAME = "gemini-2.0-flash"
       


    # 呼叫 gpt 模型協助生成回復
    def call(self, prompt:list[dict], system_instruction = '', search_web = True):
        """
        :param prompt: list[dict], 例如：[{"role":"user", "parts":["text"]}, ...]
        """
        try:
            #print(prompt)
            messages = []
            for m in prompt:
                role = m.get("role", "user")          # 預設視為 user
                part_objs = [types.Part(text=p) for p in m.get("parts", [])]
                messages.append(types.Content(role=role, parts=part_objs))
            #print(messages)
            if search_web:
                response = self.client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(
                            google_search=types.GoogleSearchRetrieval()
                        )],
                        system_instruction=system_instruction+"如果遇到不知道的問題請查詢google"
                    )
                )
                #print(response)
            else:
                response = self.client.models.generate_content(
                    model=self.MODEL_NAME,
                    contents=messages,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction
                    )
                )
                #print(response)
            #print(response)
            candidate = response.candidates[0]
            #print(candidate)
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
        讀取本地圖片，呼叫 Gemini Vision 取得 JSON + 摘要。
        :param image_path: 圖片檔案路徑
        :param system_instruction: （可選）覆寫預設提示
        :return: Gemini 回傳的文字（JSON + 摘要）
        """
        default_prompt = (
            "你是一個「活動海報資訊抽取與摘要助理」。\n"
            "當使用者上傳含有活動海報的圖片，請根據海報畫面中的文字與版面，完成下列任務並以 JSON 物件回傳結果：\n"
            "1. **精準擷取下列欄位（若缺漏，請以 null 填值）**：\n"
            "{\n"
            '  "event_name": null,\n'
            '  "organizer": null,\n'
            '  "contact_person": null,\n'
            '  "contact_email": null,\n'
            '  "target_audience": null,\n'
            '  "speaker": null,\n'
            '  "location": null,\n'
            '  "registration_period": null,\n'
            '  "session_time": null,\n'
            '  "credit_label": null,\n'
            '  "learning_passport_code": null,\n'
            '  "event_url": null\n'
            "}\n"
            "2. **圖片摘要**：以 1-2 句中文概述海報重點（活動核心、時間、地點）；勿重複 JSON 欄位值。\n"
            "3. **格式規範**：\n"
            '{ "metadata": { … }, "summary": "…" }\n'
            "所有日期時間保持原格式；僅回傳 JSON，不要額外說明或 markdown。"
        )
        sys_prompt = system_instruction or default_prompt

        try:
            # ① 準備 Content（文字 + 圖像）
            with open(image_path, 'rb') as img:
                img_bytes = img.read()
                messages = [
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text="請依說明抽取資訊並摘要："),
                            types.Part.from_bytes(
                                data=img_bytes,
                                mime_type='image/jpg'
                            )
                        ]
                    )
                ]

            # ② 呼叫 Vision 模型
            resp = self.client.models.generate_content(
                model=self.MODEL_NAME,
                contents=messages,
                config=types.GenerateContentConfig(
                    system_instruction=sys_prompt
                )
            )

            reply_text = resp.text          # SDK 0.8 可直接用 .text
            return reply_text

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
