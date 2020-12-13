from pathlib import Path, PurePosixPath
import sys
from typing import (
    BinaryIO,
    Dict,
    Literal,
    Optional,
    Sequence,
    TextIO,
    TypeVar,
    Union
)


PathLike = Union[Path, PurePosixPath, str]

T = TypeVar('T')
OneOrMore = Union[T, Sequence[T]]
NoneOrMore = Optional[OneOrMore]    # equivalent to Union[None, OneOrMore]

MswDestBase = TypeVar('MswDestBase', BinaryIO, Path, str, TextIO)
MswStdoutDest = Union[MswDestBase, type(sys.stdout), Literal['stdout']]
MswStderrDest = Union[MswDestBase, type(sys.stderr), Literal['stderr']]
