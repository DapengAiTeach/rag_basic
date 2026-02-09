from fastapi import FastAPI, HTTPException
from .schemas.login_schema import UserLogin
from .mocks.user_mock import fake_user_db

# 创建 FastAPI 应用实例
app = FastAPI()


# 登录接口
@app.post("/login")
async def login(user: UserLogin):
    # 验证用户名和密码
    if user.username in fake_user_db and fake_user_db[user.username]["password"] == user.password:
        return {"message": "Login successful!"}
    else:
        raise HTTPException(status_code=401, detail="Invalid credentials")