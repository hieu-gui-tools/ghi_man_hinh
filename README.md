# ScreenRecorder Pro - Ứng dụng Ghi & Chụp Màn Hình Siêu Tốc (BetterCam DXGI)

Ứng dụng ghi hình màn hình (Screen Record) và chụp ảnh màn hình (Screenshot) chuyên nghiệp, hiệu năng cao được xây dựng trên nền tảng **PySide6** (Qt for Python), công nghệ chụp phần cứng **BetterCam (DirectX Desktop Duplication API)** và quản lý gói bằng **uv**.

---

## ⚡ Điểm nổi bật & Tối ưu Framerate

1. **BetterCam (DirectX Desktop Duplication API)**:
   - Thu nhận khung hình trực tiếp từ VRAM của card đồ họa với độ trễ gần bằng 0 (Zero-copy GPU buffer).
   - Không gây quá tải CPU hay drop frame như các giải pháp truyền thống (MSS, PyAutoGUI, PIL).
2. **Pacing Clock & Chuẩn CFR (Constant Frame Rate)**:
   - Đồng bộ khung hình theo nhịp xung thời gian thực (30 / 60 / 120 FPS).
   - Tự động bù frame khi màn hình tĩnh, đảm bảo video xuất ra không bị giật, lag hay lệch tiếng.
3. **Pipeline FFmpeg cực nhanh**:
   - Sử dụng codec `libx264` với preset `ultrafast` và tối ưu `zerolatency`.
   - Xuất video chuẩn MP4 (H.264 / AAC) tương thích 100% mọi thiết bị và trình phát (Windows Media Player, Premiere, CapCut, web, v.v.).
4. **Phím tắt toàn cục (Global Hotkeys)**:
   - Hỗ trợ phím tắt toàn hệ thống, hoạt động ngay cả khi ứng dụng đang thu nhỏ hoặc bạn đang ở trong game, trình duyệt, ứng dụng khác:
     - **F9**: Bắt đầu / Dừng ghi hình (Start / Stop)
     - **F10**: Tạm dừng / Tiếp tục ghi (Pause / Resume)
     - **F11**: Chụp ảnh toàn màn hình (Full Screenshot)
     - **F12**: Chụp ảnh vùng chọn (Snipping Tool)
   - Có thể tùy chỉnh bất kỳ phím nào (F1-F12, Ctrl+F9, Alt+1, ...) trong tab **Phím tắt (Hotkeys)**.
5. **Giao diện Hiện đại & Khay hệ thống (System Tray)**:
   - Thiết kế tinh tế theo phong cách Fluent / Dark Mode hiện đại.
   - **Chạy ngầm khay hệ thống (Hide to Systray)**: Khi bấm nút [X] tắt cửa sổ, ứng dụng sẽ tự động ẩn xuống khay hệ thống (System Tray bên cạnh đồng hồ Windows) để sẵn sàng nhận phím tắt bất kỳ lúc nào mà không làm vướng màn hình.
   - Nhấp đúp vào icon dưới khay hệ thống hoặc chuột phải chọn "Mở giao diện ScreenRecorder" để mở lại cửa sổ.
   - Nút **Khởi động lại (Restart)**: Khởi động lại app an toàn khi cần nạp lại cấu hình.
   - Nút **Thoát hẳn (Quit)**: Thoát hoàn toàn ứng dụng (không chạy ngầm) nằm ngay cạnh nút Khởi động lại.

---

## 🛠️ Yêu cầu hệ thống

- **Hệ điều hành**: Windows 10 / Windows 11 (64-bit) có hỗ trợ DirectX 11+.
- **Python**: Phiên bản `>= 3.12`.
- **Trình quản lý gói**: Khuyến nghị dùng [uv](https://github.com/astral-sh/uv) để cài đặt và chạy siêu tốc.

---

## 📦 Hướng dẫn cài đặt

### 1. Clone repository
```bash
git clone https://github.com/hieu-gui-tools/ghi_man_hinh.git
cd ghi_man_hinh
```

### 2. Cài đặt môi trường với `uv`
Nếu chưa có `uv`, bạn có thể cài đặt nhanh qua PowerShell:
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Sau đó đồng bộ môi trường:
```bash
uv sync
```

### 3. Tạo lối tắt (Shortcut) ra màn hình Desktop
Chạy script để tạo icon khởi chạy trực tiếp trên Desktop:
```cmd
create_shortcut.cmd
```
*(hoặc chạy lệnh: `uv run python scripts/create_shortcut.py`)*

---

## 🚀 Cách khởi chạy ứng dụng

Bạn có thể chạy ứng dụng bằng các cách sau:

### Cách 1: Bấm trực tiếp Shortcut trên Màn hình Desktop (Khuyên dùng nhất)
- Trên màn hình Desktop có biểu tượng **`Ghi Man Hinh - ScreenRecorder`**.
- Lối tắt được cấu hình chạy trực tiếp với `pythonw.exe`: **hoàn toàn không hiện cửa sổ đen console**, mở ứng dụng tức thì với icon riêng.

### Cách 2: Chạy qua VBScript (Silent Mode)
- Nhấp đúp vào file **`run.vbs`**.

### Cách 3: Chạy qua CMD / Terminal
- Nhấp đúp vào file **`run.cmd`** hoặc chạy:
```powershell
uv run python main.py
```

---

## ⌨️ Bảng phím tắt mặc định

| Hành động | Phím mặc định | Tùy chọn khác |
| :--- | :---: | :---: |
| Bắt đầu / Dừng ghi hình | **F9** | Ctrl+F9 / Tùy chỉnh |
| Tạm dừng / Tiếp tục ghi | **F10** | Ctrl+F10 / Tùy chỉnh |
| Chụp toàn màn hình | **F11** | Ctrl+F11 / Tùy chỉnh |
| Chụp vùng chọn (Snipping) | **F12** | Ctrl+F12 / Tùy chỉnh |

*(Có thể thay đổi hoặc bật/tắt trong tab "Phím tắt (Hotkeys)" trên giao diện)*

---

## 📁 Cấu trúc thư mục dự án

```text
Ghi_man_hinh/
├── assets/                  # Icon ứng dụng (.ico, .png)
├── core/                    # Logic cốt lõi (ghi hình, chụp ảnh, audio, hotkeys, config)
│   ├── audio_recorder.py    # Ghi âm thanh hệ thống / micro
│   ├── capture_engine.py    # Engine BetterCam DXGI
│   ├── config.py            # Quản lý cấu hình config.json
│   ├── desktop_utils.py     # Tiện ích hệ thống Windows
│   ├── hotkey_manager.py    # Quản lý phím tắt toàn cục
│   └── recorder.py          # Luồng ghi video & FFmpeg pipeline
├── scripts/                 # Script tiện ích (tạo shortcut, tạo icon)
├── src/                     # Module package
├── ui/                      # Giao diện người dùng PySide6 (Fluent Dark)
├── config.example.json      # File mẫu cấu hình
├── create_shortcut.cmd      # Batch script tạo shortcut Desktop
├── main.py                  # Điểm khởi chạy chính của ứng dụng
├── pyproject.toml           # Cấu hình project & dependencies
├── run.cmd                  # Script khởi động dạng console
└── run.vbs                  # Script khởi động ẩn cửa sổ console
```

---

## 📄 License

Dự án phát triển mã nguồn mở phục vụ mục đích học tập và làm việc cá nhân.
