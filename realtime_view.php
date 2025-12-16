<?php
// Simple PHP viewer for outputs/latest_result.json
$latestPath = __DIR__ . '/outputs/latest_result.json';
$data = null;
if (file_exists($latestPath)) {
    $jsonContent = file_get_contents($latestPath);
    $data = json_decode($jsonContent, true);
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>OCR Live JSON (PHP)</title>
  <style>
    body { font-family: Arial, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 1.5rem; }
    .card { background: #1e293b; border-radius: 12px; padding: 1rem 1.25rem; box-shadow: 0 10px 30px rgba(0,0,0,0.35); }
    pre { background: #0b1221; border-radius: 8px; padding: 1rem; overflow-x: auto; color: #cbd5e1; }
  </style>
  <meta http-equiv="refresh" content="1" />
</head>
<body>
  <h1>EasyOCR Live Result (PHP)</h1>
  <p>Trang này tải lại mỗi giây. Đảm bảo file <code>outputs/latest_result.json</code> tồn tại.</p>
  <div class="card">
    <pre><?php echo $data ? json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) : 'Chưa có dữ liệu.'; ?></pre>
  </div>
</body>
</html>
