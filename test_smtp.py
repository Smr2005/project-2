import asyncio
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
import os
from dotenv import load_dotenv

load_dotenv()

async def test_email():
    conf = ConnectionConfig(
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
        MAIL_FROM=os.getenv("MAIL_FROM"),
        MAIL_PORT=465,
        MAIL_SERVER="smtp.gmail.com",
        MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME"),
        MAIL_STARTTLS=False,
        MAIL_SSL_TLS=True,
        USE_CREDENTIALS=True
    )
    
    message = MessageSchema(
        subject="QueryVault SMTP Test",
        recipients=[os.getenv("MAIL_FROM")], # Send to self
        body="QueryVault recovery signal test successful. SMTP is fully operational.",
        subtype=MessageType.plain
    )
    
    fm = FastMail(conf)
    print(f"Attempting to send test email via {conf.MAIL_SERVER}...")
    try:
        await fm.send_message(message)
        print("Email sent successfully!")
    except Exception as e:
        print(f"Email failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_email())
