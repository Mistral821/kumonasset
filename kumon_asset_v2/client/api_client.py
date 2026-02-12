"""
구몬 자산관리 시스템 - API 클라이언트
"""

import requests
from typing import Dict, Optional
from config import get_server_url


class APIClient:
    def __init__(self, base_url: str = None, token: str = None):
        """API 클라이언트 초기화"""
        self.base_url = base_url or get_server_url()
        self.token = token or "kumon_client_secret_token_2025"
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

    def register_pc(self, asset_number: str, pc_management_number: str,
                   location_name: str, employee_number: str) -> Dict:
        """PC 등록"""
        try:
            data = {
                "asset_number": asset_number,
                "pc_management_number": pc_management_number,
                "location_name": location_name,
                "employee_number": employee_number
            }
            response = requests.post(
                f"{self.base_url}/api/v1/pc/register",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_pc_info(self, asset_number: str) -> Dict:
        """PC 정보 조회"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/pc/{asset_number}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"success": False, "error": "등록되지 않은 자산번호입니다"}
            return {"success": False, "error": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def update_user(self, asset_number: str, new_employee_number: str) -> Dict:
        """사번 변경"""
        try:
            data = {"new_employee_number": new_employee_number}
            response = requests.put(
                f"{self.base_url}/api/v1/pc/{asset_number}/user",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def complete_pc_survey(self, asset_number: str) -> Dict:
        """PC 자산조사 완료"""
        try:
            data = {"asset_number": asset_number}
            response = requests.post(
                f"{self.base_url}/api/v1/pc/survey",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== 모니터 API =====

    def register_monitor(self, asset_number: str, monitor_management_number: str,
                        location_name: str, employee_number: str,
                        connected_pc_asset_number: Optional[str] = None) -> Dict:
        """모니터 등록"""
        try:
            data = {
                "asset_number": asset_number,
                "monitor_management_number": monitor_management_number,
                "location_name": location_name,
                "employee_number": employee_number,
                "connected_pc_asset_number": connected_pc_asset_number
            }
            response = requests.post(
                f"{self.base_url}/api/v1/monitor/register",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_monitor_info(self, asset_number: str) -> Dict:
        """모니터 정보 조회"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/monitor/{asset_number}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {"success": False, "error": "등록되지 않은 자산번호입니다"}
            return {"success": False, "error": e.response.json().get("detail", str(e))}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def complete_monitor_survey(self, asset_number: str) -> Dict:
        """모니터 자산조사 완료"""
        try:
            data = {"asset_number": asset_number}
            response = requests.post(
                f"{self.base_url}/api/v1/monitor/survey",
                json=data,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
