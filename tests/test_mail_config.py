from autoapply.inbox.imap_client import ImapInbox
from autoapply.notify.mailer import smtp_configured, usable_mail_host
from autoapply.settings import Settings


def test_example_hosts_are_placeholders():
    assert usable_mail_host("imap.example.com") is False
    assert usable_mail_host("smtp.example.com") is False
    assert usable_mail_host("imap.gmail.com") is True


def test_placeholder_imap_is_not_configured():
    settings = Settings(
        agent_email_imap_host="imap.example.com",
        agent_email_imap_username="jobs-agent@example.com",
    )
    assert ImapInbox(settings).configured() is False


def test_placeholder_smtp_is_not_configured():
    settings = Settings(agent_email_smtp_host="smtp.example.com")
    assert smtp_configured(settings) is False
