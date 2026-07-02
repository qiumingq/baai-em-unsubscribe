from flask import Flask, request, render_template_string, jsonify, Response
import sqlite3
import hmac
import hashlib
import os
from datetime import datetime

app = Flask(__name__)
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-must-change-in-render-dashboard')
DATABASE = os.path.join(os.path.dirname(__file__), 'unsubscribe.db')

SUCCESS_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>退订成功 | 智源研究院</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
.card { background: white; padding: 48px 40px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); text-align: center; max-width: 440px; width: 100%; animation: slideUp 0.5s ease-out; }
@keyframes slideUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
.icon { width: 72px; height: 72px; background: #10b981; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; color: white; font-size: 36px; font-weight: bold; }
h1 { color: #1f2937; font-size: 26px; margin-bottom: 16px; font-weight: 700; }
p { color: #6b7280; font-size: 16px; line-height: 1.7; margin-bottom: 8px; }
.email-box { background: #f3f4f6; color: #374151; font-weight: 600; padding: 10px 16px; border-radius: 8px; display: inline-block; margin: 12px 0 20px; font-size: 15px; word-break: break-all; }
.footer { margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb; font-size: 13px; color: #9ca3af; }
</style>
</head>
<body>
<div class="card">
<div class="icon">&#10003;</div>
<h1>退订成功</h1>
<p>以下邮箱地址已成功从邮件列表中移除</p>
<div class="email-box">{{ email }}</div>
<p>您将不再收到此类学术邀请邮件。<br>如有疑问，请联系 hychen@baai.ac.cn</p>
<div class="footer">&copy; 北京智源人工智能研究院</div>
</div>
</body>
</html>'''

ERROR_HTML = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>退订失败 | 智源研究院</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; background: linear-gradient(135deg,#667eea 0%,#764ba2 100%); min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px; }
.card { background: white; padding: 48px 40px; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.15); text-align: center; max-width: 440px; width: 100%; }
.icon { width: 72px; height: 72px; background: #ef4444; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; color: white; font-size: 36px; font-weight: bold; }
h1 { color: #1f2937; font-size: 26px; margin-bottom: 16px; font-weight: 700; }
p { color: #6b7280; font-size: 16px; line-height: 1.7; margin-bottom: 8px; }
.footer { margin-top: 32px; padding-top: 24px; border-top: 1px solid #e5e7eb; font-size: 13px; color: #9ca3af; }
</style>
</head>
<body>
<div class="card">
<div class="icon">&#10005;</div>
<h1>退订失败</h1>
<p>{{ message }}</p>
<div class="footer">&copy; 北京智源人工智能研究院</div>
</div>
</body>
</html>'''

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS unsubscribed (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        unsubscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ip_address TEXT
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_email ON unsubscribed(email)')
    conn.commit()
    conn.close()
    print(f"[INFO] Database initialized at {DATABASE}")

def generate_token(email):
    return hmac.new(SECRET_KEY.encode('utf-8'), email.lower().strip().encode('utf-8'), hashlib.sha256).hexdigest()[:16]

def verify_token(email, token):
    if not email or not token: return False
    return hmac.compare_digest(generate_token(email), token)

def is_unsubscribed(email):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT 1 FROM unsubscribed WHERE email = ?', (email.lower().strip(),))
    result = c.fetchone() is not None
    conn.close()
    return result

def add_unsubscribe(email, ip):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO unsubscribed (email, ip_address) VALUES (?, ?)', (email.lower().strip(), ip))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_all_unsubscribed():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT email, unsubscribed_at FROM unsubscribed ORDER BY unsubscribed_at DESC')
    rows = c.fetchall()
    conn.close()
    return rows

@app.route('/')
def index():
    return jsonify({"service": "BAAI Unsubscribe Service", "status": "running", "version": "1.0.0",
        "endpoints": {"unsubscribe": "/unsubscribe?email=xxx&token=xxx", "check": "/check?email=xxx", "export": "/export"}})

@app.route('/unsubscribe')
def unsubscribe():
    email = request.args.get('email', '').strip()
    token = request.args.get('token', '').strip()
    if not email or not token:
        return render_template_string(ERROR_HTML, message="退订链接不完整，请检查邮件中的链接。"), 400
    if not verify_token(email, token):
        return render_template_string(ERROR_HTML, message="退订链接无效或已被篡改，请重新从邮件中复制完整链接。"), 403
    if is_unsubscribed(email):
        return render_template_string(SUCCESS_HTML, email=email)
    add_unsubscribe(email, request.remote_addr)
    print(f"[UNSUBSCRIBE] {email} from {request.remote_addr} at {datetime.now()}")
    return render_template_string(SUCCESS_HTML, email=email)

@app.route('/check')
def check():
    email = request.args.get('email', '').strip()
    if not email: return jsonify({"error": "Missing email parameter"}), 400
    return jsonify({"email": email, "unsubscribed": is_unsubscribed(email), "timestamp": datetime.now().isoformat()})

@app.route('/export')
def export():
    rows = get_all_unsubscribed()
    if not rows: return "暂无退订记录\n", 200, {'Content-Type': 'text/plain; charset=utf-8'}
    lines = ["email,unsubscribed_at"]
    for email, ts in rows: lines.append(f"{email},{ts}")
    return Response("\n".join(lines), mimetype='text/csv', headers={"Content-Disposition": "attachment; filename=unsubscribed.csv"})

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
