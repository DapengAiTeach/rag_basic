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
                "assistant",
                json.dumps({
                    "text": "PostgreSQL 是一个功能强大的关系型数据库……",
                    "model": "gpt-4.1"
                })
            )
        )

# 关闭连接
conn.close()