import pymysql

def connection():
    conn = pymysql.connect(host="hostname",
                           user = "username",
                           password = "password",
                           db = "studydb")
    c = conn.cursor()

    return c, conn
