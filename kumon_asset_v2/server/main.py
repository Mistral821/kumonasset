"""
구몬 자산관리 시스템 - FastAPI 서버
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import init_db
from api_routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 시 실행"""
    print("==> 서버 시작 중...")
    init_db()
    print("==> 서버 준비 완료!")
    yield
    print("==> 서버 종료")


# FastAPI 앱 생성
app = FastAPI(
    title="구몬 자산관리 API",
    description="현장 PC 자산 관리 및 자산조사 시스템",
    version="2.1",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router)


if __name__ == "__main__":
    # 로컬 테스트용
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
