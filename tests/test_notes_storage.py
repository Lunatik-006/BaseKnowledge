from pathlib import Path

from libs.storage import Note, NotesStorage


def test_save_read_and_moc(tmp_path: Path) -> None:
    vault_path = tmp_path / "vault"
    storage = NotesStorage(vault_path)

    note1 = Note(
        slug="note1",
        title="Note 1",
        tags=["python", "ai"],
        meta={"created": "2024-01-01"},
        body="Summary 1.",
    )
    storage.save_note(note1)

    note2 = Note(
        slug="note2",
        title="Note 2",
        tags=["python"],
        meta={},
        body="Summary 2.",
    )
    storage.save_note(note2)

    read1 = storage.read_note("note1")
    assert "См. также" in read1.body
    assert "[[note2]]" in read1.body

    read2 = storage.read_note("note2")
    assert "[[note1]]" in read2.body

    moc_content = (vault_path / "00_MOC" / "topics_index.md").read_text()
    assert "## python" in moc_content
    assert "[[note1]]" in moc_content
    assert "[[note2]]" in moc_content
    assert "## ai" in moc_content
    assert moc_content.count("[[note1]]") >= 2  # listed under python and ai


def test_export_zip(tmp_path: Path) -> None:
    vault_path = tmp_path / "vault"
    storage = NotesStorage(vault_path)
    storage.save_note(Note(slug="n1", title="N1", tags=[], meta={}, body="body"))

    zip_path = tmp_path / "vault.zip"
    storage.export_zip(zip_path)

    assert zip_path.exists()
    import zipfile

    with zipfile.ZipFile(zip_path, "r") as zf:
        assert "10_Notes/n1.md" in zf.namelist()
