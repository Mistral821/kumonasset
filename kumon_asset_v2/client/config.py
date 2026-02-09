"""
구몬 자산관리 시스템 - 클라이언트 설정
"""

import os
import json
from typing import Dict


class Config:
    """클라이언트 설정 관리"""

    # 기본 설정값
    DEFAULT_SERVER_URL = "http://localhost:8000"

    def __init__(self):
        """설정 초기화"""
        self.config_file = self._get_config_path()
        self.server_url = self._load_server_url()

    def _get_config_path(self) -> str:
        """설정 파일 경로 반환"""
        # 실행 파일과 같은 디렉토리에 설정 파일 저장
        if getattr(sys, 'frozen', False):
            # PyInstaller로 패키징된 경우
            base_path = os.path.dirname(sys.executable)
        else:
            # 개발 환경
            base_path = os.path.dirname(os.path.abspath(__file__))

        return os.path.join(base_path, "server_config.json")

    def _load_server_url(self) -> str:
        """서버 URL 로드"""
        # 1. 환경변수 확인
        env_url = os.getenv("KUMON_SERVER_URL")
        if env_url:
            return env_url

        # 2. 설정 파일 확인
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('server_url', self.DEFAULT_SERVER_URL)
            except Exception as e:
                print(f"설정 파일 로드 실패: {e}")

        # 3. 기본값 사용 및 설정 파일 생성
        self._create_default_config()
        return self.DEFAULT_SERVER_URL

    def _create_default_config(self):
        """기본 설정 파일 생성"""
        default_config = {
            "server_url": self.DEFAULT_SERVER_URL,
            "comment": "Render 배포 시 server_url을 변경하세요 (예: https://your-app.onrender.com)"
        }

        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 파일 생성 실패: {e}")

    def get_server_url(self) -> str:
        """서버 URL 반환"""
        return self.server_url

    def update_server_url(self, new_url: str) -> bool:
        """서버 URL 업데이트"""
        try:
            config = {"server_url": new_url}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self.server_url = new_url
            return True
        except Exception as e:
            print(f"설정 파일 업데이트 실패: {e}")
            return False


# 전역 설정 인스턴스
import sys
_config = Config()


def get_server_url() -> str:
    """서버 URL 가져오기"""
    return _config.get_server_url()


def update_server_url(new_url: str) -> bool:
    """서버 URL 업데이트"""
    return _config.update_server_url(new_url)
