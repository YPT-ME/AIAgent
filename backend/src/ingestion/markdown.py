"""Minimal fenced-block tracking shared by metadata and section parsing."""

import re
from collections.abc import Iterator

_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


def markdown_lines(text: str) -> Iterator[tuple[str, bool]]:
    """Yield original lines and whether each is inside a fenced code block.

    A closing fence must use the same character, be at least as long as the
    opening fence, and have no info string. Both delimiter lines count as code.
    """
    fence = ""
    for line in text.splitlines(keepends=True):
        match = _FENCE.match(line.rstrip("\r\n"))
        in_code = bool(fence)
        if match:
            marker, suffix = match.groups()
            if not fence and not (marker[0] == "`" and "`" in suffix):
                fence = marker
                in_code = True
            elif (fence and marker[0] == fence[0] and len(marker) >= len(fence)
                  and not suffix.strip()):
                fence = ""
        yield line, in_code
