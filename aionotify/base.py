# Copyright (c) 2016 The aionotify project
# This code is distributed under the two-clause BSD License.

import anyio
import collections
import ctypes
import struct

from .aioutils import UnixFileDescriptorStream

Event = collections.namedtuple('Event', ['flags', 'cookie', 'name', 'alias'])


_libc = ctypes.cdll.LoadLibrary('libc.so.6')


class LibC:
    """Proxy to C functions for inotify"""
    @classmethod
    def inotify_init(cls):
        return _libc.inotify_init()

    @classmethod
    def inotify_add_watch(cls, fd, path, flags):
        return _libc.inotify_add_watch(fd, str(path).encode('utf-8'), flags)

    @classmethod
    def inotify_rm_watch(cls, fd, wd):
        return _libc.inotify_rm_watch(fd, wd)


PREFIX = struct.Struct('iIII')


class Watcher:
    max_size = 1024

    _fd: int = None
    _stream: UnixFileDescriptorStream = None

    def __init__(self):
        self.requests = {}
        self._reset()

    def _reset(self):
        self.descriptors = {}
        self.aliases = {}

    async def __aenter__(self):
        """Start the watcher, registering new watches if any."""
        if self._fd is not None:
            raise RuntimeError("Can't enter my context twice")
        self._fd = LibC.inotify_init()
        self._stream = UnixFileDescriptorStream(self._fd)

        for alias, (path, flags) in self.requests.items():
            await self._setup_watch(alias, path, flags)

        return self

    async def __aexit__(self, *exc):
        # This assumes that closing the inotify stream doesn't block
        self.close()

    setup = __aenter__  # deprecated

    def _close(self):
        self._stream.close()
        self._fd = None
        self._stream = None

        self._reset()

    close = _close  # deprecated

    def watch(self, path, flags, *, alias=None):
        """Add a new watching rule.

        This is the sync version.

        Warning: This method may block if called inside the context
        manager. You should use `awatch` instead."""
        if alias is None:
            alias = path
        if alias in self.requests:
            raise ValueError("A watch request is already scheduled for alias %s" % alias)
        self.requests[alias] = (path, flags)
        if self._stream is not None:
            # We've started, register the watch immediately.
            self._setup_watch_sync(alias, path, flags)

    async def awatch(self, path, flags, *, alias=None):
        """Add a new watching rule.

        This is the async version.
        """
        if alias is None:
            alias = path
        if alias in self.requests:
            raise ValueError("A watch request is already scheduled for alias %s" % alias)
        self.requests[alias] = (path, flags)
        if self._stream is not None:
            # We've started, register the watch immediately.
            await self._setup_watch(alias, path, flags)

    def unwatch(self, alias):
        """Stop watching a given rule."""
        if alias not in self.descriptors:
            raise ValueError("Unknown watch alias %s; current set is %r" % (alias, list(self.descriptors.keys())))
        wd = self.descriptors[alias]
        errno = LibC.inotify_rm_watch(self._fd, wd)
        if errno != 0:
            raise IOError("Failed to close watcher %d: errno=%d" % (wd, errno))
        del self.descriptors[alias]
        del self.requests[alias]
        del self.aliases[wd]

    async def _setup_watch(self, alias, path, flags):
        """Actual rule setup."""
        assert alias not in self.descriptors, "Registering alias %s twice!" % alias
        wd = await anyio.to_thread.run_sync(LibC.inotify_add_watch, self._fd, path, flags)
        if wd < 0:
            raise IOError("Error setting up watch on %s with flags %s: wd=%s" % (
                path, flags, wd))
        self.descriptors[alias] = wd
        self.aliases[wd] = alias

    def _setup_watch_sync(self, alias, path, flags):
        """Actual rule setup."""
        assert alias not in self.descriptors, "Registering alias %s twice!" % alias
        wd = LibC.inotify_add_watch(self._fd, path, flags)
        if wd < 0:
            raise IOError("Error setting up watch on %s with flags %s: wd=%s" % (
                path, flags, wd))
        self.descriptors[alias] = wd
        self.aliases[wd] = alias

    def closed(self):
        """Are we closed?"""
        return self._fd is None

    def __aiter__(self):
        return self

    async def __anext__(self):
        """whenever the fd is ready for reading."""

        # This code does not handle EOF because the file descriptor is
        # closed exclusively via `__aexit__`.

        while True:
            prefix = await self._stream.read(PREFIX.size)
            wd, flags, cookie, length = PREFIX.unpack(prefix)
            path = await self._stream.read(length)

            # All async performed, time to look at the event's content.
            try:
                alias = self.aliases[wd]
            except KeyError:
                # Event for a removed watch, skip it.
                continue

            decoded_path = struct.unpack('%ds' % length, path)[0].rstrip(b'\x00').decode('utf-8', errors="replace")
            return Event(
                flags=flags,
                cookie=cookie,
                name=decoded_path,
                alias=alias,
            )

    get_event = __anext__
