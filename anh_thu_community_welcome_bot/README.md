# ANH THU COMMUNITY Welcome Bot

Bot Discord Python có Welcome Card Luxury tự động.

## Tính năng

- Welcome Card 1024x512.
- Theme đen + vàng luxury.
- Avatar Discord tự động.
- Username tự động.
- Member count tự động.
- Gửi card vào kênh welcome.
- Ping thành viên mới.
- Auto role tùy chọn.
- Giữ lại chức năng cũ: gửi `discord_profile_themes.jpg` khi thành viên gửi ảnh trong các channel được khai báo.
- Health server cho Render.

## Deploy trên Render

Build Command:
`pip install -r requirements.txt`

Start Command:
`python bot.py`

Environment Variables:

`DISCORD_TOKEN` = Bot Token

`WELCOME_CHANNEL_ID` = ID kênh nhận welcome card

`AUTO_ROLE_ID` = ID role tự động. Để `0` nếu không dùng.

`CHANNEL_IDS` = ID các kênh dùng chức năng image-reply cũ, phân cách bằng dấu phẩy. Để trống nếu không dùng.

`PORT` = Render tự cấp, mặc định code dùng 10000.

## Discord Developer Portal

Bật:
- Server Members Intent
- Message Content Intent

Bot cần quyền ở kênh welcome:
- View Channel
- Send Messages
- Attach Files
- Mention Everyone không bắt buộc

Nếu dùng Auto Role:
- Manage Roles
- Role của bot phải nằm cao hơn role cần cấp.

## Chạy local

```bash
pip install -r requirements.txt
python bot.py
```
