# Daily Report Skill — Setup

Skill tổng hợp báo cáo tối 9h từ Gmail, Outlook, Blackboard (HCMIU). Xem chi tiết quy trình trong `SKILL.md`.

## Cài đặt lần đầu

### 1. Outlook (Microsoft Graph)
1. Đăng ký một app trên Azure AD (App registrations), scope `Mail.Read offline_access`.
2. Lấy `client_id`, `client_secret`, `tenant_id`, và một `refresh_token` (qua OAuth device code flow).
3. Đặt các biến môi trường: `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`, `MS_REFRESH_TOKEN`.

### 2. Blackboard
1. Cài Playwright: `pip install playwright && playwright install chromium`.
2. Chạy một lần: `python3 scripts/blackboard_login_once.py`, đăng nhập thủ công (kể cả 2FA).
3. Session sẽ được lưu tại `~/.config/daily-report/blackboard_state.json` (không commit file này).
4. Từ đó `scripts/blackboard_scrape.py` chạy headless dùng lại session đã lưu.

### 3. Gmail
Không cần setup thêm — dùng trực tiếp các tool MCP `mcp__Gmail__*` đã kết nối trong session.

## Lên lịch chạy tự động 9h tối

Dùng `create_trigger` (Claude Code Remote), ví dụ cron `0 21 * * *` (giờ server), prompt yêu cầu chạy
skill `daily-report` và gửi báo cáo. Bạn cần xác nhận múi giờ server trước khi tạo trigger, vì cron chạy
theo giờ UTC/server, không phải giờ Việt Nam.

## Bảo mật
- Không commit `blackboard_state.json`, token, mật khẩu.
- File state Blackboard chứa cookie phiên đăng nhập thật, coi như bí mật.
