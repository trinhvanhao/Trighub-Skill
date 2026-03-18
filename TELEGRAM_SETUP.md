# 📱 TELEGRAM SETUP GUIDE

**Cài đặt Telegram notifications cho Trighub Skill**

---

## 🤖 BƯỚC 1: Tạo Telegram Bot

### 1.1 Mở BotFather
- Mở Telegram
- Tìm: `@BotFather`
- Hoặc: https://t.me/botfather

### 1.2 Tạo Bot Mới
```
/start
/newbot
```

**Trả lời câu hỏi:**
- Bot name: `Trighub Notifier` (hoặc tên khác)
- Username: `trighub_notifier_bot` (phải unique)

### 1.3 Lấy Bot Token
BotFather sẽ gửi:
```
Use this token to access the HTTP API:
123456789:ABCDEfghijklmnopqrst_uvwxyz1234567890
```

**Lưu token này!** ← Cần dùng ở bước sau

---

## 📍 BƯỚC 2: Lấy Telegram Chat ID

### Option A: Sử dụng Bot của bạn

1. Start bot của bạn: `https://t.me/your_bot_username`
2. Send message bất kỳ: `/start`
3. Truy cập URL này:
```
https://api.telegram.org/bot123456789:ABCDEfghijklmnopqrst_uvwxyz1234567890/getUpdates
```
(Thay token của bạn)

4. Tìm `"chat":{"id":XXXXXXXX}`
5. **Đó là Chat ID của bạn!** (Ví dụ: 475039450)

### Option B: Sử dụng @userinfobot

1. Tìm: `@userinfobot`
2. Send: `/start`
3. Bot sẽ hiển thị ID của bạn

---

## 🔧 BƯỚC 3: Setup .env File

### 3.1 Tạo .env file

```bash
cd ~/Trighub\ Skill
cp .env.template .env
```

### 3.2 Edit .env
```bash
nano .env
```

**Nội dung:**
```
TELEGRAM_BOT_TOKEN=123456789:ABCDEfghijklmnopqrst_uvwxyz1234567890
TELEGRAM_CHAT_ID=475039450
```

**Lưu:**
- Ctrl+X → Y → Enter

---

## 🚀 BƯỚC 4: Chạy Webhook Server (v2.1)

```bash
cd ~/Trighub\ Skill

# Stop server cũ
pkill -f "trighub-webhook"

# Chạy server mới (v2.1 - with Telegram)
python3 trighub-webhook-telegram.py
```

**Expected output:**
```
[2026-03-19 03:30:00] ════════════════════════════════════════════════════
[2026-03-19 03:30:00] 🚀 Trighub Webhook Server v2.1 Starting
[2026-03-19 03:30:00] 📍 Port: 8888
[2026-03-19 03:30:00] 🏦 Database: ~/trighub_transactions.db
[2026-03-19 03:30:00] 💬 Telegram: ✅ ENABLED
[2026-03-19 03:30:00] ════════════════════════════════════════════════════
```

---

## ✅ BƯỚC 5: Test Telegram Notification

### Test 1: Send test webhook
```bash
curl -X POST http://localhost:8888/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 100000,
    "content": "Test Transaction",
    "bankName": "Techcombank",
    "transactionType": "OUT"
  }'
```

### Test 2: Check logs
```bash
tail -f ~/trighub-webhook.log
```

**Bạn sẽ thấy:**
```
✅ Telegram notification sent
```

### Test 3: Check Telegram
- Kiểm tra Telegram app
- Bạn sẽ nhận message:
```
📤 CHI | 100,000 VND
━━━━━━━━━━━━━━━━━━━━━
🏦 Ngân hàng: Techcombank
📝 Nội dung: Test Transaction
⏰ Thời gian: 03:30:45
📅 Ngày: 19/03/2026
```

---

## 📝 TELEGRAM MESSAGE FORMAT

Khi nhận webhook từ Trighub:

```
📤 CHI | 100,000 VND
━━━━━━━━━━━━━━━━━━━━━
🏦 Ngân hàng: Techcombank
📝 Nội dung: Payment for service
⏰ Thời gian: HH:MM:SS
📅 Ngày: DD/MM/YYYY
```

---

## 🆘 TROUBLESHOOTING

### ❌ "Telegram: DISABLED"
- **Lỗi:** Không có TELEGRAM_BOT_TOKEN
- **Fix:** 
  ```bash
  export TELEGRAM_BOT_TOKEN="your_token"
  python3 trighub-webhook-telegram.py
  ```

### ❌ "Telegram error: 404"
- **Lỗi:** Bot token sai hoặc bot không tồn tại
- **Fix:** Kiểm tra token ở BotFather

### ❌ "Telegram error: 403"
- **Lỗi:** Bot không có quyền send message
- **Fix:**
  1. Start bot: https://t.me/your_bot
  2. Send `/start` (important!)
  3. Try again

### ❌ Không nhận được message
- **Fix:**
  1. Kiểm tra Chat ID đúng không
  2. Kiểm tra bot đã được start chưa
  3. Check logs: `tail ~/trighub-webhook.log`

---

## ⚙️ SETUP PERMANENT (Auto-start)

### Using Launchd (macOS)

Cập nhật file: `~/Trighub Skill/com.trighub.webhook.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trighub.webhook</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/trinhhao/Trighub Skill/trighub-webhook-telegram.py</string>
    </array>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>YOUR_BOT_TOKEN_HERE</string>
        <key>TELEGRAM_CHAT_ID</key>
        <string>YOUR_CHAT_ID_HERE</string>
    </dict>
    
    <key>StandardOutPath</key>
    <string>/tmp/trighub-webhook.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/trighub-webhook-error.log</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
```

Load plist:
```bash
launchctl load ~/Library/LaunchAgents/com.trighub.webhook.plist
```

---

## 🎉 HOÀN THÀNH!

Bây giờ mỗi khi Trighub gửi webhook:
1. ✅ Lưu vào database
2. ✅ Tạo Excel report
3. ✅ **Gửi Telegram notification** 📱

---

**Support:** Check logs at `~/trighub-webhook.log`
