import utils.database as db
from dotenv import load_dotenv

load_dotenv()

# 今晚吃牛丼好嗎

def main():
    sql = db.MySQLManager(False)
    while True:
        uid = "'test0001'"
        message_id = "'00000000001'"
        message = "'" + input("模擬用戶輸入：") + "'"
        reply_id = "'00000000001'"

        table = "temp_dialogue"
        input_data = [uid, message, "'False'", message_id]
        properties = ["`user_id`", "`content`", "`state`", "`message_id`"]
        sql.push(table, input_data, properties)

        print(f"訊息【{message}】已經存入\n")


if __name__ == "__main__":
    main()