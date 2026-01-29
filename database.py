"""
구몬 자산관리 시스템 - 데이터베이스 모델
PostgreSQL 사용
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# 데이터베이스 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/kumon_asset"
)

# PostgreSQL URL 형식 변경 (Render.com 대응)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class PCMaster(Base):
    """PC 마스터 정보"""
    __tablename__ = "pc_master"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), unique=True, nullable=False, index=True)
    pc_management_number = Column(String(50), nullable=False)
    location_name = Column(String(100), nullable=False)
    employee_number = Column(String(50), nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = Column(Boolean, default=False)
    
    # 관계
    surveys = relationship("SurveyRecord", back_populates="pc")
    user_changes = relationship("UserChangeHistory", back_populates="pc")


class SurveyRecord(Base):
    """자산조사 기록"""
    __tablename__ = "survey_records"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), ForeignKey("pc_master.asset_number"), nullable=False)
    survey_date = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    pc = relationship("PCMaster", back_populates="surveys")


class UserChangeHistory(Base):
    """사용자 변경 이력"""
    __tablename__ = "user_change_history"
    
    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), ForeignKey("pc_master.asset_number"), nullable=False)
    old_employee_number = Column(String(50))
    new_employee_number = Column(String(50), nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow)
    
    # 관계
    pc = relationship("PCMaster", back_populates="user_changes")


def get_db():
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 초기화 (테이블 생성)"""
    Base.metadata.create_all(bind=engine)
    print("✅ 데이터베이스 테이블 생성 완료")


if __name__ == "__main__":
    print("=== 데이터베이스 초기화 ===")
    init_db()
