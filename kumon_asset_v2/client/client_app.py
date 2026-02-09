"""
구몬 자산관리 시스템 - 클라이언트 v3.1
PC 자산번호 자동 저장 및 QR 코드 표시
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import qrcode
from PIL import Image, ImageTk
from api_client import APIClient
import json
import os


class AssetClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("구몬 자산관리 시스템 v3.1")
        self.root.geometry("800x900")

        # API 클라이언트
        self.api = APIClient()

        # 설정 파일 경로
        self.config_file = "asset_config.json"

        # 저장된 자산 정보
        self.pc_asset_number = None
        self.monitor_asset_number = None

        # QR 코드 이미지 저장
        self.pc_qr_image = None
        self.monitor_qr_image = None

        # 설정 로드
        self.load_config()

        self.setup_ui()
        self.check_connection()

        # PC 자산번호가 없으면 등록 요청
        if not self.pc_asset_number:
            self.root.after(1000, self.prompt_pc_registration)

    def load_config(self):
        """로컬 설정 파일에서 자산번호 로드"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.pc_asset_number = config.get('pc_asset_number')
                    self.monitor_asset_number = config.get('monitor_asset_number')
            except:
                pass

    def save_config(self):
        """로컬 설정 파일에 자산번호 저장"""
        config = {
            'pc_asset_number': self.pc_asset_number,
            'monitor_asset_number': self.monitor_asset_number
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def setup_ui(self):
        """UI 구성"""
        # 헤더
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="구몬 자산관리 시스템",
            font=("맑은 고딕", 16, "bold")
        ).pack(side=tk.LEFT)

        self.status_label = ttk.Label(
            header,
            text="● 확인 중...",
            font=("맑은 고딕", 10)
        )
        self.status_label.pack(side=tk.LEFT, padx=20)

        ttk.Button(
            header,
            text="연결 테스트",
            command=self.check_connection
        ).pack(side=tk.RIGHT)

        # 탭 구성
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # PC 탭
        pc_tab = ttk.Frame(notebook, padding="10")
        notebook.add(pc_tab, text="PC 관리")
        self.setup_pc_tab(pc_tab)

        # 모니터 탭
        monitor_tab = ttk.Frame(notebook, padding="10")
        notebook.add(monitor_tab, text="모니터 관리")
        self.setup_monitor_tab(monitor_tab)

    def setup_pc_tab(self, parent):
        """PC 관리 탭"""
        # 현재 PC 정보
        info_frame = ttk.LabelFrame(parent, text="이 PC의 정보", padding="15")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # 자산번호 표시
        asset_frame = ttk.Frame(info_frame)
        asset_frame.pack(fill=tk.X, pady=5)

        ttk.Label(asset_frame, text="자산번호:", font=("맑은 고딕", 11, "bold")).pack(side=tk.LEFT)
        self.pc_asset_label = ttk.Label(
            asset_frame,
            text=self.pc_asset_number or "미등록",
            font=("맑은 고딕", 14, "bold"),
            foreground="blue"
        )
        self.pc_asset_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(
            asset_frame,
            text="재등록",
            command=self.prompt_pc_registration
        ).pack(side=tk.RIGHT)

        # QR 코드 섹션
        qr_frame = ttk.LabelFrame(parent, text="QR 코드 (자산조사용)", padding="15")
        qr_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            qr_frame,
            text="아래 QR 코드를 스마트폰으로 스캔하세요",
            font=("맑은 고딕", 10)
        ).pack(pady=(0, 10))

        # QR 코드 표시 영역
        self.pc_qr_label = ttk.Label(qr_frame, text="자산번호를 등록하면 QR 코드가 생성됩니다")
        self.pc_qr_label.pack(pady=20)

        # 자산조사 완료 버튼
        ttk.Button(
            qr_frame,
            text="자산조사 완료",
            command=self.complete_pc_survey
        ).pack(pady=10)

        # PC 등록되어 있으면 QR 코드 생성
        if self.pc_asset_number:
            self.generate_pc_qr()

    def setup_monitor_tab(self, parent):
        """모니터 관리 탭"""
        # 모니터 등록 섹션
        register_frame = ttk.LabelFrame(parent, text="모니터 등록", padding="15")
        register_frame.pack(fill=tk.X, pady=(0, 10))

        fields = [
            ("자산번호:", "monitor_asset_number"),
            ("모니터관리번호:", "monitor_management_number"),
            ("사업장명:", "monitor_location_name"),
            ("사번:", "monitor_employee_number"),
            ("연결된 PC 자산번호:", "monitor_connected_pc")
        ]

        self.monitor_entries = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(register_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=5)
            entry = ttk.Entry(register_frame, width=40)
            entry.grid(row=i, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
            self.monitor_entries[key] = entry

        # PC 자산번호 자동 입력
        if self.pc_asset_number:
            self.monitor_entries["monitor_connected_pc"].insert(0, self.pc_asset_number)

        register_frame.columnconfigure(1, weight=1)

        ttk.Button(
            register_frame,
            text="모니터 등록하기",
            command=self.register_monitor
        ).grid(row=len(fields), column=0, columnspan=2, pady=(10, 0))

        # QR 코드 섹션
        qr_frame = ttk.LabelFrame(parent, text="모니터 QR 코드", padding="15")
        qr_frame.pack(fill=tk.BOTH, expand=True)

        # 현재 모니터 자산번호
        if self.monitor_asset_number:
            ttk.Label(
                qr_frame,
                text=f"모니터 자산번호: {self.monitor_asset_number}",
                font=("맑은 고딕", 11, "bold"),
                foreground="green"
            ).pack(pady=10)

        self.monitor_qr_label = ttk.Label(qr_frame, text="모니터를 등록하면 QR 코드가 생성됩니다")
        self.monitor_qr_label.pack(pady=20)

        ttk.Button(
            qr_frame,
            text="모니터 자산조사 완료",
            command=self.complete_monitor_survey
        ).pack(pady=10)

        if self.monitor_asset_number:
            self.generate_monitor_qr()

    def prompt_pc_registration(self):
        """PC 등록 프롬프트"""
        dialog = tk.Toplevel(self.root)
        dialog.title("PC 등록")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text="이 PC의 정보를 등록하세요",
            font=("맑은 고딕", 14, "bold")
        ).pack(pady=20)

        # 입력 필드
        fields_frame = ttk.Frame(dialog, padding="20")
        fields_frame.pack(fill=tk.BOTH, expand=True)

        fields = [
            ("자산번호:", "asset_number"),
            ("PC관리번호:", "pc_management_number"),
            ("사업장명:", "location_name"),
            ("사번:", "employee_number")
        ]

        entries = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(fields_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=10, padx=(0, 10))
            entry = ttk.Entry(fields_frame, width=30, font=("맑은 고딕", 10))
            entry.grid(row=i, column=1, sticky=tk.EW, pady=10)
            entries[key] = entry

        fields_frame.columnconfigure(1, weight=1)

        def register():
            asset_number = entries["asset_number"].get().strip()
            pc_management_number = entries["pc_management_number"].get().strip()
            location_name = entries["location_name"].get().strip()
            employee_number = entries["employee_number"].get().strip()

            if not all([asset_number, pc_management_number, location_name, employee_number]):
                messagebox.showwarning("입력 오류", "모든 필드를 입력해주세요", parent=dialog)
                return

            result = self.api.register_pc(
                asset_number, pc_management_number, location_name, employee_number
            )

            if result["success"]:
                self.pc_asset_number = asset_number
                self.save_config()
                self.pc_asset_label.config(text=asset_number)
                self.generate_pc_qr()
                # 모니터 탭의 연결된 PC 필드 업데이트
                if hasattr(self, 'monitor_entries') and 'monitor_connected_pc' in self.monitor_entries:
                    self.monitor_entries["monitor_connected_pc"].delete(0, tk.END)
                    self.monitor_entries["monitor_connected_pc"].insert(0, asset_number)
                messagebox.showinfo("성공", "PC가 등록되었습니다", parent=dialog)
                dialog.destroy()
            else:
                messagebox.showerror("오류", result["error"], parent=dialog)

        ttk.Button(
            dialog,
            text="등록하기",
            command=register
        ).pack(pady=20)

    def generate_pc_qr(self):
        """PC QR 코드 생성"""
        if not self.pc_asset_number:
            return

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"PC:{self.pc_asset_number}")
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((350, 350))

        self.pc_qr_image = ImageTk.PhotoImage(img)
        self.pc_qr_label.config(image=self.pc_qr_image, text="")

    def generate_monitor_qr(self):
        """모니터 QR 코드 생성"""
        if not self.monitor_asset_number:
            return

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(f"MONITOR:{self.monitor_asset_number}")
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((350, 350))

        self.monitor_qr_image = ImageTk.PhotoImage(img)
        self.monitor_qr_label.config(image=self.monitor_qr_image, text="")

    def register_monitor(self):
        """모니터 등록"""
        asset_number = self.monitor_entries["monitor_asset_number"].get().strip()
        monitor_management_number = self.monitor_entries["monitor_management_number"].get().strip()
        location_name = self.monitor_entries["monitor_location_name"].get().strip()
        employee_number = self.monitor_entries["monitor_employee_number"].get().strip()
        connected_pc = self.monitor_entries["monitor_connected_pc"].get().strip() or None

        if not all([asset_number, monitor_management_number, location_name, employee_number]):
            messagebox.showwarning("입력 오류", "필수 필드를 모두 입력해주세요")
            return

        result = self.api.register_monitor(
            asset_number, monitor_management_number, location_name, employee_number, connected_pc
        )

        if result["success"]:
            self.monitor_asset_number = asset_number
            self.save_config()
            messagebox.showinfo("성공", result["data"]["message"])
            for entry in self.monitor_entries.values():
                entry.delete(0, tk.END)
            # 재시작 요청
            messagebox.showinfo("안내", "모니터 QR 코드를 생성하려면 프로그램을 재시작하세요")
        else:
            messagebox.showerror("오류", result["error"])

    def complete_pc_survey(self):
        """PC 자산조사 완료"""
        if not self.pc_asset_number:
            messagebox.showwarning("오류", "PC가 등록되지 않았습니다")
            return

        result = self.api.complete_pc_survey(self.pc_asset_number)

        if result["success"]:
            messagebox.showinfo("성공", "PC 자산조사가 완료되었습니다")
        else:
            messagebox.showerror("오류", result["error"])

    def complete_monitor_survey(self):
        """모니터 자산조사 완료"""
        if not self.monitor_asset_number:
            messagebox.showwarning("오류", "모니터가 등록되지 않았습니다")
            return

        result = self.api.complete_monitor_survey(self.monitor_asset_number)

        if result["success"]:
            messagebox.showinfo("성공", "모니터 자산조사가 완료되었습니다")
        else:
            messagebox.showerror("오류", result["error"])

    def check_connection(self):
        """서버 연결 확인"""
        result = self.api.test_connection()
        if result["success"]:
            self.status_label.config(text="● 온라인", foreground="green")
        else:
            self.status_label.config(text="● 오프라인", foreground="red")
            messagebox.showerror("연결 오류", f"서버에 연결할 수 없습니다\n{result['error']}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AssetClientApp(root)
    root.mainloop()
