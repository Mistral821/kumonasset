"""
구몬 자산관리 시스템 - API 라우트
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel

from database import get_db, PCMaster, SurveyRecord, UserChangeHistory

router = APIRouter()

# 인증 토큰 (실제로는 환경변수로 관리)
CLIENT_TOKEN = "kumon_client_secret_token_2025"
ADMIN_TOKEN = "kumon_admin_secret_token_2025"


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
    
    class Config:
        from_attributes = True


class SurveyStatusResponse(BaseModel):
    total: int
    completed: int
    remaining: int
    completion_rate: float


# ===== API 엔드포인트 =====

@router.get("/")
async def root():
    """API 상태 확인"""
    return {
        "service": "구몬 자산관리 API",
        "version": "2.0",
        "status": "running"
    }


@router.post("/api/v1/pc/register")
async def register_pc(
    request: PCRegisterRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """PC 등록"""
    # 중복 확인
    existing = db.query(PCMaster).filter(
        PCMaster.asset_number == request.asset_number,
        PCMaster.is_deleted == False
    ).first()
    
    if existing:
        if existing.is_deleted:
            # 삭제된 PC 재등록 (부활)
            existing.is_deleted = False
            existing.pc_management_number = request.pc_management_number
            existing.location_name = request.location_name
            existing.employee_number = request.employee_number
            existing.last_updated_at = datetime.utcnow()
            
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
    
    return PCResponse.from_orm(pc)


@router.put("/api/v1/pc/{asset_number}/user")
async def update_user(
    asset_number: str,
    request: PCUpdateUserRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """사용자 변경"""
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
    pc.last_updated_at = datetime.utcnow()
    
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
        
    pc.last_updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "PC 정보 수정 완료"
    }


@router.post("/api/v1/survey/complete")
async def complete_survey(
    request: SurveyCompleteRequest,
    db: Session = Depends(get_db),
    token: str = Depends(verify_client_token)
):
    """자산조사 완료"""
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
        raise HTTPException(status_code=400, detail="오늘 이미 자산조사를 완료했습니다")
    
    # 조사 기록 저장
    survey = SurveyRecord(
        asset_number=request.asset_number,
        survey_date=datetime.utcnow()
    )
    db.add(survey)
    db.commit()
    db.refresh(survey)
    
    return {
        "success": True,
        "message": "자산조사 완료!",
        "survey_id": survey.id
    }


# ===== 관리자 API =====

@router.get("/api/v1/admin/pcs")
async def get_all_pcs(
    db: Session = Depends(get_db),
    token: str = Depends(verify_admin_token)
):
    """전체 PC 목록 조회 (관리자)"""
    pcs = db.query(PCMaster).filter(PCMaster.is_deleted == False).all()
    
    result = []
    today = date.today()
    
    for pc in pcs:
        # 오늘 조사 여부 확인
        surveyed_today = db.query(SurveyRecord).filter(
            SurveyRecord.asset_number == pc.asset_number,
            func.date(SurveyRecord.survey_date) == today
        ).first() is not None
        
        result.append({
            "id": pc.id,
            "asset_number": pc.asset_number,
            "pc_management_number": pc.pc_management_number,
            "location_name": pc.location_name,
            "employee_number": pc.employee_number,
            "registered_at": pc.registered_at.isoformat(),
            "last_updated_at": pc.last_updated_at.isoformat(),
            "surveyed_today": surveyed_today
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
        
    # SurveyRecord와 PCMaster 조인 (Outer Join으로 변경)
    results = db.query(SurveyRecord, PCMaster).outerjoin(
        PCMaster, SurveyRecord.asset_number == PCMaster.asset_number
    ).filter(
        func.date(SurveyRecord.survey_date) >= start,
        func.date(SurveyRecord.survey_date) <= end
    ).order_by(SurveyRecord.survey_date.desc()).all()
    
    history = []
    for survey, pc in results:
        history.append({
            "survey_date": survey.survey_date.strftime("%Y-%m-%d %H:%M:%S"),
            "asset_number": survey.asset_number,
            "pc_management_number": pc.pc_management_number if pc else "-",
            "location_name": pc.location_name if pc else "정보 없음",
            "employee_number": pc.employee_number if pc else "-"
        })
        
    return {
        "success": True,
        "data": history
    }


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
    
    backup_data = {
        "backup_date": datetime.utcnow().isoformat(),
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
        ]
    }
    
    return backup_data
