from sentence_transformers import SentenceTransformer
import torch, os, numpy as np

class E5LargeEmbedder:
    """
    e5 規格：
      - query 文字前加 'query: '
      - passage/文件前加 'passage: '
    """
    _NAME = os.getenv("E5_MODEL_NAME", "intfloat/e5-large-v2")

    def __init__(self, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model  = SentenceTransformer(self._NAME, device=self.device)

    def encode(self, text: str | list[str], *, is_query: bool = False) -> np.ndarray:
        if isinstance(text, str):
            text = [text]

        prefix = "query: " if is_query else "passage: "
        inputs = [prefix + t for t in text]

        return self.model.encode(
            inputs,
            normalize_embeddings=True,        # 建議開啟
            convert_to_numpy=True
        )            # shape = (n, 1024)