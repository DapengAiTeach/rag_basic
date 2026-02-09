import psycopg

# 连接数据库
conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="rag",
    user="postgres",
    password="postgres"
)

# 写入测试会话
with conn:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO conversation (user_id, title)
            VALUES (%s, %s)
            """,
            (
                "1",
                "测试会话",
            )
        )

# 关闭连接
conn.close()