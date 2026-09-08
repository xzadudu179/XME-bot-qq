import aiosmtplib
from email.message import EmailMessage
from keys import MAIL_USERNAME, MAIL_PASSWORD, SMTP_HOST
from nonebot.log import logger

SMTP_PORT = 465

async def send_bot_email(
    receiver: str,
    subject: str,
    content: str,
) -> bool:
    message = EmailMessage()
    message["From"] = MAIL_USERNAME
    message["To"] = receiver
    message["Subject"] = subject
    message.set_content(content)
    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=MAIL_USERNAME,
            password=MAIL_PASSWORD,
            start_tls=True,
        )
        return True

    except Exception as e:
        logger.exception(f"邮件发送失败: {e}")
        return False