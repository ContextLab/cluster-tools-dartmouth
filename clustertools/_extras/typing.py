from pathlib import Path
import sys
from typing import BinaryIO, Literal, Optional, Sequence, TextIO, TypeVar, Union


PathLike = Union[str, Path]

T = TypeVar('T')
OneOrMore = Union[T, Sequence[T]]
NoneOrMore = Optional[OneOrMore]    # equivalent to Union[None, OneOrMore]

MswDestBase = TypeVar('MswDestBase', BinaryIO, Path, str, TextIO)
MswStdoutDest = Union[MswDestBase, sys.stdout, Literal['stdout']]
MswStderrDest = Union[MswDestBase, sys.stderr, Literal['stderr']]
