"""Cửa sổ chọn chữ từ TXT; dùng chung bộ quản lý tác phẩm với PDF."""
import tkinter as tk
from tkinter import messagebox, ttk

from .text_ops import read_text


def open_text_window(parent, path, record=None):
    try:
        original = read_text(path)
    except (OSError, UnicodeError) as error:
        messagebox.showerror("Không đọc được TXT UTF-8", str(error)); return
    window = tk.Toplevel(parent.root)
    window.title(f"Chọn chữ — {path.name}")
    window.geometry("950x700")
    instruction = "Bôi đen đúng một bản văn. Mã tác phẩm / loại bản / phiên bản lấy từ cửa sổ chính."
    if record is not None:
        instruction = f"Chọn lại đoạn thay thế cho {record['work']} / {record['kind']} / phần {record['sequence']}. Có thể hoàn tác."
    ttk.Label(window, text=instruction, wraplength=900).pack(anchor="w", padx=8, pady=8)
    frame = ttk.Frame(window); frame.pack(fill="both", expand=True)
    text = tk.Text(frame, wrap="word", undo=False)
    scroll = ttk.Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    text.pack(side="left", fill="both", expand=True); scroll.pack(side="right", fill="y")
    text.insert("1.0", original)
    # Read-only while retaining selection/copy support.
    text.configure(state="disabled")

    def save():
        try:
            start, end = text.index("sel.first"), text.index("sel.last")
            offset_start = len(text.get("1.0", start))
            offset_end = len(text.get("1.0", end))
            if record is not None:
                from .region_actions import region_id
                result = parent.workspace.regions.replace_text(region_id(record), offset_start, offset_end, parent.note.get())
            else:
                result = parent.workspace.save_text_region(path, parent.work.get().strip(), parent.kind(),
                    parent.version.get(), char_start=offset_start, char_end=offset_end, note=parent.note.get())
            parent.refresh_regions(); parent.persist_state()
            messagebox.showinfo("Đã lưu TXT", f"{result['work']} / {result['kind']} / phần {result['sequence']:04d}")
        except tk.TclError:
            messagebox.showinfo("Chưa chọn chữ", "Bôi đen đoạn cần lấy trước khi lưu.")
        except Exception as error:
            messagebox.showerror("Chưa lưu", str(error))

    ttk.Button(window, text="Lưu đoạn đã chọn vào tác phẩm", command=save).pack(pady=8)
