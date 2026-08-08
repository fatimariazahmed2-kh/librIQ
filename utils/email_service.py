from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib


class EmailService:
  """Automated email delivery engine for book return reminders and fine alerts."""

  SMTP_SERVER = "smtp.gmail.com"
  SMTP_PORT = 587

  @staticmethod
  def send_email(
      sender_email: str,
      sender_password: str,
      recipient_email: str,
      subject: str,
      body: str,
  ):
    """Sends a formatted email using SMTP TSL authentication."""
    if not sender_email or not sender_password or not recipient_email:
      return {
          "success": False,
          "message": "Missing email credentials or recipient address.",
      }

    try:
      msg = MIMEMultipart()
      msg["From"] = sender_email
      msg["To"] = recipient_email
      msg["Subject"] = subject
      msg.attach(MIMEText(body, "plain"))

      server = smtplib.SMTP(EmailService.SMTP_SERVER, EmailService.SMTP_PORT)
      server.starttls()
      server.login(sender_email, sender_password)
      server.send_message(msg)
      server.quit()

      return {"success": True, "message": "Email sent successfully!"}
    except Exception as e:
      return {"success": False, "message": f"Failed to send email: {str(e)}"}

  @classmethod
  def send_return_reminder(
      cls,
      sender_email: str,
      sender_password: str,
      student_email: str,
      student_name: str,
      department: str,
      book_title: str,
      return_date: str,
  ):
    """Sends a 1-day advance return reminder to student."""
    subject = "Reminder: Book Return Due Tomorrow - Smart Library System"
    body = (
        f"Dear {student_name},\n\n"
        f"This is an automated reminder from the Library Department"
        f" ({department}).\n"
        f"The book '{book_title}' issued under your record is scheduled for"
        f" return on {return_date}.\n\n"
        "Please make sure to return or renew the book on time to avoid late fine"
        " charges.\n\n"
        "Regards,\n"
        "Library Management Team"
    )
    return cls.send_email(
        sender_email, sender_password, student_email, subject, body
    )

  @classmethod
  def send_fine_warning(
      cls,
      sender_email: str,
      sender_password: str,
      student_email: str,
      student_name: str,
      department: str,
      fine_amount: float,
  ):
    """Sends fine threshold warning when fine reaches Rs. 300 or more."""
    subject = "Official Warning: Overdue Library Fine Notice"
    body = (
        f"Dear {student_name} ({department}),\n\n"
        f"Your overdue book penalty has accumulated to Rs. {fine_amount:.2f}.\n"
        "Please settle your outstanding fine at the library counter as soon as"
        " possible.\n\n"
        "Note: Accumulating a fine of Rs. 500 will freeze your library record,"
        " requiring payment alongside official university fees.\n\n"
        "Regards,\n"
        "Library Administration"
    )
    return cls.send_email(
        sender_email, sender_password, student_email, subject, body
    )