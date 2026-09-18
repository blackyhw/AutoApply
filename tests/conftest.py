from pathlib import Path

import pytest

from autoapply.generator.blocks import BlockCatalog
from autoapply.persistence.db import make_session_factory
from autoapply.persistence.repositories import Repository
from autoapply.settings import Settings


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path: Path) -> Repository:
    factory = make_session_factory(str(tmp_path / "test.db"))
    return Repository(factory())


@pytest.fixture
def catalog() -> BlockCatalog:
    return BlockCatalog.from_yaml(ROOT / "config" / "cv_blocks.example.yaml")


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        sqlite_path=tmp_path / "autoapply.db",
        heartbeat_path=tmp_path / "heartbeat.json",
        profile_path=ROOT / "config" / "profile.example.yaml",
        cv_blocks_path=ROOT / "config" / "cv_blocks.example.yaml",
        cover_letter_template_path=ROOT / "config" / "cover_letter.template.txt",
        file_feed_path=ROOT / "data" / "samples" / "vacancies.json",
        enabled_collectors=["file_feed"],
        dry_run=True,
        gemini_api_key="",
        groq_api_key="",
        generated_dir=tmp_path / "generated",
    )
