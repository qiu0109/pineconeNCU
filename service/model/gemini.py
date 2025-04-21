import google.generativeai as genai
import os
from PIL import Image



class Gemini():
    def __init__(self):
        google_api=os.getenv("GOOGLE_API_KEY")

        # 設定 API Key
        genai.configure(api_key=google_api)

        # 指定要使用的模型（示例名稱，實際需使用平台提供的模型ID）
        MODEL_NAME = "gemini-2.0-flash"
       
        # 發送請求
        self.model = genai.GenerativeModel(
            model_name = MODEL_NAME,
            system_instruction = "你是一個校園的客服小幫手，請針對使用者的訊息，做出生動有趣的回應，可以適時但不過多的使用現代網路用語，(如XD 、笑死、酷喔)來應答，目標是解答使用者的各種校園問題"
        )

    # 呼叫 gpt 模型協助生成回復
    def call(self, prompt:list[dict]):
        """
        :param prompt: list[dict], 例如：[{"role":"user", "parts":["text"]}, ...]
        """
        try:
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
