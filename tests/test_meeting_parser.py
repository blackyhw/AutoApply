from datetime import datetime

from autoapply.domain.enums import MeetingDisposition
from autoapply.inbox.parser import MeetingParser


def test_parses_ics_invite():
    parser = MeetingParser(llm=None)
    ics = "BEGIN:VCALENDAR\nDTSTART:20260920T140000Z\nEND:VCALENDAR\n"
    proposal = parser.parse_heuristics(
        subject="Entrevista Backend",
        body="Nos vemos acá https://meet.google.com/abc-defg-hij",
        ics_text=ics,
    )
    assert proposal is not None
    assert proposal.disposition is MeetingDisposition.CONFIRMED
    assert proposal.starts_at == datetime(2026, 9, 20, 14, 0, 0)
    assert proposal.meeting_url.endswith("abc-defg-hij")


def test_ignores_unrelated_email():
    parser = MeetingParser(llm=None)
    assert parser.parse_heuristics(subject="Gracias por postularte", body="Recibimos tu CV.") is None
