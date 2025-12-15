import datetime
from dataclasses import dataclass
from typing import List, Optional, Tuple

import mss
from PIL import Image


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
