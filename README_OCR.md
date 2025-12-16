# Professional OCR Tool

Tool OCR chuyên nghiệp với các tính năng tiền xử lý ảnh nâng cao để cải thiện độ chính xác nhận dạng.

## Tính năng

- 🆕 **Capture màn hình + bounding box tuỳ chọn**: Capture trực tiếp từ màn hình (bao gồm fullscreen), vẽ bounding box cho từng vùng cần đọc, lưu kết quả OCR và toạ độ vào file JSON.
- 🔴 **Preview realtime không cần bấm**: Màn hình được cập nhật liên tục theo chu kỳ, luôn hiển thị frame mới nhất để vẽ box và chạy OCR.
- 🔁 **OCR liên tục + realtime JSON**: Hẹn giờ OCR tự động trên bounding box đã chọn, luôn ghi đè `outputs/latest_result.json` để các web view (HTML/PHP) đọc realtime (không tạo thêm file để tránh đầy ổ cứng).
- 🎥 **Nguồn DeckLink qua DirectShow**: Nhận luồng SDI/HDMI từ Blackmagic DeckLink (WDM) bằng FFmpeg/PyAV DirectShow để tránh phụ thuộc build DeckLink.
- 🎛️ **Chọn DeckLink giống OBS**: Quét tên thiết bị DirectShow (DeckLink Video Capture/WDM), chọn preset chuẩn (1080p59.94, 1080p60, 720p…) rồi bật preview ngay sau khi kết nối để vẽ bounding box trước khi OCR.

### Tự động phát hiện và điều chỉnh (Mới!)
- ✅ **Tự động phân tích ảnh**: Phát hiện kích thước, chất lượng, blur, độ tương phản
- ✅ **Tự động điều chỉnh tham số OCR**: canvas_size, mag_ratio, thresholds dựa trên kích thước ảnh
- ✅ **Tự động điều chỉnh preprocessing**: min_dimension, border_size, noise removal dựa trên chất lượng ảnh
- ✅ **Tự động chọn các bước xử lý**: Thêm/bỏ các bước preprocessing phù hợp với từng loại ảnh

### Tiền xử lý ảnh
- ✅ **Inverted Images**: Đảo ngược màu sắc (cho ảnh nền tối, chữ sáng)
- ✅ **Rescaling**: Tự động điều chỉnh kích thước ảnh
- ✅ **Binarization**: Chuyển đổi sang ảnh đen trắng (adaptive, Otsu, simple threshold)
- ✅ **Noise Removal**: Loại bỏ nhiễu (median, gaussian, bilateral, morphology)
- ✅ **Dilation & Erosion**: Làm dày/mỏng chữ
- ✅ **Rotation/Deskewing**: Tự động phát hiện và sửa độ nghiêng
- ✅ **Removing Borders**: Tự động cắt bỏ viền trắng/đen
- ✅ **Missing Borders**: Thêm viền nếu thiếu (giúp phát hiện cạnh tốt hơn)
- ✅ **Transparency/Alpha Channel**: Xử lý ảnh có kênh alpha

## Cài đặt

```bash
pip install -r requirements.txt
```

> Lưu ý: dự án dùng thêm thư viện `av` (PyAV) để nhận luồng SRT ổn định và giảm drop frame khi decode.

Nếu gặp lỗi `ModuleNotFoundError` (ví dụ `mss` hoặc `av`), hãy chắc chắn đã cài đủ phụ thuộc bằng lệnh trên. Trên Windows bạn có thể cần "Desktop development with C++" (Visual Studio Build Tools) để biên dịch PyAV.

Hoặc cài thủ công các gói chính: `easyocr`, `opencv-python-headless`, `mss`, `Pillow`, `numpy`.

## Sử dụng

### 1. GUI Interface (Khuyến nghị)

Khởi chạy giao diện đồ họa:

```bash
python ocr_gui.py
```

**Luồng chính (capture + OCR):**
1. Chọn nguồn capture:
   - **Monitor**: nhập `Monitor index` (mặc định 1); preview sẽ tự cập nhật frame mới nhất hoặc bấm **Capture screen**.
   - **SRT**: nhập URL dạng `srt://IP:PORT`, bấm **Kết nối SRT** để nhận khung hình realtime từ VLC/encoder SRT và preview tự cập nhật.
- **DeckLink (DirectShow)**: chọn thiết bị trong combobox (tự quét bằng `ffmpeg -f dshow -list_devices true`, hiển thị sẵn "DeckLink Video Capture..." nếu tìm thấy). Chọn preset ở combobox **Mode** (ví dụ `1080p59.94`, `1080p60`, `720p50`) để tự điền Size/FPS. Nếu cần chỉnh tay bạn vẫn có thể sửa Size/FPS. Ứng dụng dùng DirectShow mặc định (không cần PyAV build DeckLink).
2. Trên preview, kéo thả chuột để vẽ các bounding box cho vùng cần đọc.
3. Chọn ngôn ngữ (ví dụ `en,vi`), bật/tắt GPU nếu cần.
4. Nhấn **Run OCR** → EasyOCR chạy trên từng bounding box, ghi đè `outputs/latest_result.json` (không tạo thêm file). Nếu muốn lưu lịch sử, đặt `KEEP_HISTORY = True` trong `ocr_gui.py`.

**OCR liên tục (auto):**
- Sau khi vẽ bounding box (preview đã tự lấy ảnh), nhập chu kỳ (ms) trong mục **Auto OCR**.
- Nhấn **Bật OCR liên tục** để chạy lặp; ứng dụng sẽ tự capture màn hình, OCR và ghi đè `outputs/latest_result.json` sau mỗi chu kỳ (mặc định **không** lưu file timestamp để tiết kiệm dung lượng).
- Nhấn lại nút để dừng.

**Auto preview:**
- Mặc định bật ngay khi mở GUI, tự capture và refresh preview theo chu kỳ.
- Có thể chỉnh chu kỳ (ms) và bật/tắt ở mục **Auto preview**. Nguồn preview sẽ là Monitor hoặc SRT tùy lựa chọn hiện tại.

Kết quả JSON bao gồm:
- Thời gian capture, monitor index, kích thước ảnh gốc
- Danh sách box: `bbox` (x1, y1, x2, y2), `text`, `confidence`

**Xem realtime trên web:**
- Chạy `python -m http.server 8000` trong thư mục dự án (hoặc dùng Apache/Nginx/PHP tùy ý).
- Mở `http://localhost:8000/realtime_view.html` để xem JSON realtime (tự refresh mỗi giây).
- Nếu dùng PHP, chép `realtime_view.php` vào webroot và truy cập; trang sẽ tự reload mỗi giây và hiển thị JSON.

Hoặc:

```bash
python run_gui.py
```

**Tính năng GUI:**
- ✅ Chọn ảnh trực tiếp từ giao diện
- ✅ Cấu hình đầy đủ các tham số OCR và tiền xử lý
- ✅ Quản lý các bước tiền xử lý (thêm/xóa/sắp xếp)
- ✅ Lưu và tải cấu hình từ file JSON
- ✅ Xem kết quả trực tiếp trong giao diện
- ✅ Các preset cấu hình có sẵn (standard, inverted, noisy, low_quality)

**Các tab cấu hình:**
- **OCR Settings**: Ngôn ngữ, GPU, các tham số OCR (thresholds, ratios, etc.)
- **Tiền xử lý**: Các tham số tiền xử lý (border, binarize, noise removal, kernels)
- **Các bước xử lý**: Quản lý pipeline tiền xử lý (kéo thả để sắp xếp)
- **Output**: Cài đặt thư mục output và lưu ảnh đã xử lý

**Quản lý cấu hình:**
- **Tải cấu hình**: Chọn từ các file config đã lưu
- **Lưu cấu hình**: Lưu cấu hình hiện tại ra file JSON
- **Cấu hình mặc định**: Đặt lại về cấu hình mặc định

Các file cấu hình được lưu trong thư mục `configs/` với định dạng JSON.

### 2. Command Line

```bash
# Sử dụng mặc định
python ocr_tool.py image.png

# Tùy chỉnh ngôn ngữ
python ocr_tool.py image.png --languages en vi

# Tắt GPU (dùng CPU)
python ocr_tool.py image.png --no-gpu

# Tùy chỉnh các bước tiền xử lý
python ocr_tool.py image.png --steps load remove_borders rescale binarize deskew

# Không lưu ảnh đã xử lý
python ocr_tool.py image.png --no-preprocess-save

# Thay đổi thư mục output
python ocr_tool.py image.png --output-dir results

# Tắt tự động phát hiện (sử dụng cấu hình cố định)
python ocr_tool.py image.png --no-auto-detect
```

### 3. Python API

```python
from ocr_tool import OCRTool
import ocr_config_example as config

# Khởi tạo
ocr = OCRTool(
    languages=['en'],
    gpu=True,
    preprocess_config=config.STANDARD_CONFIG
)

# Xử lý ảnh
results = ocr.process_image(
    'image.png',
    preprocessing_steps=config.STANDARD_STEPS,
    save_preprocessed=True
)

# In kết quả
print(results['full_text'])

# Lưu kết quả
ocr.save_results(results, 'image.png')
```

## Các bước tiền xử lý có sẵn

- `load`: Tải ảnh và xử lý alpha channel
- `remove_borders`: Loại bỏ viền
- `add_borders`: Thêm viền
- `invert`: Đảo ngược màu
- `rescale`: Điều chỉnh kích thước
- `binarize`: Chuyển sang đen trắng
- `remove_noise`: Loại bỏ nhiễu
- `dilate`: Làm dày chữ
- `erode`: Làm mỏng chữ
- `deskew`: Sửa độ nghiêng

## Quản lý cấu hình

### Sử dụng Config Manager

Tool cung cấp `OCRConfigManager` để quản lý cấu hình:

```python
from ocr_config_manager import OCRConfigManager

# Khởi tạo
config_manager = OCRConfigManager()

# Lưu cấu hình
config = {
    "ocr": {"languages": ["en"], "gpu": True},
    "preprocessing": {"min_dimension": 1000},
    "preprocessing_steps": ["load", "rescale", "binarize"],
    "output": {"save_preprocessed": True, "output_dir": "temp"}
}
config_manager.save_config(config, "my_config.json")

# Tải cấu hình
config = config_manager.load_config("my_config.json")

# Liệt kê các config có sẵn
configs = config_manager.list_configs()
```

### Cấu hình mẫu

Tool đi kèm với các cấu hình mẫu trong `ocr_config_example.py` và các preset trong GUI:

1. **STANDARD_CONFIG**: Cho ảnh thông thường
2. **INVERTED_CONFIG**: Cho ảnh đảo ngược (nền tối, chữ sáng)
3. **NOISY_CONFIG**: Cho tài liệu scan có nhiều nhiễu
4. **LOW_QUALITY_CONFIG**: Cho ảnh chất lượng thấp/mờ
5. **MISSING_BORDER_CONFIG**: Cho ảnh thiếu viền
6. **ROTATED_CONFIG**: Cho tài liệu bị nghiêng

## Ví dụ sử dụng

Xem file `ocr_example_usage.py` để biết các ví dụ chi tiết.

```python
# Ví dụ: Xử lý ảnh đảo ngược
from ocr_tool import OCRTool
import ocr_config_example as config

ocr = OCRTool(
    languages=['en'],
    gpu=True,
    preprocess_config=config.INVERTED_CONFIG
)

results = ocr.process_image(
    'inverted_image.png',
    preprocessing_steps=config.INVERTED_STEPS
)

print(results['full_text'])
```

## Kết quả

Tool sẽ tạo ra:
- File kết quả chi tiết: `ocr_result_TIMESTAMP.txt` (chứa tất cả thông tin)
- File text đơn giản: `ocr_simple_TIMESTAMP.txt` (chỉ chứa text)
- Ảnh đã xử lý: `preprocessed_TIMESTAMP.png` (nếu bật save_preprocessed)

## Tùy chỉnh

### Tùy chỉnh cấu hình tiền xử lý

```python
custom_config = {
    'border_threshold': 15,      # Ngưỡng phát hiện viền
    'border_size': 25,           # Kích thước viền thêm vào
    'min_dimension': 1000,       # Kích thước tối thiểu
    'binarize_method': 'otsu',   # 'adaptive', 'otsu', 'simple'
    'noise_method': 'bilateral', # 'median', 'gaussian', 'bilateral', 'morphology'
    'dilate_kernel': 3,          # Kích thước kernel dilation
    'erode_kernel': 1            # Kích thước kernel erosion
}
```

### Tùy chỉnh pipeline tiền xử lý

```python
custom_steps = [
    'load',           # Tải ảnh
    'add_borders',    # Thêm viền
    'rescale',        # Điều chỉnh kích thước
    'remove_noise',   # Loại bỏ nhiễu
    'binarize',       # Chuyển đen trắng
    'deskew',         # Sửa nghiêng
    'dilate',         # Làm dày chữ
    'erode'           # Làm mỏng chữ
]
```

## Tự động phát hiện

Tool tự động phân tích ảnh và điều chỉnh tham số dựa trên:

- **Kích thước ảnh**: very_small, small, medium, large, very_large
  - Ảnh nhỏ: Tăng canvas_size, mag_ratio để scale up
  - Ảnh lớn: Giảm để tối ưu tốc độ
  
- **Chất lượng ảnh**:
  - Blur: Tự động thêm noise removal, điều chỉnh mag_ratio
  - Độ tương phản thấp: Chuyển sang Otsu binarization
  - Ảnh tối/sáng: Điều chỉnh thresholds

- **Tự động chọn preprocessing steps**:
  - Ảnh nhỏ: Thêm add_borders, remove_noise
  - Ảnh mờ: Thêm remove_noise trước binarize
  - Ảnh tối: Thêm invert nếu cần

Bạn có thể tắt tự động phát hiện bằng `--no-auto-detect` hoặc toggle trong GUI.

## Lưu ý

- Tool sử dụng EasyOCR, hỗ trợ GPU để tăng tốc
- Lần đầu chạy sẽ tải model, có thể mất vài phút
- Với GPU, tốc độ xử lý nhanh hơn đáng kể
- Các bước tiền xử lý có thể ảnh hưởng đến thời gian xử lý
- **Tự động phát hiện được bật mặc định** - tool sẽ tự động tối ưu cho từng ảnh

## Yêu cầu hệ thống

- Python 3.7+
- OpenCV (opencv-python)
- NumPy
- Pillow
- EasyOCR
- CUDA (tùy chọn, cho GPU support)

