from pydantic import BaseModel

# 定义用户登录数据模型
class UserLogin(BaseModel):
    username: str
    password: str