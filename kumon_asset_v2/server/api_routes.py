"""
구몬 자산관리 시스템 - API 라우트
캠페인 관리, 대시보드, 자산 이력 포함
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel
import os
import json

from database import (
    get_db, PCMaster, SurveyRecord, UserChangeHistory,
    MonitorMaster, MonitorSurveyRecord, AuditCampaign, AssetHistory
)

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


def record_history(db: Session, asset_type: str, asset_number: str,
                   action_type: str, description: str = None,
                   old_value: str = None, new_value: str = None):
    """자산 이력 자동 기록"""
    history = AssetHistory(
        asset_type=asset_type,
        asset_number=asset_number,
        action_type=action_type,
        description=description,
        old_value=old_value,
        new_value=new_value
    )
    db.add(history)


def get_active_campaign(db: Session) -> Optional[AuditCampaign]:
    """현재 진행 중인 캠페인 조회"""
    today = date.today()
    return db.query(AuditCampaign).filter(
        AuditCampaign.status == "진행중",
        AuditCampaign.start_date <= today,
        AuditCampaign.end_date >= today
    ).first()


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
    campaign_id: Optional[int] = None  # 클라이언트에서 직접 지정 가능


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


class CampaignCreateRequest(BaseModel):
    name: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    description: Optional[str] = None


class CampaignUpdateRequest(BaseModel):
    name: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: Optional[str] = None  # 대기 / 진행중 / 완료
    description: Optional[str] = None


# ===== 기본 API =====

@router.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "구몬 자산관리 API",
        "version": "3.0",
        "status": "running"
    }


@router.get("/api/v1/active-campaign")
async def get_active_campaign_info(
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """현재 활성 캠페인 조회 (클라이언트용)"""
    campaign = get_active_campaign(db)
    if not campaign:
        return {"active": False, "campaign": None}

    return {
        "active": True,
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "start_date": campaign.start_date.isoformat(),
            "end_date": campaign.end_date.isoformat()
        }
    }


# ===== PC API =====

@router.post("/api/v1/pc/register")
async def register_pc(
    request: PCRegisterRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """PC 등록"""
    existing = db.query(PCMaster).filter(
        PCMaster.asset_number == request.asset_number
    ).first()

    if existing:
        if existing.is_deleted:
            existing.is_deleted = False
            existing.pc_management_number = request.pc_management_number
            existing.location_name = request.location_name
            existing.employee_number = request.employee_number
            existing.last_updated_at = datetime.now()

            record_history(db, "PC", request.asset_number, "복구",
                          f"삭제된 PC 재등록: {request.location_name}")
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

    pc = PCMaster(
        asset_number=request.asset_number,
        pc_management_number=request.pc_management_number,
        location_name=request.location_name,
        employee_number=request.employee_number
    )
    db.add(pc)

    record_history(db, "PC", request.asset_number, "등록",
                  f"신규 PC 등록: {request.location_name}, 사번: {request.employee_number}")
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

    old_emp = pc.employee_number
    history = UserChangeHistory(
        asset_number=asset_number,
        old_employee_number=old_emp,
        new_employee_number=request.new_employee_number
    )
    db.add(history)

    record_history(db, "PC", asset_number, "사번변경",
                  f"사번 변경: {old_emp} → {request.new_employee_number}",
                  old_emp, request.new_employee_number)

    pc.employee_number = request.new_employee_number
    pc.last_updated_at = datetime.now()
    db.commit()

    return {"success": True, "message": "사용자 변경 완료"}


@router.put("/api/v1/admin/pc/{asset_number}/info")
async def update_pc_info(
    asset_number: str,
    request: PCUpdateInfoRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """PC 정보 수정 (관리자)"""
    pc = db.query(PCMaster).filter(
        PCMaster.asset_number == asset_number,
        PCMaster.is_deleted == False
    ).first()

    if not pc:
        raise HTTPException(status_code=404, detail="PC 정보를 찾을 수 없습니다")

    changes = []

    if request.new_asset_number and request.new_asset_number != asset_number:
        existing = db.query(PCMaster).filter(
            PCMaster.asset_number == request.new_asset_number
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="변경하려는 자산번호가 이미 존재합니다")

        db.query(SurveyRecord).filter(
            SurveyRecord.asset_number == asset_number
        ).update({"asset_number": request.new_asset_number})
        db.query(UserChangeHistory).filter(
            UserChangeHistory.asset_number == asset_number
        ).update({"asset_number": request.new_asset_number})

        changes.append(f"자산번호: {asset_number} → {request.new_asset_number}")
        pc.asset_number = request.new_asset_number

    if request.pc_management_number:
        changes.append(f"관리번호: {pc.pc_management_number} → {request.pc_management_number}")
        pc.pc_management_number = request.pc_management_number
    if request.location_name:
        changes.append(f"사업장: {pc.location_name} → {request.location_name}")
        pc.location_name = request.location_name
    if request.employee_number:
        changes.append(f"사번: {pc.employee_number} → {request.employee_number}")
        pc.employee_number = request.employee_number

    pc.last_updated_at = datetime.now()

    record_history(db, "PC", request.new_asset_number or asset_number, "수정",
                  ", ".join(changes) if changes else "정보 수정")
    db.commit()

    return {"success": True, "message": "PC 정보 수정 완료"}


@router.post("/api/v1/pc/survey")
async def complete_pc_survey(
    request: SurveyCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """PC 자산조사 완료"""
    pc = db.query(PCMaster).filter(
        PCMaster.asset_number == request.asset_number,
        PCMaster.is_deleted == False
    ).first()

    if not pc:
        raise HTTPException(status_code=404, detail="PC 정보를 찾을 수 없습니다")

    # 활성 캠페인 자동 감지
    campaign_id = request.campaign_id
    if not campaign_id:
        active = get_active_campaign(db)
        if active:
            campaign_id = active.id

    # 오늘 + 동일 캠페인으로 이미 조사했는지 확인
    today = date.today()
    existing_query = db.query(SurveyRecord).filter(
        SurveyRecord.asset_number == request.asset_number,
        func.date(SurveyRecord.survey_date) == today
    )
    if campaign_id:
        existing_query = existing_query.filter(SurveyRecord.campaign_id == campaign_id)
    existing = existing_query.first()

    if existing:
        return {
            "success": True,
            "message": "오늘 이미 자산조사를 완료했습니다",
            "survey_id": existing.id
        }

    survey = SurveyRecord(
        asset_number=request.asset_number,
        campaign_id=campaign_id,
        survey_date=datetime.now()
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    return {
        "success": True,
        "message": "PC 자산조사가 완료되었습니다",
        "survey_id": survey.id,
        "campaign_id": campaign_id,
        "completed_at": survey.survey_date.isoformat()
    }


# 레거시 엔드포인트
@router.post("/api/v1/survey/complete")
async def complete_survey_legacy(
    request: SurveyCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """자산조사 완료 (레거시)"""
    return await complete_pc_survey(request, db, token)


# ===== 관리자 PC API =====

@router.get("/api/v1/admin/pcs")
async def get_all_pcs(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """전체 PC 목록 조회 (관리자)"""
    pcs = db.query(PCMaster).filter(PCMaster.is_deleted == False).all()

    today = date.today()
    surveyed_assets = set(
        row[0] for row in db.query(SurveyRecord.asset_number).filter(
            func.date(SurveyRecord.survey_date) == today
        ).all()
    )

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
    total = db.query(PCMaster).filter(PCMaster.is_deleted == False).count()
    target_date = datetime.strptime(survey_date, "%Y-%m-%d").date() if survey_date else date.today()

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

    pc.is_deleted = True
    record_history(db, "PC", asset_number, "삭제",
                  f"PC 삭제: {pc.location_name}, 사번: {pc.employee_number}")
    db.commit()

    return {"success": True, "message": "PC 삭제 완료"}


# ===== 모니터 API =====

@router.post("/api/v1/monitor/register")
async def register_monitor(
    request: MonitorRegisterRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """모니터 등록"""
    existing = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == request.asset_number
    ).first()

    if existing:
        if existing.is_deleted:
            existing.is_deleted = False
            existing.monitor_management_number = request.monitor_management_number
            existing.location_name = request.location_name
            existing.employee_number = request.employee_number
            existing.connected_pc_asset_number = request.connected_pc_asset_number
            existing.last_updated_at = datetime.now()

            record_history(db, "모니터", request.asset_number, "복구",
                          f"삭제된 모니터 재등록: {request.location_name}")
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

    monitor = MonitorMaster(
        asset_number=request.asset_number,
        monitor_management_number=request.monitor_management_number,
        location_name=request.location_name,
        employee_number=request.employee_number,
        connected_pc_asset_number=request.connected_pc_asset_number
    )
    db.add(monitor)

    record_history(db, "모니터", request.asset_number, "등록",
                  f"신규 모니터 등록: {request.location_name}, 사번: {request.employee_number}")
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

    changes = []
    if request.monitor_management_number:
        changes.append(f"관리번호: {monitor.monitor_management_number} → {request.monitor_management_number}")
        monitor.monitor_management_number = request.monitor_management_number
    if request.location_name:
        changes.append(f"사업장: {monitor.location_name} → {request.location_name}")
        monitor.location_name = request.location_name
    if request.employee_number:
        changes.append(f"사번: {monitor.employee_number} → {request.employee_number}")
        monitor.employee_number = request.employee_number
    if request.connected_pc_asset_number is not None:
        monitor.connected_pc_asset_number = request.connected_pc_asset_number

    monitor.last_updated_at = datetime.now()

    record_history(db, "모니터", asset_number, "수정",
                  ", ".join(changes) if changes else "정보 수정")
    db.commit()
    db.refresh(monitor)

    return {"success": True, "message": "모니터 정보 수정 완료"}


@router.post("/api/v1/monitor/survey")
async def complete_monitor_survey(
    request: SurveyCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """모니터 자산조사 완료"""
    monitor = db.query(MonitorMaster).filter(
        MonitorMaster.asset_number == request.asset_number,
        MonitorMaster.is_deleted == False
    ).first()

    if not monitor:
        raise HTTPException(status_code=404, detail="모니터를 찾을 수 없습니다")

    campaign_id = request.campaign_id
    if not campaign_id:
        active = get_active_campaign(db)
        if active:
            campaign_id = active.id

    today = date.today()
    existing_query = db.query(MonitorSurveyRecord).filter(
        MonitorSurveyRecord.asset_number == request.asset_number,
        func.date(MonitorSurveyRecord.survey_date) == today
    )
    if campaign_id:
        existing_query = existing_query.filter(MonitorSurveyRecord.campaign_id == campaign_id)
    existing_survey = existing_query.first()

    if existing_survey:
        return {
            "success": True,
            "message": "이미 오늘 조사 완료된 모니터입니다",
            "survey_id": existing_survey.id
        }

    survey = MonitorSurveyRecord(
        asset_number=request.asset_number,
        campaign_id=campaign_id
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)

    return {
        "success": True,
        "message": "모니터 자산조사 완료",
        "survey_id": survey.id,
        "campaign_id": campaign_id,
        "completed_at": survey.completed_at.isoformat()
    }


# ===== 관리자 모니터 API =====

@router.get("/api/v1/admin/monitors")
async def get_all_monitors(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """전체 모니터 목록 조회 (관리자)"""
    monitors = db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).all()

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

    changes = []
    if request.monitor_management_number:
        changes.append(f"관리번호 변경")
        monitor.monitor_management_number = request.monitor_management_number
    if request.location_name:
        changes.append(f"사업장 변경")
        monitor.location_name = request.location_name
    if request.employee_number:
        changes.append(f"사번 변경")
        monitor.employee_number = request.employee_number
    if request.connected_pc_asset_number is not None:
        monitor.connected_pc_asset_number = request.connected_pc_asset_number

    monitor.last_updated_at = datetime.now()
    record_history(db, "모니터", asset_number, "수정", ", ".join(changes) if changes else "정보 수정")
    db.commit()

    return {"success": True, "message": "모니터 정보 수정 완료"}


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

    monitor.is_deleted = True
    record_history(db, "모니터", asset_number, "삭제",
                  f"모니터 삭제: {monitor.location_name}")
    db.commit()

    return {"success": True, "message": "모니터 삭제 완료"}


@router.get("/api/v1/admin/monitor-survey-status")
async def get_monitor_survey_status(
    survey_date: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """모니터 자산조사 현황"""
    total = db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).count()
    target_date = datetime.strptime(survey_date, "%Y-%m-%d").date() if survey_date else date.today()

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


# ===== 캠페인 관리 API =====

@router.post("/api/v1/admin/campaigns")
async def create_campaign(
    request: CampaignCreateRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """실사 캠페인 생성"""
    try:
        start = datetime.strptime(request.start_date, "%Y-%m-%d").date()
        end = datetime.strptime(request.end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)")

    if end <= start:
        raise HTTPException(status_code=400, detail="종료일은 시작일보다 이후여야 합니다")

    campaign = AuditCampaign(
        name=request.name,
        start_date=start,
        end_date=end,
        description=request.description
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return {
        "success": True,
        "message": "캠페인 생성 완료",
        "campaign_id": campaign.id
    }


@router.get("/api/v1/admin/campaigns")
async def get_campaigns(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """캠페인 목록 조회"""
    campaigns = db.query(AuditCampaign).order_by(AuditCampaign.created_at.desc()).all()

    result = []
    for c in campaigns:
        # 각 캠페인의 조사 수 계산
        pc_count = db.query(func.count(func.distinct(SurveyRecord.asset_number))).filter(
            SurveyRecord.campaign_id == c.id
        ).scalar()
        monitor_count = db.query(func.count(func.distinct(MonitorSurveyRecord.asset_number))).filter(
            MonitorSurveyRecord.campaign_id == c.id
        ).scalar()

        result.append({
            "id": c.id,
            "name": c.name,
            "start_date": c.start_date.isoformat(),
            "end_date": c.end_date.isoformat(),
            "status": c.status,
            "description": c.description or "",
            "pc_surveyed": pc_count,
            "monitor_surveyed": monitor_count,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return result


@router.put("/api/v1/admin/campaigns/{campaign_id}")
async def update_campaign(
    campaign_id: int,
    request: CampaignUpdateRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """캠페인 수정/상태 변경"""
    campaign = db.query(AuditCampaign).filter(AuditCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="캠페인을 찾을 수 없습니다")

    if request.name:
        campaign.name = request.name
    if request.start_date:
        campaign.start_date = datetime.strptime(request.start_date, "%Y-%m-%d").date()
    if request.end_date:
        campaign.end_date = datetime.strptime(request.end_date, "%Y-%m-%d").date()
    if request.status:
        if request.status not in ("대기", "진행중", "완료"):
            raise HTTPException(status_code=400, detail="상태는 대기/진행중/완료 중 하나여야 합니다")
        campaign.status = request.status
    if request.description is not None:
        campaign.description = request.description

    db.commit()

    return {"success": True, "message": "캠페인 수정 완료"}


@router.get("/api/v1/admin/campaigns/{campaign_id}/progress")
async def get_campaign_progress(
    campaign_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """캠페인 진행률 (PC + 모니터 통합)"""
    campaign = db.query(AuditCampaign).filter(AuditCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="캠페인을 찾을 수 없습니다")

    # PC
    total_pcs = db.query(PCMaster).filter(PCMaster.is_deleted == False).count()
    surveyed_pcs = db.query(func.count(func.distinct(SurveyRecord.asset_number))).filter(
        SurveyRecord.campaign_id == campaign_id
    ).scalar()

    # 모니터
    total_monitors = db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).count()
    surveyed_monitors = db.query(func.count(func.distinct(MonitorSurveyRecord.asset_number))).filter(
        MonitorSurveyRecord.campaign_id == campaign_id
    ).scalar()

    total_all = total_pcs + total_monitors
    surveyed_all = surveyed_pcs + surveyed_monitors

    return {
        "campaign": {
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "start_date": campaign.start_date.isoformat(),
            "end_date": campaign.end_date.isoformat()
        },
        "pc": {
            "total": total_pcs,
            "completed": surveyed_pcs,
            "remaining": total_pcs - surveyed_pcs,
            "rate": round((surveyed_pcs / total_pcs * 100) if total_pcs > 0 else 0, 1)
        },
        "monitor": {
            "total": total_monitors,
            "completed": surveyed_monitors,
            "remaining": total_monitors - surveyed_monitors,
            "rate": round((surveyed_monitors / total_monitors * 100) if total_monitors > 0 else 0, 1)
        },
        "total": {
            "total": total_all,
            "completed": surveyed_all,
            "remaining": total_all - surveyed_all,
            "rate": round((surveyed_all / total_all * 100) if total_all > 0 else 0, 1)
        }
    }


@router.get("/api/v1/admin/campaigns/{campaign_id}/unaudited")
async def get_unaudited_assets(
    campaign_id: int,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """캠페인 미실사 자산 조회"""
    campaign = db.query(AuditCampaign).filter(AuditCampaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="캠페인을 찾을 수 없습니다")

    # 캠페인에서 조사 완료된 PC 자산번호
    surveyed_pc_assets = set(
        row[0] for row in db.query(SurveyRecord.asset_number).filter(
            SurveyRecord.campaign_id == campaign_id
        ).distinct().all()
    )
    # 캠페인에서 조사 완료된 모니터 자산번호
    surveyed_monitor_assets = set(
        row[0] for row in db.query(MonitorSurveyRecord.asset_number).filter(
            MonitorSurveyRecord.campaign_id == campaign_id
        ).distinct().all()
    )

    # 미실사 PC
    unaudited_pcs = []
    for pc in db.query(PCMaster).filter(PCMaster.is_deleted == False).all():
        if pc.asset_number not in surveyed_pc_assets:
            unaudited_pcs.append({
                "asset_type": "PC",
                "asset_number": pc.asset_number,
                "management_number": pc.pc_management_number,
                "location_name": pc.location_name,
                "employee_number": pc.employee_number
            })

    # 미실사 모니터
    unaudited_monitors = []
    for m in db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).all():
        if m.asset_number not in surveyed_monitor_assets:
            unaudited_monitors.append({
                "asset_type": "모니터",
                "asset_number": m.asset_number,
                "management_number": m.monitor_management_number,
                "location_name": m.location_name,
                "employee_number": m.employee_number
            })

    return {
        "campaign_name": campaign.name,
        "unaudited_pcs": len(unaudited_pcs),
        "unaudited_monitors": len(unaudited_monitors),
        "unaudited_total": len(unaudited_pcs) + len(unaudited_monitors),
        "items": unaudited_pcs + unaudited_monitors
    }


# ===== 대시보드 API =====

@router.get("/api/v1/admin/dashboard/by-location")
async def get_dashboard_by_location(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """사업장별 자산/실사 현황 통합 대시보드"""
    # 사업장별 PC 수
    pc_by_location = dict(
        db.query(PCMaster.location_name, func.count(PCMaster.id))
        .filter(PCMaster.is_deleted == False)
        .group_by(PCMaster.location_name).all()
    )

    # 사업장별 모니터 수
    monitor_by_location = dict(
        db.query(MonitorMaster.location_name, func.count(MonitorMaster.id))
        .filter(MonitorMaster.is_deleted == False)
        .group_by(MonitorMaster.location_name).all()
    )

    # 활성 캠페인 기준 실사 현황
    active = get_active_campaign(db)
    pc_surveyed_by_location = {}
    monitor_surveyed_by_location = {}

    if active:
        # 캠페인 기준 PC 실사 완료 (사업장별)
        rows = db.query(
            PCMaster.location_name,
            func.count(func.distinct(SurveyRecord.asset_number))
        ).join(
            SurveyRecord, PCMaster.asset_number == SurveyRecord.asset_number
        ).filter(
            SurveyRecord.campaign_id == active.id,
            PCMaster.is_deleted == False
        ).group_by(PCMaster.location_name).all()
        pc_surveyed_by_location = dict(rows)

        # 캠페인 기준 모니터 실사 완료 (사업장별)
        rows = db.query(
            MonitorMaster.location_name,
            func.count(func.distinct(MonitorSurveyRecord.asset_number))
        ).join(
            MonitorSurveyRecord, MonitorMaster.asset_number == MonitorSurveyRecord.asset_number
        ).filter(
            MonitorSurveyRecord.campaign_id == active.id,
            MonitorMaster.is_deleted == False
        ).group_by(MonitorMaster.location_name).all()
        monitor_surveyed_by_location = dict(rows)

    # 모든 사업장 통합
    all_locations = set(list(pc_by_location.keys()) + list(monitor_by_location.keys()))

    result = []
    for loc in sorted(all_locations):
        pc_total = pc_by_location.get(loc, 0)
        monitor_total = monitor_by_location.get(loc, 0)
        pc_done = pc_surveyed_by_location.get(loc, 0)
        monitor_done = monitor_surveyed_by_location.get(loc, 0)
        total = pc_total + monitor_total
        done = pc_done + monitor_done

        result.append({
            "location_name": loc,
            "pc_total": pc_total,
            "pc_surveyed": pc_done,
            "monitor_total": monitor_total,
            "monitor_surveyed": monitor_done,
            "total_assets": total,
            "total_surveyed": done,
            "completion_rate": round((done / total * 100) if total > 0 else 0, 1)
        })

    return {
        "active_campaign": {
            "id": active.id,
            "name": active.name
        } if active else None,
        "locations": result
    }


# ===== 자산 이력 API =====

@router.get("/api/v1/admin/asset-history/{asset_number}")
async def get_asset_history(
    asset_number: str,
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """개별 자산 이력 조회"""
    histories = db.query(AssetHistory).filter(
        AssetHistory.asset_number == asset_number
    ).order_by(AssetHistory.changed_at.desc()).all()

    return [
        {
            "id": h.id,
            "asset_type": h.asset_type,
            "asset_number": h.asset_number,
            "action_type": h.action_type,
            "description": h.description,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "changed_at": h.changed_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for h in histories
    ]


# ===== 백업 API =====

@router.get("/api/v1/admin/backup")
async def backup_all_data(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """전체 데이터 백업"""
    pcs = db.query(PCMaster).filter(PCMaster.is_deleted == False).all()
    surveys = db.query(SurveyRecord).all()
    user_changes = db.query(UserChangeHistory).all()
    monitors = db.query(MonitorMaster).filter(MonitorMaster.is_deleted == False).all()
    monitor_surveys = db.query(MonitorSurveyRecord).all()
    campaigns = db.query(AuditCampaign).all()

    return {
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
                "campaign_id": s.campaign_id,
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
                "campaign_id": ms.campaign_id,
                "survey_date": ms.survey_date.isoformat(),
                "completed_at": ms.completed_at.isoformat()
            }
            for ms in monitor_surveys
        ],
        "campaigns": [
            {
                "id": c.id,
                "name": c.name,
                "start_date": c.start_date.isoformat(),
                "end_date": c.end_date.isoformat(),
                "status": c.status,
                "description": c.description,
                "created_at": c.created_at.isoformat()
            }
            for c in campaigns
        ]
    }
