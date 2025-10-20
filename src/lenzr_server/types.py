from typing import Annotated

from pydantic import StringConstraints

UploadID = Annotated[
    str,
    StringConstraints(min_length=1, max_length=32, strict=True),
]
