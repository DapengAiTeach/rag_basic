from fastapi import FastAPI
from .routers.login_router import router as login_router

# 创建 FastAPI 应用实例
app = FastAPI()
app.include_router(login_router)
