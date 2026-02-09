"""
구몬 자산관리 시스템 - 관리자 API 클라이언트
"""

import requests
from typing import Dict, List, Optional
from config import get_server_url


class AdminAPIClient:
    def __init__(self, base_url: str = None):
        """관리자 API 클라이언트 초기화"""
        self.base_url = base_url or get_server_url()
        self.token = "kumon_admin_secret_token_2025"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> Dict:
        """서버 연결 테스트"""
        try:
            response = requests.get(f"{self.base_url}/", timeout=5)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== PC API =====

    def get_all_pcs(self) -> Dict:
        """전체 PC 목록 조회"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/pcs",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pc_survey_status(self, survey_date: Optional[str] = None) -> Dict:
        """PC 자산조사 현황"""
        try:
            params = {"survey_date": survey_date} if survey_date else {}
            response = requests.get(
                f"{self.base_url}/api/v1/admin/survey-status",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_pc(self, asset_number: str) -> Dict:
        """PC 삭제"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/admin/pc/{asset_number}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== 모니터 API =====

    def get_all_monitors(self) -> Dict:
        """전체 모니터 목록 조회"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/monitors",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_monitor_survey_status(self, survey_date: Optional[str] = None) -> Dict:
        """모니터 자산조사 현황"""
        try:
            params = {"survey_date": survey_date} if survey_date else {}
            response = requests.get(
                f"{self.base_url}/api/v1/admin/monitor-survey-status",
                headers=self.headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def delete_monitor(self, asset_number: str) -> Dict:
        """모니터 삭제"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/v1/admin/monitor/{asset_number}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== 백업 API =====

    def backup_data(self) -> Dict:
        """전체 데이터 백업"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/admin/backup",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
