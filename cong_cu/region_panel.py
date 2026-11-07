"""Danh sách ảnh đã cắt, xem trước và bảng tiến độ bốn bản văn."""
from tkinter import messagebox, ttk
import tkinter as tk

from PIL import Image, ImageTk

from ten_file import CAC_BAN
from .region_actions import region_id

STATUS = {"not_reviewed": "Chưa xem", "draft": "Đang làm", "complete": "Đã kiểm tra đủ", "not_present": "Không có trong nguồn"}


class RegionPanel:
    def __init__(self, parent, app):
        self.app = app
        self.frame = ttk.Frame(parent, padding=(8, 0))
        ttk.Label(self.frame, text="Các vùng của bài đang chọn").pack(anchor="w")
        self.tree = ttk.Treeview(self.frame, columns=("kind", "part", "page"), show="headings", height=9, selectmode="browse")
        for key, label, width in [("kind", "Bản văn", 105), ("part", "Phần", 45), ("page", "Trang", 50)]:
            self.tree.heading(key, text=label); self.tree.column(key, width=width, stretch=False)
        self.tree.pack(fill="x", pady=4)
        self.tree.bind("<<TreeviewSelect>>", self.preview)
        self.preview_label = ttk.Label(self.frame, text="Chọn một vùng để xem trước", anchor="center", wraplength=260)
        self.preview_label.pack(fill="both", expand=True)
        ttk.Button(self.frame, text="Chỉnh vùng đã chọn", command=self.edit).pack(fill="x", pady=3)
        ttk.Button(self.frame, text="Bỏ vùng đã chọn", command=self.remove).pack(fill="x", pady=3)
        ttk.Button(self.frame, text="Hoàn tác thao tác gần nhất", command=app.undo_last).pack(fill="x", pady=3)
        ttk.Button(self.frame, text="Đã kiểm tra đủ / bỏ xác nhận", command=self.toggle_reviewed).pack(fill="x", pady=3)
        ttk.Button(self.frame, text="Tiến độ bốn bản văn", command=self.progress).pack(fill="x", pady=3)
        ttk.Label(self.frame, text="Khung xanh: vùng đã lưu. Xác nhận đủ là do bạn kiểm tra, không phải kết quả dóng hàng.", wraplength=260).pack(anchor="w", pady=6)
        self.records = {}
        self.preview_image = None

    def refresh(self):
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        records = self.app.workspace.regions.list(work=self.app.work.get().strip(), version=self.app.version.get())
        self.records = {region_id(r): r for r in records}
        for record in sorted(records, key=lambda r: (list(CAC_BAN).index(r["kind"]), r["sequence"])):
            self.tree.insert("", "end", iid=region_id(record), values=(CAC_BAN[record["kind"]][0], record["sequence"], record.get("page") or "TXT"))
        if selected and selected[0] in self.records:
            self.tree.selection_set(selected[0])
            self.preview()
        else:
            self.preview_label.configure(image="", text="Chọn một vùng để xem trước")
            self.preview_image = None

    def selected(self):
        selected = self.tree.selection()
        if not selected:
            raise ValueError("Chọn một vùng trong danh sách bên phải trước.")
        return self.app.workspace.regions.find(selected[0])

    def preview(self, _event=None):
        try:
            record = self.selected()
            png = next((p for p in record["files"] if p.endswith(".png")), None)
            if png:
                with Image.open(self.app.workspace.root / png) as image:
                    image = image.convert("RGB"); image.thumbnail((265, 280))
                    self.preview_image = ImageTk.PhotoImage(image)
                self.preview_label.configure(image=self.preview_image, text="")
            else:
                text = (self.app.workspace.root / record["text_file"]).read_text(encoding="utf-8")
                self.preview_label.configure(image="", text=text[:450])
                self.preview_image = None
        except (ValueError, OSError):
            self.preview_label.configure(image="", text="Chưa xem được ảnh/text của vùng này.")

    def edit(self):
        try:
            record = self.selected()
            if record["mode"] == "text":
                from pathlib import Path
                from .text_ui import open_text_window
                open_text_window(self.app, Path(record["source_path"]), record=record)
            else:
                self.app.edit_region(record)
        except Exception as error:
            messagebox.showerror("Chưa mở vùng", str(error))

    def remove(self):
        try:
            record = self.selected()
            if not messagebox.askyesno("Bỏ vùng", f"Bỏ phần {record['sequence']} của {record['work']} / {CAC_BAN[record['kind']][0]}?\nCó thể dùng Hoàn tác để khôi phục."):
                return
            self.app.workspace.regions.remove(region_id(record))
            self.app.cancel_edit()
            self.app.refresh_regions()
            self.app.status.set("Đã bỏ vùng và cập nhật TXT ghép nếu có. Có thể hoàn tác.")
        except Exception as error:
            messagebox.showerror("Chưa bỏ vùng", str(error))

    def toggle_reviewed(self):
        try:
            app = self.app
            current = app.workspace.summary(app.work.get().strip(), app.version.get())[app.kind()]
            complete = current["status"] != "complete"
            app.workspace.regions.mark_reviewed(app.work.get().strip(), app.kind(), app.version.get(), complete)
            app.status.set("Đã xác nhận kiểm tra đủ bản văn." if complete else "Đã bỏ xác nhận đủ.")
            self.refresh()
        except Exception as error:
            messagebox.showerror("Chưa xác nhận", str(error))

    def progress(self):
        app = self.app
        window = tk.Toplevel(app.root); window.title("Tiến độ theo bài và bản văn")
        area = ttk.Frame(window); area.pack(fill="both", expand=True)
        table = ttk.Treeview(area, columns=("work", *CAC_BAN), show="headings", height=17)
        scroll = ttk.Scrollbar(area, orient="vertical", command=table.yview)
        table.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        table.heading("work", text="Bài/đoạn"); table.column("work", width=120)
        for kind, (label, _) in CAC_BAN.items():
            table.heading(kind, text=label); table.column(kind, width=160)
        table.pack(side="left", fill="both", expand=True)
        manifest = app.workspace.manifest()
        works = {r["work"] for r in manifest["records"] + manifest.get("absent", [])}
        works.add(app.work.get().strip())
        if app.book.work_range:
            works.update(f"bai{number:04d}" for number in range(app.book.work_range[0], app.book.work_range[1] + 1))
        for work in sorted(works):
            summary = app.workspace.summary(work, app.version.get(), manifest=manifest)
            values = [f"{STATUS[v['status']]} ({v['regions']})" for v in summary.values()]
            table.insert("", "end", values=(work, *values))
        ttk.Label(window, text=f"Phiên bản v{app.version.get():02d}. Số trong ngoặc là số vùng, không phải số cặp hợp lệ.").pack(pady=6)
