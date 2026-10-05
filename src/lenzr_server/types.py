from typing import Annotated, Literal

from pydantic import StringConstraints

UploadID = Annotated[
    str,
    StringConstraints(min_length=1, max_length=32, strict=True),
]

TagName = Annotated[
    str,
    StringConstraints(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9\-]*$", strict=True),
]

# Ordered best to worst: search ranks matches by position in this list.
MatchType = Literal["exact", "prefix", "substring", "fuzzy", "semantic"]

SemanticStatus = Literal["active", "disabled"]
