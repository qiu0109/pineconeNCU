from utils.database import base

class MySQLManager():
    # 初始化資料庫控制器
    def __init__(self, reset_database:bool = True):
        self.sql = base.MySQL(reset_database)
        return
    

    # 從 MySQL 獲取資料
    def fetch(self, table:str, properties:list = None, condition:str = None, rule:str = None, size:int = None):
        """
        將 `table` 依照 condition 排列，取 size 筆 uid 的 propsties。
        :param table: str, 操作的表格名稱
        :param properties: list, 取出的屬性（預設為 All）
        :param condition: str, 取出資料的條件（預設為 None）
        :param rule: str, 排序資料的條件（預設為 None）
        :param size: int, 取出資料的筆數（預設為 All）
        """
        cursor = self.sql.cursor

        properties = ", ".join(properties) if properties else "*"
        
        query = f"SELECT {properties} FROM `{table}`"
        if condition: query += f" WHERE {condition}"
        if rule is not None: query += f" ORDER BY {rule}"
        
        try:
            self.sql.execute(query)
            data = cursor.fetchmany(size) if size else cursor.fetchall()
            return data if data is not None else []
        except Exception as e:
            print(f"查詢數據時發生錯誤: {e}")
            return []
    

    # 往 MySQL 存入資料
    def push(self, table:str, data:list, properties:list = None):
        """
        將 `table` 的 properties 欄位存入 data。
        :param table: str, 操作的表格名稱
        :param data: str, 要存入的資料，例如：["'112502568'", "'user'", "'這是一條測試訊息'"]
        :param properties: list, 存入資料的屬性，例如：["`user_id`", "`role`", "`content`"]
        """
        properties = ", ".join(properties)
        data = ", ".join(data)

        query = f"INSERT INTO {table} "
        if properties is not None: query += f"({properties})"
        query += f"VALUES ({data})"

        self.sql.execute(query)
        return
    

    # 從 MySQL 刪除指定資料
    def delete(self, table, condition=None):
        """
        在 table 中依照 condition 刪除資料
        :param table: str, 要操作的資料表名稱
        :param condition: str, DELETE 時的條件 (例如 "id = 3")，可選
        """
        if condition is None: query = f"TRUNCATE TABLE {table}"
        else: query = f"DELETE FROM {table} WHERE {condition}"

        self.sql.execute(query)
        return


    # 在 MySQL 中更新資料
    def update(self, table:str, data:dict, condition:dict = None):
        """
        在 table 中依照 condition 更新資料成 data
        :param table: str, 要操作的資料表名稱
        :param data: dict, 要更新的資料
        :param condition: dict, 更新的條件（預設為 None）
        """
        data = ", ".join(f"{key} = {value}" for key, value in data.items())
        if condition is not None: condition = ", ".join(f"{key} = {value}" for key, value in condition.items())

        query = f"""
            UPDATE {table} 
            SET {data}
        """
        if condition is not None: query += f"WHERE {condition}"
        self.sql.execute(query)
        return