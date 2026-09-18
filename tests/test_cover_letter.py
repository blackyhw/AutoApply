from autoapply.domain.models import MatchDecision, Profile
from autoapply.errors import TemplateError
from autoapply.generator.cover_letter import CoverLetterRenderer


def test_cover_letter_fills_placeholders_only(tmp_path):
    template = tmp_path / "letter.txt"
    template.write_text(
        "Asunto: Postulación — {role} en {company}\n\nHola {recruiter_name},\n{matching_skills_sentence}\n{candidate_name}\n{dedicated_email}\n",
        encoding="utf-8",
    )
    renderer = CoverLetterRenderer.from_path(template)
    profile = Profile(full_name="Ada", dedicated_email="jobs-agent@example.com")
    subject, body = renderer.render(
        {
            "role": "Backend",
            "company": "Acme",
            "matching_skills_sentence": "Trabajo con Python.",
            "invented_field": "should be ignored",
        },
        profile,
    )
    assert subject == "Postulación — Backend en Acme"
    assert "Trabajo con Python." in body
    assert "should be ignored" not in body
    assert "Ada" in body


def test_unknown_placeholder_is_rejected():
    try:
        CoverLetterRenderer("Hola {free_text}\n")
        raise AssertionError("expected TemplateError")
    except TemplateError:
        pass


def test_match_decision_roundtrip_fields():
    decision = MatchDecision(
        score=0.9,
        should_apply=True,
        selected_block_ids=["header"],
        cover_letter_fields={"role": "Dev", "company": "X"},
    )
    assert decision.cover_letter_fields["role"] == "Dev"
