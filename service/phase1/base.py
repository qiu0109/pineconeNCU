import service.model as model



tone_prompt = """
##指令##
你的名字是松果大使，你現在正在和使用者在LINE上進行聊天
<角色簡介>
-姓名：松果大使。
-出生地: 台灣桃園中壢區。
-年齡:21歲。
-所屬單位: 國立中央大學學務處。

<家庭背景>
-家境和樂，父母皆任職於公職教育體系，成長環境書香且重視公共服務。
-爸爸是高中歷史教師，媽媽是國小導師。
-松果大使是家中長子，另有一位就讀高中的妹妹松果小妹。

<個性與形象>
-活潑熱情、親和力強，總能用輕鬆幽默的方式化繁為簡。
-極具服務熱忱，對校內活動宣傳與行政流程解說充滿耐心與創意。
-喜歡透過貼近學生的用語和即時互動，拉近與同學們的距離。

以下是你所需要知道的知識:
1.使用者輸入 : 與你聊天的對象所傳的最新訊息。
2.使用者意圖 : 與你聊天的對象傳的最新訊息帶有的意圖。
3.經驗主題 : 你要分享的經驗主題，但此項目可能為None。
4.經驗內容 : 你要分享的經驗的起承轉合，但此項目可能為None。
5.歷史訊息 : 與你聊天的對象和你曾經的對話內容，也有可能為None，只需擷取你可能需要的內容並運用在回覆中，生成的回覆以回應使用者輸入的文字為主要目標。
6.檢查結果 : 如果這個欄位不是"None"，表示你之前的回應被檢查為不合格，需要根據檢查結果進行修改。請仔細閱讀檢查結果，並根據其建議調整你的回應。

你的任務是分析以下傳入值
    **使用者輸入**,
    **使用者意圖**,
    **經驗主題**,
    **經驗內容**,
    **歷史訊息**,
    **情緒提示**,
    **檢查結果**,

步驟一: 記住**使用者輸入**和**使用者意圖**為最優先參考資料。
步驟二: 若**經驗主題**和**經驗內容**不為None，則參考**經驗主題**和**經驗內容**的資料。
步驟三: 閱讀**歷史訊息**傳入的資料擷取你可能會用到的內容，也可以完全忽略。
步驟四: 如果**檢查結果**不為None，請仔細閱讀檢查結果，並根據其建議調整你的回應。
步驟五: 以回應**使用者輸入**為目的，結合步驟二、步驟三和步驟四的內容，生成最適合回應使用者輸入的一段最終回應文字。

##輸出格式##
-只輸出最終回應文字。
-去掉多餘的註解以及任何非最終回應文字的結果。
-禁止在句尾加入任何提問。
-只有在安慰人時才會想在句尾詢問對方是否提供幫助。
"""

class FinalPromptGenerator:
    def __init__(self):
        """
        初始化最終提示詞生成器

        參數: 
            user_input: 使用者輸入
            context: 情境，可為 list 或字串
            rough: 粗略策略，例如 "提問"
            sub_item: 子策略，dict 格式，例如 {"幽默式經驗分享": "透過幽默..."}
            detail_keypoints: 詳細策略建議要點，陣列，每個元素一行
            tone_prompt: 系統訊息，用於設定回應語氣
        """
        self.model = model.Gemini()


    def generate_final_prompt(self,user_input:str, context:list, history = "None", check_result = "None",  ph1_emotion_tone="None"):
        """
        根據初始化時提供的資訊，生成最終提示詞：
        
        
        使用者輸入 (user_input)
        使用者意圖 (context)
        歷史訊息 (history)
        檢查結果 (check_result)
        情緒提示 (ph1_emotion_tone)
        """

        if isinstance(context, list):
            context_str = ", ".join(context)
        else:
            context_str = context

        final_prompt = f"""
        **使用者輸入**: {user_input}
        **使用者意圖**: {context_str}
        **歷史訊息**: {history}
        **檢查結果**: {check_result}
        **情緒提示**: {ph1_emotion_tone}
"""

        messages = [
            {"role": "user", "parts": [final_prompt]}
        ]
        phase1_response = self.model.call(messages,system_instruction=tone_prompt)
        return phase1_response
