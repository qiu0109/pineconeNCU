import os
import tiktoken
from ..model.gemini import Gemini

gemini_client = Gemini()  # 單例，重複建立成本高


def get_text_embedding(text: str | list[str],
                       model_name: str = "models/gemini-embedding-exp-03-07",
                       task_type: str = "RETRIEVAL_DOCUMENT"):
    """利用 Gemini 取得文字向量。"""
    return gemini_client.call_embedding(text, model_name=model_name, task_type=task_type)


def cosine_similarity(vec1, vec2):
    """計算兩個向量的 Cosine 相似度。"""
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = sum(a * a for a in vec1) ** 0.5
    norm2 = sum(a * a for a in vec2) ** 0.5
    if norm1 == 0 or norm2 == 0:
        return 0
    return dot_product / (norm1 * norm2)


def count_tokens(text: str, model: str = "cl100k_base"):
    """粗略估算 token 數。若 tiktoken 可用則使用；否則以字元數為近似。"""
    if tiktoken is None:
        return len(text)
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


class ConversationBuffer:
    """暫存對話訊息；超過 token 限制時觸發小摘要。"""

    def __init__(self, token_limit=250, model="cl100k_base"):
        self.buffer = []
        self.token_limit = token_limit
        self.model = model
        self.current_tokens = 0

    def add_message(self, role, content):
        token_count = count_tokens(content, model=self.model)
        self.buffer.append((role, content))
        self.current_tokens += token_count

    def should_summarize(self):
        return self.current_tokens > self.token_limit

    def get_conversation_text(self):
        return "\n".join([f"{r}: {c}" for r, c in self.buffer])

    def clear_buffer(self):
        self.buffer = []
        self.current_tokens = 0


class Summarizer:
    """以 Gemini 生成小摘要與大摘要。"""

    def __init__(self, temperature: float = 0.0):
        # Gemini Flash 2.0 尚未公開調溫參數，先保留
        self.temperature = temperature
        self._model = gemini_client

    def _generate(self, prompt: list[dict]):
        """統一呼叫 Gemini 產生內容。"""
        return self._model.call(prompt)

    def summarize_chunk(self, conversation_text: str) -> str:
        system_content = (
            "你是一個專業的摘要助理，請仔細閱讀使用者提供的文本，並以精簡、要點分明的方式進行摘要。"
            "請產生不超過200字的摘要，保留關鍵資訊並確保易於理解。"
        )
        user_content = f"以下是需要摘要的文本：\n\n{conversation_text}"

        prompt = [
            {"role": "system", "parts": [system_content]},
            {"role": "user", "parts": [user_content]},
        ]
        return self._generate(prompt).strip()

    def summarize_topic(self, partial_summaries: list[str]) -> str:
        joined_summaries = "\n".join(partial_summaries)
        system_content = (
            "你是一個專業的摘要助理，請整合以下多段小摘要，並產生更高階、更精簡的大摘要，保留關鍵脈絡與重要資訊。"
            "請將它們融合為一段連貫的大摘要，不超過300字，保持邏輯清晰。"
        )
        user_content = f"以下是多段小摘要內容：\n{joined_summaries}"
        prompt = [
            {"role": "system", "parts": [system_content]},
            {"role": "user", "parts": [user_content]},
        ]
        return self._generate(prompt).strip()


def need_topic_summary(partial_summaries: list[str], threshold: float = 0.84, max_partial_count: int = 5):
    """依序比較最後兩段小摘要的相似度，或累積數量以決定是否進行大摘要。"""
    if len(partial_summaries) < 2:
        return False

    new_summary, old_summary = partial_summaries[-1], partial_summaries[-2]
    new_vec = get_text_embedding(new_summary)
    old_vec = get_text_embedding(old_summary)

    similarity = cosine_similarity(new_vec, old_vec)
    print(f"[Debug] 相似度: {similarity}")

    if similarity < threshold:
        return True
    if len(partial_summaries) >= max_partial_count:
        return True
    return False
