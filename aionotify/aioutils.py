# Copyright (c) 2016 The aionotify project
# This code is distributed under the two-clause BSD License.

import anyio
import errno
import logging
import os

logger = logging.getLogger('aionotify.aioutils')


class UnixFileDescriptorStream:
    """
    A simple buffering adapter from a Unix file descriptor to an anyio bytestream.

    This class takes ownership of the descriptor.
    """
    max_size = 4096

    def __init__(self, fileno):
        super().__init__()
        self._fileno = fileno
        self._buf = b""
        self._pos = 0

    async def read(self, nbytes):
        """whenever the fd is ready for reading."""

        if not self._buf:
            await anyio.wait_readable(self._fileno)
            self._buf = os.read(self._fileno, self.max_size)

        pos = self._pos
        res = self._buf[pos:pos+nbytes]
        pos += nbytes
        if pos >= len(self._buf):
            self.pos = 0
            self._buf = b''
        else:
            self._pos = pos
        return res

    async def aclose(self):
        os.close(self._fileno)
        self._fileno = None

    def __repr__(self):
        parts = [
            self.__class__.__name__,
            'fd=%s' % self._fileno,
        ]
        return '<%s>' % ' '.join(parts)

