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
# 查询指定会话的所有聊天记录
with conn.cursor() as cursor:
    cursor.execute(
        """
        SELECT role, content, created_at
        FROM chat_message
        WHERE conversation_id = %s
        ORDER BY created_at ASC
        """,
        (conversation_id,)
    )
    rows = cursor.fetchall()

for role, content, created_at in rows:
    print(role, content["text"])

# 关闭连接
conn.close()