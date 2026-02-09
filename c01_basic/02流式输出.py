from openai import OpenAI
from environs import Env

# 加载 .env 文件中的环境变量
env = Env()
env.read_env("../.env")

# 从环境变量中读取配置
api_key = env.str("OPENAI_API_KEY")
base_url = env.str("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")

# 初始化 OpenAI 客户端（兼容接口）
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 消息列表
messages = [
    {"role": "system", "content": "你是一个严谨的技术助教"},
    {"role": "user", "content": "用一句话解释什么是大语言模型"}
]

# 使用流式输出模式
stream = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=messages,
    temperature=0.7,
    stream=True,   # 👈 核心开关
)

# 实时打印模型输出
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta and delta.content:
        print(delta.content, end="", flush=True)
print()  # 换行