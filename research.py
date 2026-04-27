#!/usr/bin/env python3
"""research.py — central research knowledge base.

Subcommands (v0.1): init, save, search, list, link, index, archive
Subcommands (v0.2): score, verify
Subcommands (v0.3): review, compress
Subcommands (v0.4): table-profile, db-profile, analyze-plan, analyze-run
Subcommands (v0.5): sync
Subcommands (bridges): extract (Omniparse)

Canonical markdown lives under a configurable content root (default:
~/dev/research). SQLite FTS5 and other operational state can live under a
separate configurable index root. Claude Code's WebFetch/Read are
assumed to have already extracted source content into entry files; this
script persists, queries, scores, and verifies.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ---------- Paths ----------

DEFAULT_BASE_DIR = Path.home() / "dev" / "research"
BASE_DIR = Path(os.environ.get("RESEARCH_BASE_DIR", DEFAULT_BASE_DIR)).expanduser()
CONTENT_DIR = Path(os.environ.get("RESEARCH_CONTENT_DIR", BASE_DIR)).expanduser()
INDEX_DIR = Path(os.environ.get("RESEARCH_INDEX_DIR", BASE_DIR)).expanduser()
DB_PATH = INDEX_DIR / ".db.sqlite3"
PLUGIN_ROOT = Path(__file__).resolve().parent
DATA_DIR = PLUGIN_ROOT / "data"
DEFAULT_PROJECTS_DIR = Path.home() / "dev" / "git-folder"
GIT_FOLDER = Path(os.environ.get("RESEARCH_PROJECTS_DIR", DEFAULT_PROJECTS_DIR)).expanduser()


# ---------- Schema ----------

SCHEMA = """
CREATE TABLE IF NOT EXISTS entries (
  id INTEGER PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  path TEXT NOT NULL,
  title TEXT,
  topics TEXT,
  projects TEXT,
  tags TEXT,
  sources TEXT,
  status TEXT,
  workflow TEXT,
  created TEXT,
  reviewed TEXT,
  topic_velocity TEXT,
  confidence TEXT,
  corroboration INTEGER DEFAULT 0,
  tldr TEXT,
  notes TEXT,
  raw TEXT,
  verification TEXT,
  inbound TEXT
);

CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
  slug, title, tldr, notes, raw,
  content='entries', content_rowid='id',
  tokenize='porter unicode61'
);

CREATE TRIGGER IF NOT EXISTS entries_ai AFTER INSERT ON entries BEGIN
  INSERT INTO entries_fts(rowid, slug, title, tldr, notes, raw)
  VALUES (new.id, new.slug, new.title, new.tldr, new.notes, new.raw);
END;

CREATE TRIGGER IF NOT EXISTS entries_ad AFTER DELETE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, slug, title, tldr, notes, raw)
  VALUES ('delete', old.id, old.slug, old.title, old.tldr, old.notes, old.raw);
END;

CREATE TRIGGER IF NOT EXISTS entries_au AFTER UPDATE ON entries BEGIN
  INSERT INTO entries_fts(entries_fts, rowid, slug, title, tldr, notes, raw)
  VALUES ('delete', old.id, old.slug, old.title, old.tldr, old.notes, old.raw);
  INSERT INTO entries_fts(rowid, slug, title, tldr, notes, raw)
  VALUES (new.id, new.slug, new.title, new.tldr, new.notes, new.raw);
END;

CREATE TABLE IF NOT EXISTS domain_scores (
  domain TEXT PRIMARY KEY,
  tier TEXT NOT NULL,
  reason TEXT,
  set_by TEXT,
  set_date TEXT
);
"""


# ---------- Utilities ----------

def db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def content_path(*parts: str) -> Path:
    return CONTENT_DIR.joinpath(*parts)


def index_path(*parts: str) -> Path:
    return INDEX_DIR.joinpath(*parts)


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def _stringify_dates(obj: Any) -> Any:
    """Recursively convert date/datetime objects to ISO strings for JSON serialization."""
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(v) for v in obj]
    return obj


def parse_frontmatter(text: str, *, fatal: bool = True) -> tuple[dict, str]:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_text, body = m.group(1), m.group(2)
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as e:
        if not fatal:
            raise ValueError(f"invalid frontmatter YAML: {e}") from e
        print(f"ERROR parsing frontmatter: {e}", file=sys.stderr)
        sys.exit(2)
    return _stringify_dates(fm), body


def dump_frontmatter(fm: dict, body: str) -> str:
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return f"---\n{fm_text}---\n{body}"


SECTION_RE = re.compile(r"^##\s+(TL;DR|Notes|Raw)\s*$", re.MULTILINE)


def split_sections(body: str) -> dict[str, str]:
    """Return {'tldr': str, 'notes': str, 'raw': str}. Missing sections -> ''."""
    parts = SECTION_RE.split(body)
    out = {"tldr": "", "notes": "", "raw": ""}
    i = 1
    while i < len(parts) - 1:
        header = parts[i]
        content = parts[i + 1].strip()
        key = {"TL;DR": "tldr", "Notes": "notes", "Raw": "raw"}[header]
        out[key] = content
        i += 2
    return out


def detect_project(cwd: Path | None = None) -> str | None:
    """If cwd is under $RESEARCH_PROJECTS_DIR/<name>/, return <name>."""
    cwd = cwd or Path.cwd()
    try:
        rel = cwd.resolve().relative_to(GIT_FOLDER.resolve())
    except ValueError:
        return None
    parts = rel.parts
    return parts[0] if parts else None


def top_level_topic(slug: str) -> str:
    return slug.split(".", 1)[0]


ETLD1_SPECIAL = {
    # Hosts where eTLD+1 alone isn't enough; keep full for scoring.
    "github.io",
    "readthedocs.io",
    "substack.com",
    "medium.com",
}


def etld1(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
    except Exception:
        return ""
    if not host:
        return ""
    # Strip port
    host = host.split(":", 1)[0]
    # Simple eTLD+1: last two labels (won't be perfect for all country TLDs but good enough)
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    # Heuristic for common two-part TLDs
    two_part_tlds = {"co.uk", "ac.uk", "gov.uk", "co.jp", "com.au", "co.nz"}
    last2 = ".".join(parts[-2:])
    last3 = ".".join(parts[-3:])
    if last2 in two_part_tlds:
        return last3
    return last2


def today_iso() -> str:
    return date.today().isoformat()


def now_iso() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z")


def ensure_layout() -> None:
    """Create the configured content and index roots if missing. Idempotent."""
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ("topics", "indices", "archive", "archive/raw", "inbox", "projects"):
        content_path(sub).mkdir(parents=True, exist_ok=True)
    for sub in ("verifier-log",):
        index_path(sub).mkdir(parents=True, exist_ok=True)
    readme = content_path("README.md")
    if not readme.exists():
        readme.write_text(
            "# Research Content Root\n\n"
            "Canonical research markdown lives in this directory. Managed by the `research` plugin.\n\n"
            "- `topics/<top>/<slug>.md` — canonical entries\n"
            "- `indices/` — auto-generated Maps of Content per topic\n"
            "- `archive/` — never-deleted moved entries (redirect stubs remain in `topics/`)\n"
            f"- SQLite index root: `{INDEX_DIR}`\n"
            f"- SQLite DB: `{DB_PATH}`\n\n"
            "Subcommands: run `python <plugin>/research.py --help`.\n"
            "Or use slash commands: `/research:search`, `/research:list`, `/research:review`, etc.\n\n"
            "## Searching\n\n"
            "```bash\n"
            "# Ranked full-text\n"
            "python <plugin>/research.py search 'chain of thought'\n\n"
            "# Or just grep\n"
            "grep -r 'chain of thought' topics/\n"
            "```\n"
        )


def ensure_db() -> None:
    conn = db_connect()
    with conn:
        conn.executescript(SCHEMA)
    conn.close()


def seed_domain_scores(refresh: bool = False) -> int:
    """Populate domain_scores from data/domain-scores-seed.json and iffy-domains.csv.

    Returns number of new/updated rows. Manual overrides (set_by='manual') are
    preserved even on refresh.
    """
    conn = db_connect()
    count = 0
    seed_json = DATA_DIR / "domain-scores-seed.json"
    if seed_json.exists():
        data = json.loads(seed_json.read_text())
        for dom, entry in data.items():
            row = conn.execute(
                "SELECT set_by FROM domain_scores WHERE domain = ?", (dom,)
            ).fetchone()
            if row and row["set_by"] == "manual" and not refresh:
                continue
            if row and row["set_by"] == "manual" and refresh:
                continue  # never clobber manual
            conn.execute(
                "INSERT OR REPLACE INTO domain_scores(domain, tier, reason, set_by, set_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (dom, entry["tier"], entry.get("reason", ""), "seed", today_iso()),
            )
            count += 1
    iffy_csv = DATA_DIR / "iffy-domains.csv"
    if iffy_csv.exists():
        with iffy_csv.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                dom = (row.get("domain") or "").strip().lower()
                if not dom:
                    continue
                existing = conn.execute(
                    "SELECT set_by FROM domain_scores WHERE domain = ?", (dom,)
                ).fetchone()
                if existing and existing["set_by"] in ("manual", "llm"):
                    continue
                conn.execute(
                    "INSERT OR REPLACE INTO domain_scores(domain, tier, reason, set_by, set_date) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (dom, "T4", f"iffy index: {row.get('reason', 'low credibility')}", "seed", today_iso()),
                )
                count += 1
    conn.commit()
    conn.close()
    return count


# ---------- init ----------

def cmd_init(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    added = seed_domain_scores(refresh=args.refresh_seeds)
    print(f"Initialized research content at {CONTENT_DIR}")
    print(f"Index root: {INDEX_DIR}")
    print(f"DB: {DB_PATH}")
    print(f"Seeded/refreshed {added} domain scores")
    return 0


# ---------- save ----------

def _slug_to_path(slug: str) -> Path:
    return content_path("topics", top_level_topic(slug), f"{slug}.md")


def _resolve_collision(slug: str, fm: dict) -> str:
    """If an entry with this slug exists with a different created date, bump -v2."""
    conn = db_connect()
    existing = conn.execute(
        "SELECT created FROM entries WHERE slug = ?", (slug,)
    ).fetchone()
    conn.close()
    if not existing:
        return slug
    if existing["created"] == fm.get("created"):
        return slug  # same entry, update
    # Collision: find next -vN
    base = re.sub(r"-v\d+$", "", slug)
    n = 2
    while True:
        candidate = f"{base}-v{n}"
        conn = db_connect()
        row = conn.execute(
            "SELECT 1 FROM entries WHERE slug = ?", (candidate,)
        ).fetchone()
        conn.close()
        if not row:
            return candidate
        n += 1


def _summary_from_tldr(tldr: str, limit: int = 120) -> str:
    """Extract a single-line summary from a TL;DR section. First sentence or `limit` chars."""
    if not tldr:
        return ""
    text = " ".join(tldr.strip().split())
    # First sentence
    m = re.search(r"^(.+?[.!?])(?:\s|$)", text)
    if m:
        sent = m.group(1).strip()
        if len(sent) <= limit:
            return sent
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "\u2026"


def _managed_projects_dir() -> Path:
    """Return the content-root projects dir for plugin-managed symlinks."""
    return content_path("projects")


def _linked_projects_registry_path() -> Path:
    """Return the index-root linked-project registry path."""
    return index_path(".linked-projects.json")


def _read_linked_projects_registry() -> dict:
    """Load the linked-projects registry as a dict. Returns {} if absent or malformed."""
    p = _linked_projects_registry_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _write_linked_projects_registry(registry: dict) -> None:
    """Write the registry deterministically (sorted keys, stable output)."""
    p = _linked_projects_registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, indent=2, sort_keys=True) + "\n")


_V030_ARTIFACT_NOTE_SHOWN: set[str] = set()


def _note_v030_artifacts(project_path: Path) -> None:
    """Print a one-time informational note if v0.3.0 artifacts are present in a project.

    v0.3.1 does not maintain these, but also does not delete them.
    """
    name = project_path.name
    if name in _V030_ARTIFACT_NOTE_SHOWN:
        return
    artifacts = []
    legacy_research_dir = project_path / "research"
    legacy_live = legacy_research_dir / ".live"
    legacy_index = project_path / "RossLabs-Research.md"
    if legacy_live.exists() and legacy_live.is_dir():
        artifacts.append(f"{legacy_live} (v0.3.0 live symlinks)")
    if legacy_research_dir.exists() and legacy_research_dir.is_dir():
        # Only flag if it looks plugin-authored (has topic subdirs matching slug tops)
        has_topic_child = any(
            (legacy_research_dir / c.name).is_dir() and c.name != ".live"
            for c in legacy_research_dir.iterdir()
        ) if legacy_research_dir.exists() else False
        if has_topic_child:
            artifacts.append(f"{legacy_research_dir} (v0.3.0 file copies)")
    if legacy_index.exists():
        artifacts.append(f"{legacy_index} (v0.3.0 project index)")
    if artifacts:
        print(
            f"Note: {name}/ contains v0.3.0 artifacts that v0.3.1 no longer maintains:",
            file=sys.stderr,
        )
        for a in artifacts:
            print(f"  - {a}", file=sys.stderr)
        print(
            "  These are preserved as-is. Remove manually if unwanted.",
            file=sys.stderr,
        )
    _V030_ARTIFACT_NOTE_SHOWN.add(name)


def _managed_symlink_path(project_name: str, canonical: Path) -> Path:
    """Return <content-root>/projects/<project_name>/<slug>.md — the central symlink target."""
    return _managed_projects_dir() / project_name / canonical.name


def _write_managed_symlink(project_name: str, canonical: Path) -> Path:
    """Create or refresh a symlink at <content-root>/projects/<name>/<slug>.md -> canonical.

    Idempotent. Returns the symlink path.
    """
    link = _managed_symlink_path(project_name, canonical)
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        try:
            link.unlink()
        except OSError:
            pass
    try:
        link.symlink_to(canonical)
    except OSError as e:
        print(f"WARN: could not create symlink {link}: {e}", file=sys.stderr)
    return link


def _extract_title_and_summary(path: Path) -> tuple[str, str]:
    """Extract (title, 1-line-summary) from a markdown file deterministically.

    Title: first '# H1' line text. Fallback to filename stem if no H1.
    Summary: first non-empty, non-heading paragraph, first sentence, truncated ~120 chars.
    Zero LLM calls. Frontmatter (if present) is skipped.
    """
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return path.stem, ""

    # Strip YAML frontmatter if present
    body = text
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            body = text[end + 5 :]
        else:
            end = text.find("\n---", 4)
            if end != -1:
                body = text[end + 4 :]

    lines = body.splitlines()
    title: str | None = None
    for ln in lines:
        stripped = ln.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            title = stripped[2:].strip()
            break
    if not title:
        title = path.stem.replace("-", " ").replace("_", " ").strip() or path.name

    # First paragraph: collect consecutive non-empty, non-heading lines after any H1
    summary_lines: list[str] = []
    in_paragraph = False
    seen_h1 = False
    hr_pat = re.compile(r"^([-*_])\1{2,}$")
    for ln in lines:
        stripped = ln.strip()
        is_heading = stripped.startswith("#")
        is_hr = bool(hr_pat.match(stripped))
        if is_heading or is_hr:
            if not seen_h1 and stripped.startswith("# "):
                seen_h1 = True
                continue
            if in_paragraph:
                break
            # Skip subsequent headings / horizontal rules until content starts
            continue
        if not stripped:
            if in_paragraph:
                break
            continue
        # Skip list markers, block quotes, table rows, code fences
        if stripped.startswith(("```", "|", "- ", "* ", "> ")) and not summary_lines:
            continue
        summary_lines.append(stripped)
        in_paragraph = True

    summary = " ".join(summary_lines)
    # First sentence, naive: cut at first ". " followed by capital or end
    m = re.search(r"([^.!?]+[.!?])(?:\s|$)", summary)
    if m:
        summary = m.group(1).strip()
    summary = re.sub(r"\s+", " ", summary).strip()
    # Strip simple markdown emphasis
    summary = re.sub(r"\*\*([^*]+)\*\*", r"\1", summary)
    summary = re.sub(r"\*([^*]+)\*", r"\1", summary)
    summary = re.sub(r"`([^`]+)`", r"\1", summary)
    if len(summary) > 120:
        summary = summary[:117].rstrip() + "..."
    return title, summary


def _scan_linked_project_files(source_dir: Path) -> list[dict]:
    """Walk source_dir recursively for *.md files. Return [{name,title,summary,mtime,size}]."""
    files: list[dict] = []
    for md in sorted(source_dir.rglob("*.md")):
        if not md.is_file():
            continue
        try:
            stat = md.stat()
        except OSError:
            continue
        title, summary = _extract_title_and_summary(md)
        files.append({
            "name": md.name,
            "relpath": str(md.relative_to(source_dir)),
            "title": title,
            "summary": summary,
            "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "size": stat.st_size,
            "abspath": str(md),
        })
    return files


def _refresh_linked_project_symlinks(project_name: str, files: list[dict]) -> list[Path]:
    """Refresh <content-root>/projects/<name>/ symlinks for a linked external project.

    Keeps one symlink per unique filename (collisions within one project resolve to last-seen).
    Wipes stale links that no longer appear in `files`. Returns list of link paths created.
    """
    link_dir = _managed_projects_dir() / project_name
    link_dir.mkdir(parents=True, exist_ok=True)
    desired: dict[str, str] = {}  # name -> abspath
    for f in files:
        desired[f["name"]] = f["abspath"]
    # Remove any existing symlinks not in desired
    existing = {c.name for c in link_dir.iterdir()} if link_dir.exists() else set()
    for stale_name in existing - set(desired.keys()):
        stale = link_dir / stale_name
        if stale.is_symlink() or stale.is_file():
            try:
                stale.unlink()
            except OSError:
                pass
    # Create / refresh
    out: list[Path] = []
    for name, target in desired.items():
        link = link_dir / name
        if link.is_symlink() or link.exists():
            try:
                link.unlink()
            except OSError:
                pass
        try:
            link.symlink_to(target)
            out.append(link)
        except OSError as e:
            print(f"WARN: could not symlink {link} -> {target}: {e}", file=sys.stderr)
    return out


def cmd_save(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    src_path = Path(args.file).resolve()
    if not src_path.exists():
        print(f"ERROR: file not found: {src_path}", file=sys.stderr)
        return 2
    text = src_path.read_text()
    fm, body = parse_frontmatter(text)
    if not fm.get("slug"):
        print("ERROR: entry missing slug in frontmatter", file=sys.stderr)
        return 2

    # Required defaults, coercing explicit-null (None) to empty-list/defaults
    fm.setdefault("created", today_iso())
    fm["reviewed"] = today_iso()
    fm.setdefault("status", "evergreen")
    fm.setdefault("workflow", "general")
    fm.setdefault("confidence", "inferred")
    fm.setdefault("corroboration", 0)
    for list_key, default in [
        ("topics", [top_level_topic(fm["slug"])]),
        ("projects", []),
        ("tags", []),
        ("sources", []),
        ("related", []),
        ("inbound", []),
    ]:
        if fm.get(list_key) is None:
            fm[list_key] = default

    # Collision resolution
    original_slug = fm["slug"]
    fm["slug"] = _resolve_collision(original_slug, fm)
    if fm["slug"] != original_slug:
        print(f"Slug collision: {original_slug} -> {fm['slug']}")

    # Determine canonical path
    canonical = _slug_to_path(fm["slug"])
    canonical.parent.mkdir(parents=True, exist_ok=True)
    sections = split_sections(body)

    # For project symlink line preview
    fm["tldr_preview"] = (sections["tldr"].split("\n")[0] if sections["tldr"] else "")[:80]

    # Write canonical file (with slug update applied)
    # Strip internal tldr_preview before writing frontmatter
    write_fm = {k: v for k, v in fm.items() if k != "tldr_preview"}
    new_text = dump_frontmatter(write_fm, body)
    canonical.write_text(new_text)

    # If source was elsewhere, move the original (unless it's the canonical path already)
    if src_path.resolve() != canonical.resolve() and args.move_source:
        src_path.unlink()

    # DB upsert
    conn = db_connect()
    verification = write_fm.get("verification") or {}
    row = (
        fm["slug"],
        str(canonical),
        fm.get("title", ""),
        json.dumps(fm.get("topics", [])),
        json.dumps(fm.get("projects", [])),
        json.dumps(fm.get("tags", [])),
        json.dumps(fm.get("sources", [])),
        fm.get("status", "evergreen"),
        fm.get("workflow", "general"),
        fm.get("created", today_iso()),
        fm.get("reviewed", today_iso()),
        fm.get("topic_velocity", "medium"),
        fm.get("confidence", "inferred"),
        int(fm.get("corroboration", 0)),
        sections["tldr"],
        sections["notes"],
        sections["raw"],
        json.dumps(verification),
        json.dumps(fm.get("inbound", [])),
    )
    conn.execute(
        """
        INSERT INTO entries
          (slug, path, title, topics, projects, tags, sources, status, workflow,
           created, reviewed, topic_velocity, confidence, corroboration,
           tldr, notes, raw, verification, inbound)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
          path=excluded.path,
          title=excluded.title,
          topics=excluded.topics,
          projects=excluded.projects,
          tags=excluded.tags,
          sources=excluded.sources,
          status=excluded.status,
          workflow=excluded.workflow,
          created=excluded.created,
          reviewed=excluded.reviewed,
          topic_velocity=excluded.topic_velocity,
          confidence=excluded.confidence,
          corroboration=excluded.corroboration,
          tldr=excluded.tldr,
          notes=excluded.notes,
          raw=excluded.raw,
          verification=excluded.verification,
          inbound=excluded.inbound
        """,
        row,
    )
    conn.commit()
    conn.close()

    # v0.3.1: plugin-managed projects get ONE symlink at <content-root>/projects/<name>/<slug>.md.
    # No file copies. No writes into the project directory (unless --with-project-index).
    project_outputs: list[tuple[str, Path]] = []  # (project_name, managed_symlink_path)
    with_project_index = bool(getattr(args, "with_project_index", False))
    if not args.skip_symlink:
        for proj in fm.get("projects", []):
            managed_link = _write_managed_symlink(proj, canonical)
            project_outputs.append((proj, managed_link))
            # Opt-in: also regenerate <project>/RossLabs-Research.md
            if with_project_index:
                proj_dir = GIT_FOLDER / proj
                if proj_dir.exists() and proj_dir.is_dir():
                    _note_v030_artifacts(proj_dir)
                    _rebuild_project_research_md(proj_dir)

    # Rebuild indexes (canonical + portfolio) unless explicitly skipped
    skip_index = bool(args.skip_index or getattr(args, "no_index", False))
    if not skip_index:
        _rebuild_indexes()
        _rebuild_portfolio()

    print(f"Saved: {fm['slug']}")
    print(f"  Canonical: {canonical}")
    for proj, managed_link in project_outputs:
        print(f"  Project:  {proj}")
        print(f"    Symlink: {managed_link}")
        if with_project_index:
            print(f"    Index:   {GIT_FOLDER / proj / 'RossLabs-Research.md'}")
    if not skip_index:
        print(f"  Portfolio: {content_path('PORTFOLIO.md')}")
    print(f"  Corroboration: {fm.get('corroboration', 0)}  Confidence: {fm.get('confidence')}")
    return 0


# ---------- search ----------

def cmd_search(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    # Build FTS5 query
    query = args.query
    # FTS5 uses double-quoted phrases; leave user query mostly intact but escape quotes
    safe_query = query.replace('"', '""')
    # Filters
    where_clauses = ["entries_fts MATCH ?"]
    params: list = [safe_query]
    if args.tag:
        where_clauses.append("entries.tags LIKE ?")
        params.append(f'%"{args.tag}"%')
    if args.topic:
        where_clauses.append("entries.topics LIKE ?")
        params.append(f'%"{args.topic}"%')
    if args.project:
        where_clauses.append("entries.projects LIKE ?")
        params.append(f'%"{args.project}"%')
    if args.status:
        where_clauses.append("entries.status = ?")
        params.append(args.status)
    sql = f"""
        SELECT entries.slug, entries.title, entries.path, entries.reviewed,
               entries.confidence, entries.corroboration,
               bm25(entries_fts) AS score
        FROM entries_fts
        JOIN entries ON entries.id = entries_fts.rowid
        WHERE {' AND '.join(where_clauses)}
        ORDER BY score
        LIMIT ?
    """
    params.append(args.n)
    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as e:
        print(f"Query error: {e}", file=sys.stderr)
        conn.close()
        return 2
    conn.close()
    if args.json:
        print(json.dumps([dict(r) for r in rows], indent=2, default=str))
    else:
        if not rows:
            print("No matches.")
            return 0
        for r in rows:
            print(f"  [{r['confidence']:8s}] {r['slug']:50s}  {r['title']}")
            print(f"     {r['path']}  (reviewed {r['reviewed']}, corroboration {r['corroboration']})")
    return 0


# ---------- list ----------

def cmd_list(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    sql = "SELECT slug, title, path, reviewed, confidence, corroboration, status FROM entries"
    params: list = []
    if args.status:
        sql += " WHERE status = ?"
        params.append(args.status)
    sql += " ORDER BY reviewed DESC LIMIT ?"
    params.append(args.n)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    if args.json:
        print(json.dumps([dict(r) for r in rows], indent=2, default=str))
        return 0
    if not rows:
        print("No entries.")
        return 0
    for r in rows:
        print(f"  {r['reviewed']}  [{r['confidence']:8s}] {r['slug']:50s}  {r['title']}")
    return 0


# ---------- link ----------

def cmd_link(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    row = conn.execute(
        "SELECT path, projects, title, reviewed, confidence, tldr FROM entries WHERE slug = ?",
        (args.slug,),
    ).fetchone()
    if not row:
        print(f"ERROR: no entry with slug: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    entry_path = Path(row["path"])
    proj_path = Path(args.project_path or Path.cwd()).resolve()
    if not proj_path.is_dir():
        print(f"ERROR: not a directory: {proj_path}", file=sys.stderr)
        conn.close()
        return 2

    # Update projects list in DB
    projs = json.loads(row["projects"] or "[]")
    project_name = proj_path.name
    if project_name not in projs:
        projs.append(project_name)
        conn.execute(
            "UPDATE entries SET projects = ? WHERE slug = ?",
            (json.dumps(projs), args.slug),
        )
        conn.commit()

    # Update entry file frontmatter too
    text = entry_path.read_text()
    fm, body = parse_frontmatter(text)
    fm["projects"] = projs
    entry_path.write_text(dump_frontmatter(fm, body))

    # v0.3.1: managed symlink under <content-root>/projects/<name>/<slug>.md
    managed_link = _write_managed_symlink(project_name, entry_path)
    _note_v030_artifacts(proj_path)
    conn.close()
    print(f"Linked {args.slug} -> {managed_link}")
    return 0


# ---------- link-project (v0.3.1) ----------

def _do_link_project(project_name: str, source_dir: Path) -> dict:
    """Register an external project research directory, scan it, create symlinks.

    Returns the registry entry dict that was written. Idempotent.
    """
    ensure_layout()
    source_dir = source_dir.resolve()
    if not source_dir.is_dir():
        raise ValueError(f"not a directory: {source_dir}")

    files = _scan_linked_project_files(source_dir)
    # Refresh symlinks at <content-root>/projects/<project_name>/
    _refresh_linked_project_symlinks(project_name, files)

    # Persist registry entry (without abspath — keep entry lean; can be rebuilt from path)
    registry = _read_linked_projects_registry()
    entry = {
        "path": str(source_dir),
        "linked": today_iso(),
        "files": [
            {k: f[k] for k in ("name", "relpath", "title", "summary", "mtime", "size")}
            for f in files
        ],
    }
    registry[project_name] = entry
    _write_linked_projects_registry(registry)
    return entry


def cmd_link_project(args: argparse.Namespace) -> int:
    """Register an existing project research directory as a linked external source.

    Walks the directory recursively for *.md files, extracts title + 1-line summary,
    records registration in the index-root registry, creates symlinks under
    <content-root>/projects/<name>/. Does NOT modify the project directory.
    """
    ensure_layout()
    ensure_db()
    source_value = args.path or args.path_arg
    if not source_value:
        print("ERROR: missing path. Use: link-project <name> <path> or link-project <name> --path <path>", file=sys.stderr)
        return 2
    source = Path(source_value).expanduser()
    if not source.is_absolute():
        source = (Path.cwd() / source).resolve()
    if not source.exists():
        print(f"ERROR: path not found: {source}", file=sys.stderr)
        return 2
    if not source.is_dir():
        print(f"ERROR: not a directory: {source}", file=sys.stderr)
        return 2
    try:
        entry = _do_link_project(args.name, source)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # Rebuild portfolio so the linked project shows up
    if not getattr(args, "no_index", False):
        _rebuild_portfolio()

    link_dir = _managed_projects_dir() / args.name
    print(f"Linked project: {args.name}")
    print(f"  Source:   {entry['path']}")
    print(f"  Files:    {len(entry['files'])}")
    print(f"  Symlinks: {link_dir}/")
    print(f"  Registry: {_linked_projects_registry_path()}")
    return 0


# ---------- index ----------

def _rebuild_project_research_md(project_path: Path) -> Path | None:
    """Regenerate <project>/RossLabs-Research.md from canonical entries linked to this project.

    Returns the index file path, or None if no entries point to this project.
    Pure read from DB + filesystem; no LLM calls.
    """
    ensure_db()
    conn = db_connect()
    project_name = project_path.name
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, topics, projects, tags, reviewed, status, "
        "confidence, tldr FROM entries WHERE status != 'archived' ORDER BY slug"
    ).fetchall()]
    conn.close()
    matched: list[dict] = []
    for r in rows:
        projs = json.loads(r["projects"] or "[]")
        if project_name in projs:
            r["topics"] = json.loads(r["topics"] or "[]")
            r["tags"] = json.loads(r["tags"] or "[]")
            matched.append(r)
    index_md = project_path / "RossLabs-Research.md"
    if not matched:
        # No entries; leave any pre-existing index alone (may be from v0.3.0; user choice to keep/remove).
        return None
    # Group by top-level topic from slug
    by_top: dict[str, list[dict]] = {}
    for r in matched:
        by_top.setdefault(top_level_topic(r["slug"]), []).append(r)

    lines: list[str] = []
    lines.append(f"# Research \u2014 {project_name}\n\n")
    lines.append("_Auto-generated by RossLabs Research Plugin. Do not edit by hand; "
                 "changes are overwritten on next save._\n\n")
    lines.append(f"Last updated: {today_iso()}\n\n")
    lines.append(f"## Entries ({len(matched)} total)\n\n")
    for top in sorted(by_top):
        lines.append(f"### {top}\n")
        for r in sorted(by_top[top], key=lambda x: x["slug"]):
            # v0.3.1: link to canonical file under the content root (no project file copies).
            canonical_path = Path(r["path"])
            confidence = r.get("confidence", "inferred") or "inferred"
            status = r.get("status", "evergreen") or "evergreen"
            summary = _summary_from_tldr(r.get("tldr") or "")
            head = f"- [{r['title']}]({canonical_path}) \u2014 reviewed {r['reviewed']}, {confidence}, {status}\n"
            lines.append(head)
            if summary:
                lines.append(f"  > {summary}\n")
        lines.append("\n")

    # Cross-references section
    lines.append("## Cross-references\n\n")
    lines.append("This project's research also relates to entries in the central corpus:\n")
    # For each topic touched by this project, show count of total entries vs here
    conn2 = db_connect()
    total_rows = [dict(r) for r in conn2.execute(
        "SELECT slug FROM entries WHERE status != 'archived'"
    ).fetchall()]
    conn2.close()
    total_by_top: dict[str, int] = {}
    for r in total_rows:
        total_by_top[top_level_topic(r["slug"])] = total_by_top.get(top_level_topic(r["slug"]), 0) + 1
    for top in sorted(by_top):
        total = total_by_top.get(top, len(by_top[top]))
        here = len(by_top[top])
        lines.append(f"- `{content_path('topics', top)}/` ({total} total entries, {here} here)\n")
    lines.append("\n")
    lines.append(f"For the full master portfolio across all your projects, see `{content_path('PORTFOLIO.md')}`.\n")

    index_md.write_text("".join(lines))
    return index_md


def _rebuild_portfolio() -> Path:
    """Regenerate the content-root PORTFOLIO.md with plugin-managed, linked, and cross-cutting sections."""
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, topics, projects, tags, reviewed, status FROM entries "
        "WHERE status != 'archived'"
    ).fetchall()]
    conn.close()
    by_project: dict[str, list[dict]] = {}
    cross_cutting: list[dict] = []
    for r in rows:
        projs = json.loads(r["projects"] or "[]")
        r["topics"] = json.loads(r["topics"] or "[]")
        r["tags"] = json.loads(r["tags"] or "[]")
        if not projs:
            cross_cutting.append(r)
        else:
            for p in projs:
                by_project.setdefault(p, []).append(r)

    registry = _read_linked_projects_registry()

    lines: list[str] = []
    lines.append("# Research Portfolio\n\n")
    lines.append(f"_Auto-generated. Updated: {today_iso()}_\n\n")

    # --- Plugin-managed projects ---
    lines.append("## Plugin-managed projects\n\n")
    lines.append("_Entries saved through `/research:save` with a `projects:` tag. "
                 f"Symlinks live at `{content_path('projects')}/<name>/`._\n\n")
    if not by_project:
        lines.append("_No project-tagged entries yet._\n\n")
    for proj in sorted(by_project):
        entries = by_project[proj]
        last_reviewed = max((e.get("reviewed") or "") for e in entries) or "unknown"
        topics_set = sorted({top_level_topic(e["slug"]) for e in entries})
        symlink_dir = _managed_projects_dir() / proj
        lines.append(f"### {proj}\n")
        lines.append(f"- {len(entries)} entries, last updated {last_reviewed}\n")
        lines.append(f"- Topics: {', '.join(topics_set)}\n")
        lines.append(f"- Symlink dir: {symlink_dir}/\n")
        tops = sorted({top_level_topic(e["slug"]) for e in entries})
        for top in tops:
            lines.append(f"- Central entries: {content_path('topics', top)}/\n")
        lines.append("\n")

    # --- Linked external research directories ---
    lines.append("## Linked external research directories\n\n")
    lines.append("_Registered via `/research:link-project`. The plugin does not own "
                 "or modify these files; it only reads, summarizes, and links them._\n\n")
    if not registry:
        lines.append("_None registered yet._\n\n")
    for name in sorted(registry):
        entry = registry[name]
        files = entry.get("files", [])
        lines.append(f"### {name}\n")
        lines.append(f"- Source: {entry.get('path', '?')}\n")
        lines.append(f"- {len(files)} files, last linked {entry.get('linked', '?')}\n")
        if files:
            lines.append("- Files:\n")
            for f in sorted(files, key=lambda x: x.get("relpath") or x.get("name", "")):
                relpath = f.get("relpath") or f.get("name", "")
                title = f.get("title") or f.get("name", "")
                summary = f.get("summary") or ""
                line = f"  - {relpath} \u2014 {title}"
                if summary:
                    line += f" \u2014 {summary}"
                lines.append(line + "\n")
        lines.append("\n")

    # --- Cross-cutting (unchanged) ---
    lines.append("## Cross-cutting\n\n")
    lines.append("_Entries without a `projects:` tag._\n\n")
    if not cross_cutting:
        lines.append("_None._\n\n")
    else:
        by_top_cc: dict[str, list[dict]] = {}
        for r in cross_cutting:
            by_top_cc.setdefault(top_level_topic(r["slug"]), []).append(r)
        for top in sorted(by_top_cc):
            entries = by_top_cc[top]
            slugs = [e["slug"].split(".", 1)[1] if "." in e["slug"] else e["slug"]
                     for e in sorted(entries, key=lambda x: x["slug"])]
            lines.append(f"### {top} ({len(entries)} entries)\n")
            lines.append(f"- {', '.join(slugs)}\n\n")

    lines.append("## Discovery for external tools\n\n")
    lines.append("Any LLM or tool can point at this file as the entry point. "
                 "Each entry resolves to a markdown file with:\n")
    lines.append("- Frontmatter (slug, title, topics, sources with tier scoring)\n")
    lines.append("- Three-layer body: TL;DR / Notes / Raw\n")
    lines.append("- Cited sources\n\n")
    lines.append("Reading order for max coverage:\n")
    lines.append("1. PORTFOLIO.md (this file) \u2014 corpus overview\n")
    lines.append(f"2. {content_path('by-topic.md')} \u2014 flat topic index\n")
    lines.append(f"3. {content_path('topics')}/*/*.md \u2014 individual entries\n")
    out = content_path("PORTFOLIO.md")
    out.write_text("".join(lines))
    return out


def _rebuild_indexes() -> None:
    """Regenerate index.md / by-topic.md / by-project.md / indices/<topic>.md / inbound."""
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, topics, projects, tags, reviewed, confidence, "
        "corroboration, status FROM entries WHERE status != 'archived' ORDER BY reviewed DESC"
    ).fetchall()]
    for r in rows:
        r["topics"] = json.loads(r["topics"] or "[]")
        r["projects"] = json.loads(r["projects"] or "[]")
        r["tags"] = json.loads(r["tags"] or "[]")

    # index.md (chronological)
    lines = ["# Research Index\n", f"Last rebuilt: {today_iso()}\n",
             f"Total entries: {len(rows)}\n\n",
             "| Date | Slug | Title | Topics | Confidence |\n",
             "|---|---|---|---|---|\n"]
    for r in rows:
        lines.append(
            f"| {r['reviewed']} | [`{r['slug']}`]({r['path']}) | {r['title']} | "
            f"{', '.join(r['topics'])} | {r['confidence']} |\n"
        )
    content_path("index.md").write_text("".join(lines))

    # by-topic.md
    by_tag: dict[str, list[dict]] = {}
    for r in rows:
        for tag in r["tags"]:
            by_tag.setdefault(tag, []).append(r)
    lines = ["# Research by Tag\n", f"Last rebuilt: {today_iso()}\n\n"]
    for tag in sorted(by_tag):
        lines.append(f"## {tag}\n\n")
        for r in sorted(by_tag[tag], key=lambda x: x["reviewed"], reverse=True):
            lines.append(f"- [`{r['slug']}`]({r['path']}) — {r['title']} ({r['reviewed']}, {r['confidence']})\n")
        lines.append("\n")
    content_path("by-topic.md").write_text("".join(lines))

    # by-project.md
    by_proj: dict[str, list[dict]] = {"(cross-cutting)": []}
    for r in rows:
        if not r["projects"]:
            by_proj["(cross-cutting)"].append(r)
        else:
            for p in r["projects"]:
                by_proj.setdefault(p, []).append(r)
    lines = ["# Research by Project\n", f"Last rebuilt: {today_iso()}\n\n"]
    for proj in sorted(by_proj):
        if not by_proj[proj]:
            continue
        lines.append(f"## {proj}\n\n")
        for r in sorted(by_proj[proj], key=lambda x: x["reviewed"], reverse=True):
            lines.append(f"- [`{r['slug']}`]({r['path']}) — {r['title']} ({r['reviewed']}, {r['confidence']})\n")
        lines.append("\n")
    content_path("by-project.md").write_text("".join(lines))

    # indices/<top-level>.md (MOCs)
    indices_dir = content_path("indices")
    indices_dir.mkdir(exist_ok=True)
    # Wipe stale MOCs
    for old in indices_dir.glob("*.md"):
        old.unlink()
    by_top: dict[str, list[dict]] = {}
    for r in rows:
        top = top_level_topic(r["slug"])
        by_top.setdefault(top, []).append(r)
    for top, entries in by_top.items():
        ml = [f"# {top} — Map of Content\n\n",
              f"Last rebuilt: {today_iso()}. {len(entries)} entries.\n\n"]
        for r in sorted(entries, key=lambda x: x["slug"]):
            ml.append(f"- [`{r['slug']}`]({r['path']}) — {r['title']} "
                      f"({r['reviewed']}, {r['confidence']}, corroboration {r['corroboration']})\n")
        (indices_dir / f"{top}.md").write_text("".join(ml))

    # Inbound link maintenance: scan Notes for [[slug]] refs, update each entry's inbound[]
    slug_to_id = {r["slug"]: None for r in rows}
    inbound_map: dict[str, set[str]] = {s: set() for s in slug_to_id}
    for r in rows:
        path = Path(r["path"])
        if not path.exists():
            continue
        body = path.read_text()
        for ref in re.findall(r"\[\[([^\]]+)\]\]", body):
            ref = ref.strip()
            # Strip archive/ prefix if present
            ref = re.sub(r"^archive/", "", ref)
            if ref in inbound_map and ref != r["slug"]:
                inbound_map[ref].add(r["slug"])
    # Persist inbound to DB + frontmatter
    for r in rows:
        inbound = sorted(inbound_map[r["slug"]])
        conn.execute("UPDATE entries SET inbound = ? WHERE slug = ?",
                     (json.dumps(inbound), r["slug"]))
        # Update frontmatter too (non-destructive)
        path = Path(r["path"])
        if path.exists():
            text = path.read_text()
            fm, body = parse_frontmatter(text)
            if fm.get("inbound") != inbound:
                fm["inbound"] = inbound
                path.write_text(dump_frontmatter(fm, body))
    conn.commit()
    conn.close()


def cmd_index(args: argparse.Namespace) -> int:
    ensure_layout()
    ensure_db()
    _rebuild_indexes()

    # v0.3.1: refresh plugin-managed symlinks at <content-root>/projects/<name>/<slug>.md
    # from current DB state (covers cases where slugs were renamed or projects re-tagged).
    conn = db_connect()
    rows = conn.execute(
        "SELECT slug, path, projects FROM entries WHERE status != 'archived'"
    ).fetchall()
    conn.close()
    managed_by_project: dict[str, set[str]] = {}
    for row in rows:
        canonical = Path(row["path"])
        for p in json.loads(row["projects"] or "[]"):
            _write_managed_symlink(p, canonical)
            managed_by_project.setdefault(p, set()).add(canonical.name)
    # Prune stale managed symlinks that no longer correspond to a DB entry
    projects_root = _managed_projects_dir()
    pruned = 0
    if projects_root.exists():
        linked_names = set(_read_linked_projects_registry().keys())
        for proj_dir in projects_root.iterdir():
            if not proj_dir.is_dir():
                continue
            if proj_dir.name in linked_names:
                # Handled by link-project rescan below
                continue
            desired = managed_by_project.get(proj_dir.name, set())
            for child in proj_dir.iterdir():
                if child.is_symlink() and child.name not in desired:
                    try:
                        child.unlink()
                        pruned += 1
                    except OSError:
                        pass

    # v0.3.1: re-scan every registered linked-external project and refresh its symlinks.
    registry = _read_linked_projects_registry()
    rescanned = 0
    missing: list[str] = []
    for name, entry in list(registry.items()):
        src = Path(entry.get("path", ""))
        if not src.is_dir():
            missing.append(f"{name} ({src})")
            continue
        _do_link_project(name, src)
        rescanned += 1
    portfolio = _rebuild_portfolio()

    print("Indexes rebuilt.")
    print(f"  Managed project symlinks: {sum(len(v) for v in managed_by_project.values())} across {len(managed_by_project)} project(s)")
    if pruned:
        print(f"  Pruned stale symlinks:    {pruned}")
    print(f"  Linked external projects: {rescanned} rescanned")
    if missing:
        print(f"  Missing sources:          {len(missing)}")
        for m in missing:
            print(f"    - {m}")
    print(f"  Portfolio:                {portfolio}")
    return 0


# ---------- archive ----------

def cmd_archive(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    row = conn.execute("SELECT path FROM entries WHERE slug = ?", (args.slug,)).fetchone()
    if not row:
        print(f"ERROR: no entry: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    orig = Path(row["path"])
    if not orig.exists():
        print(f"WARN: file missing, only updating DB: {orig}", file=sys.stderr)
    dest = content_path("archive", f"{args.slug}.md")
    dest.parent.mkdir(parents=True, exist_ok=True)
    if orig.exists():
        shutil.move(str(orig), str(dest))
    # Write redirect stub at orig path
    stub = (
        f"---\n"
        f"status: archived\n"
        f"redirect: ../../archive/{args.slug}.md\n"
        f"archived: {today_iso()}\n"
        f"---\n"
        f"Archived. See [[archive/{args.slug}]].\n"
    )
    orig.parent.mkdir(parents=True, exist_ok=True)
    orig.write_text(stub)
    conn.execute("UPDATE entries SET status = 'archived', path = ? WHERE slug = ?",
                 (str(dest), args.slug))
    conn.commit()
    conn.close()
    _rebuild_indexes()
    print(f"Archived: {args.slug} -> {dest}")
    print(f"Redirect stub: {orig}")
    return 0


# ---------- score ----------

def _score_domain_by_rule(domain: str) -> tuple[str, str] | None:
    """Apply deterministic rules. Return (tier, reason) or None if no match."""
    d = domain.lower()
    if d == "arxiv.org" or d.endswith(".arxiv.org"):
        return ("T1", "arXiv preprint server")
    if d == "doi.org":
        return ("T1", "DOI resolver")
    if d.endswith(".gov"):
        return ("T1", "government domain")
    if d.endswith(".edu"):
        return ("T1", "educational/research institution")
    if d in ("github.com",):
        # Github default — without org context, treat as T2
        return ("T2", "github.com repository")
    if d.endswith(".readthedocs.io"):
        return ("T1", "ReadTheDocs official project docs")
    if d in ("reddit.com", "stackoverflow.com", "news.ycombinator.com"):
        return ("T3", "community discussion")
    if d in ("medium.com", "dev.to", "substack.com", "hashnode.dev"):
        return ("T3", "personal blog platform")
    return None


def lookup_domain(conn: sqlite3.Connection, domain: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM domain_scores WHERE domain = ?", (domain,)
    ).fetchone()
    return dict(row) if row else None


def cmd_score(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    if args.tier:
        # Manual set
        domain = args.domain.lower()
        conn.execute(
            "INSERT OR REPLACE INTO domain_scores(domain, tier, reason, set_by, set_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (domain, args.tier, args.reason or "manual override", "manual", today_iso()),
        )
        conn.commit()
        conn.close()
        print(f"Set {domain} -> {args.tier} ({args.reason or 'manual override'})")
        return 0
    # Read
    # Allow URL or bare domain
    target = args.domain
    if "://" in target:
        target = etld1(target)
    target = target.lower()
    row = lookup_domain(conn, target)
    if row:
        print(f"{target}  {row['tier']}  ({row['set_by']}, {row['set_date']})  {row['reason'] or ''}")
        conn.close()
        return 0
    # Try rules
    rule = _score_domain_by_rule(target)
    if rule:
        tier, reason = rule
        conn.execute(
            "INSERT INTO domain_scores(domain, tier, reason, set_by, set_date) "
            "VALUES (?, ?, ?, ?, ?)",
            (target, tier, reason, "rule", today_iso()),
        )
        conn.commit()
        print(f"{target}  {tier}  (rule: {reason})")
        conn.close()
        return 0
    print(f"{target}  (unknown, flag for LLM review)")
    conn.close()
    return 0


# ---------- verify ----------

OPENALEX_BASE = "https://api.openalex.org/works"
ARXIV_API = "http://export.arxiv.org/api/query"
_ARXIV_DOI_RE = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)


def _arxiv_check(arxiv_id: str) -> dict:
    """Query the arXiv API for a paper by its ID. Authoritative for arxiv sources."""
    try:
        url = f"{ARXIV_API}?id_list={urllib.parse.quote(arxiv_id)}&max_results=1"
        req = urllib.request.Request(url, headers={"User-Agent": "research-plugin/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return {"found": False, "error": str(e), "source": "arxiv"}
    # Minimal parse: look for <entry>...<title>...</title>...<published>YYYY-...</published>
    if "<entry>" not in body:
        return {"found": False, "source": "arxiv"}
    title_m = re.search(r"<title>([^<]+)</title>", body.split("<entry>", 1)[1])
    year_m = re.search(r"<published>(\d{4})", body.split("<entry>", 1)[1])
    title = title_m.group(1).strip() if title_m else None
    year = int(year_m.group(1)) if year_m else None
    return {"found": True, "title": title, "year": year, "source": "arxiv",
            "openalex_id": f"arxiv:{arxiv_id}"}


def _title_similarity(a: str, b: str) -> float:
    """Rough title overlap: Jaccard on lowercased word sets, ignoring short words."""
    def toks(s: str) -> set[str]:
        return {w for w in re.findall(r"\w+", (s or "").lower()) if len(w) > 3}
    sa, sb = toks(a), toks(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa | sb), 1)


def _openalex_check(doi: str | None, title: str | None) -> dict:
    """Return {found, year, title, openalex_id, source, error?}.
    For arxiv DOIs, route to arxiv API (more reliable than OpenAlex's arxiv coverage)."""
    # Prefer arxiv API for arxiv DOIs
    if doi:
        m = _ARXIV_DOI_RE.match(doi)
        if m:
            return _arxiv_check(m.group(1))

    q = {}
    if doi:
        q["filter"] = f"doi:{doi}"
    elif title:
        q["search"] = title
    else:
        return {"found": False, "error": "no doi or title", "source": "openalex"}
    q["per-page"] = "1"
    q["mailto"] = "research-plugin@local"
    url = f"{OPENALEX_BASE}?{urllib.parse.urlencode(q)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "research-plugin/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        return {"found": False, "error": str(e), "source": "openalex"}
    results = data.get("results", [])
    if not results:
        return {"found": False, "source": "openalex"}
    w = results[0]
    return {
        "found": True,
        "year": w.get("publication_year"),
        "title": w.get("title"),
        "openalex_id": w.get("id"),
        "source": "openalex",
    }


# Require the number NOT to be preceded by a letter or digit (excludes "GSM8K" etc.)
# and NOT be followed by a letter-unit that isn't in our whitelist (excludes "540B").
_NUM_RE = re.compile(
    r"(?<![A-Za-z\d])(-?\d+(?:\.\d+)?)\s*(%|ms|s|x|×|gb|mb|kb|tb|hz|khz|mhz|ghz)?(?![A-Za-z])",
    re.IGNORECASE,
)


def _parse_number_with_unit(s: str) -> list[tuple[float, str]]:
    out = []
    for m in _NUM_RE.finditer(s):
        val = float(m.group(1))
        unit = (m.group(2) or "").lower().replace("×", "x")
        out.append((val, unit))
    return out


def _fts_retrieve(slug: str, query: str, k: int = 5) -> list[str]:
    """Return top-k Raw chunks for `slug` matching `query`."""
    conn = db_connect()
    row = conn.execute("SELECT raw FROM entries WHERE slug = ?", (slug,)).fetchone()
    conn.close()
    if not row or not row["raw"]:
        return []
    # Chunk by paragraph
    chunks = [c.strip() for c in re.split(r"\n\n+", row["raw"]) if c.strip()]
    # Score chunks by naive keyword overlap (FTS5 on a subset is overkill;
    # this is good enough for verification-time retrieval).
    q_terms = set(re.findall(r"\w+", query.lower()))
    scored = []
    for c in chunks:
        c_terms = set(re.findall(r"\w+", c.lower()))
        score = len(q_terms & c_terms)
        if score > 0:
            scored.append((score, c))
    scored.sort(reverse=True)
    return [c for _, c in scored[:k]]


def _verify_numeric(atom: dict, slug: str) -> dict:
    """Check if claim's numbers appear in retrieved Raw chunks (± tolerance)."""
    chunks = _fts_retrieve(slug, atom["claim"], k=5)
    claim_nums = _parse_number_with_unit(atom["claim"])
    if not claim_nums:
        return {"verdict": "inconclusive", "evidence": "no numbers parsed from claim", "confidence": "❓"}
    if not chunks:
        return {"verdict": "inconclusive", "evidence": "no supporting raw chunks found", "confidence": "❓"}
    matches = []
    for val, unit in claim_nums:
        matched_this_val = False
        for c in chunks:
            if matched_this_val:
                break
            chunk_nums = _parse_number_with_unit(c)
            for cv, cu in chunk_nums:
                # Units must match exactly (prevents spurious unitless matches)
                if unit != cu:
                    continue
                # Tolerance: 1% relative, or 0.1 absolute, whichever is larger
                tol = max(abs(val) * 0.01, 0.1)
                if abs(val - cv) <= tol:
                    matches.append({"claim": f"{val}{unit}", "source": f"{cv}{cu}",
                                    "chunk_preview": c[:120]})
                    matched_this_val = True
                    break
    if len(matches) == len(claim_nums):
        return {"verdict": "passed", "evidence": matches, "confidence": "✅"}
    if matches:
        return {"verdict": "inconclusive", "evidence": {"matched": matches, "total": len(claim_nums)}, "confidence": "⚠️"}
    return {"verdict": "failed", "evidence": f"no numeric match in {len(chunks)} chunks", "confidence": "❌"}


def _verify_symbolic(atom: dict) -> dict:
    try:
        import sympy
    except ImportError:
        return {"verdict": "inconclusive", "evidence": "sympy not installed", "confidence": "❓"}
    # Expect claim of form "lhs == rhs" or parseable equation
    claim = atom["claim"]
    m = re.search(r"(.+?)\s*(?:=|==|equals)\s*(.+)", claim)
    if not m:
        return {"verdict": "inconclusive", "evidence": "could not parse equation", "confidence": "❓"}
    try:
        lhs = sympy.sympify(m.group(1).strip())
        rhs = sympy.sympify(m.group(2).strip())
        diff = sympy.simplify(lhs - rhs)
        if diff == 0:
            return {"verdict": "passed", "evidence": f"{lhs} = {rhs} verified", "confidence": "✅"}
        return {"verdict": "failed", "evidence": f"difference: {diff}", "confidence": "❌"}
    except Exception as e:
        return {"verdict": "inconclusive", "evidence": f"sympy error: {e}", "confidence": "❓"}


def _verify_citation(atom: dict) -> dict:
    """Check a citation via arXiv (for arxiv DOIs) or OpenAlex.
    Requires returned title to overlap with expected title if provided (guards
    against API false-positives like OpenAlex sometimes returning unrelated works)."""
    doi = atom.get("doi")
    expected_title = atom.get("title") or atom["claim"]
    result = _openalex_check(doi, expected_title)
    if not result.get("found"):
        err = result.get("error", f"not found in {result.get('source', 'lookup')}")
        return {"verdict": "failed", "evidence": err, "confidence": "❌"}
    returned_title = result.get("title") or ""
    sim = _title_similarity(expected_title, returned_title)
    # If caller provided a specific title to match, require meaningful overlap.
    if atom.get("title") and sim < 0.2:
        return {
            "verdict": "failed",
            "evidence": (
                f"Title mismatch: expected '{expected_title}' but {result.get('source')} "
                f"returned '{returned_title}' (similarity {sim:.2f})"
            ),
            "confidence": "❌",
        }
    return {
        "verdict": "passed",
        "evidence": f"Found via {result.get('source')}: {returned_title} ({result.get('year')}) — {result.get('openalex_id')}",
        "confidence": "✅",
    }


def _verify_code(atom: dict) -> dict:
    """Run code sandbox-ish. v0.3: Docker if available, else subprocess with limits."""
    code = atom.get("code") or ""
    if not code:
        return {"verdict": "inconclusive", "evidence": "no code provided", "confidence": "❓"}
    docker = shutil.which("docker")
    if docker:
        try:
            proc = subprocess.run(
                [docker, "run", "--rm", "-i", "--network=none", "--memory=256m",
                 "--cpus=1", "python:3.12-slim", "python", "-c", code],
                capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired:
            return {"verdict": "failed", "evidence": "timeout", "confidence": "❌"}
    else:
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            return {"verdict": "failed", "evidence": "timeout", "confidence": "❌"}
    if proc.returncode == 0:
        return {"verdict": "passed", "evidence": proc.stdout.strip()[:500], "confidence": "✅"}
    return {"verdict": "failed", "evidence": proc.stderr.strip()[:500], "confidence": "❌"}


VERIFIERS = {
    "numeric": _verify_numeric,
    "symbolic": _verify_symbolic,
    "citation": _verify_citation,
    "code": _verify_code,
}


def cmd_verify(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    row = conn.execute("SELECT path FROM entries WHERE slug = ?", (args.slug,)).fetchone()
    if not row:
        print(f"ERROR: no entry: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    entry_path = Path(row["path"])
    conn.close()

    atoms_path = args.atoms or str(entry_path.parent / f"{args.slug}.atoms.json")
    if not Path(atoms_path).exists():
        print(f"ERROR: no atoms file at {atoms_path}.", file=sys.stderr)
        print("Extract atoms first (Claude writes JSON list of "
              "{atom_id, type, claim, doi?, code?} to that path).", file=sys.stderr)
        return 2
    atoms = json.loads(Path(atoms_path).read_text())
    if args.atom:
        atoms = [a for a in atoms if a["atom_id"] == args.atom]
        if not atoms:
            print(f"ERROR: atom {args.atom} not in {atoms_path}", file=sys.stderr)
            return 2

    log_dir = index_path("verifier-log", args.slug)
    log_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for atom in atoms:
        verifier = VERIFIERS.get(atom.get("type"))
        if not verifier:
            result = {"verdict": "inconclusive", "evidence": f"unknown type: {atom.get('type')}", "confidence": "❓"}
        elif args.dry_run:
            result = {"verdict": "dry-run", "evidence": "skipped"}
        elif atom["type"] == "numeric":
            result = verifier(atom, args.slug)
        else:
            result = verifier(atom)
        entry = {
            "atom_id": atom["atom_id"],
            "type": atom.get("type"),
            "claim": atom.get("claim"),
            "timestamp": now_iso(),
            **result,
        }
        (log_dir / f"{atom['atom_id']}.json").write_text(json.dumps(entry, indent=2, default=str))
        results.append(entry)
        print(f"  [{entry['verdict']:12s}] {atom['atom_id']}  ({atom.get('type')})  {atom.get('claim', '')[:80]}")

    # Roll up into entry frontmatter
    if not args.dry_run and not args.atom:
        passed = sum(1 for r in results if r["verdict"] == "passed")
        failed = sum(1 for r in results if r["verdict"] == "failed")
        inconclusive = sum(1 for r in results if r["verdict"] == "inconclusive")
        text = entry_path.read_text()
        fm, body = parse_frontmatter(text)
        fm["verification"] = {
            "run": now_iso(),
            "atoms": len(results),
            "passed": passed,
            "failed": failed,
            "inconclusive": inconclusive,
        }
        # Update confidence based on verification + corroboration
        corrob = int(fm.get("corroboration", 0))
        pass_rate = passed / max(len(results), 1)
        if corrob >= 2 and pass_rate >= 0.8:
            fm["confidence"] = "verified"
        elif corrob >= 1 and pass_rate >= 0.5:
            fm["confidence"] = "partial"
        else:
            fm["confidence"] = "inferred"
        entry_path.write_text(dump_frontmatter(fm, body))
        # Re-ingest to DB
        _reingest(entry_path)

    print(f"Verified {len(results)} atoms. Artifacts in {log_dir}")
    return 0


def _normalise_entry_frontmatter(fm: dict) -> dict:
    """Apply DB-safe defaults without rewriting the source markdown."""
    if not fm.get("slug"):
        raise ValueError("entry missing slug in frontmatter")
    out = dict(fm)
    out.setdefault("created", today_iso())
    out.setdefault("reviewed", today_iso())
    out.setdefault("status", "evergreen")
    out.setdefault("workflow", "general")
    out.setdefault("confidence", "inferred")
    out.setdefault("corroboration", 0)
    for list_key, default in [
        ("topics", [top_level_topic(out["slug"])]),
        ("projects", []),
        ("tags", []),
        ("sources", []),
        ("related", []),
        ("inbound", []),
    ]:
        if out.get(list_key) is None:
            out[list_key] = default
        elif not isinstance(out.get(list_key), list):
            out[list_key] = [out[list_key]]
    return out


def _reingest(entry_path: Path) -> str:
    """Re-read an entry file and upsert into DB without touching filesystem."""
    text = entry_path.read_text()
    fm, body = parse_frontmatter(text)
    fm = _normalise_entry_frontmatter(fm)
    sections = split_sections(body)
    verification = fm.get("verification") or {}
    row = (
        fm["slug"],
        str(entry_path.resolve()),
        fm.get("title", ""),
        json.dumps(fm.get("topics", [])),
        json.dumps(fm.get("projects", [])),
        json.dumps(fm.get("tags", [])),
        json.dumps(fm.get("sources", [])),
        fm.get("status", "evergreen"),
        fm.get("workflow", "general"),
        fm.get("created", today_iso()),
        fm.get("reviewed", today_iso()),
        fm.get("topic_velocity", "medium"),
        fm.get("confidence", "inferred"),
        int(fm.get("corroboration", 0) or 0),
        sections["tldr"],
        sections["notes"],
        sections["raw"],
        json.dumps(verification),
        json.dumps(fm.get("inbound", [])),
    )
    conn = db_connect()
    conn.execute(
        """
        INSERT INTO entries
          (slug, path, title, topics, projects, tags, sources, status, workflow,
           created, reviewed, topic_velocity, confidence, corroboration,
           tldr, notes, raw, verification, inbound)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
          path=excluded.path,
          title=excluded.title,
          topics=excluded.topics,
          projects=excluded.projects,
          tags=excluded.tags,
          sources=excluded.sources,
          status=excluded.status,
          workflow=excluded.workflow,
          created=excluded.created,
          reviewed=excluded.reviewed,
          topic_velocity=excluded.topic_velocity,
          confidence=excluded.confidence,
          corroboration=excluded.corroboration,
          tldr=excluded.tldr,
          notes=excluded.notes,
          raw=excluded.raw,
          verification=excluded.verification,
          inbound=excluded.inbound
        """,
        row,
    )
    conn.commit()
    conn.close()
    return fm["slug"]


def _topic_entry_paths() -> list[Path]:
    """Return canonical topic markdown paths under the configured content root."""
    topics_dir = content_path("topics")
    if not topics_dir.exists():
        return []
    return sorted(p for p in topics_dir.glob("*/*.md") if p.is_file())


def cmd_sync(args: argparse.Namespace) -> int:
    """Synchronize SQLite from canonical topic markdown without modifying entries."""
    ensure_layout()
    ensure_db()
    seen: list[str] = []
    seen_paths: dict[str, Path] = {}
    skipped: list[tuple[Path, str]] = []
    duplicates: list[tuple[str, Path, Path]] = []
    redirects = 0
    for entry_path in _topic_entry_paths():
        try:
            fm, _body = parse_frontmatter(entry_path.read_text(), fatal=False)
            slug = fm.get("slug")
            if not slug:
                if fm.get("status") == "archived" and fm.get("redirect"):
                    redirects += 1
                    continue
                raise ValueError("entry missing slug in frontmatter")
            if slug in seen_paths:
                duplicates.append((slug, seen_paths[slug], entry_path))
                continue
            seen.append(_reingest(entry_path))
            seen_paths[slug] = entry_path
        except ValueError as e:
            skipped.append((entry_path, str(e)))
        except (OSError, KeyError, yaml.YAMLError) as e:
            skipped.append((entry_path, str(e)))

    pruned = 0
    if args.prune_missing:
        conn = db_connect()
        if seen:
            placeholders = ",".join("?" for _ in seen)
            pruned = conn.execute(
                f"DELETE FROM entries WHERE slug NOT IN ({placeholders})",
                seen,
            ).rowcount
        else:
            print("WARN: no topic entries found; refusing to prune all DB rows", file=sys.stderr)
        conn.commit()
        conn.close()

    if not args.no_index:
        # Reuse the full index flow so indexes, managed symlinks, and linked projects refresh.
        class _IndexArgs:
            pass
        cmd_index(_IndexArgs())  # type: ignore[arg-type]

    print(f"Synced topic entries: {len(set(seen))}")
    if redirects:
        print(f"Ignored redirect stubs: {redirects}")
    if duplicates:
        print(f"Duplicate slugs: {len(duplicates)}")
        for slug, first, duplicate in duplicates[:10]:
            print(f"  - {slug}: kept {first}; duplicate {duplicate}")
        if len(duplicates) > 10:
            print(f"  ... {len(duplicates) - 10} more")
    if pruned:
        print(f"Pruned missing DB rows: {pruned}")
    if skipped:
        print(f"Skipped files: {len(skipped)}")
        for path, reason in skipped[:10]:
            print(f"  - {path}: {reason}")
        if len(skipped) > 10:
            print(f"  ... {len(skipped) - 10} more")
    return 0


# ---------- quantitative analysis ----------

ANALYSIS_EXTS = {".csv", ".tsv", ".json", ".jsonl", ".sqlite", ".sqlite3", ".db"}


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _analysis_runs_dir() -> Path:
    p = index_path("analysis-runs")
    p.mkdir(parents=True, exist_ok=True)
    return p


def _analysis_input_type(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".csv":
        return "csv"
    if ext == ".tsv":
        return "tsv"
    if ext in (".json", ".jsonl"):
        return ext[1:]
    if ext in (".sqlite", ".sqlite3", ".db"):
        return "sqlite"
    return "unknown"


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text:
        return None
    # Remove common visual separators but do not guess at percentages/currency.
    text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def _sample_rows(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    return rows[: max(n, 0)]


def _summarize_table_rows(rows: list[dict[str, Any]], sample_size: int = 5) -> dict[str, Any]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                columns.append(key)
                seen.add(key)

    profile_cols: list[dict[str, Any]] = []
    for col in columns:
        values = [row.get(col) for row in rows]
        blanks = sum(1 for v in values if v is None or str(v).strip() == "")
        decimals: list[Decimal] = []
        for v in values:
            d = _decimal_or_none(v)
            if d is not None:
                decimals.append(d)
        nonblank = max(len(values) - blanks, 0)
        numeric_count = len(decimals)
        inferred_type = "number" if nonblank and numeric_count == nonblank else "mixed"
        if nonblank and numeric_count == 0:
            inferred_type = "text"
        if not nonblank:
            inferred_type = "empty"
        distinct_values = {str(v) for v in values if v is not None and str(v).strip() != ""}
        col_profile: dict[str, Any] = {
            "name": col,
            "inferred_type": inferred_type,
            "nonblank": nonblank,
            "blank": blanks,
            "distinct": len(distinct_values),
        }
        if decimals:
            total = sum(decimals, Decimal("0"))
            col_profile["numeric"] = {
                "count": numeric_count,
                "min": str(min(decimals)),
                "max": str(max(decimals)),
                "mean": str(total / Decimal(numeric_count)),
            }
        if 0 < len(distinct_values) <= 10:
            col_profile["values"] = sorted(distinct_values)[:10]
        profile_cols.append(col_profile)

    return {
        "row_count": len(rows),
        "columns": profile_cols,
        "sample_rows": _sample_rows(rows, sample_size),
    }


def _read_delimited_rows(path: Path, delimiter: str) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        return [dict(row) for row in reader]


def _read_json_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            rows.append(obj if isinstance(obj, dict) else {"value": obj})
        return rows
    data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    if isinstance(data, list):
        return [x if isinstance(x, dict) else {"value": x} for x in data]
    if isinstance(data, dict):
        for key in ("rows", "data", "items", "records"):
            maybe = data.get(key)
            if isinstance(maybe, list):
                return [x if isinstance(x, dict) else {"value": x} for x in maybe]
        return [data]
    return [{"value": data}]


def _profile_table_file(path: Path, sample_size: int = 5) -> dict[str, Any]:
    input_type = _analysis_input_type(path)
    if input_type == "csv":
        rows = _read_delimited_rows(path, ",")
    elif input_type == "tsv":
        rows = _read_delimited_rows(path, "\t")
    elif input_type in ("json", "jsonl"):
        rows = _read_json_rows(path)
    else:
        raise ValueError(f"unsupported table input type: {path.suffix}")
    profile = _summarize_table_rows(rows, sample_size=sample_size)
    profile.update({
        "path": str(path),
        "input_type": input_type,
        "sha256": _file_sha256(path),
    })
    return profile


def _profile_sqlite_db(path: Path, sample_size: int = 5) -> dict[str, Any]:
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    tables = [
        dict(r) for r in conn.execute(
            "SELECT name, type, sql FROM sqlite_master "
            "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]
    out_tables: list[dict[str, Any]] = []
    for table in tables:
        name = table["name"]
        quoted = '"' + name.replace('"', '""') + '"'
        row_count = conn.execute(f"SELECT COUNT(*) AS n FROM {quoted}").fetchone()["n"]
        cols = [dict(r) for r in conn.execute(f"PRAGMA table_info({quoted})").fetchall()]
        fks = [dict(r) for r in conn.execute(f"PRAGMA foreign_key_list({quoted})").fetchall()]
        indexes = [dict(r) for r in conn.execute(f"PRAGMA index_list({quoted})").fetchall()]
        sample = [dict(r) for r in conn.execute(f"SELECT * FROM {quoted} LIMIT ?", (sample_size,)).fetchall()]
        table_profile = {
            "name": name,
            "type": table["type"],
            "row_count": row_count,
            "schema_sql": table.get("sql"),
            "columns": [
                {
                    "name": c.get("name"),
                    "declared_type": c.get("type"),
                    "notnull": bool(c.get("notnull")),
                    "default": c.get("dflt_value"),
                    "primary_key_position": c.get("pk"),
                }
                for c in cols
            ],
            "foreign_keys": fks,
            "indexes": indexes,
            "sample_rows": sample,
        }
        if sample:
            table_profile["sample_profile"] = _summarize_table_rows(sample, sample_size=sample_size)
        out_tables.append(table_profile)
    conn.close()
    return {
        "path": str(path),
        "input_type": "sqlite",
        "sha256": _file_sha256(path),
        "tables": out_tables,
    }


def _profile_input(path: Path, sample_size: int = 5) -> dict[str, Any]:
    input_type = _analysis_input_type(path)
    if input_type == "sqlite":
        return _profile_sqlite_db(path, sample_size=sample_size)
    if input_type in ("csv", "tsv", "json", "jsonl"):
        return _profile_table_file(path, sample_size=sample_size)
    raise ValueError(f"unsupported input extension: {path.suffix}")


def _certainty_from_profile(profile: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    input_type = profile.get("input_type")
    if input_type == "sqlite":
        tables = profile.get("tables") or []
        if not tables:
            return "Low", ["database has no user tables/views"]
        no_rows = [t["name"] for t in tables if int(t.get("row_count") or 0) == 0]
        no_pk = [
            t["name"] for t in tables
            if t.get("type") == "table" and not any(c.get("primary_key_position") for c in t.get("columns", []))
        ]
        if no_rows:
            reasons.append(f"empty tables/views: {', '.join(no_rows[:5])}")
        if no_pk:
            reasons.append(f"tables without primary keys: {', '.join(no_pk[:5])}")
        if reasons:
            return "Medium", reasons
        return "High", ["structured SQLite input with table schemas and row counts"]
    row_count = int(profile.get("row_count") or 0)
    columns = profile.get("columns") or []
    if row_count == 0:
        return "Low", ["input has zero rows"]
    if not columns:
        return "Low", ["input has no detected columns"]
    blank_heavy = [
        c["name"] for c in columns
        if row_count and (int(c.get("blank") or 0) / max(row_count, 1)) > 0.2
    ]
    mixed_cols = [c["name"] for c in columns if c.get("inferred_type") == "mixed"]
    if blank_heavy or mixed_cols:
        if blank_heavy:
            reasons.append(f">20% blanks in: {', '.join(blank_heavy[:5])}")
        if mixed_cols:
            reasons.append(f"mixed type columns: {', '.join(mixed_cols[:5])}")
        return "Medium", reasons
    return "High", ["structured table input with detected columns and no major profile warnings"]


def _analysis_script_text() -> str:
    """Return the generated stdlib-only analysis script."""
    return r'''#!/usr/bin/env python3
"""Generated by research.py analyze-plan.

Self-contained stdlib analysis runner. It reads analysis-plan.json, validates
declared inputs by sha256, profiles the inputs, and writes results.json plus
audit.md. It intentionally does not install packages, download code, or call
network APIs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)
    out_cols: list[dict[str, Any]] = []
    for col in columns:
        vals = [row.get(col) for row in rows]
        blanks = sum(1 for v in vals if v is None or str(v).strip() == "")
        nums = [d for d in (decimal_or_none(v) for v in vals) if d is not None]
        nonblank = len(vals) - blanks
        distinct = {str(v) for v in vals if v is not None and str(v).strip() != ""}
        inferred = "number" if nonblank and len(nums) == nonblank else "mixed"
        if nonblank and not nums:
            inferred = "text"
        if not nonblank:
            inferred = "empty"
        item: dict[str, Any] = {
            "name": col,
            "inferred_type": inferred,
            "nonblank": nonblank,
            "blank": blanks,
            "distinct": len(distinct),
        }
        if nums:
            item["numeric"] = {
                "count": len(nums),
                "min": str(min(nums)),
                "max": str(max(nums)),
                "sum": str(sum(nums, Decimal("0"))),
                "mean": str(sum(nums, Decimal("0")) / Decimal(len(nums))),
            }
        out_cols.append(item)
    return {"row_count": len(rows), "columns": out_cols, "sample_rows": rows[:5]}


def read_rows(path: Path, input_type: str) -> list[dict[str, Any]]:
    if input_type in ("csv", "tsv"):
        delim = "\t" if input_type == "tsv" else ","
        with path.open(newline="", encoding="utf-8-sig", errors="replace") as f:
            return [dict(r) for r in csv.DictReader(f, delimiter=delim)]
    if input_type == "jsonl":
        rows = []
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                obj = json.loads(line)
                rows.append(obj if isinstance(obj, dict) else {"value": obj})
        return rows
    if input_type == "json":
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, list):
            return [x if isinstance(x, dict) else {"value": x} for x in data]
        if isinstance(data, dict):
            for key in ("rows", "data", "items", "records"):
                maybe = data.get(key)
                if isinstance(maybe, list):
                    return [x if isinstance(x, dict) else {"value": x} for x in maybe]
            return [data]
        return [{"value": data}]
    raise ValueError(f"unsupported table input type: {input_type}")


def profile_sqlite(path: Path) -> dict[str, Any]:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    tables = [dict(r) for r in conn.execute(
        "SELECT name, type, sql FROM sqlite_master WHERE type IN ('table', 'view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )]
    out = []
    for table in tables:
        name = table["name"]
        quoted = '"' + name.replace('"', '""') + '"'
        row_count = conn.execute(f"SELECT COUNT(*) AS n FROM {quoted}").fetchone()["n"]
        cols = [dict(r) for r in conn.execute(f"PRAGMA table_info({quoted})")]
        fks = [dict(r) for r in conn.execute(f"PRAGMA foreign_key_list({quoted})")]
        indexes = [dict(r) for r in conn.execute(f"PRAGMA index_list({quoted})")]
        sample = [dict(r) for r in conn.execute(f"SELECT * FROM {quoted} LIMIT 5")]
        out.append({
            "name": name,
            "type": table["type"],
            "row_count": row_count,
            "schema_sql": table.get("sql"),
            "columns": cols,
            "foreign_keys": fks,
            "indexes": indexes,
            "sample_rows": sample,
        })
    conn.close()
    return {"tables": out}


def certainty(profile: dict[str, Any], input_type: str) -> tuple[str, list[str]]:
    if input_type == "sqlite":
        tables = profile.get("tables") or []
        if not tables:
            return "Low", ["database has no user tables/views"]
        no_pk = [
            t["name"] for t in tables
            if t.get("type") == "table" and not any(c.get("pk") for c in t.get("columns", []))
        ]
        if no_pk:
            return "Medium", [f"tables without primary keys: {', '.join(no_pk[:5])}"]
        return "High", ["structured SQLite input; schema and row counts profiled"]
    rows = int(profile.get("row_count") or 0)
    if rows == 0:
        return "Low", ["input has zero rows"]
    cols = profile.get("columns") or []
    mixed = [c["name"] for c in cols if c.get("inferred_type") == "mixed"]
    if mixed:
        return "Medium", [f"mixed type columns: {', '.join(mixed[:5])}"]
    return "High", ["structured table input; deterministic stdlib profiling completed"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    plan_path = Path(args.plan).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    plan = json.loads(plan_path.read_text())
    findings = []
    validations = []
    for inp in plan.get("inputs", []):
        path = Path(inp["path"]).resolve()
        actual_sha = file_sha256(path)
        expected_sha = inp.get("sha256")
        validations.append({
            "name": f"sha256:{path.name}",
            "passed": expected_sha == actual_sha,
            "expected": expected_sha,
            "actual": actual_sha,
        })
        input_type = inp.get("input_type")
        if input_type == "sqlite":
            profile = profile_sqlite(path)
        else:
            rows = read_rows(path, input_type)
            profile = summarize_rows(rows)
        level, reasons = certainty(profile, input_type)
        findings.append({
            "input": str(path),
            "input_type": input_type,
            "profile": profile,
            "certainty": level,
            "certainty_reasons": reasons,
        })
    all_valid = all(v["passed"] for v in validations)
    result = {
        "question": plan.get("question"),
        "status": "passed" if all_valid else "validation_failed",
        "validations": validations,
        "findings": findings,
        "limitations": plan.get("limitations", []),
    }
    (out_dir / "results.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    lines = [
        "# Analysis Audit\n\n",
        f"Question: {plan.get('question') or 'unspecified'}\n\n",
        f"Status: {result['status']}\n\n",
        "## Findings\n\n",
    ]
    for f in findings:
        lines.append(f"- `{f['input']}` ({f['input_type']}): certainty **{f['certainty']}** — {', '.join(f['certainty_reasons'])}\n")
    lines.append("\n## Validations\n\n")
    for v in validations:
        lines.append(f"- {v['name']}: {'passed' if v['passed'] else 'failed'}\n")
    if plan.get("limitations"):
        lines.append("\n## Limitations\n\n")
        for item in plan["limitations"]:
            lines.append(f"- {item}\n")
    (out_dir / "audit.md").write_text("".join(lines))
    print(out_dir / "results.json")
    print(out_dir / "audit.md")
    return 0 if all_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


def cmd_table_profile(args: argparse.Namespace) -> int:
    path = Path(args.input).expanduser().resolve()
    if not path.exists() or not path.is_file():
        print(f"ERROR: table input not found: {path}", file=sys.stderr)
        return 2
    try:
        profile = _profile_table_file(path, sample_size=args.sample)
    except (OSError, json.JSONDecodeError, csv.Error, ValueError) as e:
        print(f"ERROR: could not profile table: {e}", file=sys.stderr)
        return 2
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(profile, indent=2, default=str) + "\n")
        print(out)
    else:
        print(json.dumps(profile, indent=2, default=str))
    return 0


def cmd_db_profile(args: argparse.Namespace) -> int:
    path = Path(args.db).expanduser().resolve()
    if not path.exists() or not path.is_file():
        print(f"ERROR: database not found: {path}", file=sys.stderr)
        return 2
    try:
        profile = _profile_sqlite_db(path, sample_size=args.sample)
    except sqlite3.Error as e:
        print(f"ERROR: could not profile SQLite database: {e}", file=sys.stderr)
        return 2
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(profile, indent=2, default=str) + "\n")
        print(out)
    else:
        print(json.dumps(profile, indent=2, default=str))
    return 0


def cmd_analyze_plan(args: argparse.Namespace) -> int:
    ensure_layout()
    inputs = [Path(p).expanduser().resolve() for p in args.input]
    missing = [str(p) for p in inputs if not p.exists() or not p.is_file()]
    if missing:
        print(f"ERROR: missing input(s): {', '.join(missing)}", file=sys.stderr)
        return 2
    run_name = args.name or _slugify(args.question or "analysis")
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else _analysis_runs_dir() / f"{stamp}-{run_name}"
    run_dir.mkdir(parents=True, exist_ok=True)

    profiled_inputs: list[dict[str, Any]] = []
    limitations = [
        "Generated script performs deterministic profiling only until metric formulas or SQL are added to the plan.",
        "Certainty reflects input structure and validation status, not external source credibility.",
    ]
    for path in inputs:
        try:
            profile = _profile_input(path, sample_size=args.sample)
        except (OSError, json.JSONDecodeError, csv.Error, sqlite3.Error, ValueError) as e:
            print(f"ERROR: could not profile {path}: {e}", file=sys.stderr)
            return 2
        level, reasons = _certainty_from_profile(profile)
        profiled_inputs.append({
            "path": str(path),
            "input_type": profile["input_type"],
            "sha256": profile["sha256"],
            "profile_path": str(run_dir / f"{path.stem}.profile.json"),
            "profile": profile,
            "initial_certainty": level,
            "certainty_reasons": reasons,
        })
        Path(profiled_inputs[-1]["profile_path"]).write_text(json.dumps(profile, indent=2, default=str) + "\n")

    plan = {
        "question": args.question,
        "created": now_iso(),
        "workflow": "quantitative-analysis",
        "inputs": [
            {
                "path": p["path"],
                "input_type": p["input_type"],
                "sha256": p["sha256"],
                "profile_path": p["profile_path"],
                "initial_certainty": p["initial_certainty"],
                "certainty_reasons": p["certainty_reasons"],
            }
            for p in profiled_inputs
        ],
        "metrics": [],
        "validations": [
            "input sha256 must match the profiled file",
            "row counts and schemas should be reviewed before interpreting calculations",
        ],
        "certainty_rubric": {
            "High": "structured input, known schema, deterministic calculation, validations pass",
            "Medium": "some assumptions or partial validation, but data is usable",
            "Low": "ambiguous grain/schema, extraction risk, failed validation, or missing critical data",
        },
        "limitations": limitations,
        "script": str(run_dir / "analysis.py"),
        "plan_json": str(run_dir / "analysis-plan.json"),
    }
    yaml_path = run_dir / "analysis-plan.yaml"
    json_path = run_dir / "analysis-plan.json"
    script_path = run_dir / "analysis.py"
    script_path.write_text(_analysis_script_text())
    script_path.chmod(0o700)
    plan["script_sha256"] = _file_sha256(script_path)
    yaml_path.write_text(yaml.safe_dump(plan, sort_keys=False, allow_unicode=True))
    json_path.write_text(json.dumps(plan, indent=2, default=str) + "\n")

    print(f"Analysis plan: {yaml_path}")
    print(f"Plan JSON:     {json_path}")
    print(f"Script:        {script_path}")
    print("Next: python research.py analyze-run --plan " + str(yaml_path))
    return 0


def cmd_analyze_run(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan).expanduser().resolve()
    if not plan_path.exists():
        print(f"ERROR: plan not found: {plan_path}", file=sys.stderr)
        return 2
    try:
        plan = yaml.safe_load(plan_path.read_text()) or {}
    except yaml.YAMLError as e:
        print(f"ERROR: invalid plan YAML: {e}", file=sys.stderr)
        return 2
    run_dir = plan_path.parent
    script_path = Path(plan.get("script") or run_dir / "analysis.py").expanduser().resolve()
    json_path = Path(plan.get("plan_json") or run_dir / "analysis-plan.json").expanduser().resolve()
    if not script_path.exists():
        print(f"ERROR: analysis script not found: {script_path}", file=sys.stderr)
        return 2
    expected_script_hash = plan.get("script_sha256")
    if expected_script_hash and not args.allow_modified_script:
        actual_script_hash = _file_sha256(script_path)
        if actual_script_hash != expected_script_hash:
            print("ERROR: analysis script hash differs from analysis-plan.yaml.", file=sys.stderr)
            print(f"  Expected: {expected_script_hash}", file=sys.stderr)
            print(f"  Actual:   {actual_script_hash}", file=sys.stderr)
            print("Review the script, then rerun with --allow-modified-script if this edit is intentional.", file=sys.stderr)
            return 2
    if not json_path.exists():
        json_path.write_text(json.dumps(plan, indent=2, default=str) + "\n")
    proc = subprocess.run(
        [sys.executable, str(script_path), "--plan", str(json_path), "--out-dir", str(run_dir)],
        cwd=str(run_dir),
        capture_output=True,
        text=True,
        timeout=args.timeout,
    )
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print(f"ERROR: analysis failed with exit code {proc.returncode}", file=sys.stderr)
        return proc.returncode
    print(f"Analysis artifacts: {run_dir}")
    return 0


# ---------- review ----------

def _months_since(d_str: str | None) -> float:
    if not d_str:
        return 0.0
    try:
        d = date.fromisoformat(str(d_str))
    except ValueError:
        return 0.0
    delta = date.today() - d
    return delta.days / 30.4375


def _velocity_weight(v: str | None) -> float:
    return {"high": 2.0, "medium": 1.0, "low": 0.4}.get(v or "medium", 1.0)


def _compute_staleness(r: dict) -> tuple[float, dict]:
    months = _months_since(r.get("reviewed"))
    vw = _velocity_weight(r.get("topic_velocity"))
    inbound = json.loads(r.get("inbound") or "[]")
    orphan = 1 if not inbound else 0
    # source_version_drift and corroboration_loss would require external checks;
    # default to 0 here (can be flagged manually in future)
    drift = 0
    loss = 0
    staleness = 0.4 * months * vw + 0.2 * drift + 0.2 * orphan + 0.2 * loss
    return staleness, {
        "months_since_reviewed": round(months, 2),
        "velocity_weight": vw,
        "orphan": orphan,
        "source_version_drift": drift,
        "corroboration_loss": loss,
    }


def cmd_review(args: argparse.Namespace) -> int:
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, path, reviewed, topic_velocity, inbound, topics "
        "FROM entries WHERE status != 'archived'"
    ).fetchall()]
    conn.close()
    scored = []
    for r in rows:
        s, breakdown = _compute_staleness(r)
        if args.topic and args.topic not in json.loads(r.get("topics") or "[]"):
            continue
        scored.append({**r, "staleness": round(s, 3), "breakdown": breakdown})
    scored.sort(key=lambda x: x["staleness"], reverse=True)
    top = scored[: args.n]

    if args.json:
        print(json.dumps(top, indent=2, default=str))
    else:
        if not top:
            print("No entries.")
        else:
            print(f"{'Score':>6}  {'Slug':50s}  {'Reviewed':10s}  {'Velocity':8s}  Title")
            for r in top:
                print(f"{r['staleness']:6.2f}  {r['slug']:50s}  {r['reviewed']:10s}  "
                      f"{(r.get('topic_velocity') or 'medium'):8s}  {r['title']}")

    # Write review-due.md
    lines = ["# Review Due\n", f"Last rebuilt: {today_iso()}. Top {len(top)} stale entries.\n\n",
             "| Staleness | Slug | Title | Reviewed | Velocity | Orphan |\n",
             "|---|---|---|---|---|---|\n"]
    for r in top:
        lines.append(
            f"| {r['staleness']} | [`{r['slug']}`]({r['path']}) | {r['title']} | "
            f"{r['reviewed']} | {r.get('topic_velocity') or 'medium'} | "
            f"{'yes' if r['breakdown']['orphan'] else 'no'} |\n"
        )
    content_path("review-due.md").write_text("".join(lines))
    return 0


# ---------- compress ----------

def cmd_compress(args: argparse.Namespace) -> int:
    """Archive current Raw section for later reversal. Notes/TL;DR regeneration
    is left to Claude to perform via subsequent edit; this subcommand handles the
    reversible archival mechanic."""
    ensure_db()
    conn = db_connect()
    row = conn.execute("SELECT path FROM entries WHERE slug = ?", (args.slug,)).fetchone()
    if not row:
        print(f"ERROR: no entry: {args.slug}", file=sys.stderr)
        conn.close()
        return 2
    entry_path = Path(row["path"])
    conn.close()

    if not entry_path.exists():
        print(f"ERROR: entry file missing: {entry_path}", file=sys.stderr)
        return 2

    text = entry_path.read_text()
    fm, body = parse_frontmatter(text)
    sections = split_sections(body)

    # Archive pre-compress Raw content
    archive_raw = content_path("archive", "raw", f"{args.slug}.md")
    archive_raw.parent.mkdir(parents=True, exist_ok=True)
    ts = now_iso()
    archive_content = (
        f"---\nslug: {args.slug}\npre_compress_timestamp: {ts}\n---\n"
        f"## Raw (pre-compression)\n\n{sections['raw']}\n"
    )
    if archive_raw.exists():
        # Append
        archive_raw.write_text(archive_raw.read_text() + f"\n---\n\n{archive_content}")
    else:
        archive_raw.write_text(archive_content)

    # Log compression event
    log = index_path("verifier-log", args.slug)
    log.mkdir(parents=True, exist_ok=True)
    (log / f"compress-{ts.replace(':', '-')}.json").write_text(json.dumps({
        "event": "compress",
        "timestamp": ts,
        "raw_bytes_before": len(sections["raw"]),
        "archived_to": str(archive_raw),
    }, indent=2))

    # Trim Raw to a placeholder — Claude will rewrite with per-source summaries
    new_raw = (
        f"> Raw compressed {today_iso()}. Originals: [[archive/raw/{args.slug}]]\n\n"
        f"[Claude: regenerate per-source 2–3 sentence summaries here, preserving URLs and "
        f"capture dates from the archived Raw.]\n"
    )
    new_body = re.sub(
        r"(## Raw\n)(.*?)(?=\n## |\Z)",
        lambda m: f"{m.group(1)}\n{new_raw}\n",
        body,
        count=1,
        flags=re.DOTALL,
    )
    if new_body == body:
        # No Raw section found — append placeholder
        new_body = body.rstrip() + f"\n\n## Raw\n\n{new_raw}"
    fm["reviewed"] = today_iso()
    entry_path.write_text(dump_frontmatter(fm, new_body))
    _reingest(entry_path)
    print(f"Compressed {args.slug}")
    print(f"  Original Raw archived to: {archive_raw}")
    print(f"  Now have Claude edit the entry to regenerate per-source summaries.")
    return 0


# ---------- extract (Omniparse-only router) ----------
#
# Single backend: @tyroneross/omniparse CLI (Node.js, user-authored, MIT).
# Handles PDF, Excel, PPTX, Python, and directories. HTML URLs and plain
# text formats (.md/.txt/.json/.yaml) are routed to Claude's built-in tools
# (WebFetch, Read) with a clear message — no extraction needed.
#
# All successful extracts flow through a SHA-256 content-hash cache at
# <index-root>/.extract-cache/<hash>-<flags>.md so re-reads are instant.
# --no-cache bypasses.

EXTRACT_CACHE_DIR = index_path(".extract-cache")

# Extensions Omniparse handles (PDF included).
OMNIPARSE_EXTS = {
    ".pdf",
    ".xlsx", ".xls", ".csv", ".tsv", ".ods", ".xlsb",
    ".pptx",
    ".py",
}

# Read-native formats — caller should use Claude's Read tool directly.
READ_NATIVE_EXTS = {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}

# Vendored Omniparse CLI — self-contained build lives alongside this script.
# Re-vendor by following vendor/omniparse/BUILD.md.
PLUGIN_ROOT = Path(__file__).resolve().parent
VENDORED_OMNIPARSE_BIN = PLUGIN_ROOT / "vendor" / "omniparse" / "dist" / "bin" / "omniparse.js"


def _find_omniparse() -> list[str] | None:
    """Command list to invoke Omniparse CLI, or None if unavailable.
    Resolution order:
      1. `omniparse` on PATH (allows a user-installed global override).
      2. Vendored self-contained build at vendor/omniparse/dist/bin/omniparse.js
         invoked via `node`.
    The research plugin ships a pre-built, self-contained vendored copy, so
    (2) is the primary code path. No node_modules install is required.
    """
    exe = shutil.which("omniparse")
    if exe:
        return [exe]
    node = shutil.which("node")
    if node and VENDORED_OMNIPARSE_BIN.exists():
        return [node, str(VENDORED_OMNIPARSE_BIN)]
    return None


def _cache_flag_signature(args: argparse.Namespace) -> str:
    """Stable representation of the Omniparse-affecting flags for cache key."""
    parts = [
        f"f={args.format or ''}",
        f"r={int(bool(args.recursive))}",
        f"sheet={args.sheet or ''}",
        f"no_notes={int(bool(args.no_notes))}",
    ]
    return "|".join(parts)


def _cache_key(path: Path, flag_sig: str) -> str:
    """SHA-256 of file bytes + flag signature; hex. Stable across runs.
    For directories, hashes a listing of (name, size, mtime) tuples."""
    h = hashlib.sha256()
    if path.is_dir():
        entries = []
        for p in sorted(path.rglob("*")):
            if p.is_file():
                st = p.stat()
                entries.append(f"{p.relative_to(path)}:{st.st_size}:{int(st.st_mtime)}")
        h.update("\n".join(entries).encode())
    else:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    h.update(flag_sig.encode())
    return h.hexdigest()


def _cache_get(key: str) -> str | None:
    p = EXTRACT_CACHE_DIR / f"{key}.md"
    if p.exists():
        return p.read_text()
    return None


def _cache_put(key: str, markdown: str) -> None:
    EXTRACT_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (EXTRACT_CACHE_DIR / f"{key}.md").write_text(markdown)


def _run_omniparse(args: argparse.Namespace, path: Path) -> tuple[int, str | None]:
    """Invoke Omniparse CLI. Returns (exit_code, captured_stdout_or_None).
    stdout is captured so we can both emit it and cache it. When --output is
    set, we pass -o through and return (rc, None)."""
    cmd_prefix = _find_omniparse()
    if cmd_prefix is None:
        print(
            "ERROR: Omniparse CLI not found. The vendored copy at\n"
            f"  {VENDORED_OMNIPARSE_BIN}\n"
            "is missing or `node` is not on PATH. Install Node.js >=18, or\n"
            "rebuild the vendored dist by following:\n"
            f"  {PLUGIN_ROOT / 'vendor' / 'omniparse' / 'BUILD.md'}",
            file=sys.stderr,
        )
        return 3, None

    cli = list(cmd_prefix) + [str(path)]
    if args.format:
        cli += ["-f", args.format]
    if args.recursive:
        cli += ["-r"]
    if args.output:
        cli += ["-o", args.output]
    if args.quiet:
        cli += ["-q"]
    if args.sheet:
        cli += ["--sheet", args.sheet]
    if args.no_notes:
        cli += ["--no-notes"]

    try:
        proc = subprocess.run(cli, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        print("ERROR: Omniparse timed out (180s)", file=sys.stderr)
        return 4, None
    except FileNotFoundError as e:
        print(f"ERROR: could not invoke Omniparse: {e}", file=sys.stderr)
        return 4, None

    if proc.stderr and not args.quiet:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        return proc.returncode, None
    if args.output:
        print(f"Wrote {args.output}", file=sys.stderr)
        return 0, None
    return 0, proc.stdout


def cmd_extract(args: argparse.Namespace) -> int:
    target = args.target

    if target.startswith(("http://", "https://")):
        print(
            "This is a URL. Use Claude's WebFetch tool for HTML pages. If you "
            "downloaded the file locally, re-run with the local path.",
            file=sys.stderr,
        )
        return 2

    path = Path(target).expanduser().resolve()
    if not path.exists():
        print(f"ERROR: path does not exist: {path}", file=sys.stderr)
        return 2

    # Directory: Omniparse walks recursively when -r is passed.
    if path.is_dir():
        if not args.recursive:
            print(
                f"'{path}' is a directory. Pass -r/--recursive to process its "
                f"contents (Omniparse walks and concatenates).",
                file=sys.stderr,
            )
            return 2
        return _extract_and_cache(args, path)

    ext = path.suffix.lower()

    # Route HTML and plain-text formats back to Claude's built-in tools.
    if ext in (".html", ".htm"):
        print(
            "Local HTML file. Use WebFetch for URLs, or Read for a local HTML "
            "file — Omniparse does not add value here.",
            file=sys.stderr,
        )
        return 2
    if ext in READ_NATIVE_EXTS:
        print(
            f"'{ext}' files are best handled by Claude's Read tool directly "
            f"(no extraction needed).",
            file=sys.stderr,
        )
        return 2
    if ext not in OMNIPARSE_EXTS:
        supported = ", ".join(sorted(OMNIPARSE_EXTS))
        print(
            f"Extension '{ext}' is not supported by Omniparse. Supported: "
            f"{supported}. For .md/.txt/.json/.yaml use Claude's Read tool.",
            file=sys.stderr,
        )
        return 2

    return _extract_and_cache(args, path)


def _extract_and_cache(args: argparse.Namespace, path: Path) -> int:
    """Cache-aware Omniparse dispatch. Streams stdout OR writes --output."""
    flag_sig = _cache_flag_signature(args)
    use_cache = not args.no_cache and args.output is None

    if use_cache:
        key = _cache_key(path, flag_sig)
        cached = _cache_get(key)
        if cached is not None:
            if not args.quiet:
                print(f"(cache hit: {key[:12]})", file=sys.stderr)
            sys.stdout.write(cached)
            return 0

    rc, captured = _run_omniparse(args, path)
    if rc != 0:
        return rc

    if captured is not None:
        sys.stdout.write(captured)
        if use_cache:
            _cache_put(_cache_key(path, flag_sig), captured)
    return 0


# ---------- recategorize ----------

def _infer_subprefix(slug: str, top: str) -> str:
    """Given a slug like 'prompting.techniques.few-shot', return 'prompting.techniques' (one level deeper than top)."""
    rest = slug[len(top) + 1:] if slug.startswith(top + ".") else slug
    parts = rest.split(".")
    if len(parts) <= 1:
        # No deeper segment; use the slug itself as a leaf marker
        return f"{top}.<leaf>"
    return f"{top}.{parts[0]}"


def cmd_recategorize(args: argparse.Namespace) -> int:
    """Read-only suggestion mode by default. With --apply --plan <file>, perform moves."""
    ensure_db()
    conn = db_connect()
    rows = [dict(r) for r in conn.execute(
        "SELECT slug, title, topics, tldr FROM entries WHERE status != 'archived' ORDER BY slug"
    ).fetchall()]
    conn.close()

    by_top: dict[str, list[dict]] = {}
    for r in rows:
        by_top.setdefault(top_level_topic(r["slug"]), []).append(r)

    suggestions: list[dict] = []
    for top, entries in sorted(by_top.items()):
        if len(entries) <= args.threshold:
            continue
        # Cluster by inferred sub-prefix
        clusters: dict[str, list[str]] = {}
        for e in entries:
            sub = _infer_subprefix(e["slug"], top)
            clusters.setdefault(sub, []).append(e["slug"])
        suggestion = {
            "top_level": top,
            "current_count": len(entries),
            "proposed_clusters": {k: sorted(v) for k, v in sorted(clusters.items(), key=lambda x: -len(x[1]))},
        }
        suggestions.append(suggestion)

    if args.json:
        print(json.dumps({"threshold": args.threshold, "suggestions": suggestions}, indent=2))
        return 0

    if not suggestions:
        print(f"No top-level topics exceed threshold of {args.threshold} entries.")
        return 0

    print(f"# Recategorization suggestions (threshold: {args.threshold} entries per top-level)\n")
    for s in suggestions:
        proposals = ", ".join(f"{k}.* ({len(v)})" for k, v in s["proposed_clusters"].items())
        print(f"- {s['top_level']}/ has {s['current_count']} entries \u2014 consider splitting: {proposals}")
        for cluster_name, slugs in s["proposed_clusters"].items():
            print(f"    {cluster_name}:")
            for sl in slugs:
                print(f"      - {sl}")
        print()

    if args.apply:
        if not args.plan:
            print("ERROR: --apply requires --plan <file.json> with explicit slug renames.", file=sys.stderr)
            return 2
        plan_path = Path(args.plan).expanduser().resolve()
        if not plan_path.exists():
            print(f"ERROR: plan file not found: {plan_path}", file=sys.stderr)
            return 2
        try:
            plan = json.loads(plan_path.read_text())
        except json.JSONDecodeError as e:
            print(f"ERROR: invalid JSON in plan: {e}", file=sys.stderr)
            return 2
        if not isinstance(plan, dict) or "renames" not in plan:
            print("ERROR: plan must be {\"renames\": {\"old.slug\": \"new.slug\", ...}}", file=sys.stderr)
            return 2
        renames = plan["renames"]
        moved = 0
        conn = db_connect()
        for old_slug, new_slug in renames.items():
            row = conn.execute("SELECT path FROM entries WHERE slug = ?", (old_slug,)).fetchone()
            if not row:
                print(f"  SKIP: {old_slug} (not in DB)")
                continue
            old_path = Path(row["path"])
            if not old_path.exists():
                print(f"  SKIP: {old_slug} (file missing)")
                continue
            new_top = top_level_topic(new_slug)
            new_path = content_path("topics", new_top, f"{new_slug}.md")
            new_path.parent.mkdir(parents=True, exist_ok=True)
            text = old_path.read_text()
            fm, body = parse_frontmatter(text)
            fm["slug"] = new_slug
            new_path.write_text(dump_frontmatter(fm, body))
            # Leave a redirect stub at the old location
            old_path.write_text(
                f"---\nstatus: archived\nredirect: ../../topics/{new_top}/{new_slug}.md\n"
                f"archived: {today_iso()}\n---\nMoved to [[{new_slug}]] via recategorize.\n"
            )
            conn.execute(
                "UPDATE entries SET slug = ?, path = ? WHERE slug = ?",
                (new_slug, str(new_path), old_slug),
            )
            moved += 1
            print(f"  MOVED: {old_slug} -> {new_slug}")
        conn.commit()
        conn.close()
        if moved:
            _rebuild_indexes()
            _rebuild_portfolio()
        print(f"\nApplied {moved} renames.")
    else:
        print("Read-only mode. To apply, build a JSON plan and re-run with: --apply --plan <plan.json>")
        print('Plan format: {"renames": {"old.slug": "new.slug", ...}}')
    return 0


# ---------- ingest ----------

def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s.-]", "", s)
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-.")
    return s or "untitled"


def _draft_entry_from_md(path: Path, project: str | None, topics: list[str]) -> dict:
    """Deterministic extraction: title from first H1 or filename, slug from filename."""
    text = path.read_text()
    # If it already has frontmatter, keep it; otherwise derive
    fm, body = parse_frontmatter(text)
    if not fm:
        body = text
        h1 = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
        title = h1.group(1).strip() if h1 else path.stem
        slug_base = _slugify(path.stem)
        # If no topic specified, use first slug segment or "ingest"
        top = topics[0] if topics else "ingest"
        slug = slug_base if "." in slug_base else f"{top}.{slug_base}"
        fm = {
            "slug": slug,
            "title": title,
            "topics": topics or [top],
            "projects": [project] if project else [],
            "status": "fleeting",
            "workflow": "general",
            "created": today_iso(),
            "reviewed": today_iso(),
            "topic_velocity": "medium",
            "tags": [],
            "confidence": "inferred",
            "corroboration": 0,
            "sources": [],
            "related": [],
            "inbound": [],
        }
    else:
        # Augment existing frontmatter
        if project and project not in (fm.get("projects") or []):
            fm.setdefault("projects", []).append(project)
        for t in topics:
            if t not in (fm.get("topics") or []):
                fm.setdefault("topics", []).append(t)
    # Ensure body has the three sections; if not, treat existing body as Notes
    if "## TL;DR" not in body and "## Notes" not in body and "## Raw" not in body:
        body = (
            "## TL;DR\n\n_Pending synthesis._\n\n"
            "## Notes\n\n" + body.strip() + "\n\n"
            "## Raw\n\n_Source preserved at ingest path._\n"
        )
    return {"frontmatter": fm, "body": body, "source_path": str(path)}


def cmd_ingest(args: argparse.Namespace) -> int:
    src = Path(args.path).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: path not found: {src}", file=sys.stderr)
        return 2

    if args.inbox:
        # Just copy raw files to the content-root inbox, no draft, no save
        ensure_layout()
        inbox = content_path("inbox")
        inbox.mkdir(parents=True, exist_ok=True)
        copied = 0
        files = [src] if src.is_file() else [p for p in src.rglob("*.md")]
        for f in files:
            dest = inbox / f.name
            # If collision, suffix
            n = 2
            while dest.exists():
                dest = inbox / f"{f.stem}-{n}{f.suffix}"
                n += 1
            shutil.copy2(f, dest)
            copied += 1
            print(f"  inbox: {dest}")
        print(f"\nCopied {copied} file(s) to {inbox}")
        return 0

    topics = [t.strip() for t in (args.topics or "").split(",") if t.strip()]
    files = [src] if src.is_file() else sorted(src.rglob("*.md"))
    if not files:
        print(f"No markdown files found at {src}", file=sys.stderr)
        return 1

    drafts: list[dict] = []
    for f in files:
        if not f.suffix.lower() in (".md", ".markdown"):
            continue
        draft = _draft_entry_from_md(f, args.project, topics)
        drafts.append(draft)

    if args.json:
        print(json.dumps(drafts, indent=2, default=str))
    else:
        for d in drafts:
            fm = d["frontmatter"]
            print(f"\n--- DRAFT: {fm['slug']} (from {d['source_path']}) ---")
            print(dump_frontmatter(fm, d["body"]))

    if args.save:
        ensure_layout()
        ensure_db()
        saved = 0
        for d in drafts:
            fm = d["frontmatter"]
            tmp = content_path("inbox", f".ingest-{fm['slug']}.md")
            tmp.parent.mkdir(parents=True, exist_ok=True)
            tmp.write_text(dump_frontmatter(fm, d["body"]))
            # Reuse cmd_save by faking args
            class _A:
                file = str(tmp)
                move_source = True
                skip_symlink = False
                skip_index = False
                no_index = False
                with_project_index = False
            cmd_save(_A())  # type: ignore[arg-type]
            saved += 1
        print(f"\nSaved {saved} draft(s).")
    else:
        print("\n(dry run \u2014 pass --save to persist; or pipe to /research:save manually)")
    return 0


# ---------- main / argparse ----------

def main() -> int:
    ap = argparse.ArgumentParser(prog="research.py", description="Central research knowledge base.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("init", help="Bootstrap research content and index roots")
    sp.add_argument("--refresh-seeds", action="store_true", help="Re-apply seed data (preserves manual overrides)")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("save", help="Persist a markdown entry file")
    sp.add_argument("--file", required=True, help="Path to entry markdown with frontmatter")
    sp.add_argument("--move-source", action="store_true", help="Delete source file after copy to canonical path")
    sp.add_argument("--skip-symlink", action="store_true", help="Do not create project copy/symlink (used by hook)")
    sp.add_argument("--skip-index", action="store_true", help="Do not rebuild any indexes (legacy alias of --no-index)")
    sp.add_argument("--no-index", action="store_true", help="Skip per-project index + PORTFOLIO.md regen on this save")
    sp.add_argument(
        "--with-project-index",
        action="store_true",
        help="Opt-in: also regenerate <project>/RossLabs-Research.md (writes into the project dir)",
    )
    sp.set_defaults(func=cmd_save)

    sp = sub.add_parser("search", help="Full-text search (FTS5 + BM25)")
    sp.add_argument("query")
    sp.add_argument("--tag")
    sp.add_argument("--topic")
    sp.add_argument("--project")
    sp.add_argument("--status")
    sp.add_argument("-n", type=int, default=20)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("list", help="Recent entries")
    sp.add_argument("-n", type=int, default=20)
    sp.add_argument("--status")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("link", help="Retroactive project symlink")
    sp.add_argument("slug")
    sp.add_argument("project_path", nargs="?", help="Defaults to cwd")
    sp.set_defaults(func=cmd_link)

    sp = sub.add_parser(
        "link-project",
        help="Register an existing project research directory (v0.3.1). "
        "Walks recursively, extracts title+summary, symlinks into the content-root projects dir.",
    )
    sp.add_argument("name", help="Short project name used for the symlink dir and registry key")
    sp.add_argument("path_arg", nargs="?", help="Path to the research directory to link")
    sp.add_argument("--path", help="Absolute path to the research directory to link")
    sp.add_argument("--no-index", action="store_true", help="Skip PORTFOLIO.md regen on this call")
    sp.set_defaults(func=cmd_link_project)

    sp = sub.add_parser("sync", help="Rebuild SQLite from canonical topic markdown")
    sp.add_argument("--prune-missing", action="store_true", help="Delete DB rows whose slug is not present under topics/")
    sp.add_argument("--no-index", action="store_true", help="Skip markdown index and symlink refresh after DB sync")
    sp.set_defaults(func=cmd_sync)

    sp = sub.add_parser("index", help="Rebuild markdown indexes + MOCs")
    sp.set_defaults(func=cmd_index)

    sp = sub.add_parser("archive", help="Move entry to archive, leave redirect stub")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_archive)

    sp = sub.add_parser("score", help="Inspect or set a domain's tier")
    sp.add_argument("domain", help="Domain or URL")
    sp.add_argument("--tier", choices=["T1", "T2", "T3", "T4"])
    sp.add_argument("--reason")
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("verify", help="Run claim verification on an entry")
    sp.add_argument("slug")
    sp.add_argument("--atoms", help="Path to atoms JSON (default: <entry-dir>/<slug>.atoms.json)")
    sp.add_argument("--atom", help="Run a single atom by atom_id")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_verify)

    sp = sub.add_parser("table-profile", help="Profile a CSV/TSV/JSON table for quantitative analysis")
    sp.add_argument("input", help="Path to .csv, .tsv, .json, or .jsonl")
    sp.add_argument("--sample", type=int, default=5, help="Number of sample rows to include")
    sp.add_argument("-o", "--output", help="Write profile JSON to this path")
    sp.set_defaults(func=cmd_table_profile)

    sp = sub.add_parser("db-profile", help="Profile a SQLite database schema and tables")
    sp.add_argument("db", help="Path to .sqlite, .sqlite3, or .db")
    sp.add_argument("--sample", type=int, default=5, help="Number of sample rows per table")
    sp.add_argument("-o", "--output", help="Write profile JSON to this path")
    sp.set_defaults(func=cmd_db_profile)

    sp = sub.add_parser("analyze-plan", help="Create a stdlib Python analysis plan and script")
    sp.add_argument("--input", action="append", required=True, help="Input file; repeat for multiple inputs")
    sp.add_argument("--question", required=True, help="Quantitative/database question to answer")
    sp.add_argument("--name", help="Run name suffix")
    sp.add_argument("--sample", type=int, default=5, help="Sample rows for profiles")
    sp.add_argument("--out-dir", help="Write analysis artifacts to this directory")
    sp.set_defaults(func=cmd_analyze_plan)

    sp = sub.add_parser("analyze-run", help="Run a generated quantitative analysis plan")
    sp.add_argument("--plan", required=True, help="Path to analysis-plan.yaml")
    sp.add_argument("--timeout", type=int, default=30, help="Execution timeout in seconds")
    sp.add_argument("--allow-modified-script", action="store_true", help="Run even if analysis.py differs from the plan hash")
    sp.set_defaults(func=cmd_analyze_run)

    sp = sub.add_parser("review", help="Surface stale entries")
    sp.add_argument("-n", type=int, default=20)
    sp.add_argument("--topic")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_review)

    sp = sub.add_parser("compress", help="Archive Raw, prep for Claude rewrite")
    sp.add_argument("slug")
    sp.set_defaults(func=cmd_compress)

    sp = sub.add_parser("recategorize", help="Suggest top-level taxonomy splits (read-only by default)")
    sp.add_argument("--threshold", type=int, default=8, help="Min entries per top-level before suggesting a split")
    sp.add_argument("--apply", action="store_true", help="Apply slug renames from --plan")
    sp.add_argument("--plan", help="JSON file with {\"renames\": {old: new, ...}}")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_recategorize)

    sp = sub.add_parser("ingest", help="Bulk ingest markdown files; print drafts (or --save)")
    sp.add_argument("path", help="File or directory of .md files")
    sp.add_argument("--project", help="Auto-tag drafts with this project")
    sp.add_argument("--topics", help="Comma-separated topics for drafts")
    sp.add_argument("--inbox", action="store_true", help="Just copy files to the content-root inbox, no draft/save")
    sp.add_argument("--save", action="store_true", help="Persist each draft via the normal save flow")
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser(
        "extract",
        help="Extract PDF / Excel / PPTX / Python / directory via Omniparse (cached)",
        description=(
            "Routes all extraction through @tyroneross/omniparse. HTML URLs and "
            ".md/.txt/.json/.yaml files are rejected with a pointer to "
            "Claude's WebFetch/Read tools. Results are cached at "
            "<index-root>/.extract-cache/ keyed by file SHA-256 + flag signature."
        ),
    )
    sp.add_argument("target", help="Local file path or directory (URLs are rejected — use WebFetch)")
    sp.add_argument("--no-cache", action="store_true", help="Skip content-hash cache (force re-extract)")
    sp.add_argument("-f", "--format", choices=["markdown", "text", "json"], help="Output format for Omniparse (default: markdown)")
    sp.add_argument("-o", "--output", help="Write to file instead of stdout")
    sp.add_argument("-r", "--recursive", action="store_true", help="Process directory contents (required for directories)")
    sp.add_argument("-q", "--quiet", action="store_true", help="Suppress progress messages")
    sp.add_argument("--sheet", help="Excel: specific sheet name")
    sp.add_argument("--no-notes", action="store_true", help="PPTX: exclude speaker notes")
    sp.set_defaults(func=cmd_extract)

    args = ap.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
