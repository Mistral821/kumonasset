"""
구몬 자산관리 시스템 - 데이터베이스 모델
PostgreSQL / SQLite 지원
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from datetime import datetime
import os

# 데이터베이스 URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./kumon_asset.db"  # SQLite 사용 (개발용)
)

# PostgreSQL URL 형식 변경 (Render.com 대응)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# SQLite용 설정
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


class PCMaster(Base):
    """PC 마스터 정보"""
    __tablename__ = "pc_master"

    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), unique=True, nullable=False, index=True)
    pc_management_number = Column(String(50), nullable=False)
    location_name = Column(String(100), nullable=False)
    employee_number = Column(String(50), nullable=False)
    registered_at = Column(DateTime, default=datetime.now)
    last_updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)

    # 관계
    surveys = relationship("SurveyRecord", back_populates="pc")
    user_changes = relationship("UserChangeHistory", back_populates="pc")


class SurveyRecord(Base):
    """자산조사 기록"""
    __tablename__ = "survey_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), ForeignKey("pc_master.asset_number"), nullable=False)
    survey_date = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, default=datetime.now)

    # 관계
    pc = relationship("PCMaster", back_populates="surveys")


class UserChangeHistory(Base):
    """사용자 변경 이력"""
    __tablename__ = "user_change_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), ForeignKey("pc_master.asset_number"), nullable=False)
    old_employee_number = Column(String(50))
    new_employee_number = Column(String(50), nullable=False)
    changed_at = Column(DateTime, default=datetime.now)

    # 관계
    pc = relationship("PCMaster", back_populates="user_changes")


class MonitorMaster(Base):
    """모니터 마스터 정보"""
    __tablename__ = "monitor_master"

    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), unique=True, nullable=False, index=True)
    monitor_management_number = Column(String(50), nullable=False)
    location_name = Column(String(100), nullable=False)
    employee_number = Column(String(50), nullable=False)
    connected_pc_asset_number = Column(String(50), nullable=True)  # 연결된 PC 자산번호
    registered_at = Column(DateTime, default=datetime.now)
    last_updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    is_deleted = Column(Boolean, default=False)

    # 관계
    surveys = relationship("MonitorSurveyRecord", back_populates="monitor")


class MonitorSurveyRecord(Base):
    """모니터 자산조사 기록"""
    __tablename__ = "monitor_survey_records"

    id = Column(Integer, primary_key=True, index=True)
    asset_number = Column(String(50), ForeignKey("monitor_master.asset_number"), nullable=False)
    survey_date = Column(DateTime, default=datetime.now)
    completed_at = Column(DateTime, default=datetime.now)

    # 관계
    monitor = relationship("MonitorMaster", back_populates="surveys")


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
    print("==> 데이터베이스 테이블 생성 완료")


if __name__ == "__main__":
    print("=== 데이터베이스 초기화 ===")
    init_db()
