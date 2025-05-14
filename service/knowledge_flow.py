import ast


def get_main_intent(intent_result):
    if isinstance(intent_result, list) and len(intent_result) > 0:
        max_intent = None
        max_prob = -1
        for item in intent_result:
            for k, v in item.items():
                if v > max_prob:
                    max_intent = k
                    max_prob = v
    if max_intent:
        return max_intent
    return "尚無完整意圖"

def get_non_schedule_steps(kb, schedule_topic):
    all_rows = kb.df
    schedule_row = all_rows[(all_rows['Topic'].str.strip() == schedule_topic.strip()) & (all_rows['metadata'].str.strip() == 'schedule')]
    if schedule_row.empty:
        print(f"[DEBUG] 找不到 schedule topic: {schedule_topic}")
        return []
    steps_str = schedule_row.iloc[0]['content']
    steps = ast.literal_eval(steps_str) if steps_str else []
    print(f"[DEBUG] 流程步驟: {steps}")
    print(f"[DEBUG] 所有 non_schedule topic: {all_rows[all_rows['metadata'].str.strip() == 'non_schedule']['Topic'].tolist()}")
    non_schedule_rows = []
    for idx, step in enumerate(steps):
        step = step.strip()
        row = all_rows[(all_rows['Topic'].str.strip() == step) & (all_rows['metadata'].str.strip() == 'non_schedule')]
        if not row.empty:
            row_dict = row.iloc[0].to_dict()
            row_dict['step_index'] = idx + 1
            non_schedule_rows.append(row_dict)
        else:
            print(f"[DEBUG] 找不到 non_schedule step: {step}")
    return non_schedule_rows

def get_data_by_link(kb, link):
    all_rows = kb.df
    if not link or link == "[]":
        return []
    topics = ast.literal_eval(link)
    data_rows = []
    for topic in topics:
        topic = topic.strip()
        rows = all_rows[(all_rows['metadata'].str.strip() == 'data') & (all_rows['Topic'].str.strip() == topic)]
        for _, row in rows.iterrows():
            data_rows.append(row.to_dict())
    return data_rows 

def get_data_by_link_database(sql, link = 'event_info'):
    table = link.strip("[").strip("]").strip("'")
    properties = ["event_name", "organizer", "contact_person", "contact_email", "target_audience", "speaker",
                 "location", "registration_period", "session_time", "credit_label", "learning_passport_code", "event_url"]
    rows = sql.fetch(table,properties)
    
    ans = ""
    # [(), (), ...]
    for idx, event in enumerate(rows):
        ans += f"第{idx+1}活動: \n"
        if event[0]!=None:
            ans += f"event_name:{event[0]}\n"
        if event[1]!=None:
            ans += f"organizer:{event[1]}\n"
        if event[2]!=None:
            ans += f"contact_person:{event[2]}\n"
        if event[3]!=None:
            ans += f"contact_email:{event[3]}\n"
        if event[4]!=None:
            ans += f"target_audience:{event[4]}\n"
        if event[5]!=None:
            ans += f"speaker:{event[5]}\n"
        if event[6]!=None:
            ans += f"location:{event[6]}\n"
        if event[7]!=None:
            ans += f"registration_period:{event[7]}\n"
        if event[8]!=None:
            ans += f"session_time:{event[8]}\n"
        if event[9]!=None:
            ans += f"credit_label:{event[9]}\n"
        if event[10]!=None:
            ans += f"learning_passport_code:{event[10]}\n"
        if event[11]!=None:
            ans += f"event_url:{event[11]}\n"
    return ans


