import sys
from io import BufferedIOBase, BytesIO, StringIO, TextIOBase
from pathlib import Path
from typing import Sequence


class MultiStreamWrapper:
    # notes:
    # 1. sys.stdout & sys.stderr will always write strings, even when passed bytes
    # 2. always writes to files with no buffering
    def __init__(self, destinations, encoding='utf-8'):
        if destinations is None:
            destinations = tuple()
        elif (
                isinstance(destinations, (str, Path)) or
                not isinstance(destinations, Sequence)
        ):
            destinations = [destinations]

        # kwargs passed to built-in open for path-like destinations
        if encoding is None:
            # binary content
            memory_stream_class = BytesIO
            file_io_kwargs = {'mode': 'wb', 'buffering': 0}
        else:
            # string content
            memory_stream_class = StringIO
            file_io_kwargs = {'mode': 'w', 'buffering': 1}

        self.closed = False
        # holds content of self.memory_stream after closing for persisting access
        self.final = None
        self.memory_stream = memory_stream_class()
        self.streams = list()
        # minimum attrs/methods necessary for IOBase subclass or
        # user-defined stream to be supported
        min_required_attrs = ('write', 'close', 'closed')
        for s in destinations:
            if (
                    s in (sys.stdout, sys.stderr) or
                    all(hasattr(s, a) for a in min_required_attrs)
            ):
                # stream is valid as-is
                pass
            elif s == 'stdout':
                s = sys.stdout
            elif s == 'stderr':
                s = sys.stderr
            elif isinstance(s, (str, Path)):
                try:
                    s = open(s, encoding=encoding, **file_io_kwargs)
                except:
                    self.close()
                    raise
            else:
                self.close()
                raise ValueError(f"Invalid stream type: {type(s)}")

            self.streams.append(s)

        self._all_streams = [self.memory_stream] + self.streams

    def __repr__(self):
        status = 'closed' if self.closed else 'open'
        streams = ', '.join([str(s) for s in self._all_streams])
        return f"MultiStreamWrapper(status={status}, streams={streams}\noutput={self})"

    def __str__(self):
        return self.output

    @property
    def output(self):
        if self.closed:
            return self.final
        else:
            return self.memory_stream.getvalue()

    def close(self):
        self.final = self.memory_stream.getvalue()
        for stream in self._all_streams:
            if stream not in (sys.stdout, sys.stderr):
                stream.close()

        self.closed = True

    def write(self, data):
        for stream in self._all_streams:
            stream.write(data)
