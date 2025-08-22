from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List
from collections import defaultdict
import re
from zipfile import ZipFile


@dataclass
class Note:
    """Representation of a single note."""

    slug: str
    title: str
    tags: List[str]
    meta: Dict[str, Any] = field(default_factory=dict)
    body: str = ""


class NotesStorage:
    """File system based storage for Markdown notes with YAML frontmatter."""

    def __init__(self, vault_path: Path) -> None:
        self.vault_path = Path(vault_path)
        self.notes_dir = self.vault_path / "10_Notes"
        self.moc_dir = self.vault_path / "00_MOC"
        self.moc_file = self.moc_dir / "topics_index.md"

    # ------------------------------------------------------------------
    # public API
    def save_note(self, note: Note) -> None:
        """Save note to disk and update cross-links and MOC."""

        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.moc_dir.mkdir(parents=True, exist_ok=True)

        self._write_note_file(note)
        # regenerate cross links for all notes including newly saved
        self._generate_crosslinks()
        # update topics index
        self._update_moc()

    def read_note(self, slug: str) -> Note:
        """Read note from disk by slug."""

        path = self.notes_dir / f"{slug}.md"
        text = path.read_text(encoding="utf-8")
        if text.startswith("---"):
            _, fm, body = text.split("---", 2)
            front = _load_yaml(fm)
            body = body.lstrip("\n")
        else:
            front, body = {}, text
        return Note(
            slug=slug,
            title=front.get("title", ""),
            tags=front.get("tags", []),
            meta=front.get("meta", {}),
            body=body.rstrip(),
        )

    def list_notes(self) -> List[Note]:
        """Return all notes stored in the vault."""

        return list(self._load_all_notes().values())

    def export_zip(self, output_path: Path) -> None:
        """Export entire vault as ZIP archive."""

        output_path = Path(output_path)
        with ZipFile(output_path, "w") as zf:
            for file in self.vault_path.rglob("*"):
                if file.is_file():
                    zf.write(file, file.relative_to(self.vault_path))

    # ------------------------------------------------------------------
    # helpers
    def _write_note_file(self, note: Note) -> None:
        front = {"title": note.title, "tags": note.tags}
        if note.meta:
            front["meta"] = note.meta
        fm = _dump_yaml(front)
        path = self.notes_dir / f"{note.slug}.md"
        content = f"---\n{fm}\n---\n\n{note.body.rstrip()}\n"
        path.write_text(content, encoding="utf-8")

    def _load_all_notes(self) -> Dict[str, Note]:
        notes: Dict[str, Note] = {}
        if not self.notes_dir.exists():
            return notes
        for file in self.notes_dir.glob("*.md"):
            slug = file.stem
            notes[slug] = self.read_note(slug)
        return notes

    def _generate_crosslinks(self) -> None:
        notes = self._load_all_notes()
        tag_map: Dict[str, set[str]] = defaultdict(set)
        for slug, note in notes.items():
            for tag in note.tags:
                tag_map[tag].add(slug)

        for slug, note in notes.items():
            related: set[str] = set()
            for tag in note.tags:
                related.update(tag_map[tag])
            related.discard(slug)

            base_body = re.sub(
                r"\n## См\. также\n(?:- \[\[.*?\]\]\n?)*",
                "",
                note.body,
                flags=re.MULTILINE,
            ).rstrip()

            if related:
                links = "\n".join(f"- [[{r}]]" for r in sorted(related))
                note.body = f"{base_body}\n\n## См. также\n{links}\n"
            else:
                note.body = f"{base_body}\n"
            self._write_note_file(note)

    def _update_moc(self) -> None:
        notes = self._load_all_notes()
        tag_map: Dict[str, List[Note]] = defaultdict(list)
        for note in notes.values():
            for tag in note.tags:
                tag_map[tag].append(note)

        lines = ["# Topics Index", ""]
        for tag in sorted(tag_map):
            lines.append(f"## {tag}")
            for note in sorted(tag_map[tag], key=lambda n: n.slug):
                lines.append(f"- [[{note.slug}]] {note.title}")
            lines.append("")

        self.moc_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


# ----------------------------------------------------------------------
# minimal YAML helpers (since PyYAML is not installed)

def _dump_yaml(data: Dict[str, Any]) -> str:
    lines: List[str] = []
    for key, value in data.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, dict):
            lines.append(f"{key}:")
            for k, v in value.items():
                lines.append(f"  {k}: {v}")
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines)


def _load_yaml(text: str) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    lines = [ln.rstrip() for ln in text.strip().splitlines() if ln.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val == "":
                # list or dict
                i += 1
                items: List[str] = []
                subitems: Dict[str, str] = {}
                while i < len(lines) and lines[i].startswith("  "):
                    subline = lines[i].strip()
                    if subline.startswith("-"):
                        items.append(subline[2:].strip())
                    elif ":" in subline:
                        sk, sv = subline.split(":", 1)
                        subitems[sk.strip()] = sv.strip()
                    i += 1
                if items:
                    data[key] = items
                else:
                    data[key] = subitems
                continue
            else:
                data[key] = val
        i += 1
    return data
