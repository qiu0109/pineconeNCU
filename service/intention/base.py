import json
import re
import service.model as model
import utils.database as db
import service.Chroma as cm

class Intention():
    def __init__(self):
        self.model = model.Gemini()
        # 粗略多標籤意圖機率偵測 prompt
        with open("service/intention/roughLabel.txt", "r", encoding="utf-8") as file:
            self.rough_prompt = file.read()
        with open("service/intention/detailLabel.txt", "r", encoding="utf-8") as file:
            self.detail_prompt = file.read()
        with open("service/intention/compareLabel.txt", "r", encoding="utf-8") as file: 
            self.compare_prompt = file.read()
        with open("utils/database/intention_menu.json", 'r', encoding='utf-8') as file:
            self.intention_menu = json.load(file)
        self.sql = db.MySQLManager(False)
        self.chroma = cm.ChromaDBManager()
        # self.createRoughTable()

        self.detail_label = []

    def _strip_code_fence(self, raw: str) -> str:
        """
        將 LLM 回傳的字串去掉最開頭 ```json（或 ```）與最末尾 ```。
        其他內容一律原樣保留。
        """
        if not raw:
            return raw
        return re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw, flags=re.I)
    
    def _extract_json(self, raw: str) -> dict:
        """
        去掉 ```json code fence，並回傳第一個合法 JSON 物件。
        取不到就 raise ValueError。
        """
        raw = self._strip_code_fence(raw)
        m = re.search(r"\{.*?\}", raw, re.S)
        if not m:
            print(raw)
            raise ValueError("找不到 JSON 區塊")
        return json.loads(m.group(0))


    # 填入 Rough 表的內容
    def createRoughTable(self):
        table = "`Rough`"
        data = [
            ["'Emotional Support'", "'話者表達情緒困擾、需要安慰或關懷。'", "'None'"],
            ["'Self-Exploration'", "'話者自我反思，探索自己的想法、價值觀或情緒。'", "'None'"],
            ["'Interpersonal/Relationships'", "'討論與他人（朋友、家人、伴侶等）之間的關係或互動問題。'", "'None'"],
            ["'Guidance/Advice'", "'話者尋求或提供建議、指導或解決方案。'", "'None'"],
            ["'Complaint/Venting'", "'話者表達不滿、抱怨、發洩情緒。'", "'None'"],
            ["'Information/Product Inquiry'", "'話者詢問某些資訊、產品或服務的相關問題。'", "'None'"],
            ["'Self-Improvement'", "'話者關注個人成長，如學習新技能、改善行為或習慣。'", "'None'"],
            ["'Celebration/Good News'", "'話者分享開心的消息或慶祝某件事。'", "'None'"],
            ["'Social Interaction/Interests'", "'話者進行社交對話，討論興趣或休閒話題。'", "'None'"],
            ["'尚無完整意圖'", "'對話尚不完整，無法明確歸類。'", "'None'"],
        ]
        for num in range(10):
            self.sql.push(table, data[num])
        return


    def multiIntention(self, message:str, reply_message:str = "None") -> dict:
        # 生成粗略多標籤意圖機率
        rough = self.roughLabel(message, reply_message)
        # 篩選粗略多標籤意圖
        rough = self.filterLabel(rough)

        if '尚無完整意圖' in rough or rough == []: return [{
            "insert": "False",
            "intention": "無明顯意圖:使用者沒有明顯的意圖，不用參考此傳入值。"
        }]

        # 篩出詳細多標籤意圖
        oldLabel = self.get_detail(rough)

        # 生成詳細多標籤意圖
        detail_key, detail_value = self.detailLabel(rough, message, reply_message)

        # 判斷新標籤是否有獨立存在的必要
        newLabel = []
        for i in range(len(detail_key)):
            newLabel.append(detail_key[i] + ':' + detail_value[i])
        detail = self.compareLabel(oldLabel, newLabel)

        # 判斷新標籤是否有獨立存在的必要
        for i in range(len(detail)):
            print(f"\n\nTest:\n{detail}\n\n{rough}\n\n{detail_key}\n\n{detail_value}\n\n")
            if detail[i].get("insert") == "True": self.insertChroma(rough[i], detail_key[i], detail_value[i])

        return detail


    # 篩出詳細多標籤意圖
    def get_detail(self, rough:list) -> list:
        detail = []

        for i in range(len(rough)):
            detail.append(self.chroma.search_data("Intention_Collection", rough[i]))
        return detail


    # 比較新舊標籤的相似度
    def compareLabel(self, oldLabel:list, newLabel:list) -> list:
        """
        比較傳入的兩個新舊標籤列表其每個元素的相似度。
        :param oldLabel: list, 舊標籤
        :param newLabel: list, 新標籤
        """
        detail = []
        for i in range(len(oldLabel)):
            prompt = [
                {"role": "user", "parts": [f"既有的多標籤意圖：**{oldLabel[i]}**\n新的多標籤意圖：**{newLabel[i]}**"]}
            ]
            
            for attempt in range(30):
                try:
                    response = self.model.call(prompt, self.compare_prompt)
                    response = self._extract_json(response)
                    detail.append(response)
                    break
                except Exception as e:
                    if attempt < 29:  # 失敗，最多重試29次
                        print(f"[Intention Error] 第{attempt+1}次解析失敗，正在重試... ({e})")
                    else:  # 仍然失敗
                        print(f"[Intention Error] 30次解析皆失敗，回傳舊標籤 ({e})")
                        detail.append( {
                            "insert":"False",
                            "story":oldLabel[i]
                        } )
        return detail


    # 存入 ChromaDB、json
    def insertChroma(self, rough:str, label:str, description:str):
        self.chroma.add_custom_data("Intention_Collection", label, description)
        
        for i in range(10):
            if self.intention_menu[i].get("intention") == rough:
                self.intention_menu[i].get("menu").append({label:description})
                break
        
        with open("utils/database/intention_menu.json", 'w', encoding='utf-8') as file:
            json.dump(self.intention_menu, file, indent=4, ensure_ascii=False)
       
        return


    # 篩選粗略多標籤意圖
    def filterLabel(self, data:dict):
        """
        回傳最多3個粗略多標籤意圖。規則為：若該標籤機率大於0.20。
        無標籤符合或【無明顯意圖】機率大於0.50，則僅篩出【無明顯意圖】。
        :param data: dict, 多標籤意圖（粗略）機率
        """
        label = []
        # 篩選大於 0.20 的標籤機率
        for key, value in data.items():
            if value >= 0.20: label.append(key)

        if label == [] or data.get('尚無完整意圖') >= 0.50:
            return ['尚無完整意圖']
        
        if '尚無完整意圖' in label: label.remove('尚無完整意圖')
        return label


    # 粗略多標籤意圖機率分析
    def roughLabel(self, message:str, reply_message:str = "None") -> dict:
        """
        使用 GPT-4o 進行粗略多標籤意圖機率分析，模型解析後傳回 json 。
        :param message: str, 要分析的使用者訊息
        :param history: str, 歷史訊息（可選）
        """ 
        prompt = [
            {"role": "user", "parts": [f"使用者重點回覆的訊息：**{reply_message}**\n請分析使用者最新訊息：**{message}**"]}
        ]
         
        for attempt in range(30):
            try:
                response =self.model.call(prompt,system_instruction=self.rough_prompt)
                response = self._extract_json(response)
                print(response)
                return response
            except Exception as e:
                if attempt < 29:  # 失敗，最多重試29次
                        print(f"[Intention Error] 第{attempt+1}次解析失敗，正在重試... ({e})")
                else:  # 仍然失敗
                    print(f"[Intention Error] 30次解析皆失敗，回傳尚無完整意圖 ({e})")
                    return {
                        "情感支持": 0.00,
                        "自我探索": 0.00,
                        "人際/關係": 0.00,
                        "指引/建議": 0.00,
                        "投訴/抱怨/發洩": 0.00,
                        "資訊/產品需求": 0.00,
                        "自我成長/改善": 0.00,
                        "慶祝/好消息": 0.00,
                        "社交互動/興趣話題": 0.00,
                        "尚無完整意圖": 1.00
                    }


    def detailLabel(self, Labels: list, message: str, reply_message: str = "None") -> dict:
        """
        使用 GPT-4o 進行詳細多標籤意圖分析，模型解析後傳回 json 。
        :param Labels: list, 該使用者訊息的粗略多標籤意圖
        :param message: str, 要分析的使用者訊息
        :param history: str, 歷史訊息（可選）
        """
        detail = []
        
        for label in Labels:
            prompt = [
                {"role": "user", "parts": [f"使用者重點回覆的訊息：**{reply_message}**\n請分析使用者最新訊息：**{message}**"]}
            ]

            for attempt in range(30):  # 嘗試兩次
                try:
                    response =self.model.call(prompt,system_instruction=f"{self.detail_prompt}\n粗略多標籤意圖：**{label}**\n")
                    response = self._extract_json(response)
                    print(response)
                    detail.append(response)
                    break  # 成功解析 JSON，跳出重試迴圈
                except Exception as e:
                    if attempt < 29:  # 失敗，最多重試29次
                        print(f"[Intention Error] 第{attempt+1}次解析失敗，正在重試... ({e})")
                    else:  # 仍然失敗
                        print(f"[Intention Error] 30次解析皆失敗，回傳未知意圖 ({e})")
                        detail.append({"未知意圖（Unknow Intent）": "無意義"})
        
        detail_key = [list(item.keys())[0].split('（')[0] for item in detail]
        detail_value = [list(item.values())[0] for item in detail]
        
        return detail_key, detail_value