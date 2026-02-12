"""
구몬 자산관리 시스템 - 관리자 v3.5
대시보드, 실사 캠페인, PC/모니터 관리, 자산 이력
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from api_client import AdminAPIClient
from config import get_server_url
import json
import os
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class AdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("구몬 자산관리 시스템 - 관리자 v3.5")
        self.root.geometry("1200x800")

        self.api = AdminAPIClient()
        self.pc_data = []
        self.monitor_data = []

        self.setup_ui()
        self.check_connection()
        self.root.after(500, self.refresh_all)

    def setup_ui(self):
        """UI 구성"""
        # 헤더
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill=tk.X)

        ttk.Label(header, text="구몬 자산관리 - 관리자",
                  font=("맑은 고딕", 16, "bold")).pack(side=tk.LEFT)

        self.status_label = ttk.Label(header, text="● 확인 중...",
                                      font=("맑은 고딕", 10))
        self.status_label.pack(side=tk.LEFT, padx=20)

        btn_frame = ttk.Frame(header)
        btn_frame.pack(side=tk.RIGHT)
        ttk.Button(btn_frame, text="백업", command=self.backup_data).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Excel 내보내기",
                   command=self.export_to_excel).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="새로고침",
                   command=self.refresh_all).pack(side=tk.LEFT, padx=3)

        # 탭
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 대시보드 탭
        dashboard_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(dashboard_tab, text="📊 대시보드")
        self.setup_dashboard_tab(dashboard_tab)

        # 실사 관리 탭
        campaign_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(campaign_tab, text="📋 실사 관리")
        self.setup_campaign_tab(campaign_tab)

        # PC 관리 탭
        pc_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(pc_tab, text="PC 관리")
        self.setup_pc_tab(pc_tab)

        # 모니터 관리 탭
        monitor_tab = ttk.Frame(self.notebook, padding="5")
        self.notebook.add(monitor_tab, text="모니터 관리")
        self.setup_monitor_tab(monitor_tab)

        # 재등록 요청 탭
        rereg_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(rereg_tab, text="📝 재등록 요청")
        self.setup_rereg_tab(rereg_tab)

    # ===== 대시보드 탭 =====

    def setup_dashboard_tab(self, parent):
        """대시보드 탭 구성"""
        # 상단: 전체 요약
        summary_frame = ttk.LabelFrame(parent, text="전체 자산 현황 요약", padding="15")
        summary_frame.pack(fill=tk.X, pady=(0, 10))

        self.summary_labels = {}
        cols = [
            ("전체 PC", "total_pc"), ("전체 모니터", "total_monitor"),
            ("전체 자산", "total_assets"), ("활성 캠페인", "active_campaign")
        ]
        for i, (text, key) in enumerate(cols):
            frame = ttk.Frame(summary_frame)
            frame.pack(side=tk.LEFT, expand=True, padx=20)
            ttk.Label(frame, text=text, font=("맑은 고딕", 9)).pack()
            lbl = ttk.Label(frame, text="-", font=("맑은 고딕", 20, "bold"))
            lbl.pack()
            self.summary_labels[key] = lbl

        # 중앙: 사업장별 현황 테이블
        loc_frame = ttk.LabelFrame(parent, text="사업장별 자산/실사 현황 (활성 캠페인 기준)", padding="5")
        loc_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("location", "pc_total", "pc_surveyed", "monitor_total",
                   "monitor_surveyed", "total", "surveyed", "rate")
        self.location_tree = ttk.Treeview(loc_frame, columns=columns,
                                          show="headings", height=12)

        headers = [("사업장명", 150), ("PC 수", 70), ("PC 조사", 70),
                   ("모니터 수", 80), ("모니터 조사", 80),
                   ("전체 자산", 80), ("조사 완료", 80), ("완료율(%)", 80)]

        for (col, (text, width)) in zip(columns, headers):
            self.location_tree.heading(col, text=text)
            self.location_tree.column(col, width=width, anchor=tk.CENTER)
        self.location_tree.column("location", anchor=tk.W)

        scrollbar = ttk.Scrollbar(loc_frame, orient=tk.VERTICAL,
                                  command=self.location_tree.yview)
        self.location_tree.configure(yscrollcommand=scrollbar.set)
        self.location_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(parent, text="대시보드 새로고침",
                   command=self.refresh_dashboard).pack(pady=5)

    def refresh_dashboard(self):
        """대시보드 새로고침"""
        result = self.api.get_dashboard_by_location()
        if not result["success"]:
            messagebox.showerror("오류", f"대시보드 조회 실패\n{result['error']}")
            return

        data = result["data"]
        locations = data.get("locations", [])
        campaign = data.get("active_campaign")

        # 요약 업데이트
        total_pc = sum(loc["pc_total"] for loc in locations)
        total_monitor = sum(loc["monitor_total"] for loc in locations)
        self.summary_labels["total_pc"].config(text=str(total_pc))
        self.summary_labels["total_monitor"].config(text=str(total_monitor))
        self.summary_labels["total_assets"].config(text=str(total_pc + total_monitor))
        self.summary_labels["active_campaign"].config(
            text=campaign["name"] if campaign else "없음",
            foreground="blue" if campaign else "gray"
        )

        # 테이블 업데이트
        for item in self.location_tree.get_children():
            self.location_tree.delete(item)

        for loc in locations:
            self.location_tree.insert("", tk.END, values=(
                loc["location_name"],
                loc["pc_total"], loc["pc_surveyed"],
                loc["monitor_total"], loc["monitor_surveyed"],
                loc["total_assets"], loc["total_surveyed"],
                f"{loc['completion_rate']}%"
            ))

        # 합계 행
        if locations:
            totals = {
                "pc_total": sum(l["pc_total"] for l in locations),
                "pc_surveyed": sum(l["pc_surveyed"] for l in locations),
                "monitor_total": sum(l["monitor_total"] for l in locations),
                "monitor_surveyed": sum(l["monitor_surveyed"] for l in locations)
            }
            totals["total"] = totals["pc_total"] + totals["monitor_total"]
            totals["surveyed"] = totals["pc_surveyed"] + totals["monitor_surveyed"]
            rate = round((totals["surveyed"] / totals["total"] * 100) if totals["total"] > 0 else 0, 1)

            self.location_tree.insert("", tk.END, values=(
                "【합계】", totals["pc_total"], totals["pc_surveyed"],
                totals["monitor_total"], totals["monitor_surveyed"],
                totals["total"], totals["surveyed"], f"{rate}%"
            ), tags=("total",))
            self.location_tree.tag_configure("total", font=("맑은 고딕", 10, "bold"))

    # ===== 실사 관리 탭 =====

    def setup_campaign_tab(self, parent):
        """실사 캠페인 관리 탭"""
        # 상단: 캠페인 생성
        create_frame = ttk.LabelFrame(parent, text="캠페인 생성", padding="10")
        create_frame.pack(fill=tk.X, pady=(0, 10))

        row1 = ttk.Frame(create_frame)
        row1.pack(fill=tk.X, pady=5)

        ttk.Label(row1, text="캠페인명:").pack(side=tk.LEFT)
        self.campaign_name_entry = ttk.Entry(row1, width=30)
        self.campaign_name_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text="시작일:").pack(side=tk.LEFT, padx=(20, 0))
        self.campaign_start_entry = ttk.Entry(row1, width=12)
        self.campaign_start_entry.pack(side=tk.LEFT, padx=5)
        self.campaign_start_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(row1, text="종료일:").pack(side=tk.LEFT, padx=(20, 0))
        self.campaign_end_entry = ttk.Entry(row1, width=12)
        self.campaign_end_entry.pack(side=tk.LEFT, padx=5)

        ttk.Button(row1, text="캠페인 생성",
                   command=self.create_campaign).pack(side=tk.RIGHT, padx=5)

        row2 = ttk.Frame(create_frame)
        row2.pack(fill=tk.X, pady=5)
        ttk.Label(row2, text="설명:").pack(side=tk.LEFT)
        self.campaign_desc_entry = ttk.Entry(row2, width=80)
        self.campaign_desc_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        # 중앙: 캠페인 목록
        list_frame = ttk.LabelFrame(parent, text="캠페인 목록", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ("id", "name", "start", "end", "status", "pc_done", "monitor_done")
        self.campaign_tree = ttk.Treeview(list_frame, columns=columns,
                                          show="headings", height=8)

        headers = [("ID", 40), ("캠페인명", 250), ("시작일", 100),
                   ("종료일", 100), ("상태", 70),
                   ("PC 조사 수", 90), ("모니터 조사 수", 100)]

        for (col, (text, width)) in zip(columns, headers):
            self.campaign_tree.heading(col, text=text)
            self.campaign_tree.column(col, width=width, anchor=tk.CENTER)
        self.campaign_tree.column("name", anchor=tk.W)

        self.campaign_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                  command=self.campaign_tree.yview)
        self.campaign_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.campaign_tree.bind("<Double-1>", self.show_campaign_detail)

        # 우클릭 메뉴
        self.campaign_menu = tk.Menu(self.campaign_tree, tearoff=0)
        self.campaign_menu.add_command(label="진행중으로 변경",
                                      command=lambda: self.change_campaign_status("진행중"))
        self.campaign_menu.add_command(label="완료로 변경",
                                      command=lambda: self.change_campaign_status("완료"))
        self.campaign_menu.add_command(label="대기로 변경",
                                      command=lambda: self.change_campaign_status("대기"))
        self.campaign_menu.add_separator()
        self.campaign_menu.add_command(label="미실사 자산 보기",
                                      command=self.show_unaudited)
        self.campaign_menu.add_command(label="캠페인 진행률",
                                      command=self.show_campaign_progress)
        self.campaign_tree.bind("<Button-3>", self.show_campaign_context_menu)

        # 하단: 미실사 자산 표시
        unaudited_frame = ttk.LabelFrame(parent, text="미실사 자산 목록", padding="5")
        unaudited_frame.pack(fill=tk.BOTH, expand=True)

        columns2 = ("type", "asset_number", "mgmt_number", "location", "employee")
        self.unaudited_tree = ttk.Treeview(unaudited_frame, columns=columns2,
                                           show="headings", height=8)

        headers2 = [("유형", 60), ("자산번호", 120), ("관리번호", 120),
                    ("사업장", 150), ("사번", 100)]

        for (col, (text, width)) in zip(columns2, headers2):
            self.unaudited_tree.heading(col, text=text)
            self.unaudited_tree.column(col, width=width, anchor=tk.CENTER)

        self.unaudited_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar2 = ttk.Scrollbar(unaudited_frame, orient=tk.VERTICAL,
                                   command=self.unaudited_tree.yview)
        self.unaudited_tree.configure(yscrollcommand=scrollbar2.set)
        scrollbar2.pack(side=tk.RIGHT, fill=tk.Y)

    def create_campaign(self):
        """캠페인 생성"""
        name = self.campaign_name_entry.get().strip()
        start = self.campaign_start_entry.get().strip()
        end = self.campaign_end_entry.get().strip()
        desc = self.campaign_desc_entry.get().strip() or None

        if not all([name, start, end]):
            messagebox.showwarning("입력 오류", "캠페인명, 시작일, 종료일을 모두 입력해주세요")
            return

        result = self.api.create_campaign(name, start, end, desc)
        if result["success"]:
            messagebox.showinfo("성공", f"캠페인 '{name}' 생성 완료")
            self.campaign_name_entry.delete(0, tk.END)
            self.campaign_desc_entry.delete(0, tk.END)
            self.refresh_campaigns()
        else:
            messagebox.showerror("오류", result["error"])

    def refresh_campaigns(self):
        """캠페인 목록 새로고침"""
        result = self.api.get_campaigns()
        if not result["success"]:
            return

        for item in self.campaign_tree.get_children():
            self.campaign_tree.delete(item)

        for c in result["data"]:
            status_tag = c["status"]
            self.campaign_tree.insert("", tk.END, values=(
                c["id"], c["name"], c["start_date"], c["end_date"],
                c["status"], c["pc_surveyed"], c["monitor_surveyed"]
            ), tags=(status_tag,))

        self.campaign_tree.tag_configure("진행중", foreground="green")
        self.campaign_tree.tag_configure("완료", foreground="gray")
        self.campaign_tree.tag_configure("대기", foreground="orange")

    def show_campaign_context_menu(self, event):
        """캠페인 우클릭 메뉴"""
        item = self.campaign_tree.identify_row(event.y)
        if item:
            self.campaign_tree.selection_set(item)
            self.campaign_menu.post(event.x_root, event.y_root)

    def change_campaign_status(self, new_status):
        """캠페인 상태 변경"""
        selection = self.campaign_tree.selection()
        if not selection:
            return
        values = self.campaign_tree.item(selection[0])["values"]
        campaign_id = values[0]

        result = self.api.update_campaign(campaign_id, status=new_status)
        if result["success"]:
            messagebox.showinfo("성공", f"캠페인 상태가 '{new_status}'(으)로 변경되었습니다")
            self.refresh_campaigns()
        else:
            messagebox.showerror("오류", result["error"])

    def show_campaign_detail(self, event):
        """캠페인 더블클릭 — 진행률 표시"""
        self.show_campaign_progress()

    def show_campaign_progress(self):
        """캠페인 진행률 대화 상자"""
        selection = self.campaign_tree.selection()
        if not selection:
            return

        values = self.campaign_tree.item(selection[0])["values"]
        campaign_id = values[0]

        result = self.api.get_campaign_progress(campaign_id)
        if not result["success"]:
            messagebox.showerror("오류", result["error"])
            return

        data = result["data"]
        campaign = data["campaign"]
        pc = data["pc"]
        monitor = data["monitor"]
        total = data["total"]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"캠페인 진행률 - {campaign['name']}")
        dialog.geometry("500x400")
        dialog.transient(self.root)

        ttk.Label(dialog, text=campaign["name"],
                  font=("맑은 고딕", 14, "bold")).pack(pady=15)

        info = ttk.Frame(dialog, padding="10")
        info.pack(fill=tk.X)
        ttk.Label(info, text=f"기간: {campaign['start_date']} ~ {campaign['end_date']}").pack()
        ttk.Label(info, text=f"상태: {campaign['status']}",
                  font=("맑은 고딕", 11, "bold")).pack(pady=5)

        # PC 진행률
        pc_frame = ttk.LabelFrame(dialog, text=f"PC 실사 ({pc['completed']}/{pc['total']})", padding="10")
        pc_frame.pack(fill=tk.X, padx=20, pady=5)

        pc_bar = ttk.Progressbar(pc_frame, length=400, mode='determinate')
        pc_bar.pack(fill=tk.X)
        pc_bar['value'] = pc['rate']
        ttk.Label(pc_frame, text=f"{pc['rate']}% (미실사: {pc['remaining']}대)",
                  font=("맑은 고딕", 10)).pack()

        # 모니터 진행률
        mon_frame = ttk.LabelFrame(dialog, text=f"모니터 실사 ({monitor['completed']}/{monitor['total']})", padding="10")
        mon_frame.pack(fill=tk.X, padx=20, pady=5)

        mon_bar = ttk.Progressbar(mon_frame, length=400, mode='determinate')
        mon_bar.pack(fill=tk.X)
        mon_bar['value'] = monitor['rate']
        ttk.Label(mon_frame, text=f"{monitor['rate']}% (미실사: {monitor['remaining']}대)",
                  font=("맑은 고딕", 10)).pack()

        # 전체 진행률
        total_frame = ttk.LabelFrame(dialog, text=f"전체 ({total['completed']}/{total['total']})", padding="10")
        total_frame.pack(fill=tk.X, padx=20, pady=5)

        total_bar = ttk.Progressbar(total_frame, length=400, mode='determinate')
        total_bar.pack(fill=tk.X)
        total_bar['value'] = total['rate']
        ttk.Label(total_frame, text=f"{total['rate']}% (미실사: {total['remaining']}대)",
                  font=("맑은 고딕", 11, "bold")).pack()

    def show_unaudited(self):
        """미실사 자산 표시"""
        selection = self.campaign_tree.selection()
        if not selection:
            return

        values = self.campaign_tree.item(selection[0])["values"]
        campaign_id = values[0]

        result = self.api.get_unaudited_assets(campaign_id)
        if not result["success"]:
            messagebox.showerror("오류", result["error"])
            return

        data = result["data"]

        for item in self.unaudited_tree.get_children():
            self.unaudited_tree.delete(item)

        for asset in data["items"]:
            self.unaudited_tree.insert("", tk.END, values=(
                asset["asset_type"], asset["asset_number"],
                asset["management_number"], asset["location_name"],
                asset["employee_number"]
            ))

        messagebox.showinfo(
            "미실사 자산",
            f"캠페인: {data['campaign_name']}\n"
            f"미실사 PC: {data['unaudited_pcs']}대\n"
            f"미실사 모니터: {data['unaudited_monitors']}대\n"
            f"전체 미실사: {data['unaudited_total']}대"
        )

    # ===== PC 관리 탭 =====

    def setup_pc_tab(self, parent):
        """PC 관리 탭"""
        left_panel = ttk.Frame(parent)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        # 통계
        stats_frame = ttk.LabelFrame(left_panel, text="전체 통계", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.pc_stats_labels = {}
        for key, text in [("total", "전체 PC:"), ("done", "조사 완료:"),
                          ("remain", "미완료:"), ("rate", "완료율:")]:
            row = ttk.Frame(stats_frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=text, font=("맑은 고딕", 9, "bold")).pack(side=tk.LEFT)
            lbl = ttk.Label(row, text="-")
            lbl.pack(side=tk.RIGHT)
            self.pc_stats_labels[key] = lbl

        # 검색
        search_frame = ttk.LabelFrame(left_panel, text="검색", padding="10")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="자산번호/사업장/사번:").pack(anchor=tk.W)
        self.pc_search_entry = ttk.Entry(search_frame, width=25)
        self.pc_search_entry.pack(fill=tk.X, pady=5)
        self.pc_search_entry.bind('<Return>', lambda e: self.search_pcs())
        ttk.Button(search_frame, text="검색",
                   command=self.search_pcs).pack(fill=tk.X)

        # 테이블
        right_panel = ttk.Frame(parent)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        columns = ("asset_no", "pc_mgmt", "location", "employee",
                   "registered", "last_survey")
        self.pc_tree = ttk.Treeview(right_panel, columns=columns,
                                    show="headings", height=20)

        pc_headers = [("자산번호", 120), ("PC관리번호", 120), ("사업장명", 140),
                      ("사번", 90), ("등록일시", 100), ("최종조사", 140)]

        for (col, (text, width)) in zip(columns, pc_headers):
            self.pc_tree.heading(col, text=text)
            self.pc_tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL,
                                  command=self.pc_tree.yview)
        self.pc_tree.configure(yscrollcommand=scrollbar.set)
        self.pc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 우클릭 메뉴
        self.pc_menu = tk.Menu(self.pc_tree, tearoff=0)
        self.pc_menu.add_command(label="수정", command=self.edit_pc)
        self.pc_menu.add_command(label="이력 보기", command=self.show_pc_history)
        self.pc_menu.add_separator()
        self.pc_menu.add_command(label="삭제", command=self.delete_pc)
        self.pc_tree.bind("<Button-3>", self.show_pc_context_menu)
        self.pc_tree.bind("<Double-1>", lambda e: self.edit_pc())

    def search_pcs(self):
        """PC 검색"""
        keyword = self.pc_search_entry.get().strip().lower()
        for item in self.pc_tree.get_children():
            self.pc_tree.delete(item)

        for pc in self.pc_data:
            if keyword and not any(keyword in str(pc.get(f, "")).lower()
                    for f in ["asset_number", "pc_management_number",
                              "location_name", "employee_number"]):
                continue
            self.pc_tree.insert("", tk.END, values=(
                pc["asset_number"], pc["pc_management_number"],
                pc["location_name"], pc["employee_number"],
                pc["registered_at"], pc.get("last_survey_date", "-") or "-"
            ))

    def refresh_pc_data(self):
        """PC 데이터 새로고침"""
        result = self.api.get_all_pcs()
        if result["success"]:
            self.pc_data = result["data"]
            self.search_pcs()

            # 통계
            status = self.api.get_pc_survey_status()
            if status["success"]:
                d = status["data"]
                self.pc_stats_labels["total"].config(text=f"{d['total']}")
                self.pc_stats_labels["done"].config(text=f"{d['completed']}")
                self.pc_stats_labels["remain"].config(text=f"{d['remaining']}")
                self.pc_stats_labels["rate"].config(text=f"{d['completion_rate']}%")
        else:
            messagebox.showerror("오류", f"PC 목록 조회 실패\n{result['error']}")

    def show_pc_context_menu(self, event):
        item = self.pc_tree.identify_row(event.y)
        if item:
            self.pc_tree.selection_set(item)
            self.pc_menu.post(event.x_root, event.y_root)

    def edit_pc(self):
        """PC 수정 다이얼로그"""
        selection = self.pc_tree.selection()
        if not selection:
            return
        values = self.pc_tree.item(selection[0])["values"]
        asset_number = values[0]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"PC 수정 - {asset_number}")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()

        fields = [
            ("자산번호:", "new_asset_number", values[0]),
            ("PC관리번호:", "pc_management_number", values[1]),
            ("사업장명:", "location_name", values[2]),
            ("사번:", "employee_number", values[3])
        ]

        entries = {}
        for i, (label, key, val) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, sticky=tk.W,
                                               padx=20, pady=10)
            entry = ttk.Entry(dialog, width=30)
            entry.grid(row=i, column=1, padx=10, pady=10)
            entry.insert(0, str(val))
            entries[key] = entry

        def save():
            data = {}
            if entries["new_asset_number"].get().strip() != str(values[0]):
                data["new_asset_number"] = entries["new_asset_number"].get().strip()
            if entries["pc_management_number"].get().strip() != str(values[1]):
                data["pc_management_number"] = entries["pc_management_number"].get().strip()
            if entries["location_name"].get().strip() != str(values[2]):
                data["location_name"] = entries["location_name"].get().strip()
            if entries["employee_number"].get().strip() != str(values[3]):
                data["employee_number"] = entries["employee_number"].get().strip()

            if not data:
                messagebox.showinfo("알림", "변경된 내용이 없습니다", parent=dialog)
                return

            result = self.api.update_pc_info(asset_number, **data)
            if result["success"]:
                messagebox.showinfo("성공", "수정 완료", parent=dialog)
                dialog.destroy()
                self.refresh_pc_data()
            else:
                messagebox.showerror("오류", result["error"], parent=dialog)

        ttk.Button(dialog, text="저장", command=save).grid(
            row=len(fields), column=0, columnspan=2, pady=20)

    def show_pc_history(self):
        """PC 이력 보기"""
        selection = self.pc_tree.selection()
        if not selection:
            return
        asset_number = self.pc_tree.item(selection[0])["values"][0]
        self.show_asset_history(asset_number)

    def delete_pc(self):
        """PC 삭제"""
        selection = self.pc_tree.selection()
        if not selection:
            return
        asset_number = self.pc_tree.item(selection[0])["values"][0]

        if not messagebox.askyesno("확인", f"PC '{asset_number}'을(를) 삭제하시겠습니까?"):
            return

        result = self.api.delete_pc(asset_number)
        if result["success"]:
            messagebox.showinfo("성공", "PC가 삭제되었습니다")
            self.refresh_pc_data()
        else:
            messagebox.showerror("오류", result["error"])

    # ===== 모니터 관리 탭 =====

    def setup_monitor_tab(self, parent):
        """모니터 관리 탭"""
        left_panel = ttk.Frame(parent)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))

        stats_frame = ttk.LabelFrame(left_panel, text="전체 통계", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))

        self.monitor_stats_labels = {}
        for key, text in [("total", "전체 모니터:"), ("done", "조사 완료:"),
                          ("remain", "미완료:"), ("rate", "완료율:")]:
            row = ttk.Frame(stats_frame)
            row.pack(fill=tk.X, pady=3)
            ttk.Label(row, text=text, font=("맑은 고딕", 9, "bold")).pack(side=tk.LEFT)
            lbl = ttk.Label(row, text="-")
            lbl.pack(side=tk.RIGHT)
            self.monitor_stats_labels[key] = lbl

        search_frame = ttk.LabelFrame(left_panel, text="검색", padding="10")
        search_frame.pack(fill=tk.X)

        ttk.Label(search_frame, text="자산번호/사업장/사번:").pack(anchor=tk.W)
        self.monitor_search_entry = ttk.Entry(search_frame, width=25)
        self.monitor_search_entry.pack(fill=tk.X, pady=5)
        self.monitor_search_entry.bind('<Return>', lambda e: self.search_monitors())
        ttk.Button(search_frame, text="검색",
                   command=self.search_monitors).pack(fill=tk.X)

        right_panel = ttk.Frame(parent)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        columns = ("asset_no", "mgmt_no", "location", "employee",
                   "connected_pc", "registered", "last_survey")
        self.monitor_tree = ttk.Treeview(right_panel, columns=columns,
                                         show="headings", height=20)

        headers = [("자산번호", 110), ("관리번호", 110), ("사업장명", 130),
                   ("사번", 80), ("연결 PC", 110), ("등록일", 100), ("최종조사", 130)]

        for (col, (text, width)) in zip(columns, headers):
            self.monitor_tree.heading(col, text=text)
            self.monitor_tree.column(col, width=width, anchor=tk.CENTER)

        scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL,
                                  command=self.monitor_tree.yview)
        self.monitor_tree.configure(yscrollcommand=scrollbar.set)
        self.monitor_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.monitor_menu = tk.Menu(self.monitor_tree, tearoff=0)
        self.monitor_menu.add_command(label="수정", command=self.edit_monitor)
        self.monitor_menu.add_command(label="이력 보기", command=self.show_monitor_history)
        self.monitor_menu.add_separator()
        self.monitor_menu.add_command(label="삭제", command=self.delete_monitor)
        self.monitor_tree.bind("<Button-3>", self.show_monitor_context_menu)
        self.monitor_tree.bind("<Double-1>", lambda e: self.edit_monitor())

    def search_monitors(self):
        """모니터 검색"""
        keyword = self.monitor_search_entry.get().strip().lower()
        for item in self.monitor_tree.get_children():
            self.monitor_tree.delete(item)

        for m in self.monitor_data:
            if keyword and not any(keyword in str(m.get(f, "")).lower()
                    for f in ["asset_number", "monitor_management_number",
                              "location_name", "employee_number"]):
                continue
            self.monitor_tree.insert("", tk.END, values=(
                m["asset_number"], m["monitor_management_number"],
                m["location_name"], m["employee_number"],
                m.get("connected_pc_asset_number", "-") or "-",
                m["registered_at"], m.get("last_survey_date", "-") or "-"
            ))

    def refresh_monitor_data(self):
        """모니터 데이터 새로고침"""
        result = self.api.get_all_monitors()
        if result["success"]:
            self.monitor_data = result["data"]
            self.search_monitors()

            status = self.api.get_monitor_survey_status()
            if status["success"]:
                d = status["data"]
                self.monitor_stats_labels["total"].config(text=f"{d['total']}")
                self.monitor_stats_labels["done"].config(text=f"{d['completed']}")
                self.monitor_stats_labels["remain"].config(text=f"{d['remaining']}")
                self.monitor_stats_labels["rate"].config(text=f"{d['completion_rate']}%")
        else:
            messagebox.showerror("오류", f"모니터 목록 조회 실패\n{result['error']}")

    def show_monitor_context_menu(self, event):
        item = self.monitor_tree.identify_row(event.y)
        if item:
            self.monitor_tree.selection_set(item)
            self.monitor_menu.post(event.x_root, event.y_root)

    def edit_monitor(self):
        """모니터 수정 다이얼로그"""
        selection = self.monitor_tree.selection()
        if not selection:
            return
        values = self.monitor_tree.item(selection[0])["values"]
        asset_number = values[0]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"모니터 수정 - {asset_number}")
        dialog.geometry("400x320")
        dialog.transient(self.root)
        dialog.grab_set()

        fields = [
            ("관리번호:", "monitor_management_number", values[1]),
            ("사업장명:", "location_name", values[2]),
            ("사번:", "employee_number", values[3]),
            ("연결 PC:", "connected_pc_asset_number", values[4])
        ]

        entries = {}
        for i, (label, key, val) in enumerate(fields):
            ttk.Label(dialog, text=label).grid(row=i, column=0, sticky=tk.W,
                                               padx=20, pady=10)
            entry = ttk.Entry(dialog, width=30)
            entry.grid(row=i, column=1, padx=10, pady=10)
            val_str = str(val) if val and str(val) != "-" else ""
            entry.insert(0, val_str)
            entries[key] = entry

        def save():
            data = {}
            if entries["monitor_management_number"].get().strip() != str(values[1]):
                data["monitor_management_number"] = entries["monitor_management_number"].get().strip()
            if entries["location_name"].get().strip() != str(values[2]):
                data["location_name"] = entries["location_name"].get().strip()
            if entries["employee_number"].get().strip() != str(values[3]):
                data["employee_number"] = entries["employee_number"].get().strip()
            new_pc = entries["connected_pc_asset_number"].get().strip()
            old_pc = str(values[4]) if values[4] and str(values[4]) != "-" else ""
            if new_pc != old_pc:
                data["connected_pc_asset_number"] = new_pc or None

            if not data:
                messagebox.showinfo("알림", "변경된 내용이 없습니다", parent=dialog)
                return

            result = self.api.update_monitor(asset_number, **data)
            if result["success"]:
                messagebox.showinfo("성공", "수정 완료", parent=dialog)
                dialog.destroy()
                self.refresh_monitor_data()
            else:
                messagebox.showerror("오류", result["error"], parent=dialog)

        ttk.Button(dialog, text="저장", command=save).grid(
            row=len(fields), column=0, columnspan=2, pady=20)

    def show_monitor_history(self):
        """모니터 이력 보기"""
        selection = self.monitor_tree.selection()
        if not selection:
            return
        asset_number = self.monitor_tree.item(selection[0])["values"][0]
        self.show_asset_history(asset_number)

    def delete_monitor(self):
        """모니터 삭제"""
        selection = self.monitor_tree.selection()
        if not selection:
            return
        asset_number = self.monitor_tree.item(selection[0])["values"][0]

        if not messagebox.askyesno("확인", f"모니터 '{asset_number}'을(를) 삭제하시겠습니까?"):
            return

        result = self.api.delete_monitor(asset_number)
        if result["success"]:
            messagebox.showinfo("성공", "모니터가 삭제되었습니다")
            self.refresh_monitor_data()
        else:
            messagebox.showerror("오류", result["error"])

    # ===== 공통: 자산 이력 보기 =====

    def show_asset_history(self, asset_number):
        """자산 이력 다이얼로그"""
        result = self.api.get_asset_history(asset_number)
        if not result["success"]:
            messagebox.showerror("오류", result["error"])
            return

        histories = result["data"]

        dialog = tk.Toplevel(self.root)
        dialog.title(f"자산 이력 - {asset_number}")
        dialog.geometry("700x400")
        dialog.transient(self.root)

        ttk.Label(dialog, text=f"자산번호: {asset_number}",
                  font=("맑은 고딕", 13, "bold")).pack(pady=10)

        if not histories:
            ttk.Label(dialog, text="이력 데이터가 없습니다",
                      font=("맑은 고딕", 11)).pack(pady=30)
            return

        columns = ("date", "type", "action", "description")
        tree = ttk.Treeview(dialog, columns=columns, show="headings", height=15)

        for col, (text, width) in zip(columns, [
            ("날짜", 150), ("유형", 60), ("작업", 80), ("상세", 350)
        ]):
            tree.heading(col, text=text)
            tree.column(col, width=width, anchor=tk.CENTER if width < 200 else tk.W)

        for h in histories:
            tree.insert("", tk.END, values=(
                h["changed_at"], h["asset_type"],
                h["action_type"], h["description"] or ""
            ))

        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    # ===== 공통 기능 =====

    def check_connection(self):
        """서버 연결 확인"""
        result = self.api.test_connection()
        if result["success"]:
            self.status_label.config(text="● 온라인", foreground="green")
        else:
            self.status_label.config(text="● 오프라인", foreground="red")

    def refresh_all(self):
        """전체 새로고침"""
        self.refresh_pc_data()
        self.refresh_monitor_data()
        self.refresh_dashboard()
        self.refresh_campaigns()
        self.refresh_rereg_requests()

    def backup_data(self):
        """데이터 백업"""
        result = self.api.backup_data()
        if result["success"]:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON 파일", "*.json")],
                initialfile=f"kumon_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(result["data"], f, ensure_ascii=False, indent=2)
                messagebox.showinfo("성공", f"백업 완료\n{file_path}")
        else:
            messagebox.showerror("오류", f"백업 실패\n{result['error']}")

    def export_to_excel(self):
        """Excel 내보내기"""
        if not HAS_PANDAS:
            messagebox.showwarning("알림", "pandas가 설치되어 있지 않습니다")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx")],
            initialfile=f"kumon_asset_{datetime.now().strftime('%Y%m%d')}.xlsx"
        )
        if not file_path:
            return

        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                if self.pc_data:
                    pc_df = pd.DataFrame(self.pc_data)
                    pc_df.to_excel(writer, sheet_name='PC', index=False)
                if self.monitor_data:
                    mon_df = pd.DataFrame(self.monitor_data)
                    mon_df.to_excel(writer, sheet_name='모니터', index=False)

            messagebox.showinfo("성공", f"Excel 내보내기 완료\n{file_path}")
        except Exception as e:
            messagebox.showerror("오류", f"Excel 내보내기 실패\n{e}")


    # ===== 재등록 요청 탭 =====

    def setup_rereg_tab(self, parent):
        """재등록 요청 관리 탭"""
        # 필터 프레임
        filter_frame = ttk.Frame(parent)
        filter_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(filter_frame, text="상태 필터:",
                  font=("맑은 고딕", 10)).pack(side=tk.LEFT)

        self.rereg_filter_var = tk.StringVar(value="전체")
        for status in ["전체", "대기", "승인", "거절"]:
            ttk.Radiobutton(filter_frame, text=status,
                            variable=self.rereg_filter_var, value=status,
                            command=self.refresh_rereg_requests
                            ).pack(side=tk.LEFT, padx=5)

        self.rereg_count_label = ttk.Label(filter_frame, text="",
                                           font=("맑은 고딕", 10, "bold"),
                                           foreground="red")
        self.rereg_count_label.pack(side=tk.RIGHT)

        ttk.Button(filter_frame, text="새로고침",
                   command=self.refresh_rereg_requests).pack(side=tk.RIGHT, padx=5)

        # 테이블
        columns = ("id", "asset_number", "requester", "reason",
                   "new_mgmt", "new_location", "new_employee", "status", "requested_at")
        self.rereg_tree = ttk.Treeview(parent, columns=columns, show="headings", height=20)

        col_config = [
            ("id", "ID", 40),
            ("asset_number", "자산번호", 100),
            ("requester", "요청자", 80),
            ("reason", "사유", 200),
            ("new_mgmt", "새 관리번호", 100),
            ("new_location", "새 사업장", 100),
            ("new_employee", "새 사번", 80),
            ("status", "상태", 60),
            ("requested_at", "요청일시", 130)
        ]

        for col_id, heading, width in col_config:
            self.rereg_tree.heading(col_id, text=heading)
            self.rereg_tree.column(col_id, width=width, minwidth=40)

        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.rereg_tree.yview)
        self.rereg_tree.configure(yscrollcommand=scrollbar.set)

        self.rereg_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 더블클릭 → 상세
        self.rereg_tree.bind("<Double-1>", self.show_rereg_detail)

        # 우클릭 메뉴
        self.rereg_menu = tk.Menu(self.root, tearoff=0)
        self.rereg_menu.add_command(label="✅ 승인", command=lambda: self.process_rereg("approve"))
        self.rereg_menu.add_command(label="❌ 거절", command=lambda: self.process_rereg("reject"))
        self.rereg_tree.bind("<Button-3>", self.show_rereg_context_menu)

    def show_rereg_context_menu(self, event):
        """재등록 요청 우클릭 메뉴"""
        item = self.rereg_tree.identify_row(event.y)
        if item:
            self.rereg_tree.selection_set(item)
            vals = self.rereg_tree.item(item, 'values')
            if vals and vals[7] == "대기":
                self.rereg_menu.post(event.x_root, event.y_root)

    def refresh_rereg_requests(self):
        """재등록 요청 목록 갱신"""
        status_filter = self.rereg_filter_var.get()
        status_param = None if status_filter == "전체" else status_filter

        result = self.api.get_re_register_requests(status=status_param)
        if not result["success"]:
            return

        for item in self.rereg_tree.get_children():
            self.rereg_tree.delete(item)

        pending_count = 0
        for r in result["data"]:
            if r["status"] == "대기":
                pending_count += 1
            tag = "pending" if r["status"] == "대기" else ""
            self.rereg_tree.insert("", tk.END, values=(
                r["id"], r["asset_number"], r["requester_employee"],
                r["reason"][:50], r["new_pc_management_number"],
                r["new_location_name"], r["new_employee_number"],
                r["status"], r["requested_at"]
            ), tags=(tag,))

        self.rereg_tree.tag_configure("pending", background="#FFF3CD")

        # 대기 건수 표시
        if pending_count > 0:
            self.rereg_count_label.config(text=f"⚠️ 대기 중: {pending_count}건")
        else:
            self.rereg_count_label.config(text="")

    def show_rereg_detail(self, event=None):
        """재등록 요청 상세 다이얼로그"""
        selected = self.rereg_tree.selection()
        if not selected:
            return

        vals = self.rereg_tree.item(selected[0], 'values')
        req_id = int(vals[0])
        is_pending = vals[7] == "대기"

        dialog = tk.Toplevel(self.root)
        dialog.title(f"재등록 요청 상세 - #{req_id}")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=f"📋 재등록 요청 #{req_id}",
                  font=("맑은 고딕", 14, "bold")).pack(pady=15)

        info_frame = ttk.Frame(dialog, padding="20")
        info_frame.pack(fill=tk.BOTH, expand=True)

        details = [
            ("자산번호", vals[1]),
            ("요청자 사번", vals[2]),
            ("상태", vals[7]),
            ("요청일시", vals[8]),
            ("새 PC관리번호", vals[4]),
            ("새 사업장명", vals[5]),
            ("새 사번", vals[6]),
        ]

        for i, (label, value) in enumerate(details):
            ttk.Label(info_frame, text=f"{label}:",
                      font=("맑은 고딕", 10, "bold")).grid(row=i, column=0, sticky=tk.W, pady=4)
            ttk.Label(info_frame, text=str(value),
                      font=("맑은 고딕", 10)).grid(row=i, column=1, sticky=tk.W, pady=4, padx=(10, 0))

        # 사유 (전체 표시)
        row_reason = len(details)
        ttk.Label(info_frame, text="재등록 사유:",
                  font=("맑은 고딕", 10, "bold")).grid(row=row_reason, column=0, sticky=tk.NW, pady=4)
        reason_text = tk.Text(info_frame, width=35, height=3, font=("맑은 고딕", 10),
                              state=tk.NORMAL, wrap=tk.WORD)
        reason_text.grid(row=row_reason, column=1, sticky=tk.EW, pady=4, padx=(10, 0))
        reason_text.insert(tk.END, vals[3])
        reason_text.config(state=tk.DISABLED)

        info_frame.columnconfigure(1, weight=1)

        if is_pending:
            # 코멘트 입력
            comment_frame = ttk.LabelFrame(dialog, text="관리자 코멘트", padding="10")
            comment_frame.pack(fill=tk.X, padx=20, pady=5)
            comment_entry = tk.Text(comment_frame, width=40, height=2,
                                     font=("맑은 고딕", 10))
            comment_entry.pack(fill=tk.X)

            # 버튼
            btn_frame = ttk.Frame(dialog)
            btn_frame.pack(pady=15)

            def approve():
                comment = comment_entry.get("1.0", tk.END).strip()
                result = self.api.approve_re_register(req_id, comment or None)
                if result["success"]:
                    messagebox.showinfo("승인 완료", "재등록이 승인되었습니다", parent=dialog)
                    dialog.destroy()
                    self.refresh_rereg_requests()
                    self.refresh_pc_data()
                else:
                    messagebox.showerror("오류", result["error"], parent=dialog)

            def reject():
                comment = comment_entry.get("1.0", tk.END).strip()
                if not comment:
                    messagebox.showwarning("입력 필요", "거절 사유를 입력해주세요", parent=dialog)
                    return
                result = self.api.reject_re_register(req_id, comment)
                if result["success"]:
                    messagebox.showinfo("거절 완료", "재등록 요청이 거절되었습니다", parent=dialog)
                    dialog.destroy()
                    self.refresh_rereg_requests()
                else:
                    messagebox.showerror("오류", result["error"], parent=dialog)

            ttk.Button(btn_frame, text="✅ 승인", command=approve).pack(side=tk.LEFT, padx=10)
            ttk.Button(btn_frame, text="❌ 거절", command=reject).pack(side=tk.LEFT, padx=10)

    def process_rereg(self, action: str):
        """우클릭 메뉴에서 승인/거절 처리"""
        selected = self.rereg_tree.selection()
        if not selected:
            return

        vals = self.rereg_tree.item(selected[0], 'values')
        req_id = int(vals[0])

        if action == "approve":
            if messagebox.askyesno("승인 확인", f"재등록 요청 #{req_id}을 승인하시겠습니까?"):
                result = self.api.approve_re_register(req_id)
                if result["success"]:
                    messagebox.showinfo("성공", "승인 완료")
                    self.refresh_rereg_requests()
                    self.refresh_pc_data()
                else:
                    messagebox.showerror("오류", result["error"])
        elif action == "reject":
            comment = simpledialog.askstring("거절 사유", "거절 사유를 입력하세요:")
            if comment:
                result = self.api.reject_re_register(req_id, comment)
                if result["success"]:
                    messagebox.showinfo("성공", "거절 완료")
                    self.refresh_rereg_requests()
                else:
                    messagebox.showerror("오류", result["error"])


if __name__ == "__main__":
    root = tk.Tk()
    app = AdminApp(root)
    root.mainloop()
