import chromadb
import json
import uuid  # 用於生成唯一 ID
import os
from dotenv import load_dotenv
from ..model.gemini import Gemini

load_dotenv()


class ChromaDBManager:
    def __init__(self, db_path="./chroma_db", api_key=None):
        """
        初始化 ChromaDB 管理器，讀取 strategy_menu.json & intention_menu.json，
        確保 ChromaDB 內的數據最新，避免重複插入。
        """
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.gemini_client = Gemini()
        
        # 定義 Collection 名稱
        self.strategy_collection_name = "Strategy_Collection"
        self.intention_collection_name = "Intention_Collection"
        self.story_collection_name = "Story_Collection"
        # 設定 JSON 檔案的絕對路徑
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.strategy_json_path = os.path.join(base_dir, "../../utils/database/strategy_menu.json")
        self.intention_json_path = os.path.join(base_dir, "../../utils/database/intention_menu.json")
        self.story_json_path = os.path.join(base_dir, "../../utils/database/story_menu.json")
        # 初始化兩個 Collection
        self.reset_and_populate_collection(self.strategy_collection_name, self.strategy_json_path)
        self.reset_and_populate_collection(self.intention_collection_name, self.intention_json_path)
        self.reset_and_populate_collection(self.story_collection_name, self.story_json_path)

    def get_embedding(self, text):
        """取得 OpenAI 向量嵌入表示（將文字轉成向量）。"""
        return self.gemini_client.call_embedding(
        content=text,
        model_name="models/gemini-embedding-exp-03-07",  # 預設
        task_type="RETRIEVAL_DOCUMENT")

    def get_collection(self, collection_name):
        """取得指定名稱的 Collection，若不存在則創建。"""
        return self.chroma_client.get_or_create_collection(name=collection_name)

    def add_custom_data(self, collection_name, key, value=""):
        """
        向指定的 ChromaDB Collection 插入自定義數據，並自動生成 UUID 作為 ID。
        :param collection_name: Collection 名稱 (Strategy_Collection / Intention_Collection)
        :param text: 存入的文字內容
        """
        text = key
        if value is not "": text += ":" + value
        collection = self.get_collection(collection_name)
        embedding = self.get_embedding(text)  # 取得 OpenAI 向量
        unique_id = str(uuid.uuid4())  # 生成唯一 ID

        collection.add(
            ids=[unique_id],
            embeddings=[embedding],
            metadatas=[{"text": text}]
        )

        print(f"✅ {collection_name} 插入成功：{unique_id} -> {text}")

    def reset_and_populate_collection(self, collection_name, json_path):
        """
        確保指定的 Collection 內有最新的 JSON 內容，但不刪除已存在的數據，避免重複插入相同內容。
        這樣可以加快重啟速度，只有新的內容才會被加入。
        """
        collection = self.get_collection(collection_name)

        # 取得所有現有數據的 text
        existing_data = collection.get()
        existing_texts = set(metadata["text"] for metadata in existing_data.get("metadatas", []) if "text" in metadata)

        print(f"📊 {collection_name} 內已有 {len(existing_texts)} 筆數據，將檢查是否需要新增。")

        # 讀取 JSON 檔案
        if not os.path.exists(json_path):
            print(f"⚠️ 找不到 {json_path}，跳過初始化 {collection_name}")
            return
        
        with open(json_path, "r", encoding="utf-8") as file:
            menu_data = json.load(file)

        new_count = 0  # 計算新增的數據數量

        for category in menu_data:
            menu = category.get("menu", [])
            for item in menu:
                for key, value in item.items():
                    text = f"{key}:{value}"  # 轉成 "key: value" 形式
                    
                    if text in existing_texts:
                        print(f"⚠️ {collection_name} 已存在，跳過: {text}")
                        continue  # 如果已存在則跳過

                    self.add_custom_data(collection_name, text)  # 插入新數據
                    new_count += 1  # 計算新增數量

        print(f"🎉 新增 {new_count} 策略數據至 {collection_name}，總數 {len(existing_texts) + new_count}。")

    def search_data(self, collection_name, query):
        """
        在指定的 Collection 內搜尋最相似的數據，並回傳單一字串結果。
        :param collection_name: Collection 名稱 (Strategy_Collection / Intention_Collection)
        :param query: 查詢內容
        """
        collection = self.get_collection(collection_name)
        query_embedding = self.get_embedding(query)
        results = collection.query(query_embeddings=[query_embedding], n_results=1)  # 只取 1 筆資料

        if results["ids"] and results["metadatas"][0]:  # 檢查是否有結果
            return results["metadatas"][0][0]["text"]  # 直接回傳第一筆資料的 text

        return "❌ 沒有找到相關資料"


if __name__ == "__main__":
    db_manager = ChromaDBManager()

    # 指定 Collection 名稱
    collection_name = "Strategy_Collection"

    # 獲取 Collection 對象
    collection = db_manager.get_collection(collection_name)
    
    # 取得所有數據
    all_data = collection.get()

    # 確認 'documents' 欄位是否存在並提取文本資料
    all_texts = [metadata['text'] for metadata in all_data.get('metadatas', []) if 'text' in metadata]

# 列出所有文本
    for text in all_texts:
        print(text)
