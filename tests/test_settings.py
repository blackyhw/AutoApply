from autoapply.settings import Settings


def test_enabled_collectors_accepts_csv_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "ENABLED_COLLECTORS=file_feed,linkedin,computrabajo,indeed\n",
        encoding="utf-8",
    )
    settings = Settings()
    assert settings.enabled_collectors == [
        "file_feed",
        "linkedin",
        "computrabajo",
        "indeed",
    ]


def test_enabled_collectors_accepts_json_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        'ENABLED_COLLECTORS=["file_feed", "indeed"]\n',
        encoding="utf-8",
    )
    settings = Settings()
    assert settings.enabled_collectors == ["file_feed", "indeed"]
