from pathlib import Path, PurePosixPath
import sys
from typing import (BinaryIO,
                    Literal,
                    NewType,
                    Optional,
                    Sequence,
                    TextIO,
                    Type,
                    TypeVar,
                    Union)


PathLike = Union[Path, PurePosixPath, str]


T = TypeVar('T')
OneOrMore = Union[T, Sequence[T]]
NoneOrMore = Optional[OneOrMore]    # equivalent to Union[None, OneOrMore]


MswDestBase = TypeVar('MswDestBase', BinaryIO, Path, str, TextIO)
MswStdoutDest = Union[MswDestBase, Type[type(sys.stdout)], Literal['stdout']]
MswStderrDest = Union[MswDestBase, Type[type(sys.stderr)], Literal['stderr']]


WallTimeStr = NewType('WallTimeStr', str)


# EmailAddress = NewType('EmailAddress', str)
# email_regex = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
#
# def validate_email(email_str: str) -> EmailAddress:
#     is_valid = bool(email_regex.match(email_str))
#     if not is_valid:
#         raise ValueError(
#             f"{email_str} does not appear to be formatted as a valid email "
#             f"address"
#         )
#     return EmailAddress(email_str)
