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

def get_recent_messages(conn, conversation_id: int, limit: int = 10):
    with conn.cursor() as cursor:
        cursor.execute(
            """
            SELECT role, content
            FROM chat_message
            WHERE conversation_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (conversation_id, limit)
        )

        rows = cursor.fetchall()

    # ⚠️ 注意：倒序查出来，要反转成时间正序给模型
    messages = [
        {
            "role": role,
            "content": content["text"]
        }
        for role, content in reversed(rows)
    ]

    return messages

# 会话ID
conversation_id = 1
# 限制获取的记录数
limit = 10
# 获取最近N条记录
messages = get_recent_messages(conn, conversation_id, limit)
# 遍历结果
for message in messages:
    print(f"{message['role']}: {message['content']}")

# 关闭连接
conn.close()