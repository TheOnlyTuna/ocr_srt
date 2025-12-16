import datetime
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

import easyocr


@dataclass
class OCRBoxResult:
    bbox: Tuple[int, int, int, int]
    text: str
    confidence: float


@dataclass
class OCRSessionResult:
    capture_time: str
    monitor_index: int
    image_size: Tuple[int, int]
    boxes: List[OCRBoxResult]

    def to_json(self) -> str:
        return json.dumps({
            "capture_time": self.capture_time,
            "monitor_index": self.monitor_index,
            "image_size": self.image_size,
            "boxes": [asdict(box) for box in self.boxes],
        }, ensure_ascii=False, indent=2)


class OCRProcessor:
    """Wrap EasyOCR with helper utilities."""

    def __init__(self, languages: List[str], gpu: bool = False) -> None:
        self.languages = languages
        self.gpu = gpu
        self.reader = easyocr.Reader(languages, gpu=gpu)

    def _crop_region(self, image: Image.Image, bbox: Tuple[int, int, int, int]) -> np.ndarray:
        left, top, right, bottom = bbox
        cropped = image.crop((left, top, right, bottom))
        return np.array(cropped)

    def run(self, image: Image.Image, bboxes: List[Tuple[int, int, int, int]], monitor_index: int) -> OCRSessionResult:
        results: List[OCRBoxResult] = []
        for bbox in bboxes:
            cropped_arr = self._crop_region(image, bbox)
            ocr_result = self.reader.readtext(cropped_arr, detail=1)
            text_parts = []
            confidences = []
            for item in ocr_result:
                # EasyOCR returns (bbox, text, confidence)
                if len(item) >= 3:
                    _, text, conf = item
                else:
                    text, conf = item[1], item[2] if len(item) > 2 else 0.0
                text_parts.append(text)
                confidences.append(conf)
            text = " ".join(text_parts).strip()
            confidence = float(np.mean(confidences)) if confidences else 0.0
            results.append(OCRBoxResult(bbox=bbox, text=text, confidence=confidence))

        capture_time = datetime.datetime.now().isoformat()
        session = OCRSessionResult(
            capture_time=capture_time,
            monitor_index=monitor_index,
            image_size=image.size,
            boxes=results,
        )
        return session

    def save_result(self, result: OCRSessionResult, output_dir: Path, keep_history: bool = False) -> Path:
        """Persist the latest OCR session as JSON.

        When ``keep_history`` is False (mặc định), chỉ ghi đè một file ``latest_result.json``
        để tránh tạo quá nhiều file trên máy. Nếu cần lưu lại lịch sử, bật ``keep_history``
        để ghi thêm file timestamp.
        """

        output_dir.mkdir(parents=True, exist_ok=True)
        json_data = result.to_json()

        latest_path = output_dir / "latest_result.json"
        latest_path.write_text(json_data, encoding="utf-8")

        if keep_history:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            history_path = output_dir / f"ocr_result_{timestamp}.json"
            history_path.write_text(json_data, encoding="utf-8")

        return latest_path
