import psycopg
import json

# 连接数据库
conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="rag",
    user="postgres",
    password="postgres"
)

# 会话ID
conversation_id = 1
# 写入用户信息
with conn:
    with conn.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO chat_message (conversation_id, role, content)
            VALUES (%s, %s, %s)
            """,
            (
                conversation_id,
                "user",
                json.dumps({"text": "什么是 PostgreSQL？"})
            )
        )

# 关闭连接
conn.close()