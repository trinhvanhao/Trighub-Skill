#!/usr/bin/env python3
"""
Trighub Webhook v2.1 - With Direct Telegram Support
- Receives webhook data from Trighub
- Persists to SQLite database
- Sends Telegram notifications directly (no openclaw dependency)
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

def send_telegram(message):
    """Send message to Telegram via Bot API"""
    if not TELEGRAM_BOT_TOKEN:
        log("⚠️ TELEGRAM_BOT_TOKEN not configured - skipping Telegram notification")
        return False
    
    try:
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
                (timestamp, received_at, amount, content, bank_name, transaction_type, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('timestamp', datetime.now().isoformat()),
                datetime.now().isoformat(),
                data.get('amount', 0),
                data.get('content', ''),
                data.get('bankName', ''),
                data.get('transactionType', ''),
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
                amount = data.get('amount', 0)
                content = data.get('content', '')[:100]
                bank = data.get('bankName', 'Unknown')
                
                txn_type = "📥 THU" if 'NHAN' in content.upper() else "📤 CHI"
                
                telegram_msg = f"""<b>{txn_type} | {amount:,} VND</b>
━━━━━━━━━━━━━━━━━━━━━
🏦 <b>Ngân hàng:</b> {bank}
📝 <b>Nội dung:</b> {content}
⏰ <b>Thời gian:</b> {datetime.now().strftime('%H:%M:%S')}
📅 <b>Ngày:</b> {datetime.now().strftime('%d/%m/%Y')}"""
                
                send_telegram(telegram_msg)
            
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
    log(f"🚀 Trighub Webhook Server v2.1 Starting")
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
