import os
import openai
from dotenv import load_dotenv

load_dotenv()

class GPT4O():
    openai.api_key = os.getenv("OPENAI_API_KEY")        # 從環境變數載入 OpenAI API Key

    # 呼叫 gpt 模型協助生成回復
    def call(self, prompt:list[dict]):
        """
        :param prompt: list[dict], 例如：[{"role":"user", "content":"text"}, ...]
        """
        try:
            response = openai.ChatCompletion.create(
                model = "gpt-4o",
                messages = prompt,
                max_tokens = 512,
                temperature = 0.8
            )
            return response.choices[0].message["content"]
        except Exception as e:
            return f"[Error] GPT-4 呼叫失敗: {e}"
        
    def call_embedding(self,content):
        try:
            response = openai.Embedding.create(
                model="text-embedding-ada-002",  # 指定要使用的 Embedding model
                input=content  # 你想轉成向量的文字
            )

            # 從回傳結果中取出向量
            return response["data"][0]["embedding"]
        except Exception as e:
            return f"[Error] GPT-4 呼叫失敗: {e}"
