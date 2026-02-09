"""
구몬 자산관리 시스템 - FastAPI 서버
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import init_db
from api_routes import router

# FastAPI 앱 생성
app = FastAPI(
    title="구몬 자산관리 API",
    description="현장 PC 자산 관리 및 자산조사 시스템",
    version="2.0"
)

# CORS 설정 (모든 클라이언트 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 데이터베이스 초기화"""
    print("==> 서버 시작 중...")
    init_db()
    print("==> 서버 준비 완료!")


if __name__ == "__main__":
    # 로컬 테스트용
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
