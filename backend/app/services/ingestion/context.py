"""Document context for chunks.

A chunk taken out of its document often loses what it is about: "Each employee gets 27 days of
leave" does not say *which company*. A question that names the company then matches other
chunks that happen to contain the name, and misses the one holding the answer.

Remedy: before computing a chunk's embedding (and before reranking), prepend the document's
title to its text. The stored and displayed content stays the original text.
"""

import re
from pathlib import PurePath


def document_title(filename: str) -> str:
    """ "guide-salarie_novalia.pdf" -> "guide salarie novalia" """
    return re.sub(r"[-_\s]+", " ", PurePath(filename).stem).strip()


def contextualize(filename: str, text: str) -> str:
    return f"Document : {document_title(filename)}\n{text}"
