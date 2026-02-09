from openai import OpenAI
from environs import Env

# 加载 .env 文件中的环境变量
env = Env()
env.read_env("../.env")

# 从环境变量中读取配置
api_key = env.str("OPENAI_API_KEY")
base_url = env.str("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")

# 使用硅基流动的 OpenAI 兼容地址
client = OpenAI(
    api_key=api_key,
    base_url=base_url
)

# 消息列表
messages = [
    {"role": "system", "content": "你是一个严谨的技术助教"},
    {"role": "user", "content": "用一句话解释什么是大语言模型"}
]
response = client.chat.completions.create(
    model="Qwen/Qwen3-8B",
    messages=messages,
    temperature=0.7
)
print(response.choices[0].message.content)
