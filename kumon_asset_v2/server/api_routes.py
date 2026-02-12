"""
구몬 자산관리 시스템 - API 라우트
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
import os

from database import get_db, PCMaster, SurveyRecord, UserChangeHistory, MonitorMaster, MonitorSurveyRecord

router = APIRouter()

# 인증 토큰 (환경변수 우선, 없으면 기본값)
CLIENT_TOKEN = os.getenv("CLIENT_TOKEN", "kumon_client_secret_token_2025")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "kumon_admin_secret_token_2025")


def verify_client_token(authorization: str = Header(None)):
    """클라이언트 토큰 검증"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 없습니다")

    token = authorization.replace("Bearer ", "")
    if token != CLIENT_TOKEN:
        raise HTTPException(status_code=403, detail="유효하지 않은 토큰입니다")

    return token


def verify_admin_token(authorization: str = Header(None)):
    """관리자 토큰 검증"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증 토큰이 없습니다")

    token = authorization.replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다")

    return token


# ===== Pydantic 모델 =====

class PCRegisterRequest(BaseModel):
    asset_number: str
    pc_management_number: str
    location_name: str
    employee_number: str


class PCUpdateInfoRequest(BaseModel):
    new_asset_number: Optional[str] = None
    pc_management_number: Optional[str] = None
    location_name: Optional[str] = None
    employee_number: Optional[str] = None


class PCUpdateUserRequest(BaseModel):
    new_employee_number: str


class SurveyCompleteRequest(BaseModel):
    asset_number: str


class PCResponse(BaseModel):
    id: int
    asset_number: str
    pc_management_number: str
    location_name: str
    employee_number: str
    registered_at: datetime
    last_updated_at: datetime

    model_config = {"from_attributes": True}


class SurveyStatusResponse(BaseModel):
    total: int
    completed: int
    remaining: int
    completion_rate: float


class MonitorRegisterRequest(BaseModel):
    asset_number: str
    monitor_management_number: str
    location_name: str
    employee_number: str
    connected_pc_asset_number: Optional[str] = None


class MonitorUpdateRequest(BaseModel):
    monitor_management_number: Optional[str] = None
    location_name: Optional[str] = None
    employee_number: Optional[str] = None
    connected_pc_asset_number: Optional[str] = None


class MonitorResponse(BaseModel):
    id: int
    asset_number: str
    monitor_management_number: str
    location_name: str
    employee_number: str
    connected_pc_asset_number: Optional[str]
    registered_at: datetime
    last_updated_at: datetime

    model_config = {"from_attributes": True}


# ===== API 엔드포인트 =====

@router.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "구몬 자산관리 API",
        "version": "2.1",
        "status": "running"
    }


@router.post("/api/v1/pc/register")
async def register_pc(
    request: PCRegisterRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """PC 등록"""
    # is_deleted 필터 없이 전체 검색 (삭제된 PC 부활 지원)
    existing = db.query(PCMaster).filter(
        PCMaster.asset_number == request.asset_number
    ).first()

    if existing:
        if existing.is_deleted:
            # 삭제된 PC 재등록 (부활)
            existing.is_deleted = False
            existing.pc_management_number = request.pc_management_number
            existing.location_name = request.location_name
            existing.employee_number = request.employee_number
            existing.last_updated_at = datetime.now()

            db.commit()
            db.refresh(existing)

            return {
                "success": True,
                "message": "PC 재등록 완료 (복구됨)",
                "pc_id": existing.id,
                "asset_number": existing.asset_number
            }
        else:
            raise HTTPException(status_code=400, detail="이미 등록된 자산번호입니다")

    # PC 등록
    pc = PCMaster(
        asset_number=request.asset_number,
        pc_management_number=request.pc_management_number,
        location_name=request.location_name,
        employee_number=request.employee_number
    )

    db.add(pc)
    db.commit()
    db.refresh(pc)

    return {
        "success": True,
        "message": "PC 등록 완료",
        "pc_id": pc.id,
        "asset_number": pc.asset_number
    }


@router.get("/api/v1/pc/{asset_number}")
async def get_pc_info(
    asset_number: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """PC 정보 조회"""
    pc = db.query(PCMaster).filter(
        PCMaster.asset_number == asset_number,
        PCMaster.is_deleted == False
    ).first()

    if not pc:
        raise HTTPException(status_code=404, detail="PC 정보를 찾을 수 없습니다")

    return PCResponse.model_validate(pc)


@router.put("/api/v1/pc/{asset_number}/user")
async def update_user(
    asset_number: str,
    request: PCUpdateUserRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """사용자(사번) 변경 - 클라이언트용"""
    pc = db.query(PCMaster).filter(
        PCMaster.asset_number == asset_number,
        PCMaster.is_deleted == False
    ).first()

    if not pc:
        raise HTTPException(status_code=404, detail="PC 정보를 찾을 수 없습니다")

    # 변경 이력 저장
    history = UserChangeHistory(
        asset_number=asset_number,
        old_employee_number=pc.employee_number,
        new_employee_number=request.new_employee_number
    )
    db.add(history)

    # 사용자 변경
    pc.employee_number = request.new_employee_number
    pc.last_updated_at = datetime.now()

    db.commit()

    return {
        "success": True,
        "message": "사용자 변경 완료"
    }


@router.put("/api/v1/admin/pc/{asset_number}/info")
async def update_pc_info(
    asset_number: str,
    request: PCUpdateInfoRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """PC 정보 수정 (관리자, 자산번호 변경 포함)"""
    pc = db.query(PCMaster).filter(
        PCMaster.asset_number == asset_number,
        PCMaster.is_deleted == False
    ).first()

    if not pc:
        raise HTTPException(status_code=404, detail="PC 정보를 찾을 수 없습니다")

    # 자산번호 변경 시 중복 체크 및 Cascade 업데이트
    if request.new_asset_number and request.new_asset_number != asset_number:
        # 중복 체크
        existing = db.query(PCMaster).filter(
            PCMaster.asset_number == request.new_asset_number
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="변경하려는 자산번호가 이미 존재합니다")

        # FK Cascade 수동 처리
        # 1. SurveyRecord
        db.query(SurveyRecord).filter(
            SurveyRecord.asset_number == asset_number
        ).update({"asset_number": request.new_asset_number})

        # 2. UserChangeHistory
        db.query(UserChangeHistory).filter(
            UserChangeHistory.asset_number == asset_number
        ).update({"asset_number": request.new_asset_number})

        # 3. PCMaster
        pc.asset_number = request.new_asset_number

    # 기타 필드 업데이트
    if request.pc_management_number:
        pc.pc_management_number = request.pc_management_number
    if request.location_name:
        pc.location_name = request.location_name
    if request.employee_number:
        pc.employee_number = request.employee_number

    pc.last_updated_at = datetime.now()
    db.commit()

    return {
        "success": True,
        "message": "PC 정보 수정 완료"
    }


@router.post("/api/v1/pc/survey")
async def complete_pc_survey(
    request: SurveyCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """PC 자산조사 완료"""
    # PC 존재 확인
    pc = db.query(PCMaster).filter(
        PCMaster.asset_number == request.asset_number,
        PCMaster.is_deleted == False
    ).first()

    if not pc:
        raise HTTPException(status_code=404, detail="PC 정보를 찾을 수 없습니다")

    # 오늘 이미 조사했는지 확인
    today = date.today()
    existing = db.query(SurveyRecord).filter(
        SurveyRecord.asset_number == request.asset_number,
        func.date(SurveyRecord.survey_date) == today
    ).first()

    if existing:
        return {
            "success": True,
            "message": "오늘 이미 자산조사를 완료했습니다",
            "survey_id": existing.id
        }

    # 조사 기록 저장
    survey = SurveyRecord(
        asset_number=request.asset_number,
        survey_date=datetime.now()
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    return {
        "success": True,
        "message": "PC 자산조사가 완료되었습니다",
        "survey_id": survey.id,
        "completed_at": survey.survey_date.isoformat()
    }


# 레거시 엔드포인트 → 신규 엔드포인트로 리다이렉트
@router.post("/api/v1/survey/complete")
async def complete_survey_legacy(
    request: SurveyCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """자산조사 완료 (레거시 - /api/v1/pc/survey 사용 권장)"""
    return await complete_pc_survey(request, db, token)


# ===== 관리자 API =====

@router.get("/api/v1/admin/pcs")
async def get_all_pcs(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """전체 PC 목록 조회 (관리자) - N+1 최적화"""
    pcs = db.query(PCMaster).filter(PCMaster.is_deleted == False).all()

    # 오늘 조사 완료된 자산번호 목록 (1회 쿼리)
    today = date.today()
    surveyed_assets = set(
        row[0] for row in db.query(SurveyRecord.asset_number).filter(
            func.date(SurveyRecord.survey_date) == today
        ).all()
    )

    # 각 PC의 마지막 조사일 (1회 쿼리)
    last_surveys = dict(
        db.query(
            SurveyRecord.asset_number,
            func.max(SurveyRecord.survey_date)
        ).group_by(SurveyRecord.asset_number).all()
    )

    result = []
    for pc in pcs:
        last_survey = last_surveys.get(pc.asset_number)
        result.append({
            "id": pc.id,
            "asset_number": pc.asset_number,
            "pc_management_number": pc.pc_management_number,
            "location_name": pc.location_name,
            "employee_number": pc.employee_number,
            "registered_at": pc.registered_at.strftime("%Y-%m-%d"),
            "last_updated_at": pc.last_updated_at.isoformat(),
            "surveyed_today": pc.asset_number in surveyed_assets,
            "last_survey_date": last_survey.strftime("%Y-%m-%d %H:%M:%S") if last_survey else None
        })

    return result


@router.get("/api/v1/admin/survey-status")
async def get_survey_status(
    survey_date: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """자산조사 현황 (관리자)"""
    # 전체 PC 수
    total = db.query(PCMaster).filter(PCMaster.is_deleted == False).count()

    # 조사 날짜
    if survey_date:
        target_date = datetime.strptime(survey_date, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    # 조사 완료 수 (삭제된 PC 제외)
    completed = db.query(func.count(func.distinct(SurveyRecord.asset_number))).join(
        PCMaster, SurveyRecord.asset_number == PCMaster.asset_number
    ).filter(
        func.date(SurveyRecord.survey_date) == target_date,
        PCMaster.is_deleted == False
    ).scalar()

    return SurveyStatusResponse(
        total=total,
        completed=completed,
        remaining=total - completed,
        completion_rate=round((completed / total * 100) if total > 0 else 0, 2)
    )


@router.get("/api/v1/admin/survey-history")
async def get_survey_history(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """기간별 조사 이력 조회"""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")

    # SurveyRecord와 PCMaster 조인 (Outer Join)
    results = db.query(SurveyRecord, PCMaster).outerjoin(
        PCMaster, SurveyRecord.asset_number == PCMaster.asset_number
    ).filter(
        func.date(SurveyRecord.survey_date) >= start,
        func.date(SurveyRecord.survey_date) <= end
    ).order_by(SurveyRecord.survey_date.desc()).all()

    history = []
    for survey, pc in results:
        history.append({
            "survey_date": survey.survey_date.strftime("%Y-%m-%d"),
            "asset_number": survey.asset_number,
            "pc_management_number": pc.pc_management_number if pc else "-",
            "location_name": pc.location_name if pc else "정보 없음",
            "employee_number": pc.employee_number if pc else "-"
        })

    return history


@router.delete("/api/v1/admin/pc/{asset_number}")
async def delete_pc(
    asset_number: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """PC 삭제 (관리자)"""
    pc = db.query(PCMaster).filter(
        PCMaster.asset_number == asset_number,
        PCMaster.is_deleted == False
    ).first()

    if not pc:
        raise HTTPException(status_code=404, detail="PC 정보를 찾을 수 없습니다")

    # Soft delete
    pc.is_deleted = True
    db.commit()

    return {
        "success": True,
        "message": "PC 삭제 완료"
    }


@router.get("/api/v1/admin/backup")
async def backup_all_data(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """전체 데이터 백업 (관리자)"""
    pcs = db.query(PCMaster).filter(PCMaster.is_deleted == False).all()
    surveys = db.query(SurveyRecord).all()
    user_changes = db.query(UserChangeHistory).all()
    monitors = db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).all()
    monitor_surveys = db.query(MonitorSurveyRecord).all()

    backup_data = {
        "backup_date": datetime.now().isoformat(),
        "pcs": [
            {
                "asset_number": pc.asset_number,
                "pc_management_number": pc.pc_management_number,
                "location_name": pc.location_name,
                "employee_number": pc.employee_number,
                "registered_at": pc.registered_at.isoformat(),
                "last_updated_at": pc.last_updated_at.isoformat()
            }
            for pc in pcs
        ],
        "surveys": [
            {
                "asset_number": s.asset_number,
                "survey_date": s.survey_date.isoformat(),
                "completed_at": s.completed_at.isoformat()
            }
            for s in surveys
        ],
        "user_changes": [
            {
                "asset_number": uc.asset_number,
                "old_employee_number": uc.old_employee_number,
                "new_employee_number": uc.new_employee_number,
                "changed_at": uc.changed_at.isoformat()
            }
            for uc in user_changes
        ],
        "monitors": [
            {
                "asset_number": m.asset_number,
                "monitor_management_number": m.monitor_management_number,
                "location_name": m.location_name,
                "employee_number": m.employee_number,
                "connected_pc_asset_number": m.connected_pc_asset_number,
                "registered_at": m.registered_at.isoformat(),
                "last_updated_at": m.last_updated_at.isoformat()
            }
            for m in monitors
        ],
        "monitor_surveys": [
            {
                "asset_number": ms.asset_number,
                "survey_date": ms.survey_date.isoformat(),
                "completed_at": ms.completed_at.isoformat()
            }
            for ms in monitor_surveys
        ]
    }

    return backup_data


# ===== 모니터 API =====

@router.post("/api/v1/monitor/register")
async def register_monitor(
    request: MonitorRegisterRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """모니터 등록"""
    # is_deleted 필터 없이 전체 검색 (삭제된 모니터 부활 지원)
    existing = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == request.asset_number
    ).first()

    if existing:
        if existing.is_deleted:
            # 삭제된 모니터 재등록 (부활)
            existing.is_deleted = False
            existing.monitor_management_number = request.monitor_management_number
            existing.location_name = request.location_name
            existing.employee_number = request.employee_number
            existing.connected_pc_asset_number = request.connected_pc_asset_number
            existing.last_updated_at = datetime.now()

            db.commit()
            db.refresh(existing)

            return {
                "success": True,
                "message": "모니터 재등록 완료 (복구됨)",
                "monitor_id": existing.id,
                "asset_number": existing.asset_number
            }
        else:
            raise HTTPException(status_code=400, detail="이미 등록된 자산번호입니다")

    # 모니터 등록
    monitor = MonitorMaster(
        asset_number=request.asset_number,
        monitor_management_number=request.monitor_management_number,
        location_name=request.location_name,
        employee_number=request.employee_number,
        connected_pc_asset_number=request.connected_pc_asset_number
    )

    db.add(monitor)
    db.commit()
    db.refresh(monitor)

    return {
        "success": True,
        "message": "모니터 등록 완료",
        "monitor_id": monitor.id,
        "asset_number": monitor.asset_number
    }


@router.get("/api/v1/monitor/{asset_number}")
async def get_monitor_info(
    asset_number: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """모니터 정보 조회"""
    monitor = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == asset_number,
        MonitorMaster.is_deleted == False
    ).first()

    if not monitor:
        raise HTTPException(status_code=404, detail="모니터 정보를 찾을 수 없습니다")

    return MonitorResponse.model_validate(monitor)


@router.put("/api/v1/monitor/{asset_number}")
async def update_monitor(
    asset_number: str,
    request: MonitorUpdateRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """모니터 정보 수정"""
    monitor = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == asset_number,
        MonitorMaster.is_deleted == False
    ).first()

    if not monitor:
        raise HTTPException(status_code=404, detail="모니터 정보를 찾을 수 없습니다")

    # 수정
    if request.monitor_management_number:
        monitor.monitor_management_number = request.monitor_management_number
    if request.location_name:
        monitor.location_name = request.location_name
    if request.employee_number:
        monitor.employee_number = request.employee_number
    if request.connected_pc_asset_number is not None:
        monitor.connected_pc_asset_number = request.connected_pc_asset_number

    monitor.last_updated_at = datetime.now()

    db.commit()
    db.refresh(monitor)

    return {
        "success": True,
        "message": "모니터 정보 수정 완료"
    }


@router.post("/api/v1/monitor/survey")
async def complete_monitor_survey(
    request: SurveyCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """모니터 자산조사 완료"""
    # 모니터 존재 확인
    monitor = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == request.asset_number,
        MonitorMaster.is_deleted == False
    ).first()

    if not monitor:
        raise HTTPException(status_code=404, detail="모니터를 찾을 수 없습니다")

    # 오늘 날짜로 이미 조사했는지 확인
    today = date.today()
    existing_survey = db.query(MonitorSurveyRecord).filter(
        MonitorSurveyRecord.asset_number == request.asset_number,
        func.date(MonitorSurveyRecord.survey_date) == today
    ).first()

    if existing_survey:
        return {
            "success": True,
            "message": "이미 오늘 조사 완료된 모니터입니다",
            "survey_id": existing_survey.id
        }

    # 조사 기록 생성
    survey = MonitorSurveyRecord(
        asset_number=request.asset_number
    )

    db.add(survey)
    db.commit()
    db.refresh(survey)

    return {
        "success": True,
        "message": "모니터 자산조사 완료",
        "survey_id": survey.id,
        "completed_at": survey.completed_at.isoformat()
    }


# ===== 관리자 API - 모니터 =====

@router.get("/api/v1/admin/monitors")
async def get_all_monitors(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """전체 모니터 목록 조회 (관리자) - N+1 최적화"""
    monitors = db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).all()

    # 각 모니터의 마지막 조사일 (1회 쿼리)
    last_surveys = dict(
        db.query(
            MonitorSurveyRecord.asset_number,
            func.max(MonitorSurveyRecord.completed_at)
        ).group_by(MonitorSurveyRecord.asset_number).all()
    )

    result = []
    for monitor in monitors:
        last_survey = last_surveys.get(monitor.asset_number)
        result.append({
            "asset_number": monitor.asset_number,
            "monitor_management_number": monitor.monitor_management_number,
            "location_name": monitor.location_name,
            "employee_number": monitor.employee_number,
            "connected_pc_asset_number": monitor.connected_pc_asset_number,
            "registered_at": monitor.registered_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_updated_at": monitor.last_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "last_survey_date": last_survey.strftime("%Y-%m-%d %H:%M:%S") if last_survey else None
        })

    return result


@router.put("/api/v1/admin/monitor/{asset_number}")
async def admin_update_monitor(
    asset_number: str,
    request: MonitorUpdateRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """모니터 정보 수정 (관리자)"""
    monitor = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == asset_number,
        MonitorMaster.is_deleted == False
    ).first()

    if not monitor:
        raise HTTPException(status_code=404, detail="모니터를 찾을 수 없습니다")

    if request.monitor_management_number:
        monitor.monitor_management_number = request.monitor_management_number
    if request.location_name:
        monitor.location_name = request.location_name
    if request.employee_number:
        monitor.employee_number = request.employee_number
    if request.connected_pc_asset_number is not None:
        monitor.connected_pc_asset_number = request.connected_pc_asset_number

    monitor.last_updated_at = datetime.now()
    db.commit()

    return {
        "success": True,
        "message": "모니터 정보 수정 완료"
    }


@router.delete("/api/v1/admin/monitor/{asset_number}")
async def delete_monitor(
    asset_number: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """모니터 삭제 (관리자)"""
    monitor = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == asset_number,
        MonitorMaster.is_deleted == False
    ).first()

    if not monitor:
        raise HTTPException(status_code=404, detail="모니터를 찾을 수 없습니다")

    # Soft delete
    monitor.is_deleted = True
    db.commit()

    return {
        "success": True,
        "message": "모니터 삭제 완료"
    }


@router.get("/api/v1/admin/monitor-survey-status")
async def get_monitor_survey_status(
    survey_date: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """모니터 자산조사 현황 (관리자)"""
    # 전체 모니터 수
    total = db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).count()

    # 조사 날짜 설정
    if survey_date:
        target_date = datetime.strptime(survey_date, "%Y-%m-%d").date()
    else:
        target_date = date.today()

    # 조사 완료 수
    completed = db.query(func.count(func.distinct(MonitorSurveyRecord.asset_number))).join(
        MonitorMaster,
        and_(
            MonitorSurveyRecord.asset_number == MonitorMaster.asset_number,
            MonitorMaster.is_deleted == False
        )
    ).filter(
        func.date(MonitorSurveyRecord.survey_date) == target_date
    ).scalar()

    return SurveyStatusResponse(
        total=total,
        completed=completed,
        remaining=total - completed,
        completion_rate=round((completed / total * 100), 2) if total > 0 else 0.0
    )
