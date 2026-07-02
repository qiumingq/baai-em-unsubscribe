"""
阿里云邮箱批量发送 - 退订功能集成示例
将此代码集成到你现有的发送脚本中即可
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hmac
import hashlib
import urllib.parse

# ==================== 配置区（必须修改）====================
# 1. 必须与 Render 服务上设置的 SECRET_KEY 完全一致
SECRET_KEY = "baai-unsubscribe-secret-2024-change-this"

# 2. Render 部署后获得的域名（示例，替换为你自己的）
UNSUBSCRIBE_BASE_URL = "https://baai-unsubscribe.onrender.com"

# 3. 阿里云企业邮箱 SMTP 配置
SMTP_HOST = "smtp.qiye.aliyun.com"  # 或 smtp.mxhichina.com
SMTP_PORT = 465
SMTP_USER = "your_email@baai.ac.cn"
SMTP_PASS = "your_password_or_app_password"

# 4. 发件人地址
FROM_ADDR = "your_email@baai.ac.cn"

# ==================== 退订链接生成 ====================
def generate_unsubscribe_link(email):
    """
    生成带签名的退订链接
    阿里云邮箱要求的格式: https://xxx.onrender.com/unsubscribe?email=xxx&token=xxx
    """
    token = hmac.new(
        SECRET_KEY.encode('utf-8'),
        email.lower().strip().encode('utf-8'),
        hashlib.sha256
    ).hexdigest()[:16]
    params = urllib.parse.urlencode({'email': email, 'token': token})
    return f"{UNSUBSCRIBE_BASE_URL}/unsubscribe?{params}"

# ==================== 发送单封邮件 ====================
def send_email(to_addr, subject, html_body):
    """
    发送一封符合阿里云邮箱反垃圾要求的邮件
    包含 List-Unsubscribe 头和正文退订链接
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_ADDR
    msg['To'] = to_addr

    # 生成退订链接
    unsub_link = generate_unsubscribe_link(to_addr)

    # ===== 关键：阿里云要求的 List-Unsubscribe 邮件头 =====
    # 格式必须是 <URL>，用尖括号包裹
    msg['List-Unsubscribe'] = f'<{unsub_link}>'

    # ===== 关键：支持一键退订（Gmail/阿里邮箱会显示"取消订阅"按钮）=====
    msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'

    # ===== 邮件正文：底部添加可见的退订链接 =====
    # 这是阿里云反垃圾系统的另一项要求：收件人必须能在邮件正文中找到退订方式
    full_html = html_body + f"""
    <div style="margin-top:40px;padding-top:20px;border-top:1px solid #e5e7eb;color:#999;font-size:12px;text-align:center;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
        <p>北京智源人工智能研究院</p>
        <p>地址：北京市海淀区成府路...</p>
        <p style="margin-top:12px;">
            如您不希望继续收到此类邮件，请<a href="{unsub_link}" style="color:#666;text-decoration:underline;">点击此处退订</a>
        </p>
    </div>
    """

    msg.attach(MIMEText(full_html, 'html', 'utf-8'))

    # 发送
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_ADDR, to_addr, msg.as_string())

    print(f"[SENT] {to_addr} | 退订链接已嵌入")


# ==================== 批量发送示例 ====================
if __name__ == '__main__':
    # 示例：发送给一位学者
    recipient = "professor@example.edu"
    subject = "邀请您参加智源研究院学术论坛"

    body = """
    <div style="max-width:600px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#333;line-height:1.6;">
        <h2 style="color:#1f2937;">尊敬的教授，您好</h2>
        <p>北京智源人工智能研究院诚挚邀请您参加...</p>
        <p>期待您的回复。</p>
    </div>
    """

    send_email(recipient, subject, body)
