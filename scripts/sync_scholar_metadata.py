#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote, unquote

DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
TITLE_RE = re.compile(r'^title:\s*(.+)$', re.M)
DATE_RE = re.compile(r'^date:\s*(.+)$', re.M)
DRAFT_RE = re.compile(r'^draft:\s*true\s*$', re.I | re.M)
FIELD_LINE_RE = re.compile(r'^(journal|doi|pdf_url):\s*.*$')
LIST_ITEM_RE = re.compile(r'^\s*-\s+')
INDENTED_RE = re.compile(r'^\s+')


@dataclass
class BibEntry:
    key: str
    entry_type: str
    fields: Dict[str, str]

    @property
    def doi(self) -> str:
        return normalize_doi(self.fields.get("doi", ""))

    @property
    def journal(self) -> str:
        return clean_inline_text(self.fields.get("journal", "") or self.fields.get("booktitle", ""))

    @property
    def authors(self) -> List[str]:
        raw = strip_outer_wrapping(self.fields.get("author", ""))
        return [clean_author_name(part) for part in split_top_level(raw, " and ") if clean_author_name(part)]

    @property
    def title(self) -> str:
        return clean_inline_text(self.fields.get("title", ""))


def normalize_doi(value: str) -> str:
    value = value.strip()
    value = re.sub(r'^https?://(dx\.)?doi\.org/', '', value, flags=re.I)
    return value.lower().strip('{} ')


def clean_inline_text(value: str) -> str:
    value = value.strip().strip(',')
    value = strip_outer_wrapping(value)
    value = value.replace('\n', ' ')
    value = value.replace('{', '').replace('}', '')
    value = re.sub(r'\s+', ' ', value)
    return value.strip()


def strip_outer_wrapping(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and ((value[0] == '{' and value[-1] == '}') or (value[0] == '"' and value[-1] == '"')):
        return value[1:-1].strip()
    return value


def clean_author_name(value: str) -> str:
    value = clean_inline_text(value)
    if ',' in value:
        last, first = [part.strip() for part in value.split(',', 1)]
        return f"{first} {last}".strip()
    return value


def split_top_level(text: str, delimiter: str) -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth = max(depth - 1, 0)
        if depth == 0 and text.startswith(delimiter, i):
            parts.append(''.join(buf))
            buf = []
            i += len(delimiter)
            continue
        buf.append(ch)
        i += 1
    parts.append(''.join(buf))
    return parts


def parse_bibtex(text: str) -> List[BibEntry]:
    entries: List[BibEntry] = []
    i = 0
    while True:
        start = text.find('@', i)
        if start == -1:
            break
        brace_start = text.find('{', start)
        if brace_start == -1:
            break
        entry_type = text[start + 1:brace_start].strip().lower()
        depth = 1
        j = brace_start + 1
        while j < len(text) and depth:
            if text[j] == '{':
                depth += 1
            elif text[j] == '}':
                depth -= 1
            j += 1
        body = text[brace_start + 1:j - 1].strip()
        i = j
        if ',' not in body:
            continue
        key, fields_blob = body.split(',', 1)
        key = key.strip()
        fields = parse_bib_fields(fields_blob)
        entries.append(BibEntry(key=key, entry_type=entry_type, fields=fields))
    return entries


def parse_bib_fields(blob: str) -> Dict[str, str]:
    fields: Dict[str, str] = {}
    i = 0
    while i < len(blob):
        while i < len(blob) and blob[i] in ' \t\r\n,':
            i += 1
        if i >= len(blob):
            break
        eq = blob.find('=', i)
        if eq == -1:
            break
        name = blob[i:eq].strip().lower()
        i = eq + 1
        while i < len(blob) and blob[i].isspace():
            i += 1
        if i >= len(blob):
            break
        if blob[i] == '{':
            depth = 1
            j = i + 1
            while j < len(blob) and depth:
                if blob[j] == '{':
                    depth += 1
                elif blob[j] == '}':
                    depth -= 1
                j += 1
            value = blob[i:j]
            i = j
        elif blob[i] == '"':
            j = i + 1
            escaped = False
            while j < len(blob):
                ch = blob[j]
                if ch == '"' and not escaped:
                    j += 1
                    break
                escaped = (ch == '\\' and not escaped)
                if ch != '\\':
                    escaped = False
                j += 1
            value = blob[i:j]
            i = j
        else:
            j = i
            while j < len(blob) and blob[j] not in ',\n\r':
                j += 1
            value = blob[i:j]
            i = j
        fields[name] = value.strip().rstrip(',')
    return fields


def extract_front_matter(text: str) -> Tuple[str, str, str]:
    if not text.startswith('---\n'):
        raise ValueError('expected YAML front matter')
    second = text.find('\n---\n', 4)
    if second == -1:
        raise ValueError('unterminated front matter')
    front = text[4:second]
    body = text[second + 5:]
    return '---\n', front, body


def extract_doi(text: str) -> str:
    match = DOI_RE.search(text)
    return normalize_doi(match.group(0)) if match else ''


def extract_pdf_url(front_matter: str) -> str:
    existing = re.search(r'^pdf_url:\s*(.+)$', front_matter, re.M)
    if existing:
        return normalize_pdf_path(strip_yaml_scalar(existing.group(1)))

    lines = front_matter.splitlines()
    in_links = False
    current_name: Optional[str] = None
    for line in lines:
        if line.startswith('links:'):
            in_links = True
            current_name = None
            continue
        if in_links and re.match(r'^[A-Za-z_][A-Za-z0-9_]*:', line):
            in_links = False
        if not in_links:
            continue
        name_match = re.match(r'^\s*name:\s*(.+)$', line)
        if name_match:
            current_name = strip_yaml_scalar(name_match.group(1))
            continue
        url_match = re.match(r'^\s*url:\s*(.+)$', line)
        if url_match:
            raw = strip_yaml_scalar(url_match.group(1))
            if current_name and current_name.lower() == 'pdf':
                return normalize_pdf_path(raw)
            if raw.lower().endswith('.pdf') or 'publication_pdf/' in raw.lower() or 'full_texts/' in raw.lower():
                return normalize_pdf_path(raw)
    return ''


def strip_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
        value = value[1:-1]
    return value.strip()


def normalize_pdf_path(path: str) -> str:
    path = path.strip()
    if not path:
        return ''
    if re.match(r'^https?://', path, re.I):
        return path
    path = '/' + path.lstrip('/')
    return quote(unquote(path), safe='/-_.~')


def yaml_quote(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def remove_existing_scholar_fields(lines: List[str]) -> List[str]:
    cleaned: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if FIELD_LINE_RE.match(line):
            i += 1
            continue
        if re.match(r'^citation_authors:\s*$', line):
            i += 1
            while i < len(lines) and (re.match(r'^\s+-\s+', lines[i]) or re.match(r'^\s*$', lines[i])):
                i += 1
            continue
        cleaned.append(line)
        i += 1
    return cleaned


def inject_scholar_fields(front_matter: str, journal: str, doi: str, authors: List[str], pdf_url: str) -> str:
    lines = remove_existing_scholar_fields(front_matter.splitlines())
    insert_at = 0
    for idx, line in enumerate(lines):
        if line.startswith('date:') or line.startswith('draft:'):
            insert_at = idx + 1
    new_lines = [
        f'journal: {yaml_quote(journal)}',
        f'doi: {yaml_quote(doi)}',
        'citation_authors:',
        *[f'  - {yaml_quote(author)}' for author in authors],
        f'pdf_url: {yaml_quote(pdf_url)}',
    ]
    updated = lines[:insert_at] + new_lines + lines[insert_at:]
    return '\n'.join(updated) + '\n'


def build_bib_index(entries: List[BibEntry]) -> Tuple[Dict[str, BibEntry], Dict[str, List[BibEntry]]]:
    by_doi: Dict[str, BibEntry] = {}
    duplicates: Dict[str, List[BibEntry]] = defaultdict(list)
    for entry in entries:
        doi = entry.doi
        if not doi:
            continue
        if doi in by_doi:
            duplicates[doi].append(entry)
        else:
            by_doi[doi] = entry
    return by_doi, duplicates


def main() -> int:
    parser = argparse.ArgumentParser(description='Sync Hugo publication front matter with Scholar-safe metadata from a BibTeX export.')
    parser.add_argument('--bib', default='metadata/zotero-publications.bib', help='Path to Zotero/BibTeX export')
    parser.add_argument('--content-dir', default='content/publications', help='Publication content directory')
    parser.add_argument('--write', action='store_true', help='Write changes instead of reporting only')
    args = parser.parse_args()

    bib_path = Path(args.bib)
    content_dir = Path(args.content_dir)
    entries = parse_bibtex(bib_path.read_text(encoding='utf-8'))
    by_doi, duplicates = build_bib_index(entries)

    matched = 0
    changed = 0
    skipped: List[str] = []

    for path in sorted(content_dir.glob('*/index.md')):
        text = path.read_text(encoding='utf-8')
        _, front_matter, body = extract_front_matter(text)
        if DRAFT_RE.search(front_matter):
            skipped.append(f'{path}: draft')
            continue
        doi = extract_doi(front_matter + '\n' + body)
        if not doi:
            skipped.append(f'{path}: no DOI found in content')
            continue
        entry = by_doi.get(doi)
        if not entry:
            skipped.append(f'{path}: DOI not found in BibTeX ({doi})')
            continue
        journal = entry.journal
        authors = entry.authors
        pdf_url = extract_pdf_url(front_matter)
        if not journal:
            skipped.append(f'{path}: BibTeX match has no journal/booktitle')
            continue
        if not authors:
            skipped.append(f'{path}: BibTeX match has no authors')
            continue
        if not pdf_url:
            skipped.append(f'{path}: no PDF URL found in front matter links')
            continue

        matched += 1
        new_front_matter = inject_scholar_fields(front_matter, journal, doi, authors, pdf_url)
        new_text = f'---\n{new_front_matter}---\n{body}'
        if new_text != text:
            changed += 1
            if args.write:
                path.write_text(new_text, encoding='utf-8')

    print(f'BibTeX entries parsed: {len(entries)}')
    print(f'DOIs with duplicate BibTeX entries: {len(duplicates)}')
    print(f'Publication pages matched: {matched}')
    print(f'Publication pages {"updated" if args.write else "needing update"}: {changed}')
    if skipped:
        print('Skipped:')
        for item in skipped:
            print(f'  - {item}')
    if duplicates:
        print('Duplicate DOI entries in BibTeX:')
        for doi, extra in sorted(duplicates.items()):
            print(f'  - {doi}: {1 + len(extra)} entries')
    return 0


if __name__ == '__main__':
    sys.exit(main())
