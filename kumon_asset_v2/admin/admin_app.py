"""
구몬 자산관리 시스템 - 관리자 프로그램 v3.0
PC와 모니터 통합 관리
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import json
from api_client import AdminAPIClient


class AssetAdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("구몬 자산관리 시스템 - 관리자 v3.0")
        self.root.geometry("1400x800")

        self.api = AdminAPIClient()
        self.pc_data = []
        self.monitor_data = []

        self.setup_ui()
        self.check_connection()

    def setup_ui(self):
        """UI 구성"""
        # 헤더
        header = ttk.Frame(self.root, padding="10")
        header.pack(fill=tk.X)

        ttk.Label(
            header,
            text="구몬 자산관리 - 관리자",
            font=("맑은 고딕", 16, "bold")
        ).pack(side=tk.LEFT, padx=(0, 20))

        self.status_label = ttk.Label(header, text="● 확인 중...", font=("맑은 고딕", 10))
        self.status_label.pack(side=tk.LEFT)

        ttk.Button(header, text="새로고침", command=self.refresh_all).pack(side=tk.RIGHT, padx=5)
        ttk.Button(header, text="Excel 내보내기", command=self.export_to_excel).pack(side=tk.RIGHT, padx=5)
        ttk.Button(header, text="백업", command=self.backup_data).pack(side=tk.RIGHT, padx=5)

        # 탭
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
        # 좌측 통계 패널
        left_panel = ttk.Frame(parent, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        ttk.Label(left_panel, text="PC 현황", font=("맑은 고딕", 14, "bold")).pack(pady=(0, 20))

        # 통계
        stats_frame = ttk.LabelFrame(left_panel, text="전체 통계", padding="15")
        stats_frame.pack(fill=tk.X, pady=(0, 15))

        self.pc_stats_labels = {}
        for key, label in [("total", "전체 PC"), ("surveyed", "조사 완료"),
                          ("remaining", "미완료"), ("rate", "완료율")]:
            frame = ttk.Frame(stats_frame)
            frame.pack(fill=tk.X, pady=5)
            ttk.Label(frame, text=label + ":", font=("맑은 고딕", 10)).pack(side=tk.LEFT)
            value_label = ttk.Label(frame, text="-", font=("맑은 고딕", 10, "bold"))
            value_label.pack(side=tk.RIGHT)
            self.pc_stats_labels[key] = value_label

        # 검색
        search_frame = ttk.LabelFrame(left_panel, text="검색", padding="15")
        search_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(search_frame, text="자산번호/사업장:").pack(anchor=tk.W, pady=(0, 5))
        self.pc_search_entry = ttk.Entry(search_frame)
        self.pc_search_entry.pack(fill=tk.X, pady=(0, 10))
        self.pc_search_entry.bind('<Return>', lambda e: self.search_pc())
        ttk.Button(search_frame, text="검색", command=self.search_pc).pack(fill=tk.X)

        # 우측 테이블
        right_panel = ttk.Frame(parent)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 테이블
        columns = ("자산번호", "PC관리번호", "사업장명", "사번", "등록일시", "최종조사")
        self.pc_tree = ttk.Treeview(right_panel, columns=columns, show="headings", height=25)

        for col in columns:
            self.pc_tree.heading(col, text=col)
            self.pc_tree.column(col, width=150)

        scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.pc_tree.yview)
        self.pc_tree.configure(yscrollcommand=scrollbar.set)

        self.pc_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 우클릭 메뉴
        self.pc_context_menu = tk.Menu(self.root, tearoff=0)
        self.pc_context_menu.add_command(label="삭제", command=self.delete_selected_pc)
        self.pc_tree.bind("<Button-3>", self.show_pc_context_menu)

    def setup_monitor_tab(self, parent):
        """모니터 관리 탭"""
        # 좌측 통계 패널
        left_panel = ttk.Frame(parent, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)

        ttk.Label(left_panel, text="모니터 현황", font=("맑은 고딕", 14, "bold")).pack(pady=(0, 20))

        # 통계
        stats_frame = ttk.LabelFrame(left_panel, text="전체 통계", padding="15")
        stats_frame.pack(fill=tk.X, pady=(0, 15))

        self.monitor_stats_labels = {}
        for key, label in [("total", "전체 모니터"), ("surveyed", "조사 완료"),
                          ("remaining", "미완료"), ("rate", "완료율")]:
            frame = ttk.Frame(stats_frame)
            frame.pack(fill=tk.X, pady=5)
            ttk.Label(frame, text=label + ":", font=("맑은 고딕", 10)).pack(side=tk.LEFT)
            value_label = ttk.Label(frame, text="-", font=("맑은 고딕", 10, "bold"))
            value_label.pack(side=tk.RIGHT)
            self.monitor_stats_labels[key] = value_label

        # 검색
        search_frame = ttk.LabelFrame(left_panel, text="검색", padding="15")
        search_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(search_frame, text="자산번호/사업장:").pack(anchor=tk.W, pady=(0, 5))
        self.monitor_search_entry = ttk.Entry(search_frame)
        self.monitor_search_entry.pack(fill=tk.X, pady=(0, 10))
        self.monitor_search_entry.bind('<Return>', lambda e: self.search_monitor())
        ttk.Button(search_frame, text="검색", command=self.search_monitor).pack(fill=tk.X)

        # 우측 테이블
        right_panel = ttk.Frame(parent)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 테이블
        columns = ("자산번호", "모니터관리번호", "사업장명", "사번", "연결PC", "등록일시", "최종조사")
        self.monitor_tree = ttk.Treeview(right_panel, columns=columns, show="headings", height=25)

        for col in columns:
            self.monitor_tree.heading(col, text=col)
            self.monitor_tree.column(col, width=130)

        scrollbar = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.monitor_tree.yview)
        self.monitor_tree.configure(yscrollcommand=scrollbar.set)

        self.monitor_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 우클릭 메뉴
        self.monitor_context_menu = tk.Menu(self.root, tearoff=0)
        self.monitor_context_menu.add_command(label="삭제", command=self.delete_selected_monitor)
        self.monitor_tree.bind("<Button-3>", self.show_monitor_context_menu)

    def check_connection(self):
        """서버 연결 확인"""
        result = self.api.test_connection()
        if result["success"]:
            self.status_label.config(text="● 온라인", foreground="green")
            self.refresh_all()
        else:
            self.status_label.config(text="● 오프라인", foreground="red")
            messagebox.showerror("연결 오류", f"서버에 연결할 수 없습니다\n{result['error']}")

    def refresh_all(self):
        """전체 새로고침"""
        self.refresh_pc_data()
        self.refresh_monitor_data()

    def refresh_pc_data(self):
        """PC 데이터 새로고침"""
        # PC 목록 조회
        result = self.api.get_all_pcs()
        if result["success"]:
            self.pc_data = result["data"]
            self.update_pc_table(self.pc_data)
        else:
            messagebox.showerror("오류", f"PC 목록 조회 실패\n{result['error']}")

        # PC 통계 조회
        result = self.api.get_pc_survey_status()
        if result["success"]:
            stats = result["data"]
            self.pc_stats_labels["total"].config(text=f"{stats['total']}대")
            self.pc_stats_labels["surveyed"].config(text=f"{stats['completed']}대")
            self.pc_stats_labels["remaining"].config(text=f"{stats['remaining']}대")
            self.pc_stats_labels["rate"].config(text=f"{stats['completion_rate']}%")

    def refresh_monitor_data(self):
        """모니터 데이터 새로고침"""
        # 모니터 목록 조회
        result = self.api.get_all_monitors()
        if result["success"]:
            self.monitor_data = result["data"]
            self.update_monitor_table(self.monitor_data)
        else:
            messagebox.showerror("오류", f"모니터 목록 조회 실패\n{result['error']}")

        # 모니터 통계 조회
        result = self.api.get_monitor_survey_status()
        if result["success"]:
            stats = result["data"]
            self.monitor_stats_labels["total"].config(text=f"{stats['total']}대")
            self.monitor_stats_labels["surveyed"].config(text=f"{stats['completed']}대")
            self.monitor_stats_labels["remaining"].config(text=f"{stats['remaining']}대")
            self.monitor_stats_labels["rate"].config(text=f"{stats['completion_rate']}%")

    def update_pc_table(self, data):
        """PC 테이블 업데이트"""
        self.pc_tree.delete(*self.pc_tree.get_children())
        for pc in data:
            self.pc_tree.insert("", tk.END, values=(
                pc["asset_number"],
                pc["pc_management_number"],
                pc["location_name"],
                pc["employee_number"],
                pc["registered_at"],
                pc.get("last_survey_date", "-")
            ))

    def update_monitor_table(self, data):
        """모니터 테이블 업데이트"""
        self.monitor_tree.delete(*self.monitor_tree.get_children())
        for monitor in data:
            self.monitor_tree.insert("", tk.END, values=(
                monitor["asset_number"],
                monitor["monitor_management_number"],
                monitor["location_name"],
                monitor["employee_number"],
                monitor.get("connected_pc_asset_number", "-"),
                monitor["registered_at"],
                monitor.get("last_survey_date", "-")
            ))

    def search_pc(self):
        """PC 검색"""
        keyword = self.pc_search_entry.get().strip().lower()
        if not keyword:
            self.update_pc_table(self.pc_data)
            return

        filtered = [
            pc for pc in self.pc_data
            if keyword in pc["asset_number"].lower() or keyword in pc["location_name"].lower()
        ]
        self.update_pc_table(filtered)

    def search_monitor(self):
        """모니터 검색"""
        keyword = self.monitor_search_entry.get().strip().lower()
        if not keyword:
            self.update_monitor_table(self.monitor_data)
            return

        filtered = [
            m for m in self.monitor_data
            if keyword in m["asset_number"].lower() or keyword in m["location_name"].lower()
        ]
        self.update_monitor_table(filtered)

    def show_pc_context_menu(self, event):
        """PC 우클릭 메뉴"""
        item = self.pc_tree.identify_row(event.y)
        if item:
            self.pc_tree.selection_set(item)
            self.pc_context_menu.post(event.x_root, event.y_root)

    def show_monitor_context_menu(self, event):
        """모니터 우클릭 메뉴"""
        item = self.monitor_tree.identify_row(event.y)
        if item:
            self.monitor_tree.selection_set(item)
            self.monitor_context_menu.post(event.x_root, event.y_root)

    def delete_selected_pc(self):
        """선택된 PC 삭제"""
        selected = self.pc_tree.selection()
        if not selected:
            return

        values = self.pc_tree.item(selected[0])["values"]
        asset_number = values[0]

        if messagebox.askyesno("확인", f"PC {asset_number}을(를) 삭제하시겠습니까?"):
            result = self.api.delete_pc(asset_number)
            if result["success"]:
                messagebox.showinfo("성공", "PC가 삭제되었습니다")
                self.refresh_pc_data()
            else:
                messagebox.showerror("오류", result["error"])

    def delete_selected_monitor(self):
        """선택된 모니터 삭제"""
        selected = self.monitor_tree.selection()
        if not selected:
            return

        values = self.monitor_tree.item(selected[0])["values"]
        asset_number = values[0]

        if messagebox.askyesno("확인", f"모니터 {asset_number}을(를) 삭제하시겠습니까?"):
            result = self.api.delete_monitor(asset_number)
            if result["success"]:
                messagebox.showinfo("성공", "모니터가 삭제되었습니다")
                self.refresh_monitor_data()
            else:
                messagebox.showerror("오류", result["error"])

    def backup_data(self):
        """데이터 백업"""
        result = self.api.backup_data()
        if not result["success"]:
            messagebox.showerror("오류", f"백업 실패\n{result['error']}")
            return

        # 저장 경로 선택
        filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=filename
        )

        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(result["data"], f, ensure_ascii=False, indent=2)
                messagebox.showinfo("성공", f"백업 완료\n{filepath}")
            except Exception as e:
                messagebox.showerror("오류", f"파일 저장 실패\n{str(e)}")

    def export_to_excel(self):
        """Excel 내보내기"""
        try:
            import pandas as pd

            # PC 데이터프레임
            df_pc = pd.DataFrame(self.pc_data)
            if not df_pc.empty:
                df_pc = df_pc[['asset_number', 'pc_management_number', 'location_name',
                              'employee_number', 'registered_at', 'last_survey_date']]
                df_pc.columns = ['자산번호', 'PC관리번호', '사업장명', '사번', '등록일시', '최종조사']

            # 모니터 데이터프레임
            df_monitor = pd.DataFrame(self.monitor_data)
            if not df_monitor.empty:
                df_monitor = df_monitor[['asset_number', 'monitor_management_number', 'location_name',
                                        'employee_number', 'connected_pc_asset_number', 'registered_at', 'last_survey_date']]
                df_monitor.columns = ['자산번호', '모니터관리번호', '사업장명', '사번', '연결PC', '등록일시', '최종조사']

            # 저장
            filename = f"asset_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile=filename
            )

            if filepath:
                with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                    if not df_pc.empty:
                        df_pc.to_excel(writer, sheet_name='PC목록', index=False)
                    if not df_monitor.empty:
                        df_monitor.to_excel(writer, sheet_name='모니터목록', index=False)

                messagebox.showinfo("성공", f"Excel 내보내기 완료\n{filepath}")

        except ImportError:
            messagebox.showerror("오류", "pandas 또는 openpyxl이 설치되지 않았습니다")
        except Exception as e:
            messagebox.showerror("오류", f"Excel 내보내기 실패\n{str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = AssetAdminApp(root)
    root.mainloop()
