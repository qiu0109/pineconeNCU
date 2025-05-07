from utils.database import MySQLManager

if __name__ == '__main__':
    sql = MySQLManager(False)
    print(sql.fetch('event_info'))