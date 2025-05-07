import pandas as pd
import os

class KnowledgeBase:
    def __init__(self, csv_path=None):
        if csv_path is None:
            csv_path = os.path.join(os.path.dirname(__file__), '..', 'knowledge.csv')
        self.df = pd.read_csv(csv_path, encoding='utf-8')
        self.df = self.df.fillna('')

    def query_by_topic(self, topic):
        """
        根據 Topic 完全匹配查詢知識內容。
        """
        result = self.df[self.df['Topic'] == topic]
        return result.to_dict(orient='records')

    def query_by_keyword(self, keyword):
        """
        根據關鍵字模糊查詢 Topic、content 欄位。
        """
        mask = self.df['Topic'].str.contains(keyword, na=False) | self.df['content'].str.contains(keyword, na=False)
        result = self.df[mask]
        return result.to_dict(orient='records')

    def get_all_topics(self):
        """
        取得所有 Topic 清單。
        """
        return self.df['Topic'].unique().tolist() 