"""Build ``passages.html``, the passage index that replaces ``Resource-Passage Names``.

Rows come from ``story_graph.json`` (passages and links) and
``nanoif.twee.files`` (file, line, tags). Writer, date and day are inferred
from the file name (``<INITIALS>-<YYYYMMDD>.twee``) and from the file's
``:: Day <N> <INITIALS>`` passage when there is one. The Loose ends list above the
table is read from ``src/`` because ``story_graph.json`` has no link lines.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path

from nanoif.errors import BuildError
from nanoif.formats.common import html_environment
from nanoif.schemas.artifacts import load_artifact
from nanoif.twee.files import (
    DAY_PASSAGE_RE,
    PassageLocation,
    find_twee_files,
    link_line,
    parse_prose_file_name,
    passage_locations,
    relative_file,
    split_twee,
)
from nanoif.twee.links import find_links
from nanoif.twee.parse import StoryGraph
from nanoif.twee.prose import UNWRITTEN, word_count


@dataclass(frozen=True)
class PassageRow:
    """One row of the passage index.

    Attributes:
        name: Passage name.
        anchor: HTML id for the row.
        file: Repository-relative source file, or None when not found in ``src/``.
        line: Line of the passage header, or None.
        initials: Writer initials, when inferable.
        date: File date as ``YYYY-MM-DD``, when inferable.
        day: Day number, when inferable.
        tags: Passage tags.
        links_out: Passages this one links to.
        links_in: Passages that link to this one.
        words: Words a reader sees.
    """

    name: str
    anchor: str
    file: str | None
    line: int | None
    initials: str | None
    date: str | None
    day: int | None
    tags: tuple[str, ...]
    links_out: tuple[str, ...]
    links_in: tuple[str, ...]
    words: int


@dataclass(frozen=True)
class LooseEnd:
    """One choice that points at :data:`~nanoif.twee.prose.UNWRITTEN`.

    Attributes:
        text: The choice as the reader sees it.
        passage: The passage holding the choice.
        file: Repository-relative source file.
        line: Line of the link in that file.
        initials: Writer initials of the file, when inferable.
        day: Day number of the file, when inferable.
    """

    text: str
    passage: str
    file: str
    line: int
    initials: str | None
    day: int | None


@dataclass(frozen=True)
class PassagesResult:
    """What ``build_passages`` wrote.

    Attributes:
        html_path: The page.
        passage_count: Rows on the page.
        file_count: Distinct source files.
    """

    html_path: Path
    passage_count: int
    file_count: int


def _file_days(locations: Mapping[str, PassageLocation]) -> dict[Path, tuple[int, str]]:
    """Map each file to the day and initials of its first ``Day <N> <INITIALS>`` passage."""
    days: dict[Path, tuple[int, str, int]] = {}
    for name, location in locations.items():
        match = DAY_PASSAGE_RE.match(name)
        if match is None:
            continue
        current = days.get(location.file)
        if current is None or location.line < current[2]:
            days[location.file] = (int(match.group("day")), match.group("initials"), location.line)
    return {file: (day, initials) for file, (day, initials, _line) in days.items()}


def _writer(
    file: Path, file_days: Mapping[Path, tuple[int, str]]
) -> tuple[str | None, str | None, int | None]:
    """Return the initials, date and day a file's name and ``Day`` passage give."""
    parsed = parse_prose_file_name(file.name)
    initials, date = (parsed.initials, parsed.date) if parsed else (None, None)
    day: int | None = None
    if file in file_days:
        day, day_initials = file_days[file]
        initials = initials or day_initials
    return initials, date, day


def loose_ends(src_dir: Path, repo_root: Path) -> list[LooseEnd]:
    """List every link to the ``Unwritten`` passage under ``src_dir``.

    Args:
        src_dir: The story source.
        repo_root: Root that file paths are shown relative to.

    Returns:
        One entry per link, sorted by file then line.

    Raises:
        BuildError: ``src_dir`` does not exist or a ``.twee`` file cannot be read as UTF-8.
    """
    if not src_dir.is_dir():
        raise BuildError(f"story source not found: {src_dir}")
    root = repo_root.resolve()
    found: list[tuple[Path, str, int, str]] = []
    for path in find_twee_files(src_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise BuildError(f"cannot read {path.relative_to(root)} for loose ends: {exc}") from exc
        for passage in split_twee(text):
            for link in find_links(passage.text):
                if link.target == UNWRITTEN:
                    found.append((path, passage.name, link_line(passage, link), link.text))
    file_days = _file_days(passage_locations(src_dir))
    ends = []
    for path, passage, line, text in found:
        initials, _date, day = _writer(path, file_days)
        file = path.relative_to(root).as_posix()
        ends.append(LooseEnd(text, passage, file, line, initials, day))
    return sorted(ends, key=lambda end: (end.file, end.line))


def passage_rows(
    story_graph: StoryGraph, locations: Mapping[str, PassageLocation], repo_root: Path
) -> list[PassageRow]:
    """Compute the passage index rows.

    Args:
        story_graph: A parsed story.
        locations: Passage name to where it is declared.
        repo_root: Root that file paths are shown relative to.

    Returns:
        Rows sorted by file then line; passages with no known file come last.
    """
    incoming: dict[str, list[str]] = {name: [] for name in story_graph["passages"]}
    for source, passage in story_graph["passages"].items():
        for target in passage["links"]:
            if target in incoming and source not in incoming[target]:
                incoming[target].append(source)
    file_days = _file_days(locations)
    rows: list[PassageRow] = []
    for name, passage in story_graph["passages"].items():
        location = locations.get(name)
        initials, date, day = _writer(location.file, file_days) if location else (None, None, None)
        rows.append(
            PassageRow(
                name=name,
                anchor="",
                file=relative_file(location, repo_root) if location else None,
                line=location.line if location else None,
                initials=initials,
                date=date,
                day=day,
                tags=location.tags if location else (),
                links_out=tuple(passage["links"]),
                links_in=tuple(sorted(incoming[name])),
                words=word_count(passage["content"]),
            )
        )
    rows.sort(key=lambda row: (row.file is None, row.file or "", row.line or 0, row.name))
    return [replace(row, anchor=f"p{index}") for index, row in enumerate(rows, 1)]


def render_html(
    story_title: str, rows: list[PassageRow], ends: list[LooseEnd], generated_at: datetime
) -> str:
    """Render ``passages.html``.

    Args:
        story_title: Shown in the header.
        rows: From :func:`passage_rows`.
        ends: From :func:`loose_ends`.
        generated_at: Shown in the header.

    Returns:
        The HTML page.
    """
    anchors = {row.name: row.anchor for row in rows}
    return (
        html_environment()
        .get_template("passages.html.jinja2")
        .render(
            story_title=story_title,
            rows=rows,
            loose_ends=ends,
            anchors=anchors,
            file_count=len({row.file for row in rows if row.file}),
            generated_date=generated_at.strftime("%Y-%m-%d %H:%M"),
        )
    )


def build_passages(
    src_dir: Path,
    story_graph_path: Path,
    output_dir: Path,
    generated_at: datetime | None = None,
) -> PassagesResult:
    """Write ``passages.html``.

    Args:
        src_dir: Story source (for files, lines and tags).
        story_graph_path: ``story_graph.json`` from ``nanoif build core``.
        output_dir: Where the page goes.
        generated_at: Timestamp shown on the page; defaults to now.

    Returns:
        The page written and its counts.

    Raises:
        BuildError: If the story graph is missing or not valid JSON, or ``src/`` cannot be
            read for the loose ends.
        ArtifactValidationError: If it does not match its schema.
    """
    story_graph = load_artifact(story_graph_path, "story_graph")
    repo_root = src_dir.resolve().parent
    ends = loose_ends(src_dir, repo_root)
    rows = passage_rows(story_graph, passage_locations(src_dir), repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / "passages.html"
    html_path.write_text(
        render_html(
            story_graph["metadata"]["story_title"], rows, ends, generated_at or datetime.now()
        ),
        encoding="utf-8",
    )
    return PassagesResult(
        html_path=html_path,
        passage_count=len(rows),
        file_count=len({row.file for row in rows if row.file}),
    )
