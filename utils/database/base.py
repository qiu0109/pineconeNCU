import os
import json
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

class MySQL():
    # 維護連接資料庫變數
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWD = os.getenv("MYSQL_PASSWD")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
    


    # 初始化本機端資料庫
    def __init__(self, reset_database:bool = True):
        # 與資料庫連結並初始化 
        self.mydb = self.connect()
        self.cursor = self.mydb.cursor(buffered=True)

        # 讀取 JSON 檔案
        with open('utils/database/table.json', 'r', encoding='utf-8') as file:
            schema = json.load(file)

        # 分割成兩個變數
        self.table = list(schema.keys())
        self.properties = {table: [f'{column_name} {column_type}' for column_name, column_type in columns.items()] for table, columns in schema.items()}
        
        # 新增完整資料庫
        if reset_database: self.delete_database()
        self.create_database()
        return 


    # 與資料庫連結
    def connect(self):
        try:
            return mysql.connector.connect(
                host = self.MYSQL_HOST,     
                user = self.MYSQL_USER,
                passwd = self.MYSQL_PASSWD,
            )
        except Exception as e:
            print(e)

    #重連測試
    def reconnect(self):
        try:
            self.mydb.ping(reconnect=True)
            # 如果沒拋出例外，代表連線仍可用或已自動重連
        except:
            # 這裡執行手動重連邏輯
            self.connect()

    # 進行操作
    def execute(self, query):
        try:
            self.cursor.execute(query)
            self.mydb.commit()
        except mysql.connector.Error as err:
            print(f"操作表格時發生錯誤: {err}")
        return


    # 建立完整資料庫
    def create_database(self):
        # 建立 chatbot 資料庫，並 USE chatbot
        self.execute(f"CREATE DATABASE IF NOT EXISTS `{MySQL.MYSQL_DATABASE}`;")
        self.execute(f"USE `{MySQL.MYSQL_DATABASE}`;")

        for table_name in self.table:
            property = self.properties.get(table_name, [])
            self.create_table(table_name, property)
        return


    # 刪除舊資料庫
    def delete_database(self):
        self.execute(f"DROP DATABASE `{MySQL.MYSQL_DATABASE}`;")
        return


    # 新增傳入的表格及其屬性
    def create_table(self, table: str, properties: list):
        """
        :param table: 表格名稱
        :param properties: 欲新增的屬性列表 (包含資料類型，如 'id INT PRIMARY KEY AUTO_INCREMENT')
        """
        if not properties:
            raise ValueError("創建資料庫表格的屬性列表不能為空")
        
        properties = ", ".join(properties)
        query = f"CREATE TABLE IF NOT EXISTS {table} ({properties});"

        self.execute(query)
        return


    # 刪除傳入的表格
    def delete_table(self, table: str):
        self.execute(f"DROP TABLE {table};")
        return


    