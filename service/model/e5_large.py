from sentence_transformers import SentenceTransformer
import torch, os, numpy as np
from typing import List, Union

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

    def _to_list(self, obj):
        """
        把 ndarray / Tensor / list / float 統一轉成純 Python list
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, torch.Tensor):
            return obj.detach().cpu().tolist()
        # 若已經是 list 或標量（float、int）直接回傳／包裝
        if isinstance(obj, list):
            return obj
        return [obj]          # 標量 → 單元素 list


    def encode(
        self,
        text: Union[str, List[str]],
        *,
        is_query: bool = False
    ) -> Union[List[float], List[List[float]]]:
        """
        Args
        ----
        text      : str 或 List[str]；欲編碼的句子(們)。
        is_query  : True => "query: " 前綴；False => "passage: " 前綴。

        Returns
        -------
        - 若輸入單一句子 → List[float]   （長度 = embedding dim）
        - 若輸入多句子   → List[List[float]] （形狀 = (n, dim)）
        """
        single = isinstance(text, str)
        if single:
            text = [text]

        prefix = "query: " if is_query else "passage: "
        inputs = [prefix + t for t in text]

        # ① 拿 ndarray；② tolist() 直接轉 list
        emb_batch = self.model.encode(
            inputs,
            normalize_embeddings=True,
            convert_to_numpy=True          # ndarray
        )                      # 立即轉純 Python list
        #print(emb_batch)
        emb_batch = self._to_list(emb_batch)

        return emb_batch[0] if single else emb_batch