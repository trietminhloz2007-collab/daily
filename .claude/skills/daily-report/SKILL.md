---
name: daily-report
description: Tổng hợp báo cáo tối 9h gồm email chưa đọc quan trọng (Gmail + Outlook) và deadline/thông báo sắp tới trên Blackboard (blackboard.hcmiu.edu.vn). Dùng khi người dùng gọi "/daily-report" hoặc khi Routine 9h tối kích hoạt.
---

# Daily Report Skill (Gmail / Outlook / Blackboard)

Skill này tạo một báo cáo tổng hợp mỗi tối lúc 9h, gồm 3 phần:

1. **Gmail** — các thread chưa đọc quan trọng trong 24h qua.
2. **Outlook** — các email chưa đọc quan trọng trong 24h qua.
3. **Blackboard (HCMIU)** — bài tập/deadline/thông báo sắp đến hạn.

## Quy trình thực hiện

### 1. Gmail
Dùng các tool MCP `mcp__Gmail__search_threads` với query `is:unread newer_than:1d` (có thể thêm
`label:important` hoặc lọc theo người gửi quan trọng nếu người dùng cấu hình). Tóm tắt: người gửi,
tiêu đề, 1 dòng nội dung chính.

### 2. Outlook
Chưa có MCP server cho Outlook trong môi trường này. Dùng script
`scripts/outlook_unread.py` gọi Microsoft Graph API (`/me/mailFolders/inbox/messages?$filter=isRead eq false`).
Script đọc credentials từ biến môi trường, KHÔNG hard-code:
- `MS_CLIENT_ID`, `MS_CLIENT_SECRET`, `MS_TENANT_ID`, `MS_REFRESH_TOKEN`

Nếu các biến này chưa được cấu hình, báo rõ cho người dùng là phần Outlook bị bỏ qua và cần thiết lập
OAuth app đăng ký trên Azure AD (Microsoft Graph, scope `Mail.Read offline_access`) trước khi bật.

### 3. Blackboard (blackboard.hcmiu.edu.vn)
Trường không cấp Blackboard Learn REST API cho sinh viên, nên dùng scraping bằng Playwright:
`scripts/blackboard_scrape.py`. Script:
- Đăng nhập bằng `BLACKBOARD_USERNAME` / `BLACKBOARD_PASSWORD` (biến môi trường, không hard-code).
- Nếu trường dùng SSO/2FA, thay vào đó dùng session cookie đã lưu tại
  `~/.config/daily-report/blackboard_state.json` (Playwright storage state) — tạo file này bằng cách
  đăng nhập thủ công 1 lần qua `scripts/blackboard_login_once.py` (mở trình duyệt có giao diện để nhập
  mật khẩu / mã 2FA), sau đó các lần sau script chạy headless dùng lại session.
- Sau khi đăng nhập, vào trang "To-Do" / "Calendar" (Ultra) của Blackboard, lấy danh sách các mục có hạn
  trong 7 ngày tới, in ra JSON: `[{course, title, due_date, url}]`.

### 4. Tổng hợp báo cáo
Gộp 3 phần trên thành một bản tóm tắt ngắn gọn (Markdown), ưu tiên các mục có deadline gần nhất lên đầu.
Với Blackboard, mỗi announcement đều có trường `course` (lấy từ "Posted to:") — **luôn hiển thị tên môn
học làm nhãn chính** (ví dụ "Physics 2"), người đăng (`posted_by`) chỉ ghi kèm phụ, không đặt lên đầu.
Gửi báo cáo bằng cách tạo Gmail draft tới chính người dùng (`mcp__Gmail__create_draft`) hoặc in trực tiếp
trong session nếu Routine chạy vào session hiện tại.

## Lên lịch tự động 9h tối

Dùng `create_trigger` (Claude Code Remote) với cron `0 21 * * *`, prompt trỏ tới skill này
(`/daily-report` hoặc mô tả tương đương). Xem `README.md` trong thư mục này để biết lệnh cụ thể.

## Lưu ý bảo mật
- Không bao giờ commit mật khẩu, token, cookie thật vào repo.
- Tất cả credentials đọc từ biến môi trường hoặc file state nằm ngoài repo (`~/.config/...`).
- `blackboard_state.json` chứa session cookie thật — không commit, đã thêm vào `.gitignore`.
