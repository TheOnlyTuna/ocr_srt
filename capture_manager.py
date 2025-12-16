import datetime
from dataclasses import dataclass
import threading
from typing import List, Optional, Tuple

import importlib.util

REQUIRED_MODULES = {
    "mss": "pip install -r requirements.txt",
    "av": "pip install -r requirements.txt",
}

_missing = [name for name in REQUIRED_MODULES if importlib.util.find_spec(name) is None]
if _missing:
    missing_list = ", ".join(_missing)
    instructions = REQUIRED_MODULES[_missing[0]]
    raise ImportError(
        f"Thiếu thư viện: {missing_list}. Hãy cài đặt bằng `{instructions}` trước khi chạy GUI."
    )

import mss
from PIL import Image
import av


@dataclass
class MonitorInfo:
    index: int
    width: int
    height: int


class CaptureManager:
    """Manage screen captures using mss."""

    def __init__(self, monitor_index: int = 1) -> None:
        self.monitor_index = monitor_index

    def list_monitors(self) -> List[MonitorInfo]:
        """Return available monitors with their sizes."""
        with mss.mss() as sct:
            monitors = []
            for idx, mon in enumerate(sct.monitors[1:], start=1):
                monitors.append(MonitorInfo(index=idx, width=mon["width"], height=mon["height"]))
            return monitors

    def grab_frame(self, bbox: Optional[Tuple[int, int, int, int]] = None) -> Image.Image:
        """Capture a frame from the selected monitor or a specific bounding box.

        bbox format: (x1, y1, x2, y2)
        """
        with mss.mss() as sct:
            monitor = sct.monitors[self.monitor_index]
            if bbox:
                left, top, right, bottom = bbox
                region = {
                    "top": top,
                    "left": left,
                    "width": right - left,
                    "height": bottom - top,
                }
            else:
                region = monitor
            raw = sct.grab(region)
            img = Image.frombytes("RGB", raw.size, raw.rgb)
            return img

    def grab_and_save(self, path: str, bbox: Optional[Tuple[int, int, int, int]] = None) -> str:
        """Capture a frame and save it to disk."""
        image = self.grab_frame(bbox=bbox)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{path}/capture_{timestamp}.png"
        image.save(output_path)
        return output_path


class SRTStreamCapture:
    """Receive frames from an SRT video source using PyAV to minimize drop frames."""

    def __init__(self, url: str, options: Optional[dict] = None) -> None:
        self.url = url
        self.options = options or {"timeout": "5000000", "max_delay": "200", "reorder_queue_size": "30"}
        self.container: Optional[av.container.input.InputContainer] = None
        self.stream: Optional[av.video.stream.VideoStream] = None
        self.latest_frame: Optional[Image.Image] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.error: Optional[str] = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.container:
            try:
                self.container.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _run(self) -> None:
        try:
            self.container = av.open(self.url, options=self.options)
            video_streams = [s for s in self.container.streams if s.type == "video"]
            if not video_streams:
                raise RuntimeError("Không tìm thấy video stream trong SRT")
            self.stream = video_streams[0]
            self.stream.thread_type = "AUTO"
            for packet in self.container.demux(self.stream):
                if not self.running:
                    break
                for frame in packet.decode():
                    if not self.running:
                        break
                    img = frame.to_ndarray(format="rgb24")
                    self.latest_frame = Image.fromarray(img)
        except Exception as exc:
            self.error = str(exc)
        finally:
            if self.container:
                try:
                    self.container.close()
                except Exception:
                    pass
            self.running = False

    def get_latest_frame(self) -> Optional[Image.Image]:
        return self.latest_frame


class DeckLinkCapture:
    """Capture frames from a Blackmagic DeckLink device via PyAV."""

    def __init__(self, device: str, video_size: str = "1920x1080", fps: str = "60") -> None:
        self.device = device
        self.video_size = video_size
        self.fps = fps
        self.container: Optional[av.container.input.InputContainer] = None
        self.stream: Optional[av.video.stream.VideoStream] = None
        self.latest_frame: Optional[Image.Image] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.error: Optional[str] = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.running = False
        if self.container:
            try:
                self.container.close()
            except Exception:
                pass
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)

    def _run(self) -> None:
        try:
            self.container = av.open(
                f"decklink:{self.device}",
                format="decklink",
                options={"video_size": self.video_size, "framerate": self.fps},
            )
            video_streams = [s for s in self.container.streams if s.type == "video"]
            if not video_streams:
                raise RuntimeError("Không tìm thấy video stream từ DeckLink")
            self.stream = video_streams[0]
            self.stream.thread_type = "AUTO"
            for packet in self.container.demux(self.stream):
                if not self.running:
                    break
                for frame in packet.decode():
                    if not self.running:
                        break
                    img = frame.to_ndarray(format="rgb24")
                    self.latest_frame = Image.fromarray(img)
        except Exception as exc:
            self.error = str(exc)
        finally:
            if self.container:
                try:
                    self.container.close()
                except Exception:
                    pass
            self.running = False

    def get_latest_frame(self) -> Optional[Image.Image]:
        return self.latest_frame
