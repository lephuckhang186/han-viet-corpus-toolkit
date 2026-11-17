"""Đăng nhập Google Drive trên máy cá nhân để dùng quyền OAuth ở Kaggle.

Chỉ chạy thủ công khi bạn muốn cấp quyền. Không cài hoặc chạy OCR.
Token lưu ngoài repository, không in thông tin xác thực ra màn hình.
"""
from pathlib import Path
import argparse
import json
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", required=True, type=Path, help="JSON OAuth client loại Desktop app, tải từ Google Cloud.")
    parser.add_argument("--output", type=Path, help="Nơi lưu token ngoài repository; mặc định trong thư mục dữ liệu ứng dụng của user.")
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home()/".local/share")))
    target = (args.output or base/"han-viet-corpus-toolkit"/"drive-token.json").expanduser().resolve()
    if target.is_relative_to(project):
        parser.error("Đặt token ngoài repository để tránh đưa quyền tài khoản vào Git hoặc gói bàn giao.")
    if target.exists():
        parser.error("File token đã tồn tại; dùng --output trỏ tới tên mới để cấp lại, không ghi đè.")
    client = json.loads(args.client.expanduser().read_text(encoding="utf-8"))
    if "installed" not in client:
        parser.error("Cần OAuth client loại Desktop app, không dùng Web application.")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        raise SystemExit("Cài trước: python -m pip install google-auth-oauthlib") from None
    flow = InstalledAppFlow.from_client_config(client, SCOPES)
    credentials = flow.run_local_server(host="127.0.0.1", port=0, open_browser=True,
                                       access_type="offline", prompt="consent")
    if not credentials.refresh_token:
        raise SystemExit("Google chưa cấp quyền làm mới; chạy lại và chấp thuận quyền truy cập.")
    target.parent.mkdir(parents=True, exist_ok=True)
    # x không ghi đè token cũ; muốn cấp lại dùng --output trỏ tới tên mới.
    with target.open("x", encoding="utf-8") as stream:
        stream.write(credentials.to_json())
    try:
        target.chmod(0o600)
    except OSError:
        pass
    print("Đã lưu quyền đọc Drive tại:", target)
    print("Tự mở file và lưu nội dung vào Kaggle Secret GOOGLE_DRIVE_CREDENTIALS. Không gửi nội dung file vào chat.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
