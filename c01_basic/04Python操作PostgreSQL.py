import psycopg

# 连接数据库
conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="rag",
    user="postgres",
    password="postgres"
)

# 查询所有用户
with conn.cursor() as cursor:
    cursor.execute("SELECT * FROM users")
    print(cursor.fetchall())

# 关闭连接
conn.close()