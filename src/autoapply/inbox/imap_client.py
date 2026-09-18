from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import imaplib
import email
from email.message import Message
from email.utils import parseaddr

from autoapply.errors import ConfigurationError
from autoapply.notify.mailer import usable_mail_host
from autoapply.settings import Settings


@dataclass(frozen=True, slots=True)
class IncomingEmail:
    message_id: str
    subject: str
    from_addr: str
    body: str
    ics_text: str | None = None
    imap_uid: str | None = None

    @property
    def from_email(self) -> str:
        return parseaddr(self.from_addr)[1]


class ImapInbox:
    def __init__(self, settings: Settings):
        self.settings = settings

    def configured(self) -> bool:
        return usable_mail_host(self.settings.agent_email_imap_host) and bool(
            self.settings.agent_email_imap_username
        )

    def fetch_unseen(self, limit: int = 40) -> list[IncomingEmail]:
        if not self.configured():
            raise ConfigurationError("IMAP is not configured for the dedicated mailbox")
        mailbox = imaplib.IMAP4_SSL(self.settings.agent_email_imap_host, self.settings.agent_email_imap_port)
        try:
            mailbox.login(self.settings.agent_email_imap_username, self.settings.agent_email_imap_password)
            mailbox.select("INBOX")
            _, data = mailbox.search(None, "UNSEEN")
            ids = data[0].split() if data and data[0] else []
            emails: list[IncomingEmail] = []
            for msg_id in ids[:limit]:
                _, payload = mailbox.fetch(msg_id, "(RFC822)")
                if not payload or not payload[0]:
                    continue
                raw = payload[0][1]
                parsed = _parse_message(email.message_from_bytes(raw), imap_uid=msg_id.decode("ascii", errors="replace"))
                emails.append(parsed)
            return emails
        finally:
            try:
                mailbox.logout()
            except Exception:
                pass

    def mark_seen(self, uids: list[str]) -> None:
        if not uids or not self.configured():
            return
        mailbox = imaplib.IMAP4_SSL(self.settings.agent_email_imap_host, self.settings.agent_email_imap_port)
        try:
            mailbox.login(self.settings.agent_email_imap_username, self.settings.agent_email_imap_password)
            mailbox.select("INBOX")
            for uid in uids:
                mailbox.store(uid.encode("ascii"), "+FLAGS", "\\Seen")
        finally:
            try:
                mailbox.logout()
            except Exception:
                pass


def _parse_message(message: Message, imap_uid: str | None = None) -> IncomingEmail:
    subject = message.get("Subject", "")
    from_addr = message.get("From", "")
    message_id = message.get("Message-ID", subject)
    body_parts: list[str] = []
    ics_text = None
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            payload = part.get_payload(decode=True) or b""
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/calendar" or (part.get_filename() or "").endswith(".ics"):
                ics_text = text
            elif ctype == "text/plain":
                body_parts.append(text)
    else:
        payload = message.get_payload(decode=True) or b""
        body_parts.append(payload.decode(message.get_content_charset() or "utf-8", errors="replace"))
    return IncomingEmail(
        message_id=str(message_id),
        subject=str(subject),
        from_addr=str(from_addr),
        body="\n".join(body_parts),
        ics_text=ics_text,
        imap_uid=imap_uid,
    )


def iter_bodies(emails: Iterable[IncomingEmail]) -> Iterable[IncomingEmail]:
    yield from emails
