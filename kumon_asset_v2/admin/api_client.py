"""
구몬 자산관리 시스템 - 관리자 API 클라이언트
캠페인, 대시보드, 자산 이력 지원
"""

import requests
import urllib3
from typing import Dict, List, Optional
from config import get_server_url

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AdminAPIClient:
    def __init__(self, base_url: str = None):
        """관리자 API 클라이언트 초기화"""
        self.base_url = base_url or get_server_url()
        self.token = "kumon_admin_secret_token_2025"
        self.verify_ssl = False
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def _get(self, path: str, timeout: int = 30, **kwargs) -> Dict:
        """공통 GET 요청"""
        try:
            response = requests.get(
                f"{self.base_url}{path}",
                headers=self.headers, timeout=timeout,
                verify=self.verify_ssl, **kwargs
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _post(self, path: str, data: dict, timeout: int = 30) -> Dict:
        """공통 POST 요청"""
        try:
            response = requests.post(
                f"{self.base_url}{path}",
                json=data, headers=self.headers, timeout=timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _put(self, path: str, data: dict, timeout: int = 30) -> Dict:
        """공통 PUT 요청"""
        try:
            response = requests.put(
                f"{self.base_url}{path}",
                json=data, headers=self.headers, timeout=timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _delete(self, path: str, timeout: int = 30) -> Dict:
        """공통 DELETE 요청"""
        try:
            response = requests.delete(
                f"{self.base_url}{path}",
                headers=self.headers, timeout=timeout,
                verify=self.verify_ssl
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def test_connection(self) -> Dict:
        try:
            response = requests.get(f"{self.base_url}/", timeout=10, verify=self.verify_ssl)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ... (omit methods showing defaults, will rely on replaced class methods or just changing definitions)


    # ===== PC API =====
    def get_all_pcs(self) -> Dict:
        return self._get("/api/v1/admin/pcs")

    def get_pc_survey_status(self, survey_date: Optional[str] = None) -> Dict:
        params = {"survey_date": survey_date} if survey_date else {}
        return self._get("/api/v1/admin/survey-status", params=params)

    def update_pc_info(self, asset_number: str, **kwargs) -> Dict:
        data = {k: v for k, v in kwargs.items() if v}
        return self._put(f"/api/v1/admin/pc/{asset_number}/info", data)

    def delete_pc(self, asset_number: str) -> Dict:
        return self._delete(f"/api/v1/admin/pc/{asset_number}")

    # ===== 모니터 API =====
    def get_all_monitors(self) -> Dict:
        return self._get("/api/v1/admin/monitors")

    def get_monitor_survey_status(self, survey_date: Optional[str] = None) -> Dict:
        params = {"survey_date": survey_date} if survey_date else {}
        return self._get("/api/v1/admin/monitor-survey-status", params=params)

    def update_monitor(self, asset_number: str, **kwargs) -> Dict:
        data = {k: v for k, v in kwargs.items() if v is not None}
        return self._put(f"/api/v1/admin/monitor/{asset_number}", data)

    def delete_monitor(self, asset_number: str) -> Dict:
        return self._delete(f"/api/v1/admin/monitor/{asset_number}")

    # ===== 캠페인 API =====
    def get_campaigns(self) -> Dict:
        return self._get("/api/v1/admin/campaigns")

    def create_campaign(self, name: str, start_date: str, end_date: str,
                       description: str = None) -> Dict:
        data = {"name": name, "start_date": start_date, "end_date": end_date}
        if description:
            data["description"] = description
        return self._post("/api/v1/admin/campaigns", data)

    def update_campaign(self, campaign_id: int, **kwargs) -> Dict:
        data = {k: v for k, v in kwargs.items() if v is not None}
        return self._put(f"/api/v1/admin/campaigns/{campaign_id}", data)

    def get_campaign_progress(self, campaign_id: int) -> Dict:
        return self._get(f"/api/v1/admin/campaigns/{campaign_id}/progress")

    def get_unaudited_assets(self, campaign_id: int) -> Dict:
        return self._get(f"/api/v1/admin/campaigns/{campaign_id}/unaudited")

    # ===== 대시보드 API =====
    def get_dashboard_by_location(self) -> Dict:
        return self._get("/api/v1/admin/dashboard/by-location")

    # ===== 자산 이력 API =====
    def get_asset_history(self, asset_number: str) -> Dict:
        return self._get(f"/api/v1/admin/asset-history/{asset_number}")

    # ===== 백업 API =====
    def backup_data(self) -> Dict:
        return self._get("/api/v1/admin/backup", timeout=30)

    # ===== 재등록 요청 API =====
    def get_re_register_requests(self, status: str = None) -> Dict:
        params = {"status": status} if status else {}
        return self._get("/api/v1/admin/re-register-requests", params=params)

    def approve_re_register(self, request_id: int, comment: str = None) -> Dict:
        return self._put(f"/api/v1/admin/re-register-requests/{request_id}/approve",
                         {"admin_comment": comment})

    def reject_re_register(self, request_id: int, comment: str = None) -> Dict:
        return self._put(f"/api/v1/admin/re-register-requests/{request_id}/reject",
                         {"admin_comment": comment})
