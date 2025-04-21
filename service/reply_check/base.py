import os
import service.model as model

class ReplyChecker:
    def __init__(self):
        self.model = model.GPT4O()
        # 讀取外部檔案 tone_prompt.txt，如果有的話
        tone_prompt_path = os.path.join("service", "reply_check", "tone_prompt.txt")
        if os.path.exists(tone_prompt_path):
            with open(tone_prompt_path, "r", encoding="utf-8") as f:
                self.tone_prompt = f.read()

    def check_response(self, user_message_input, original_text, context_str, history_str, result_checker_emotion_tone=None):
        """
        根據當前對話主題、歷史訊息、使用者輸入，檢查BOT回覆是否合理。
        
        參數:
            user_message_input: 使用者輸入
            original_text: BOT回覆
            context_str: 當前對話主題
            history_str: 歷史訊息
            emotion_tone: 情緒提示，默認為 None
        """

            
        user_prompt = (
            f"當前對話主題：{context_str}\n\n"
            f"歷史訊息：{history_str}\n\n"
            f"使用者輸入：{user_message_input}\n\n" 
            f"BOT回覆：\n{original_text}\n\n"
            f"情緒提示：\n{result_checker_emotion_tone}\n\n"
        )
        
        messages = [
            {"role": "system", "content": self.tone_prompt},
            {"role": "user", "content": user_prompt}
        ]
        print(user_prompt, original_text, context_str, history_str, end='\n')
        check_result = self.model.call(messages)

        return check_result.strip()



