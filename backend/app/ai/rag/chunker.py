"""
Code chunker — splits source files into semantic chunks by function/class boundary.

Strategy:
  - Python: split on `def ` and `class ` top-level boundaries
  - JS/TS: split on `function `, `const X = `, `class ` boundaries
  - Other: sliding window with 50-line chunks, 10-line overlap
  - Hard cap: 400 tokens (~1600 chars) per chunk to stay inside context limits
"""
import re
from dataclasses import dataclass

MAX_CHARS = 1600   # ~400 tokens
OVERLAP = 10       # lines of overlap for sliding window


@dataclass
class CodeChunk:
    file_path: str
    chunk_index: int
    content: str
    language: str


def chunk_file(file_path: str, content: str, language: str) -> list[CodeChunk]:
    """Split a source file into semantic chunks."""
    if not content.strip():
        return []

    lines = content.splitlines()

    if language in ("Python",):
        boundaries = _python_boundaries(lines)
    elif language in ("JavaScript", "TypeScript", "TSX", "JSX"):
        boundaries = _js_boundaries(lines)
    else:
        boundaries = _sliding_window(lines)

    chunks = _extract_chunks(lines, boundaries, file_path, language)
    return chunks


def _python_boundaries(lines: list[str]) -> list[int]:
    boundaries = [0]
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if (stripped.startswith("def ") or stripped.startswith("class ") or
                stripped.startswith("async def ")):
            if i > 0:
                boundaries.append(i)
    return boundaries


def _js_boundaries(lines: list[str]) -> list[int]:
    boundaries = [0]
    patterns = [
        re.compile(r"^(export\s+)?(default\s+)?(async\s+)?function\s+\w+"),
        re.compile(r"^(export\s+)?(const|let|var)\s+\w+\s*=\s*(async\s+)?\("),
        re.compile(r"^(export\s+)?(default\s+)?class\s+\w+"),
        re.compile(r"^\s*(public|private|protected|async)?\s+\w+\s*\("),
    ]
    for i, line in enumerate(lines):
        for pat in patterns:
            if pat.match(line.lstrip()):
                if i > 0:
                    boundaries.append(i)
                break
    return boundaries


def _sliding_window(lines: list[str]) -> list[int]:
    boundaries = list(range(0, len(lines), 50 - OVERLAP))
    return boundaries


def _extract_chunks(
    lines: list[str],
    boundaries: list[int],
    file_path: str,
    language: str,
) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    boundaries = sorted(set(boundaries))
    boundaries.append(len(lines))  # sentinel

    for i, start in enumerate(boundaries[:-1]):
        end = boundaries[i + 1]
        segment = "\n".join(lines[start:end]).strip()

        if not segment:
            continue

        # Hard cap — split oversized segments
        if len(segment) > MAX_CHARS:
            sub_lines = segment.splitlines()
            for j in range(0, len(sub_lines), 50):
                sub = "\n".join(sub_lines[j : j + 50]).strip()
                if sub:
                    chunks.append(CodeChunk(
                        file_path=file_path,
                        chunk_index=len(chunks),
                        content=sub,
                        language=language,
                    ))
        else:
            chunks.append(CodeChunk(
                file_path=file_path,
                chunk_index=len(chunks),
                content=segment,
                language=language,
            ))

    return chunks
