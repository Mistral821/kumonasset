"""
구몬 자산관리 시스템 - 클라이언트 v3.0
PC와 모니터 등록/자산조사 + QR 코드 표시
"""

import tkinter as tk
from tkinter import ttk, messagebox
import qrcode
from PIL import Image, ImageTk
from api_client import APIClient


class AssetClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("구몬 자산관리 시스템 v3.0")
        self.root.geometry("700x800")

        # API 클라이언트
        self.api = APIClient()

        # QR 코드 이미지 저장
        self.qr_image = None

        self.setup_ui()
        self.check_connection()

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

        # PC 등록 탭
        pc_tab = ttk.Frame(notebook, padding="10")
        notebook.add(pc_tab, text="PC 등록/조사")
        self.setup_pc_tab(pc_tab)

        # 모니터 등록 탭
        monitor_tab = ttk.Frame(notebook, padding="10")
        notebook.add(monitor_tab, text="모니터 등록/조사")
        self.setup_monitor_tab(monitor_tab)

    def setup_pc_tab(self, parent):
        """PC 등록/조사 탭"""
        # 등록 섹션
        register_frame = ttk.LabelFrame(parent, text="PC 등록", padding="15")
        register_frame.pack(fill=tk.X, pady=(0, 10))

        # 입력 필드
        fields = [
            ("자산번호:", "pc_asset_number"),
            ("PC관리번호:", "pc_management_number"),
            ("사업장명:", "pc_location_name"),
            ("사번:", "pc_employee_number")
        ]

        self.pc_entries = {}
        for i, (label, key) in enumerate(fields):
            ttk.Label(register_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=5)
            entry = ttk.Entry(register_frame, width=40)
            entry.grid(row=i, column=1, sticky=tk.EW, pady=5, padx=(10, 0))
            self.pc_entries[key] = entry

        register_frame.columnconfigure(1, weight=1)

        # 등록 버튼
        ttk.Button(
            register_frame,
            text="PC 등록하기",
            command=self.register_pc
        ).grid(row=len(fields), column=0, columnspan=2, pady=(10, 0))

        # 자산조사 섹션
        survey_frame = ttk.LabelFrame(parent, text="PC 자산조사", padding="15")
        survey_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            survey_frame,
            text="자산번호를 입력하고 QR 코드를 생성하세요",
            font=("맑은 고딕", 10)
        ).pack(pady=(0, 10))

        # 자산번호 입력
        input_frame = ttk.Frame(survey_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="자산번호:").pack(side=tk.LEFT)
        self.pc_survey_entry = ttk.Entry(input_frame, width=30)
        self.pc_survey_entry.pack(side=tk.LEFT, padx=10)

        ttk.Button(
            input_frame,
            text="QR 코드 생성",
            command=lambda: self.generate_qr_code("PC")
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            input_frame,
            text="자산조사 완료",
            command=self.complete_pc_survey
        ).pack(side=tk.LEFT)

        # QR 코드 표시 영역
        self.pc_qr_label = ttk.Label(survey_frame, text="QR 코드가 여기에 표시됩니다")
        self.pc_qr_label.pack(pady=20)

    def setup_monitor_tab(self, parent):
        """모니터 등록/조사 탭"""
        # 등록 섹션
        register_frame = ttk.LabelFrame(parent, text="모니터 등록", padding="15")
        register_frame.pack(fill=tk.X, pady=(0, 10))

        # 입력 필드
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

        register_frame.columnconfigure(1, weight=1)

        # 등록 버튼
        ttk.Button(
            register_frame,
            text="모니터 등록하기",
            command=self.register_monitor
        ).grid(row=len(fields), column=0, columnspan=2, pady=(10, 0))

        # 자산조사 섹션
        survey_frame = ttk.LabelFrame(parent, text="모니터 자산조사", padding="15")
        survey_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            survey_frame,
            text="자산번호를 입력하고 QR 코드를 생성하세요",
            font=("맑은 고딕", 10)
        ).pack(pady=(0, 10))

        # 자산번호 입력
        input_frame = ttk.Frame(survey_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="자산번호:").pack(side=tk.LEFT)
        self.monitor_survey_entry = ttk.Entry(input_frame, width=30)
        self.monitor_survey_entry.pack(side=tk.LEFT, padx=10)

        ttk.Button(
            input_frame,
            text="QR 코드 생성",
            command=lambda: self.generate_qr_code("Monitor")
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            input_frame,
            text="자산조사 완료",
            command=self.complete_monitor_survey
        ).pack(side=tk.LEFT)

        # QR 코드 표시 영역
        self.monitor_qr_label = ttk.Label(survey_frame, text="QR 코드가 여기에 표시됩니다")
        self.monitor_qr_label.pack(pady=20)

    def check_connection(self):
        """서버 연결 확인"""
        result = self.api.test_connection()
        if result["success"]:
            self.status_label.config(text="● 온라인", foreground="green")
        else:
            self.status_label.config(text="● 오프라인", foreground="red")
            messagebox.showerror("연결 오류", f"서버에 연결할 수 없습니다\n{result['error']}")

    def register_pc(self):
        """PC 등록"""
        # 입력 검증
        asset_number = self.pc_entries["pc_asset_number"].get().strip()
        pc_management_number = self.pc_entries["pc_management_number"].get().strip()
        location_name = self.pc_entries["pc_location_name"].get().strip()
        employee_number = self.pc_entries["pc_employee_number"].get().strip()

        if not all([asset_number, pc_management_number, location_name, employee_number]):
            messagebox.showwarning("입력 오류", "모든 필드를 입력해주세요")
            return

        # API 호출
        result = self.api.register_pc(
            asset_number, pc_management_number, location_name, employee_number
        )

        if result["success"]:
            messagebox.showinfo("성공", result["data"]["message"])
            # 입력 필드 초기화
            for entry in self.pc_entries.values():
                entry.delete(0, tk.END)
        else:
            messagebox.showerror("오류", result["error"])

    def register_monitor(self):
        """모니터 등록"""
        # 입력 검증
        asset_number = self.monitor_entries["monitor_asset_number"].get().strip()
        monitor_management_number = self.monitor_entries["monitor_management_number"].get().strip()
        location_name = self.monitor_entries["monitor_location_name"].get().strip()
        employee_number = self.monitor_entries["monitor_employee_number"].get().strip()
        connected_pc = self.monitor_entries["monitor_connected_pc"].get().strip() or None

        if not all([asset_number, monitor_management_number, location_name, employee_number]):
            messagebox.showwarning("입력 오류", "필수 필드를 모두 입력해주세요")
            return

        # API 호출
        result = self.api.register_monitor(
            asset_number, monitor_management_number, location_name, employee_number, connected_pc
        )

        if result["success"]:
            messagebox.showinfo("성공", result["data"]["message"])
            # 입력 필드 초기화
            for entry in self.monitor_entries.values():
                entry.delete(0, tk.END)
        else:
            messagebox.showerror("오류", result["error"])

    def generate_qr_code(self, asset_type):
        """QR 코드 생성"""
        # 자산번호 가져오기
        if asset_type == "PC":
            asset_number = self.pc_survey_entry.get().strip()
            qr_label = self.pc_qr_label
        else:
            asset_number = self.monitor_survey_entry.get().strip()
            qr_label = self.monitor_qr_label

        if not asset_number:
            messagebox.showwarning("입력 오류", "자산번호를 입력해주세요")
            return

        # QR 코드 생성
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(asset_number)
        qr.make(fit=True)

        # 이미지 생성
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((300, 300))

        # tkinter 이미지로 변환
        self.qr_image = ImageTk.PhotoImage(img)

        # 표시
        qr_label.config(image=self.qr_image, text="")

        messagebox.showinfo(
            "QR 코드 생성 완료",
            f"{asset_type} 자산번호: {asset_number}\n\n스마트폰 카메라로 QR 코드를 스캔하세요"
        )

    def complete_pc_survey(self):
        """PC 자산조사 완료"""
        asset_number = self.pc_survey_entry.get().strip()

        if not asset_number:
            messagebox.showwarning("입력 오류", "자산번호를 입력해주세요")
            return

        result = self.api.complete_pc_survey(asset_number)

        if result["success"]:
            messagebox.showinfo("성공", "PC 자산조사가 완료되었습니다")
            self.pc_survey_entry.delete(0, tk.END)
            self.pc_qr_label.config(image="", text="QR 코드가 여기에 표시됩니다")
        else:
            messagebox.showerror("오류", result["error"])

    def complete_monitor_survey(self):
        """모니터 자산조사 완료"""
        asset_number = self.monitor_survey_entry.get().strip()

        if not asset_number:
            messagebox.showwarning("입력 오류", "자산번호를 입력해주세요")
            return

        result = self.api.complete_monitor_survey(asset_number)

        if result["success"]:
            messagebox.showinfo("성공", "모니터 자산조사가 완료되었습니다")
            self.monitor_survey_entry.delete(0, tk.END)
            self.monitor_qr_label.config(image="", text="QR 코드가 여기에 표시됩니다")
        else:
            messagebox.showerror("오류", result["error"])


if __name__ == "__main__":
    root = tk.Tk()
    app = AssetClientApp(root)
    root.mainloop()
