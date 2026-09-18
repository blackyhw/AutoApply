from pathlib import Path

from autoapply.domain.models import MatchDecision, Profile
from autoapply.generator.blocks import BlockCatalog
from autoapply.generator.cover_letter import ApplicationGenerator, CoverLetterRenderer
from autoapply.generator.cv_assembler import CvAssembler
from autoapply.generator.pdf import render_cv_pdf

ROOT = Path(__file__).resolve().parents[1]


def test_render_cv_pdf(tmp_path: Path):
    path = tmp_path / "cv.pdf"
    render_cv_pdf("Nombre Apellido\nPython developer", path)
    data = path.read_bytes()
    assert data.startswith(b"%PDF")
    assert path.stat().st_size > 100


def test_generator_writes_pdf(tmp_path: Path):
    catalog = BlockCatalog.from_yaml(ROOT / "config" / "cv_blocks.example.yaml")
    renderer = CoverLetterRenderer.from_path(ROOT / "config" / "cover_letter.template.txt")
    generator = ApplicationGenerator(CvAssembler(catalog), renderer)
    profile = Profile(full_name="Ada", dedicated_email="jobs-agent@example.com")
    decision = MatchDecision(
        score=0.9,
        should_apply=True,
        selected_block_ids=["header", "summary_backend"],
        cover_letter_fields={"role": "Backend", "company": "Acme", "matching_skills_sentence": "Python."},
    )
    package = generator.build(decision, profile, pdf_path=tmp_path / "out.pdf")
    assert package.cv_pdf_path
    assert Path(package.cv_pdf_path).read_bytes().startswith(b"%PDF")
    assert package.candidate_email == "jobs-agent@example.com"
