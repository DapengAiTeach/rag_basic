import json
import os
from dataclasses import dataclass, field
from typing import Iterable, List, Dict

from environs import Env
from openai import OpenAI


@dataclass
class chat_history_manager:
    """
    一个简单但够用的历史记录管理器：
    - 负责维护 messages 列表
    - 负责追加 user/assistant 消息
    - 负责做“按条数裁剪”的基础策略（避免无限增长）
    """
    system_prompt: str
    # 保留最近多少轮（1轮=1次user+1次assistant）
    max_turns: int = 10
    messages: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        # 初始化时把 system 放在第一条，且只放一次
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def add_user_message(self, user_content: str) -> None:
        self.messages.append({"role": "user", "content": user_content})
        self._trim_history()

    def add_assistant_message(self, assistant_content: str) -> None:
        self.messages.append({"role": "assistant", "content": assistant_content})
        self._trim_history()

    def _trim_history(self) -> None:
        """
        最朴素的裁剪策略：按“轮数”裁剪。
        - system 永远保留
        - 只保留最近 max_turns 轮对话
        这不是最精确的 token 裁剪，但对零基础同学最好理解、最稳定。
        """
        # 除 system 外的历史条数
        history = self.messages[1:]

        # 每轮2条：user + assistant
        max_history_items = self.max_turns * 2

        if len(history) <= max_history_items:
            return

        # 丢弃最早的部分，只保留最近的
        history = history[-max_history_items:]
        self.messages = [self.messages[0]] + history

    def dump_jsonl(self, file_path: str) -> None:
        """
        把当前 messages 落盘
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            for item in self.messages:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")


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
    - 返回最终完整文本（用于写回历史）
    """
    stream = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
    )

    full_content_parts: List[str] = []

    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta and delta.content:
            # 1) 实时输出到终端
            print(delta.content, end="", flush=True)
            # 2) 同时收集起来，便于落到历史记录里
            full_content_parts.append(delta.content)

    print()  # 换行
    return "".join(full_content_parts)



# 读取 .env 配置
env = Env()
env.read_env("../.env")

# 模型相关的参数
api_key = env.str("OPENAI_API_KEY")
base_url = env.str("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
model_name = "Qwen/Qwen3-8B"

# 初始化 OpenAI 客户端（兼容接口）
client = OpenAI(api_key=api_key, base_url=base_url)

# 初始化历史管理器（system 只放一次）
history = chat_history_manager(
    system_prompt="你是一个严谨的技术助教",
    max_turns=8,  # 只保留最近 8 轮，避免上下文越来越大
)

# 欢迎语
print("输入 /exit 退出，输入 /reset 清空历史。\n")
while True:
    user_input = input("你：").strip()
    if not user_input:
        continue

    if user_input == "/exit":
        # 退出前落盘一次，方便你做课堂复盘
        history.dump_jsonl("run_data/chat_history.jsonl")
        print("已保存历史到 run_data/chat_history.jsonl")
        break

    if user_input == "/reset":
        # 清空历史 = 重新初始化，只保留 system
        history = chat_history_manager(
            system_prompt="你是一个严谨的技术助教",
            max_turns=8,
        )
        print("历史已清空。")
        continue

    # 追加用户消息
    history.add_user_message(user_input)

    # 调用模型（流式输出）
    print("助教：", end="", flush=True)
    assistant_reply = stream_chat_completion(
        client=client,
        model=model_name,
        messages=history.messages,
        temperature=0.7,
    )

    # 把完整回复写回历史
    history.add_assistant_message(assistant_reply)

