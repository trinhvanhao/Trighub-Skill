#!/usr/bin/env python3
"""
Trighub Webhook v2.2 - With Enhanced Telegram Notifications
- Receives webhook data from Trighub
- Persists to SQLite database
- Sends formatted Telegram notifications
- Supports recovery queue for reliability
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import sqlite3
import os
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "475039450")
TRIGHUB_SECRET = os.environ.get("TRIGHUB_SECRET", "")
LOG_FILE = os.path.expanduser("~/trighub-webhook.log")
DB_PATH = os.path.expanduser("~/trighub_transactions.db")
QUEUE_DB_PATH = os.path.expanduser("~/trighub_queue.db")

def log(message):
    """Log to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, "a") as f:
        f.write(log_line + "\n")

def send_telegram(data):
    """Send formatted message to Telegram via Bot API"""
    if not TELEGRAM_BOT_TOKEN:
        log("⚠️ TELEGRAM_BOT_TOKEN not configured - skipping notification")
        return False
    
    try:
        # Extract data
        amount = data.get('amount', 0)
        content = data.get('content', '')
        bank = data.get('bankName', '').strip()
        receiver_name = (data.get('receiverName', '') or '').strip()
        
        # Logic phân biệt 4 loại giao dịch:
        # 1. bankName = "VPBank" + content có "NHAN TU" → 💚 NHẬN VPBank
        # 2. bankName = "" + receiverName = "" → 💚 NHẬN NH khác
        # 3. bankName = "VPBank" + content KHÔNG có "NHAN TU" → ❤️ CHUYỂN VPBank
        # 4. bankName có giá trị khác (Techcombank, ACB...) → ❤️ CHUYỂN NH khác
        
        content_upper = content.upper()
        is_vpbank = (bank.upper() == 'VPBANK')
        has_nhan_tu = ('NHAN TU' in content_upper)
        bank_empty = (bank == '')
        receiver_empty = (receiver_name == '')
        
        if is_vpbank and has_nhan_tu:
            # 💚 NHẬN VPBank
            message = f"""<b>💚 NHẬN TIỀN</b>

<b>Ngân hàng:</b> VPBank
<b>Số tiền:</b> <code>+{amount:,.0f} VND</code>
<b>Nội dung:</b> <i>{content}</i>

<b>⏰ Thời gian:</b> {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}"""
        
        elif bank_empty and receiver_empty:
            # 💚 NHẬN NH khác
            message = f"""<b>💚 NHẬN TIỀN</b>

<b>Ngân hàng:</b> Ngân hàng khác
<b>Số tiền:</b> <code>+{amount:,.0f} VND</code>
<b>Nội dung:</b> <i>{content}</i>

<b>⏰ Thời gian:</b> {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}"""
        
        elif is_vpbank and not has_nhan_tu:
            # ❤️ CHUYỂN VPBank
            message = f"""<b>❤️ CHUYỂN TIỀN</b>

<b>Ngân hàng:</b> VPBank
<b>Số tiền:</b> <code>-{amount:,.0f} VND</code>
<b>Nội dung:</b> <i>{content}</i>

<b>⏰ Thời gian:</b> {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}"""
        
        else:
            # ❤️ CHUYỂN NH khác (bankName = Techcombank, ACB...)
            bank_display = bank if bank else 'Ngân hàng khác'
            receiver_display = receiver_name if receiver_name else ''
            
            if receiver_display:
                message = f"""<b>❤️ CHUYỂN TIỀN</b>

<b>Người nhận:</b> {receiver_display}
<b>Ngân hàng:</b> {bank_display}
<b>Số tiền:</b> <code>-{amount:,.0f} VND</code>
<b>Nội dung:</b> <i>{content}</i>

<b>⏰ Thời gian:</b> {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}"""
            else:
                message = f"""<b>❤️ CHUYỂN TIỀN</b>

<b>Ngân hàng:</b> {bank_display}
<b>Số tiền:</b> <code>-{amount:,.0f} VND</code>
<b>Nội dung:</b> <i>{content}</i>

<b>⏰ Thời gian:</b> {datetime.now().strftime('%H:%M:%S - %d/%m/%Y')}"""
        
        # Send to Telegram
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            log(f"✅ Telegram notification sent (Chat: {TELEGRAM_CHAT_ID})")
            return True
        else:
            log(f"❌ Telegram error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        log(f"❌ Telegram send failed: {e}")
        return False

class Database:
    """Handle transaction storage and queue"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.queue_db_path = QUEUE_DB_PATH
        self.init_transaction_db()
        self.init_queue_db()
    
    def init_transaction_db(self):
        """Create transaction table"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                received_at TEXT NOT NULL,
                amount REAL NOT NULL,
                content TEXT,
                bank_name TEXT,
                transaction_type TEXT,
                transaction_id TEXT,
                recipient_name TEXT,
                category TEXT,
                raw_data TEXT,
                processed INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    
    def init_queue_db(self):
        """Create recovery queue table"""
        conn = sqlite3.connect(self.queue_db_path)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                webhook_data TEXT NOT NULL,
                received_at TEXT NOT NULL,
                retry_count INTEGER DEFAULT 0,
                processed INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
    
    def save_transaction(self, data):
        """Save transaction to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('''
                INSERT INTO transactions 
                (timestamp, received_at, amount, content, bank_name, transaction_type, transaction_id, recipient_name, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp', datetime.now().isoformat()),
                datetime.now().isoformat(),
                data.get('amount', 0),
                data.get('content', ''),
                data.get('bankName', ''),
                data.get('transactionType', ''),
                data.get('transaction_id', ''),
                data.get('recipient_name', ''),
                json.dumps(data)
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            log(f"❌ Database error: {e}")
            return False

class WebhookHandler(BaseHTTPRequestHandler):
    """Handle webhook requests from Trighub"""
    
    db = Database()
    
    def do_POST(self):
        """Handle POST request"""
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return
        
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            log(f"📨 Webhook received: {data.get('amount')} VND")
            
            # Save to database
            if self.db.save_transaction(data):
                log(f"✅ Transaction saved to database")
                
                # Send Telegram notification
                send_telegram(data)
            
            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = {"status": "ok", "timestamp": datetime.now().isoformat()}
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            log(f"❌ Error: {e}")
            self.send_response(500)
            self.end_headers()

def main():
    """Start webhook server"""
    port = 8888
    server = HTTPServer(('localhost', port), WebhookHandler)
    
    log("════════════════════════════════════════════════════")
    log(f"🚀 Trighub Webhook Server v2.2 Starting")
    log(f"📍 Port: {port}")
    log(f"🏦 Database: {DB_PATH}")
    log(f"💬 Telegram: {'✅ ENABLED' if TELEGRAM_BOT_TOKEN else '⚠️ DISABLED'}")
    log("════════════════════════════════════════════════════")
    log("Listening for webhooks...")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("\n🛑 Server stopped")

if __name__ == '__main__':
    main()
