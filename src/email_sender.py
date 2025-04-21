import smtplib
import json
import logging
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders

logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self, config_path: str, dry_run=False):
        self.config = self._load_config(config_path)
        self.dry_run = dry_run
        
    def _load_config(self, config_path: str) -> dict:
        """Load email configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading email config: {str(e)}")
            raise
            
    def send_email(self, attachment_path: str) -> bool:
        """Send email with the specified attachment."""
        try:
            logger.info(f"Preparing to send email with attachment: {attachment_path}")
            
            # Create message container
            msg = MIMEMultipart()
            msg['From'] = self.config['from_email']
            msg['To'] = self.config['to_email']
            msg['Subject'] = self.config.get('subject', 'Your DayNews Digest')
            msg['Date'] = formatdate(localtime=True)
            
            # Attach message body
            msg.attach(MIMEText(self.config.get('message_body', 'Here is your daily news digest.'), 'plain'))
            
            # Attach the file
            attachment = self._create_attachment(attachment_path)
            msg.attach(attachment)
            
            if self.dry_run:
                logger.info(f"DRY RUN: Would send email from {self.config['from_email']} to {self.config['to_email']} with subject '{msg['Subject']}'")
                logger.info(f"DRY RUN: Email would contain attachment: {os.path.basename(attachment_path)}")
                return True
                
            # Connect to SMTP server and send email
            with smtplib.SMTP(self.config['smtp_server'], self.config['smtp_port']) as smtp:
                if self.config.get('use_tls', True):
                    smtp.starttls()
                
                smtp.login(self.config['username'], self.config['password'])
                smtp.sendmail(self.config['from_email'], self.config['to_email'], msg.as_string())
                
            logger.info(f"Email sent successfully to {self.config['to_email']}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def _create_attachment(self, file_path: str) -> MIMEBase:
        """Create an email attachment from a file."""
        with open(file_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="{os.path.basename(file_path)}"'
        )
        return part
