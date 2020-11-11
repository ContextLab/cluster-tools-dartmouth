from pathlib import Path
from typing import Sequence, TypeVar, Union


__all__ = ('PathLike', 'OneOrMore')

PathLike = Union[str, Path]

T = TypeVar('T')
OneOrMore = Union[T, Sequence[T]]