import json
import psycopg

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from environs import Env
from openai import OpenAI


# ----------------------------
# 配置与常量
# ----------------------------
SYSTEM_PROMPT = "你是一个严谨的技术助教"
DEFAULT_USER_ID = "demo_user"


# ----------------------------
# PostgreSQL 数据访问层
# ----------------------------
@dataclass
class pg_chat_store:
    """
    负责：
    - 创建会话
    - 写入消息
    - 查询最近 N 条上下文
    - 清理演示数据（可选）
    """
    conn: psycopg.Connection

    def create_conversation(self, user_id: str, title: Optional[str] = None) -> int:
        """
        创建一条会话记录，返回 conversation_id
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO conversation (user_id, title)
                VALUES (%s, %s)
                RETURNING id
                """,
                (user_id, title),
            )
            conversation_id = cursor.fetchone()[0]
        self.conn.commit()
        return int(conversation_id)

    def touch_conversation(self, conversation_id: int) -> None:
        """
        更新会话的 updated_at（表示最近活跃）
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE conversation
                SET updated_at = NOW()
                WHERE id = %s
                """,
                (conversation_id,),
            )
        self.conn.commit()

    def insert_message(self, conversation_id: int, role: str, text: str, extra: Optional[Dict[str, Any]] = None) -> None:
        """
        写入一条聊天消息：
        - content 使用 JSONB，至少包含 text
        - extra 用来扩展存 model、token、tool_calls 等信息
        """
        payload: Dict[str, Any] = {"text": text}
        if extra:
            payload.update(extra)

        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_message (conversation_id, role, content)
                VALUES (%s, %s, %s)
                """,
                (conversation_id, role, json.dumps(payload, ensure_ascii=False)),
            )
        self.conn.commit()

        # 写完消息后更新会话活跃时间
        self.touch_conversation(conversation_id)

    def get_recent_messages_for_llm(self, conversation_id: int, limit: int = 10) -> List[Dict[str, str]]:
        """
        查询最近 N 条消息，按时间正序返回，供 LLM 直接使用：
        [
          {"role": "user", "content": "..."},
          {"role": "assistant", "content": "..."},
        ]
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT role, content
                FROM chat_message
                WHERE conversation_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (conversation_id, limit),
            )
            rows = cursor.fetchall()

        # 倒序取出来需要反转，确保喂给模型是时间正序
        messages: List[Dict[str, str]] = []
        for role, content in reversed(rows):
            # psycopg 会把 jsonb 自动解成 dict（多数环境如此），否则可能是 str
            if isinstance(content, str):
                content_obj = json.loads(content)
            else:
                content_obj = content

            messages.append({"role": role, "content": content_obj.get("text", "")})

        return messages

    def wipe_demo_data(self, user_id: str) -> None:
        """
        清空演示数据：删除该 user_id 的所有会话（级联删除消息）
        """
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM conversation
                WHERE user_id = %s
                """,
                (user_id,),
            )
        self.conn.commit()


# ----------------------------
# OpenAI 流式调用
# ----------------------------
def stream_chat_completion(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
) -> str:
    """
    发起流式请求：
    - 实时打印
    - 同时拼接完整回复
    - 返回最终完整文本（用于写回 DB）
    """
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )

    full_parts: List[str] = []

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            print(delta.content, end="", flush=True)
            full_parts.append(delta.content)

    print()
    return "".join(full_parts)


# ----------------------------
# 主程序：终端聊天机器人
# ----------------------------
# 读取 .env
env = Env()
env.read_env(".env")

# OpenAI 配置（兼容接口）
api_key = env.str("OPENAI_API_KEY")
base_url = env.str("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
model_name = env.str("OPENAI_MODEL", "Qwen/Qwen3-8B")

# 创建 OpenAI 客户端
client = OpenAI(api_key=api_key, base_url=base_url)

# PostgreSQL 连接（本机 docker 的默认配置）
conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="rag",
    user="postgres",
    password="postgres",
)

# 创建一个数据库存储
store = pg_chat_store(conn=conn)

# 创建一个新的会话（/reset 时会重建）
conversation_id = store.create_conversation(
    user_id=DEFAULT_USER_ID,
    title="demo_chat",
)
# 最近 N 条上下文
context_limit = 10

print("输入 /exit 退出，输入 /reset 新会话，输入 /wipe 清空演示数据。\n")
try:
    while True:
        user_input = input("你：").strip()
        if not user_input:
            continue

        if user_input == "/exit":
            print("已退出。")
            break

        if user_input == "/reset":
            conversation_id = store.create_conversation(user_id=DEFAULT_USER_ID, title="demo_chat_reset")
            print(f"已创建新会话 conversation_id={conversation_id}")
            continue

        if user_input == "/wipe":
            store.wipe_demo_data(user_id=DEFAULT_USER_ID)
            conversation_id = store.create_conversation(user_id=DEFAULT_USER_ID, title="demo_chat_after_wipe")
            print("已清空演示数据，并创建新会话。")
            continue

        # 1) 写入用户消息到 DB（长期记忆）
        store.insert_message(conversation_id, "user", user_input)

        # 2) 查询最近 N 条上下文 + system prompt
        recent_messages = store.get_recent_messages_for_llm(conversation_id, limit=context_limit)
        llm_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + recent_messages

        # 3) 调用模型（流式输出）
        print("助教：", end="", flush=True)
        assistant_reply = stream_chat_completion(
            client=client,
            model=model_name,
            messages=llm_messages,
            temperature=0.7,
        )

        # 4) 写入助手回复到 DB
        store.insert_message(
            conversation_id,
            "assistant",
            assistant_reply,
            extra={"model": model_name},
        )

finally:
    conn.close()
