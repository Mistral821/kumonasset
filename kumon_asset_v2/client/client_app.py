"""
구몬 자산관리 시스템 - 클라이언트 v3.5
캠페인 자동 연동, 사번 변경, QR 코드
"""

import tkinter as tk
from tkinter import ttk, messagebox
import qrcode
from PIL import Image, ImageTk
from api_client import APIClient
import json
import os


class AssetClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("구몬 자산관리 시스템 v3.5")
        self.root.geometry("800x900")

        self.api = APIClient()
        self.config_file = "asset_config.json"

        self.pc_asset_number = None
        self.monitor_asset_number = None
        self.active_campaign_id = None
        self.active_campaign_name = None

        self.pc_qr_image = None
        self.monitor_qr_image = None

        self.load_config()
        self.setup_ui()
        self.check_connection()

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
            except (json.JSONDecodeError, IOError) as e:
                print(f"설정 파일 로드 실패: {e}")

    def save_config(self):
        """로컬 설정 파일에 자산번호 저장"""
        config = {
            'pc_asset_number': self.pc_asset_number,
            'monitor_asset_number': self.monitor_asset_number
        }
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def load_pc_details(self):
        """서버에서 PC 상세 정보 조회 및 UI 갱신"""
        if not self.pc_asset_number:
            return

        result = self.api.get_pc_info(self.pc_asset_number)
        if result["success"]:
            data = result["data"]
            # UI가 초기화된 경우에만 업데이트
            if hasattr(self, 'lbl_pc_mgmt'):
                self.lbl_pc_mgmt.config(text=data.get("pc_management_number", "-"))
                self.lbl_pc_loc.config(text=data.get("location_name", "-"))
                self.lbl_pc_emp.config(text=data.get("employee_number", "-"))
        else:
            print(f"PC 정보 로드 실패: {result['error']}")

    def setup_ui(self):
        """UI 구성"""
        # 헤더
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill=tk.X)

        ttk.Label(header, text="구몬 자산관리 시스템",
                  font=("맑은 고딕", 16, "bold")).pack(side=tk.LEFT)

        self.status_label = ttk.Label(header, text="● 확인 중...",
                                      font=("맑은 고딕", 10))
        self.status_label.pack(side=tk.LEFT, padx=20)

        ttk.Button(header, text="연결 테스트",
                   command=self.check_connection).pack(side=tk.RIGHT)

        ttk.Button(header, text="초기화",
                   command=self.reset_app).pack(side=tk.RIGHT, padx=5)

    def reset_app(self):
        """앱 초기화 (자산번호 삭제 및 재등록)"""
        if not messagebox.askyesno("초기화", "앱을 초기화하시겠습니까?\n저장된 자산번호가 삭제되고 재등록이 필요합니다."):
            return

        try:
            if os.path.exists(self.config_file):
                os.remove(self.config_file)
            
            self.pc_asset_number = None
            self.monitor_asset_number = None
            self.active_campaign_id = None
            self.active_campaign_name = None
            
            # UI 초기화
            self.pc_asset_label.config(text="미등록")
            if hasattr(self, 'lbl_pc_mgmt'):
                self.lbl_pc_mgmt.config(text="-")
                self.lbl_pc_loc.config(text="-")
                self.lbl_pc_emp.config(text="-")
            
            self.pc_qr_label.config(image='', text="자산번호를 등록하면 QR 코드가 생성됩니다")
            
            messagebox.showinfo("초기화 완료", "앱이 초기화되었습니다.\n다시 등록해주세요.")
            self.prompt_pc_registration()
            
        except Exception as e:
            messagebox.showerror("오류", f"초기화 실패: {e}")

        # 캠페인 표시 바
        self.campaign_frame = ttk.LabelFrame(self.root, text="현재 실사 캠페인", padding="8")
        self.campaign_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        self.campaign_label = ttk.Label(
            self.campaign_frame, text="캠페인 정보 조회 중...",
            font=("맑은 고딕", 10)
        )
        self.campaign_label.pack(side=tk.LEFT)

        # 탭 구성
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        pc_tab = ttk.Frame(notebook, padding="10")
        notebook.add(pc_tab, text="PC 관리")
        self.setup_pc_tab(pc_tab)

        monitor_tab = ttk.Frame(notebook, padding="10")
        notebook.add(monitor_tab, text="모니터 관리")
        self.setup_monitor_tab(monitor_tab)

    def setup_pc_tab(self, parent):
        """PC 관리 탭"""
        info_frame = ttk.LabelFrame(parent, text="이 PC의 정보", padding="15")
        info_frame.pack(fill=tk.X, pady=(0, 10))

        asset_frame = ttk.Frame(info_frame)
        asset_frame.pack(fill=tk.X, pady=5)

        ttk.Label(asset_frame, text="자산번호:",
                  font=("맑은 고딕", 11, "bold")).pack(side=tk.LEFT)
        self.pc_asset_label = ttk.Label(
            asset_frame, text=self.pc_asset_number or "미등록",
            font=("맑은 고딕", 14, "bold"), foreground="blue"
        )
        self.pc_asset_label.pack(side=tk.LEFT, padx=10)

        ttk.Button(asset_frame, text="재등록",
                   command=self.prompt_pc_registration).pack(side=tk.RIGHT)

        # 상세 정보 표시 (New)
        details_frame = ttk.Frame(info_frame)
        details_frame.pack(fill=tk.X, pady=5)

        ttk.Label(details_frame, text="PC관리번호:", font=("맑은 고딕", 10)).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.lbl_pc_mgmt = ttk.Label(details_frame, text="-", font=("맑은 고딕", 10, "bold"))
        self.lbl_pc_mgmt.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))

        ttk.Label(details_frame, text="사업장:", font=("맑은 고딕", 10)).grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.lbl_pc_loc = ttk.Label(details_frame, text="-", font=("맑은 고딕", 10, "bold"))
        self.lbl_pc_loc.grid(row=0, column=3, sticky=tk.W, padx=(0, 20))

        ttk.Label(details_frame, text="사용자:", font=("맑은 고딕", 10)).grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        self.lbl_pc_emp = ttk.Label(details_frame, text="-", font=("맑은 고딕", 10, "bold"))
        self.lbl_pc_emp.grid(row=0, column=5, sticky=tk.W)

        # 사번 변경
        user_frame = ttk.LabelFrame(parent, text="사번 변경", padding="15")
        user_frame.pack(fill=tk.X, pady=(0, 10))

        user_input_frame = ttk.Frame(user_frame)
        user_input_frame.pack(fill=tk.X)

        ttk.Label(user_input_frame, text="새 사번:",
                  font=("맑은 고딕", 10)).pack(side=tk.LEFT)
        self.new_employee_entry = ttk.Entry(user_input_frame, width=20,
                                            font=("맑은 고딕", 10))
        self.new_employee_entry.pack(side=tk.LEFT, padx=10)
        self.new_employee_entry.bind('<Return>', lambda e: self.change_employee_number())
        ttk.Button(user_input_frame, text="사번 변경",
                   command=self.change_employee_number).pack(side=tk.LEFT, padx=5)

        # QR 코드
        qr_frame = ttk.LabelFrame(parent, text="QR 코드 (자산조사용)", padding="15")
        qr_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(qr_frame, text="아래 QR 코드를 스마트폰으로 스캔하세요",
                  font=("맑은 고딕", 10)).pack(pady=(0, 10))

        self.pc_qr_label = ttk.Label(qr_frame,
                                     text="자산번호를 등록하면 QR 코드가 생성됩니다")
        self.pc_qr_label.pack(pady=20)

        ttk.Button(qr_frame, text="자산조사 완료",
                   command=self.complete_pc_survey).pack(pady=10)

        if self.pc_asset_number:
            self.generate_pc_qr()

    def setup_monitor_tab(self, parent):
        """모니터 관리 탭"""
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

        if self.pc_asset_number:
            self.monitor_entries["monitor_connected_pc"].insert(0, self.pc_asset_number)

        register_frame.columnconfigure(1, weight=1)

        ttk.Button(register_frame, text="모니터 등록하기",
                   command=self.register_monitor).grid(row=len(fields), column=0,
                                                       columnspan=2, pady=(10, 0))

        # QR 코드
        qr_frame = ttk.LabelFrame(parent, text="모니터 QR 코드", padding="15")
        qr_frame.pack(fill=tk.BOTH, expand=True)

        self.monitor_asset_display_label = ttk.Label(
            qr_frame,
            text=f"모니터 자산번호: {self.monitor_asset_number}" if self.monitor_asset_number else "",
            font=("맑은 고딕", 11, "bold"), foreground="green"
        )
        if self.monitor_asset_number:
            self.monitor_asset_display_label.pack(pady=10)

        self.monitor_qr_label = ttk.Label(qr_frame,
                                          text="모니터를 등록하면 QR 코드가 생성됩니다")
        self.monitor_qr_label.pack(pady=20)

        ttk.Button(qr_frame, text="모니터 자산조사 완료",
                   command=self.complete_monitor_survey).pack(pady=10)

        if self.monitor_asset_number:
            self.generate_monitor_qr()

    def prompt_pc_registration(self):
        """PC 등록/재등록 프롬프트"""
        # 이미 등록된 PC가 있으면 재등록 요청 다이얼로그
        if self.pc_asset_number:
            self.prompt_re_registration()
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("PC 등록")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="이 PC의 정보를 등록하세요",
                  font=("맑은 고딕", 14, "bold")).pack(pady=20)

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
            vals = {k: e.get().strip() for k, e in entries.items()}
            if not all(vals.values()):
                messagebox.showwarning("입력 오류", "모든 필드를 입력해주세요", parent=dialog)
                return

            result = self.api.register_pc(
                vals["asset_number"], vals["pc_management_number"],
                vals["location_name"], vals["employee_number"]
            )

            if result["success"]:
                self.pc_asset_number = vals["asset_number"]
                self.save_config()
                self.pc_asset_label.config(text=vals["asset_number"])
                self.generate_pc_qr()
                if hasattr(self, 'monitor_entries') and 'monitor_connected_pc' in self.monitor_entries:
                    self.monitor_entries["monitor_connected_pc"].delete(0, tk.END)
                    self.monitor_entries["monitor_connected_pc"].insert(0, vals["asset_number"])
                messagebox.showinfo("성공", "PC가 등록되었습니다", parent=dialog)
                dialog.destroy()
            else:
                messagebox.showerror("오류", result["error"], parent=dialog)

        ttk.Button(dialog, text="등록하기", command=register).pack(pady=20)

    def prompt_re_registration(self):
        """PC 재등록 요청 다이얼로그 (관리자 승인 필요)"""
        dialog = tk.Toplevel(self.root)
        dialog.title("PC 재등록 요청")
        dialog.geometry("550x550")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="🔄 PC 재등록 요청",
                  font=("맑은 고딕", 14, "bold")).pack(pady=15)

        ttk.Label(dialog, text="관리자 승인 후 재등록이 처리됩니다",
                  font=("맑은 고딕", 10), foreground="gray").pack()

        fields_frame = ttk.Frame(dialog, padding="20")
        fields_frame.pack(fill=tk.BOTH, expand=True)

        # 현재 자산번호 (읽기 전용)
        ttk.Label(fields_frame, text="현재 자산번호:").grid(row=0, column=0, sticky=tk.W, pady=8)
        asset_label = ttk.Label(fields_frame, text=self.pc_asset_number,
                                font=("맑은 고딕", 10, "bold"), foreground="blue")
        asset_label.grid(row=0, column=1, sticky=tk.W, pady=8, padx=(10, 0))

        # 새 정보 입력
        fields = [
            ("새 PC관리번호:", "new_pc_management_number"),
            ("새 사업장명:", "new_location_name"),
            ("새 사번:", "new_employee_number"),
        ]

        entries = {}
        for i, (label, key) in enumerate(fields, 1):
            ttk.Label(fields_frame, text=label).grid(row=i, column=0, sticky=tk.W, pady=8, padx=(0, 10))
            entry = ttk.Entry(fields_frame, width=30, font=("맑은 고딕", 10))
            entry.grid(row=i, column=1, sticky=tk.EW, pady=8)
            entries[key] = entry

        # 요청자 사번
        row_requester = len(fields) + 1
        ttk.Label(fields_frame, text="요청자 사번:").grid(row=row_requester, column=0, sticky=tk.W, pady=8)
        requester_entry = ttk.Entry(fields_frame, width=30, font=("맑은 고딕", 10))
        requester_entry.grid(row=row_requester, column=1, sticky=tk.EW, pady=8)

        # 재등록 사유 (텍스트 영역)
        row_reason = row_requester + 1
        ttk.Label(fields_frame, text="재등록 사유:").grid(row=row_reason, column=0, sticky=tk.NW, pady=8)
        reason_text = tk.Text(fields_frame, width=30, height=4, font=("맑은 고딕", 10))
        reason_text.grid(row=row_reason, column=1, sticky=tk.EW, pady=8)

        fields_frame.columnconfigure(1, weight=1)

        def submit_request():
            vals = {k: e.get().strip() for k, e in entries.items()}
            requester = requester_entry.get().strip()
            reason = reason_text.get("1.0", tk.END).strip()

            if not all(vals.values()) or not requester or not reason:
                messagebox.showwarning("입력 오류", "모든 필드와 사유를 입력해주세요", parent=dialog)
                return

            result = self.api.request_re_registration(
                asset_number=self.pc_asset_number,
                requester_employee=requester,
                reason=reason,
                new_pc_management_number=vals["new_pc_management_number"],
                new_location_name=vals["new_location_name"],
                new_employee_number=vals["new_employee_number"]
            )

            if result["success"]:
                messagebox.showinfo(
                    "요청 접수",
                    "재등록 요청이 접수되었습니다.\n관리자 승인을 기다려주세요.",
                    parent=dialog
                )
                dialog.destroy()
            else:
                messagebox.showerror("오류", result["error"], parent=dialog)

        ttk.Button(dialog, text="📨 재등록 요청하기", command=submit_request).pack(pady=15)

    def change_employee_number(self):
        """사번 변경"""
        if not self.pc_asset_number:
            messagebox.showwarning("오류", "PC가 등록되지 않았습니다")
            return

        new_employee = self.new_employee_entry.get().strip()
        if not new_employee:
            messagebox.showwarning("입력 오류", "새 사번을 입력해주세요")
            return

        if not messagebox.askyesno("확인", f"사번을 '{new_employee}'(으)로 변경하시겠습니까?"):
            return

        result = self.api.update_user(self.pc_asset_number, new_employee)
        if result["success"]:
            messagebox.showinfo("성공", "사번이 변경되었습니다")
            self.new_employee_entry.delete(0, tk.END)
        else:
            messagebox.showerror("오류", result["error"])

    def generate_pc_qr(self):
        """PC QR 코드 생성"""
        if not self.pc_asset_number:
            return
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10, border=4)
        qr.add_data(f"PC:{self.pc_asset_number}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").resize((350, 350))
        self.pc_qr_image = ImageTk.PhotoImage(img)
        self.pc_qr_label.config(image=self.pc_qr_image, text="")

    def generate_monitor_qr(self):
        """모니터 QR 코드 생성"""
        if not self.monitor_asset_number:
            return
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L,
                            box_size=10, border=4)
        qr.add_data(f"MONITOR:{self.monitor_asset_number}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").resize((350, 350))
        self.monitor_qr_image = ImageTk.PhotoImage(img)
        self.monitor_qr_label.config(image=self.monitor_qr_image, text="")

    def register_monitor(self):
        """모니터 등록"""
        asset_number = self.monitor_entries["monitor_asset_number"].get().strip()
        mgmt = self.monitor_entries["monitor_management_number"].get().strip()
        loc = self.monitor_entries["monitor_location_name"].get().strip()
        emp = self.monitor_entries["monitor_employee_number"].get().strip()
        pc = self.monitor_entries["monitor_connected_pc"].get().strip() or None

        if not all([asset_number, mgmt, loc, emp]):
            messagebox.showwarning("입력 오류", "필수 필드를 모두 입력해주세요")
            return

        result = self.api.register_monitor(asset_number, mgmt, loc, emp, pc)
        if result["success"]:
            self.monitor_asset_number = asset_number
            self.save_config()
            self.monitor_asset_display_label.config(text=f"모니터 자산번호: {asset_number}")
            self.monitor_asset_display_label.pack(pady=10)
            self.generate_monitor_qr()
            messagebox.showinfo("성공", result["data"]["message"])
            for entry in self.monitor_entries.values():
                entry.delete(0, tk.END)
        else:
            messagebox.showerror("오류", result["error"])

    def complete_pc_survey(self):
        """PC 자산조사 완료"""
        if not self.pc_asset_number:
            messagebox.showwarning("오류", "PC가 등록되지 않았습니다")
            return
        result = self.api.complete_pc_survey(self.pc_asset_number, self.active_campaign_id)
        if result["success"]:
            msg = "PC 자산조사가 완료되었습니다"
            if self.active_campaign_name:
                msg += f"\n(캠페인: {self.active_campaign_name})"
            messagebox.showinfo("성공", msg)
        else:
            messagebox.showerror("오류", result["error"])

    def complete_monitor_survey(self):
        """모니터 자산조사 완료"""
        if not self.monitor_asset_number:
            messagebox.showwarning("오류", "모니터가 등록되지 않았습니다")
            return
        result = self.api.complete_monitor_survey(self.monitor_asset_number, self.active_campaign_id)
        if result["success"]:
            msg = "모니터 자산조사가 완료되었습니다"
            if self.active_campaign_name:
                msg += f"\n(캠페인: {self.active_campaign_name})"
            messagebox.showinfo("성공", msg)
        else:
            messagebox.showerror("오류", result["error"])

    def check_connection(self):
        """서버 연결 확인 + 활성 캠페인 조회"""
        result = self.api.test_connection()
        if result["success"]:
            self.status_label.config(text="● 온라인", foreground="green")
            self.load_pc_details()
            # 활성 캠페인 조회
            campaign_result = self.api.get_active_campaign()
            if campaign_result["success"]:
                data = campaign_result["data"]
                if data.get("active"):
                    c = data["campaign"]
                    self.active_campaign_id = c["id"]
                    self.active_campaign_name = c["name"]
                    self.campaign_label.config(
                        text=f"📋 {c['name']}  ({c['start_date']} ~ {c['end_date']})",
                        foreground="blue"
                    )
                else:
                    self.campaign_label.config(text="현재 진행 중인 실사 캠페인이 없습니다",
                                              foreground="gray")
        else:
            self.status_label.config(text="● 오프라인", foreground="red")
            self.campaign_label.config(text="서버 연결 실패", foreground="red")


if __name__ == "__main__":
    root = tk.Tk()
    app = AssetClientApp(root)
    root.mainloop()
