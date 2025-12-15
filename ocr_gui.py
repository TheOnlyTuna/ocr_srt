import os
from pathlib import Path
from typing import List, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from capture_manager import CaptureManager
from ocr_pipeline import OCRProcessor

OUTPUT_DIR = Path("outputs")


class BoundingBoxManager:
    def __init__(self) -> None:
        self.boxes: List[Tuple[int, int, int, int]] = []

    def add_box(self, box: Tuple[int, int, int, int]) -> None:
        self.boxes.append(box)

    def remove(self, index: int) -> None:
        if 0 <= index < len(self.boxes):
            self.boxes.pop(index)

    def clear(self) -> None:
        self.boxes.clear()


class OCRApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("EasyOCR Capture Pro")
        self.root.geometry("1200x800")

        self.monitor_index = tk.IntVar(value=1)
        self.languages_var = tk.StringVar(value="en,vi")
        self.gpu_var = tk.BooleanVar(value=False)

        self.capture_manager = CaptureManager(monitor_index=self.monitor_index.get())
        self.image = None
        self.display_image = None
        self.photo = None
        self.canvas_rect = None
        self.start_x = 0
        self.start_y = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.box_manager = BoundingBoxManager()

        self._build_layout()

    def _build_layout(self) -> None:
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control_frame, text="Capture Settings", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        monitor_row = ttk.Frame(control_frame)
        monitor_row.pack(fill=tk.X, pady=5)
        ttk.Label(monitor_row, text="Monitor index:").pack(side=tk.LEFT)
        ttk.Entry(monitor_row, textvariable=self.monitor_index, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(monitor_row, text="Refresh monitors", command=self._refresh_monitors).pack(side=tk.LEFT)

        ttk.Button(control_frame, text="Capture screen", command=self.capture_screen).pack(fill=tk.X, pady=5)

        ttk.Label(control_frame, text="OCR", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(control_frame, text="Languages (comma-separated)").pack(anchor=tk.W)
        ttk.Entry(control_frame, textvariable=self.languages_var).pack(fill=tk.X, pady=2)
        ttk.Checkbutton(control_frame, text="Use GPU", variable=self.gpu_var).pack(anchor=tk.W, pady=2)

        ttk.Button(control_frame, text="Run OCR", command=self.run_ocr).pack(fill=tk.X, pady=8)

        ttk.Label(control_frame, text="Bounding boxes", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.box_list = tk.Listbox(control_frame, height=10)
        self.box_list.pack(fill=tk.X, pady=4)

        box_actions = ttk.Frame(control_frame)
        box_actions.pack(fill=tk.X)
        ttk.Button(box_actions, text="Remove selected", command=self.remove_selected_box).pack(side=tk.LEFT, expand=True, fill=tk.X)
        ttk.Button(box_actions, text="Clear", command=self.clear_boxes).pack(side=tk.LEFT, expand=True, fill=tk.X)

        ttk.Label(control_frame, text="Status", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(control_frame, textvariable=self.status_var, foreground="#0a9396").pack(anchor=tk.W)

        canvas_frame = ttk.Frame(self.root, padding=10)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(canvas_frame, bg="#1e1e1e")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def _refresh_monitors(self) -> None:
        monitors = self.capture_manager.list_monitors()
        if not monitors:
            messagebox.showwarning("No monitors", "Không tìm thấy màn hình khả dụng.")
            return
        monitor_info = " | ".join([f"{m.index}: {m.width}x{m.height}" for m in monitors])
        messagebox.showinfo("Monitors", f"Monitors detected: {monitor_info}")

    def capture_screen(self) -> None:
        try:
            self.capture_manager.monitor_index = self.monitor_index.get()
            self.image = self.capture_manager.grab_frame()
            self._display_image(self.image)
            self.status_var.set("Đã capture màn hình. Vẽ bounding box để đọc OCR.")
        except Exception as exc:
            messagebox.showerror("Capture failed", f"Không thể capture: {exc}")

    def _display_image(self, image: Image.Image) -> None:
        canvas_width = self.canvas.winfo_width() or 800
        canvas_height = self.canvas.winfo_height() or 600
        img_width, img_height = image.size
        scale = min(canvas_width / img_width, canvas_height / img_height)
        display_width = int(img_width * scale)
        display_height = int(img_height * scale)
        self.scale_x = img_width / display_width
        self.scale_y = img_height / display_height
        resized = image.resize((display_width, display_height))
        self.display_image = resized
        self.photo = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def on_mouse_down(self, event: tk.Event) -> None:
        if not self.display_image:
            return
        self.start_x, self.start_y = event.x, event.y
        self.canvas_rect = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="#ffb703", width=2)

    def on_mouse_drag(self, event: tk.Event) -> None:
        if self.canvas_rect:
            self.canvas.coords(self.canvas_rect, self.start_x, self.start_y, event.x, event.y)

    def on_mouse_up(self, event: tk.Event) -> None:
        if not self.canvas_rect:
            return
        end_x, end_y = event.x, event.y
        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)
        scaled_box = (
            int(x1 * self.scale_x),
            int(y1 * self.scale_y),
            int(x2 * self.scale_x),
            int(y2 * self.scale_y),
        )
        self.box_manager.add_box(scaled_box)
        self._update_box_list()
        self.canvas_rect = None

    def _update_box_list(self) -> None:
        self.box_list.delete(0, tk.END)
        for idx, box in enumerate(self.box_manager.boxes):
            self.box_list.insert(tk.END, f"{idx+1}: {box}")

    def remove_selected_box(self) -> None:
        selection = self.box_list.curselection()
        if not selection:
            return
        self.box_manager.remove(selection[0])
        self._update_box_list()

    def clear_boxes(self) -> None:
        self.box_manager.clear()
        self._update_box_list()

    def run_ocr(self) -> None:
        if not self.image:
            messagebox.showwarning("No capture", "Hãy capture màn hình trước.")
            return
        if not self.box_manager.boxes:
            messagebox.showwarning("No boxes", "Hãy vẽ ít nhất một bounding box.")
            return

        languages = [lang.strip() for lang in self.languages_var.get().split(",") if lang.strip()]
        if not languages:
            messagebox.showwarning("Languages", "Cần nhập ít nhất một ngôn ngữ (ví dụ: en,vi)")
            return

        self.status_var.set("Đang chạy EasyOCR...")
        self.root.update_idletasks()
        try:
            processor = OCRProcessor(languages=languages, gpu=self.gpu_var.get())
            result = processor.run(self.image, self.box_manager.boxes, monitor_index=self.monitor_index.get())
            path = processor.save_result(result, OUTPUT_DIR)
            self.status_var.set(f"Hoàn thành! Lưu JSON tại {path}")
            self._show_result_dialog(path, result.boxes)
        except Exception as exc:
            messagebox.showerror("OCR failed", f"Lỗi khi chạy EasyOCR: {exc}")
            self.status_var.set("OCR thất bại")

    def _show_result_dialog(self, path: Path, boxes: List[Tuple[int, int, int, int]]) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("OCR Result")
        dialog.geometry("500x400")

        ttk.Label(dialog, text=f"File JSON: {path}").pack(anchor=tk.W, pady=5, padx=5)
        box_frame = ttk.Frame(dialog)
        box_frame.pack(fill=tk.BOTH, expand=True)
        listbox = tk.Listbox(box_frame)
        listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        for box in boxes:
            listbox.insert(tk.END, str(box))

        ttk.Button(dialog, text="Đóng", command=dialog.destroy).pack(pady=5)


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
