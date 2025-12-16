import os
from pathlib import Path
from typing import List, Tuple

import tkinter as tk
from tkinter import messagebox, ttk

from PIL import Image, ImageTk

from capture_manager import (
    CaptureManager,
    DeckLinkCapture,
    SRTStreamCapture,
    list_decklink_devices,
)
from ocr_pipeline import OCRProcessor

OUTPUT_DIR = Path("outputs")
KEEP_HISTORY = False  # tránh ghi quá nhiều file; bật True nếu muốn lưu lịch sử


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

        self.source_var = tk.StringVar(value="monitor")
        self.monitor_index = tk.IntVar(value=1)
        self.languages_var = tk.StringVar(value="en,vi")
        self.gpu_var = tk.BooleanVar(value=False)
        self.interval_ms_var = tk.IntVar(value=1500)
        self.preview_interval_ms = tk.IntVar(value=1000)
        self.srt_url_var = tk.StringVar(value="srt://127.0.0.1:9000")
        self.decklink_device_var = tk.StringVar(value="DeckLink Duo (1)")
        self.decklink_fps_var = tk.StringVar(value="60")
        self.decklink_size_var = tk.StringVar(value="1920x1080")
        self.auto_running = False
        self.auto_cycles = tk.IntVar(value=0)
        self.preview_running = False
        self.decklink_devices: List[str] = []

        self.capture_manager = CaptureManager(monitor_index=self.monitor_index.get())
        self.srt_capture: SRTStreamCapture | None = None
        self.decklink_capture = None
        self.image = None
        self.display_image = None
        self.photo = None
        self.canvas_rect = None
        self._canvas_overlays: List[int] = []
        self.start_x = 0
        self.start_y = 0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.box_manager = BoundingBoxManager()
        self.processor = None
        self.processor_config: Tuple[Tuple[str, ...], bool] = (tuple(), False)

        self._build_layout()
        self._refresh_decklink_devices(initial=True)
        self._start_live_preview()

    def _build_layout(self) -> None:
        control_frame = ttk.Frame(self.root, padding=10)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)

        ttk.Label(control_frame, text="Capture Settings", font=("Arial", 12, "bold")).pack(anchor=tk.W)
        source_row = ttk.Frame(control_frame)
        source_row.pack(fill=tk.X, pady=2)
        ttk.Radiobutton(source_row, text="Monitor", variable=self.source_var, value="monitor").pack(side=tk.LEFT)
        ttk.Radiobutton(source_row, text="SRT", variable=self.source_var, value="srt").pack(side=tk.LEFT, padx=4)
        ttk.Radiobutton(source_row, text="DeckLink", variable=self.source_var, value="decklink").pack(side=tk.LEFT, padx=4)

        monitor_row = ttk.Frame(control_frame)
        monitor_row.pack(fill=tk.X, pady=5)
        ttk.Label(monitor_row, text="Monitor index:").pack(side=tk.LEFT)
        ttk.Entry(monitor_row, textvariable=self.monitor_index, width=5).pack(side=tk.LEFT, padx=5)
        ttk.Button(monitor_row, text="Refresh monitors", command=self._refresh_monitors).pack(side=tk.LEFT)

        srt_row = ttk.Frame(control_frame)
        srt_row.pack(fill=tk.X, pady=2)
        ttk.Label(srt_row, text="SRT URL:").pack(side=tk.LEFT)
        ttk.Entry(srt_row, textvariable=self.srt_url_var, width=26).pack(side=tk.LEFT, padx=4)
        ttk.Button(control_frame, text="Kết nối SRT", command=self.connect_srt).pack(fill=tk.X, pady=4)

        decklink_row = ttk.Frame(control_frame)
        decklink_row.pack(fill=tk.X, pady=2)
        ttk.Label(decklink_row, text="DeckLink device:").pack(side=tk.LEFT)
        self.decklink_combo = ttk.Combobox(
            decklink_row, textvariable=self.decklink_device_var, width=22, state="readonly"
        )
        self.decklink_combo.pack(side=tk.LEFT, padx=4)
        ttk.Button(decklink_row, text="Refresh", command=self._refresh_decklink_devices).pack(side=tk.LEFT, padx=2)

        decklink_opts = ttk.Frame(control_frame)
        decklink_opts.pack(fill=tk.X, pady=2)
        ttk.Label(decklink_opts, text="Size (WxH):").pack(side=tk.LEFT)
        ttk.Entry(decklink_opts, textvariable=self.decklink_size_var, width=9).pack(side=tk.LEFT, padx=2)
        ttk.Label(decklink_opts, text="FPS:").pack(side=tk.LEFT)
        ttk.Entry(decklink_opts, textvariable=self.decklink_fps_var, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="Kết nối DeckLink", command=self.connect_decklink).pack(fill=tk.X, pady=4)

        ttk.Button(control_frame, text="Capture screen", command=self.capture_screen).pack(fill=tk.X, pady=5)

        ttk.Label(control_frame, text="OCR", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
        ttk.Label(control_frame, text="Languages (comma-separated)").pack(anchor=tk.W)
        ttk.Entry(control_frame, textvariable=self.languages_var).pack(fill=tk.X, pady=2)
        ttk.Checkbutton(control_frame, text="Use GPU", variable=self.gpu_var).pack(anchor=tk.W, pady=2)

        ttk.Button(control_frame, text="Run OCR", command=self.run_ocr).pack(fill=tk.X, pady=8)

        ttk.Label(control_frame, text="Auto OCR", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
        interval_row = ttk.Frame(control_frame)
        interval_row.pack(fill=tk.X, pady=2)
        ttk.Label(interval_row, text="Interval (ms):").pack(side=tk.LEFT)
        ttk.Entry(interval_row, textvariable=self.interval_ms_var, width=8).pack(side=tk.LEFT, padx=5)
        self.auto_button = ttk.Button(control_frame, text="Bật OCR liên tục", command=self.toggle_auto_ocr)
        self.auto_button.pack(fill=tk.X, pady=4)
        ttk.Label(control_frame, text="Chu kỳ đã chạy:").pack(anchor=tk.W)
        ttk.Label(control_frame, textvariable=self.auto_cycles, foreground="#9b2226").pack(anchor=tk.W)

        ttk.Label(control_frame, text="Auto preview", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 0))
        preview_row = ttk.Frame(control_frame)
        preview_row.pack(fill=tk.X, pady=2)
        ttk.Label(preview_row, text="Interval (ms):").pack(side=tk.LEFT)
        ttk.Entry(preview_row, textvariable=self.preview_interval_ms, width=8).pack(side=tk.LEFT, padx=5)
        self.preview_button = ttk.Button(control_frame, text="Dừng cập nhật màn hình", command=self.toggle_preview)
        self.preview_button.pack(fill=tk.X, pady=4)

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

    def _refresh_decklink_devices(self, initial: bool = False) -> None:
        devices = list_decklink_devices()
        self.decklink_devices = devices
        if not devices:
            self.status_var.set("Không tìm thấy DeckLink (dùng tên thủ công nếu cần)")
            return

        if hasattr(self, "decklink_combo"):
            self.decklink_combo["values"] = devices
            if not self.decklink_device_var.get() or self.decklink_device_var.get() not in devices:
                self.decklink_device_var.set(devices[0])

        if not initial:
            self.status_var.set(f"Đã tải {len(devices)} DeckLink input giống OBS")

    def capture_screen(self) -> None:
        try:
            self.image = self._grab_current_frame()
            self._display_image(self.image)
            self.status_var.set("Đã capture màn hình. Vẽ bounding box để đọc OCR.")
        except Exception as exc:
            messagebox.showerror("Capture failed", f"Không thể capture: {exc}")

    def _start_live_preview(self) -> None:
        if self.preview_running:
            return
        self.preview_running = True
        if hasattr(self, "preview_button"):
            self.preview_button.config(text="Dừng cập nhật màn hình")
        self.status_var.set("Đang cập nhật màn hình tự động")
        self._preview_job = self.root.after(200, self._run_live_preview)

    def toggle_preview(self) -> None:
        if self.preview_running:
            self.preview_running = False
            if hasattr(self, "_preview_job"):
                self.root.after_cancel(self._preview_job)
            self.status_var.set("Đã dừng cập nhật màn hình tự động")
            if hasattr(self, "preview_button"):
                self.preview_button.config(text="Bật cập nhật màn hình")
            return

        try:
            interval = max(300, int(self.preview_interval_ms.get()))
        except (TypeError, ValueError):
            messagebox.showwarning("Interval", "Khoảng thời gian preview phải là số nguyên (ms).")
            return

        self.preview_interval_ms.set(interval)
        self.preview_running = True
        self.status_var.set("Đang cập nhật màn hình tự động")
        if hasattr(self, "preview_button"):
            self.preview_button.config(text="Dừng cập nhật màn hình")
        self._preview_job = self.root.after(50, self._run_live_preview)

    def _ensure_preview_running(self) -> None:
        if not self.preview_running:
            self._start_live_preview()

    def _run_live_preview(self) -> None:
        if not self.preview_running:
            return
        try:
            live_image = self._grab_current_frame()
            self.image = live_image
            self._display_image(live_image)
            self.status_var.set("Đang xem preview màn hình trực tiếp")
        except Exception as exc:
            self.status_var.set(f"Preview lỗi: {exc}")
        finally:
            if self.preview_running:
                self._preview_job = self.root.after(self.preview_interval_ms.get(), self._run_live_preview)

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
        self._draw_boxes()

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
        self._draw_boxes()

    def _update_box_list(self) -> None:
        self.box_list.delete(0, tk.END)
        for idx, box in enumerate(self.box_manager.boxes):
            self.box_list.insert(tk.END, f"{idx+1}: {box}")

    def _draw_boxes(self) -> None:
        if not self.display_image:
            return

        for overlay in self._canvas_overlays:
            self.canvas.delete(overlay)
        self._canvas_overlays.clear()

        for idx, box in enumerate(self.box_manager.boxes, start=1):
            x1 = int(box[0] / self.scale_x)
            y1 = int(box[1] / self.scale_y)
            x2 = int(box[2] / self.scale_x)
            y2 = int(box[3] / self.scale_y)
            rect = self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00d1b2", width=2)
            label = self.canvas.create_text(x1 + 4, y1 + 4, anchor=tk.NW, text=str(idx), fill="#f4f4f4", font=("Arial", 10, "bold"))
            self._canvas_overlays.extend([rect, label])

    def remove_selected_box(self) -> None:
        selection = self.box_list.curselection()
        if not selection:
            return
        self.box_manager.remove(selection[0])
        self._update_box_list()
        self._draw_boxes()

    def clear_boxes(self) -> None:
        self.box_manager.clear()
        self._update_box_list()
        self._draw_boxes()

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
            result, latest_path = self._process_ocr(self.image, languages, show_dialog=True)
            self.status_var.set(f"Hoàn thành! Lưu JSON tại {latest_path}")
        except Exception as exc:
            messagebox.showerror("OCR failed", f"Lỗi khi chạy EasyOCR: {exc}")
            self.status_var.set("OCR thất bại")

    def _process_ocr(self, image: Image.Image, languages: List[str], show_dialog: bool = False):
        processor = self._get_processor(languages)
        result = processor.run(image, self.box_manager.boxes, monitor_index=self.monitor_index.get())
        latest_path = processor.save_result(result, OUTPUT_DIR, keep_history=KEEP_HISTORY)
        if show_dialog:
            self._show_result_dialog(latest_path, result.boxes)
        return result, latest_path

    def _get_processor(self, languages: List[str]) -> OCRProcessor:
        config = (tuple(languages), self.gpu_var.get())
        if not self.processor or self.processor_config != config:
            self.processor = OCRProcessor(languages=languages, gpu=self.gpu_var.get())
            self.processor_config = config
        return self.processor

    def toggle_auto_ocr(self) -> None:
        if not self.image:
            try:
                self.capture_manager.monitor_index = self.monitor_index.get()
                self.image = self.capture_manager.grab_frame()
                self._display_image(self.image)
            except Exception:
                messagebox.showwarning("No capture", "Hãy capture màn hình để vẽ bounding box trước.")
                return
        if not self.box_manager.boxes:
            messagebox.showwarning("No boxes", "Cần ít nhất một bounding box để bật OCR liên tục.")
            return

        try:
            interval = max(500, int(self.interval_ms_var.get()))
        except (TypeError, ValueError):
            messagebox.showwarning("Interval", "Khoảng thời gian phải là số nguyên (ms).")
            return

        if self.auto_running:
            self.auto_running = False
            self.status_var.set("Đã dừng OCR liên tục")
            job = getattr(self, "_auto_job", None)
            if job:
                self.root.after_cancel(job)
            self.auto_cycles.set(0)
            self.auto_button.config(text="Bật OCR liên tục")
            return

        self.interval_ms_var.set(interval)
        self.auto_running = True
        self.status_var.set("Đang chạy OCR liên tục...")
        self.auto_cycles.set(0)
        self.auto_button.config(text="Dừng OCR liên tục")
        self._auto_job = self.root.after(interval, self._run_auto_ocr)

    def _run_auto_ocr(self) -> None:
        if not self.auto_running:
            return

        try:
            live_image = self._grab_current_frame()
            self.image = live_image
            self._display_image(live_image)
            languages = [lang.strip() for lang in self.languages_var.get().split(",") if lang.strip()]
            if not languages:
                raise ValueError("Languages rỗng; hãy nhập ví dụ en,vi")

            self.status_var.set("OCR liên tục: đang đọc...")
            result, latest_path = self._process_ocr(live_image, languages, show_dialog=False)
            self.auto_cycles.set(self.auto_cycles.get() + 1)
            self.status_var.set(
                f"OCR liên tục #{self.auto_cycles.get()} | JSON: {latest_path.name} (ghi đè)"
            )
        except Exception as exc:
            self.status_var.set(f"OCR liên tục lỗi: {exc}")
        finally:
            if self.auto_running:
                self._auto_job = self.root.after(self.interval_ms_var.get(), self._run_auto_ocr)

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

    def _grab_current_frame(self) -> Image.Image:
        if self.source_var.get() == "srt":
            if not self.srt_capture or not self.srt_capture.running:
                raise RuntimeError("Chưa kết nối SRT hoặc stream chưa sẵn sàng.")
            frame = self.srt_capture.get_latest_frame()
            if frame is None:
                raise RuntimeError("Chưa nhận frame từ SRT. Hãy đợi vài giây hoặc kiểm tra URL.")
            return frame

        if self.source_var.get() == "decklink":
            if not self.decklink_capture or not self.decklink_capture.running:
                raise RuntimeError("Chưa kết nối DeckLink hoặc stream chưa sẵn sàng.")
            frame = self.decklink_capture.get_latest_frame()
            if frame is None:
                raise RuntimeError("Chưa nhận frame từ DeckLink. Kiểm tra thiết bị/độ phân giải.")
            return frame

        self.capture_manager.monitor_index = self.monitor_index.get()
        return self.capture_manager.grab_frame()

    def connect_srt(self) -> None:
        url = self.srt_url_var.get().strip()
        if not url:
            messagebox.showwarning("SRT", "Hãy nhập URL SRT (ví dụ srt://127.0.0.1:9000)")
            return

        if self.srt_capture:
            self.srt_capture.stop()
        self.srt_capture = SRTStreamCapture(url)
        self.srt_capture.start()
        self.source_var.set("srt")
        self.status_var.set("Đang kết nối tới SRT... chờ khung hình đầu tiên")

    def connect_decklink(self) -> None:
        device = self.decklink_device_var.get().strip()
        fps = self.decklink_fps_var.get().strip() or "60"
        size = self.decklink_size_var.get().strip() or "1920x1080"

        if not device:
            messagebox.showwarning("DeckLink", "Hãy nhập tên thiết bị DeckLink (ví dụ DeckLink Duo (1))")
            return

        if self.decklink_capture:
            self.decklink_capture.stop()
        self.decklink_capture = DeckLinkCapture(device=device, video_size=size, fps=fps)
        self.decklink_capture.start()
        self.source_var.set("decklink")
        self._ensure_preview_running()
        self.status_var.set("Đang kết nối DeckLink... chờ khung hình đầu tiên")
        self._await_decklink_frame()

    def _await_decklink_frame(self, retries: int = 30, delay_ms: int = 200) -> None:
        if not self.decklink_capture:
            return

        frame = self.decklink_capture.get_latest_frame()
        if frame is not None:
            self.image = frame
            self._display_image(frame)
            self.status_var.set("DeckLink đã lên hình. Vẽ bounding rồi chạy OCR.")
            return

        if retries <= 0:
            self.status_var.set("DeckLink chưa có hình. Kiểm tra cáp / định dạng input.")
            return

        self.root.after(delay_ms, lambda: self._await_decklink_frame(retries=retries - 1, delay_ms=delay_ms))


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    root = tk.Tk()
    app = OCRApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
