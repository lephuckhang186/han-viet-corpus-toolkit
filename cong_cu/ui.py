"""Giao diện chọn vùng PDF bằng chuột; lưu theo tác phẩm, không theo trang."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from ten_file import CAC_BAN, DPI, MA_DE_TAI
from .models import Box
from .region_actions import region_id
from .region_panel import RegionPanel
from . import pdf_ops


class CropWindow:
    def __init__(self, root, workspace):
        self.root, self.workspace = root, workspace
        self.book = workspace.book
        self.selection = None
        self.selection_id = None
        self.drag_start = None
        self.image = self.tk_image = None
        self.editing_id = None
        session = workspace.read_session()
        source_keys = [s.key for s in self.book.sources]
        source_key = session.get("source") if session.get("source") in source_keys else source_keys[0]
        source = self.book.source(source_key)
        self.source_pages = session.get("pages", {})
        self.source_key = tk.StringVar(value=source_key)
        self.page = tk.IntVar(value=self.source_pages.get(source_key, source.ranges[0][0]))
        self.work = tk.StringVar(value=session.get("work", self.book.first_work))
        kind = session.get("kind", self.default_kind(source))
        self.kind_label = tk.StringVar(value=CAC_BAN.get(kind, CAC_BAN[self.default_kind(source)])[0])
        self.version = tk.IntVar(value=session.get("version", 1))
        self.preview_dpi = tk.IntVar(value=session.get("preview_dpi", 100))
        self.save_text = tk.BooleanVar(value=session.get("extract_text", False))
        self.allow_outside = tk.BooleanVar(value=False)
        self.note = tk.StringVar()
        self.status = tk.StringVar(value="Kéo chuột khoanh một vùng. Giữ cùng mã tác phẩm để thêm vùng ở trang khác.")
        root.title(f"TV2 — {self.book.title}")
        root.geometry("1280x900")
        top = ttk.Frame(root, padding=8); top.pack(fill="x")
        ttk.Label(top, text=self.book.note, wraplength=1160).pack(anchor="w")
        ttk.Label(top, text=f"Mã đề tài: {MA_DE_TAI} — sửa tại ten_file.py trước khi bàn giao.").pack(anchor="w")
        row = ttk.Frame(top); row.pack(fill="x", pady=5)
        ttk.Label(row, text="Nguồn:").pack(side="left")
        sources = ttk.Combobox(row, textvariable=self.source_key, values=[s.key for s in self.book.sources], width=9, state="readonly")
        sources.pack(side="left"); sources.bind("<<ComboboxSelected>>", self.change_source)
        self.source_combo = sources
        ttk.Button(row, text="←", command=lambda: self.navigate(-1)).pack(side="left", padx=4)
        ttk.Label(row, text="Trang PDF gốc:").pack(side="left")
        ttk.Spinbox(row, from_=1, to=9999, width=6, textvariable=self.page).pack(side="left")
        ttk.Button(row, text="Mở trang", command=self.load_page).pack(side="left", padx=4)
        ttk.Button(row, text="→", command=lambda: self.navigate(1)).pack(side="left")
        ttk.Label(row, text="  Xem ở DPI:").pack(side="left")
        zoom = ttk.Combobox(row, textvariable=self.preview_dpi, values=[75, 100, 150, 200], width=5, state="readonly")
        zoom.pack(side="left"); zoom.bind("<<ComboboxSelected>>", lambda _: self.load_page())
        ttk.Button(row, text="Mở TXT để chọn chữ", command=self.open_text).pack(side="right")
        row = ttk.Frame(top); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Mã tác phẩm:").pack(side="left")
        self.work_entry = ttk.Entry(row, textvariable=self.work, width=22)
        self.work_entry.pack(side="left", padx=4)
        self.kind_combo = ttk.Combobox(row, textvariable=self.kind_label, values=[v[0] for v in CAC_BAN.values()], width=16, state="readonly")
        self.kind_combo.pack(side="left")
        self.kind_combo.bind("<<ComboboxSelected>>", self.context_changed)
        self.work_entry.bind("<FocusOut>", self.context_changed)
        ttk.Label(row, text="  Phiên bản:").pack(side="left")
        self.version_spin = ttk.Spinbox(row, textvariable=self.version, from_=1, to=9999, width=5, command=self.context_changed)
        self.version_spin.pack(side="left")
        self.version_spin.bind("<FocusOut>", self.context_changed)
        ttk.Button(row, text="Xem đủ/thiếu bản văn", command=self.show_summary).pack(side="left", padx=6)
        ttk.Button(row, text="Ghi nhận không có bản này", command=self.mark_absent).pack(side="left")
        row = ttk.Frame(top); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Ghi chú / lý do:").pack(side="left")
        ttk.Entry(row, textvariable=self.note).pack(side="left", fill="x", expand=True, padx=5)
        self.text_checkbox = ttk.Checkbutton(top, text="Lấy thêm lớp chữ PDF của vùng này (tùy chọn bước 4; scan sẽ báo không có chữ)", variable=self.save_text)
        self.text_checkbox.pack(anchor="w")
        ttk.Checkbutton(top, text="Cho phép ngữ cảnh/mẫu ngoài phạm vi TV2", variable=self.allow_outside).pack(anchor="w")
        body = ttk.Panedwindow(root, orient="horizontal"); body.pack(fill="both", expand=True, padx=8)
        area = ttk.Frame(body); body.add(area, weight=3)
        self.canvas = tk.Canvas(area, background="#555555", highlightthickness=0)
        vertical = ttk.Scrollbar(area, orient="vertical", command=self.canvas.yview)
        horizontal = ttk.Scrollbar(area, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.canvas.grid(row=0, column=0, sticky="nsew"); vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        area.rowconfigure(0, weight=1); area.columnconfigure(0, weight=1)
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.end_drag)
        self.canvas.bind("<MouseWheel>", lambda event: self.canvas.yview_scroll(-int(event.delta / 120), "units"))
        self.panel = RegionPanel(body, self); body.add(self.panel.frame, weight=1)
        bottom = ttk.Frame(root, padding=8); bottom.pack(fill="x")
        self.save_button = ttk.Button(bottom, text="Lưu vùng vào tác phẩm (PNG)", command=self.save_region)
        self.save_button.pack(side="left")
        ttk.Button(bottom, text="Bỏ khung chọn", command=self.clear_selection).pack(side="left", padx=5)
        ttk.Button(bottom, text="Hủy chỉnh vùng", command=self.cancel_edit).pack(side="left", padx=3)
        ttk.Label(bottom, textvariable=self.status, wraplength=760).pack(side="left", padx=5)
        root.bind("<Control-s>", lambda _: self.save_region())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.load_page()

    @staticmethod
    def default_kind(source):
        return "dich_nghia" if source.archive_side == "viet" else "han"

    def persist_state(self):
        if not hasattr(self, "loaded_page"):
            return
        self.source_pages[self.loaded_source] = self.loaded_page
        self.workspace.save_session({"source": self.loaded_source, "pages": self.source_pages,
            "work": self.work.get().strip(), "kind": self.kind(), "version": self.version.get(),
            "preview_dpi": self.preview_dpi.get(), "extract_text": self.save_text.get()})

    def context_changed(self, _event=None):
        try:
            self.refresh_regions(); self.persist_state()
        except (tk.TclError, ValueError):
            pass  # Chưa lưu nội dung đang gõ dở, ví dụ ô phiên bản còn trống.

    def close(self):
        try:
            self.persist_state()
        except (tk.TclError, ValueError):
            pass
        self.root.destroy()

    def kind(self):
        return next(key for key, (label, _) in CAC_BAN.items() if label == self.kind_label.get())

    def change_source(self, _event=None):
        self.cancel_edit()
        source = self.book.source(self.source_key.get())
        self.page.set(self.source_pages.get(source.key, source.ranges[0][0]))
        self.kind_label.set(CAC_BAN[self.default_kind(source)][0])
        self.load_page()

    def navigate(self, step):
        try:
            self.page.set(max(1, self.page.get() + step)); self.load_page()
        except tk.TclError:
            messagebox.showerror("Trang", "Nhập số trang hợp lệ.")

    def load_page(self):
        try:
            image = pdf_ops.render_page(self.book.source(self.source_key.get()).path, self.page.get(), self.preview_dpi.get())
            self.image = image
            self.tk_image = ImageTk.PhotoImage(image)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            self.canvas.configure(scrollregion=(0, 0, image.width, image.height))
            self.canvas.xview_moveto(0); self.canvas.yview_moveto(0)
            self.selection = self.selection_id = None
            self.loaded_page = self.page.get()
            self.loaded_source = self.source_key.get()
            self.refresh_regions(); self.persist_state()
            count = self.workspace.summary(self.work.get(), self.version.get())[self.kind()]["regions"]
            self.status.set(f"Trang {self.loaded_page}; bản này đã có {count} vùng. Chọn vùng ở danh sách để xem hoặc sửa.")
        except Exception as error:
            messagebox.showerror("Không mở được trang", str(error))

    def point(self, event):
        return (max(0, min(self.image.width, self.canvas.canvasx(event.x))),
                max(0, min(self.image.height, self.canvas.canvasy(event.y))))

    def clear_selection(self):
        self.selection = None
        if self.selection_id:
            self.canvas.delete(self.selection_id)
        self.selection_id = None

    def refresh_regions(self):
        self.panel.refresh()
        self.canvas.delete("saved")
        if self.image is None or not hasattr(self, "loaded_page"):
            return
        for record in self.workspace.regions.list(source=self.loaded_source, page=self.loaded_page):
            if "box" not in record:
                continue
            x0, y0, x1, y1 = record["box"]
            color = "#66e58d" if record["work"] == self.work.get().strip() else "#d4d4d4"
            self.canvas.create_rectangle(x0*self.image.width, y0*self.image.height, x1*self.image.width,
                y1*self.image.height, outline=color, width=2, dash=(5, 3), tags="saved")
            self.canvas.create_text(x0*self.image.width+3, y0*self.image.height+3, anchor="nw", fill=color,
                text=f"{record['work']} · {CAC_BAN[record['kind']][0]} · {record['sequence']}", tags="saved")

    def cancel_edit(self):
        self.editing_id = None
        self.work_entry.configure(state="normal"); self.version_spin.configure(state="normal")
        self.kind_combo.configure(state="readonly"); self.source_combo.configure(state="readonly")
        self.text_checkbox.configure(state="normal")
        self.save_button.configure(text="Lưu vùng vào tác phẩm (PNG)")

    def edit_region(self, record):
        self.cancel_edit()
        self.source_key.set(record["source_key"]); self.page.set(record["page"])
        self.work.set(record["work"]); self.kind_label.set(CAC_BAN[record["kind"]][0])
        self.version.set(record["version"]); self.save_text.set(record["mode"] == "pdf_text")
        self.note.set(record.get("note", "")); self.load_page()
        self.editing_id = region_id(record)
        self.selection = Box(*record["box"])
        x0, y0, x1, y1 = record["box"]
        self.selection_id = self.canvas.create_rectangle(x0*self.image.width, y0*self.image.height,
            x1*self.image.width, y1*self.image.height, outline="#ff4c38", width=2)
        self.work_entry.configure(state="disabled"); self.version_spin.configure(state="disabled")
        self.kind_combo.configure(state="disabled"); self.source_combo.configure(state="disabled")
        self.text_checkbox.configure(state="disabled")
        self.save_button.configure(text="Lưu thay khung vùng đã chọn")
        self.status.set("Đang chỉnh vùng: khoanh lại khung rồi bấm Lưu thay. Dùng Hoàn tác để lấy lại bản trước.")

    def undo_last(self):
        try:
            action = self.workspace.undo_last()
            self.cancel_edit(); self.clear_selection(); self.refresh_regions()
            self.status.set(f"Đã hoàn tác: {action}.")
        except Exception as error:
            messagebox.showerror("Chưa hoàn tác", str(error))

    def start_drag(self, event):
        if self.image is None:
            return
        self.clear_selection(); self.drag_start = self.point(event)
        self.selection_id = self.canvas.create_rectangle(*self.drag_start, *self.drag_start, outline="#ff4c38", width=2)

    def drag(self, event):
        if self.drag_start and self.selection_id:
            self.canvas.coords(self.selection_id, *self.drag_start, *self.point(event))

    def end_drag(self, event):
        if not self.drag_start:
            return
        x0, y0 = self.drag_start; x1, y1 = self.point(event)
        self.drag_start = None
        if abs(x1 - x0) < 4 or abs(y1 - y0) < 4:
            self.clear_selection(); return
        self.selection = Box(min(x0, x1) / self.image.width, min(y0, y1) / self.image.height,
                             max(x0, x1) / self.image.width, max(y0, y1) / self.image.height)
        self.status.set("Đã chọn vùng. Kiểm tra mã tác phẩm và Hán/dịch âm/dịch nghĩa/dịch thơ trước khi lưu.")

    def save_region(self):
        if self.selection is None:
            messagebox.showinfo("Chưa chọn vùng", "Kéo chuột để khoanh vùng trên trang PDF."); return
        try:
            if self.page.get() != self.loaded_page or self.source_key.get() != self.loaded_source:
                messagebox.showerror("Trang chưa mở", "Bấm Mở trang sau khi thay số trang, rồi chọn vùng lại."); return
            source = self.book.source(self.loaded_source)
            mismatch = (source.archive_side == "viet" and self.kind() == "han") or (source.archive_side == "han" and self.kind() != "han")
            if mismatch and not messagebox.askyesno("Kiểm tra loại bản văn", "Loại bản đang chọn khác ngôn ngữ của nguồn. Bạn đã kiểm tra và vẫn muốn lưu như vậy?"):
                return
            overlaps = self.workspace.regions.overlaps(self.loaded_source, self.loaded_page, self.work.get().strip(),
                self.kind(), self.version.get(), self.selection, excluding=self.editing_id)
            if overlaps and not messagebox.askyesno("Vùng gần trùng", f"Vùng này gần trùng {len(overlaps)} vùng đã lưu. Vẫn tiếp tục?"):
                return
            if self.editing_id:
                result = self.workspace.regions.replace_pdf(self.editing_id, self.loaded_page, self.selection,
                    self.note.get(), self.allow_outside.get())
                self.cancel_edit()
            else:
                result = self.workspace.save_pdf_region(self.loaded_source, self.loaded_page, self.selection,
                    self.work.get().strip(), self.kind(), self.version.get(), DPI,
                    self.save_text.get(), self.note.get(), self.allow_outside.get())
            self.refresh_regions(); self.persist_state()
            prefix = "Vùng đã có, bỏ qua" if result.get("skipped") else f"Đã lưu phần {result['sequence']:04d}"
            self.status.set(f"{prefix} → {result['work']} / {CAC_BAN[result['kind']][0]}. Có thể qua trang để thêm cùng bài.")
        except Exception as error:
            messagebox.showerror("Chưa lưu", str(error))

    def show_summary(self):
        try:
            self.panel.progress()
        except Exception as error:
            messagebox.showerror("Thông tin", str(error))

    def mark_absent(self):
        try:
            self.workspace.mark_absent(self.work.get().strip(), self.kind(), self.version.get(), self.note.get())
            self.status.set("Đã ghi nhận không có bản văn theo ghi chú của bạn; không tạo file trống.")
        except Exception as error:
            messagebox.showerror("Chưa ghi nhận", str(error))

    def open_text(self):
        path = filedialog.askopenfilename(title="Chọn TXT UTF-8 có sẵn", filetypes=[("Văn bản UTF-8", "*.txt")])
        if not path:
            return
        from .text_ui import open_text_window
        open_text_window(self, Path(path))


def open_window(workspace):
    print("Đang tạo bố cục và kiểm tra bản sao nguồn...")
    workspace.prepare()
    root = tk.Tk()
    CropWindow(root, workspace)
    root.mainloop()
