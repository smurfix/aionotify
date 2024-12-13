# Copyright (c) 2016 The aionotify project
# This code is distributed under the two-clause BSD License.

import anyio
import pytest

import aionotify

pytestmark = pytest.mark.anyio


class AIONotifyTestCase:
    # Utility functions
    # =================

    # Those allow for more readable tests.

    @pytest.fixture(autouse=True)
    def with_watcher(self):
        self.watcher = aionotify.Watcher()

    @pytest.fixture(autouse=True)
    def with_tempdir(self, tmp_path):
        self.testdir = tmp_path
        yield
        self.testdir = None

    def _touch(self, filename, *, parent=None):
        path = (parent or self.testdir) / filename
        with path.open('w'):
            pass

    def _unlink(self, filename, *, parent=None):
        path = (parent or self.testdir) / filename
        path.unlink()

    def _rename(self, source, target, *, parent=None):
        source_path = (parent or self.testdir) / source
        target_path = (parent or self.testdir) / target
        source_path.rename(target_path)

    def _assert_file_event(self, event, name, flags=aionotify.Flags.CREATE, alias=None):
        """Check for an expected file event.

        Allows for more readable tests.
        """
        if alias is None:
            alias = self.testdir

        assert name == event.name
        assert flags == event.flags
        assert alias == event.alias

    async def _assert_no_events(self, timeout=0.1):
        """Ensure that no events are left in the queue."""
        with anyio.move_on_after(timeout):
            result = await self.watcher.get_event()
            raise AssertionError("Event %r occurred within timeout %s" % (result, timeout))


class TestSimpleUsage(AIONotifyTestCase):

    async def test_watch_before_start(self):
        """A watch call is valid before startup."""
        self.watcher.watch(self.testdir, aionotify.Flags.CREATE)
        async with self.watcher:
            # Touch a file: we get the event.
            self._touch('a')
            event = await self.watcher.get_event()
            self._assert_file_event(event, 'a')

            # And it's over.
            await self._assert_no_events()

    async def test_watch_before_start_async(self):
        """A watch call is valid before startup."""
        await self.watcher.awatch(self.testdir, aionotify.Flags.CREATE)
        async with self.watcher:

            # Touch a file: we get the event.
            self._touch('a')
            event = await self.watcher.get_event()
            self._assert_file_event(event, 'a')

            # And it's over.
            await self._assert_no_events()

    async def test_watch_after_start(self):
        """A watch call is valid after startup."""
        async with self.watcher:
            self.watcher.watch(self.testdir, aionotify.Flags.CREATE)

            # Touch a file: we get the event.
            self._touch('a')
            event = await self.watcher.get_event()
            self._assert_file_event(event, 'a')

            # And it's over.
            await self._assert_no_events()

    async def test_watch_after_start_async(self):
        """A watch call is valid after startup."""
        async with self.watcher:
            await self.watcher.awatch(self.testdir, aionotify.Flags.CREATE)

            # Touch a file: we get the event.
            self._touch('a')
            event = await self.watcher.get_event()
            self._assert_file_event(event, 'a')

            # And it's over.
            await self._assert_no_events()

    async def test_event_ordering(self):
        """Events should arrive in the order files where created."""
        async with self.watcher:
            self.watcher.watch(self.testdir, aionotify.Flags.CREATE)

            # Touch 2 files
            self._touch('a')
            self._touch('b')

            # Get the events
            event1 = await self.watcher.get_event()
            event2 = await self.watcher.get_event()
            self._assert_file_event(event1, 'a')
            self._assert_file_event(event2, 'b')

            # And it's over.
            await self._assert_no_events()

    async def test_filtering_events(self):
        """We only get targeted events."""
        async with self.watcher:
            self.watcher.watch(self.testdir, aionotify.Flags.CREATE)
            self._touch('a')
            event = await self.watcher.get_event()
            self._assert_file_event(event, 'a')

            # Perform a filtered-out event; we shouldn't see anything
            self._unlink('a')
            await self._assert_no_events()

    async def test_watch_unwatch(self):
        """Watches can be removed."""
        self.watcher.watch(self.testdir, aionotify.Flags.CREATE)
        async with self.watcher:

            self.watcher.unwatch(self.testdir)

            # Touch a file; we shouldn't see anything.
            self._touch('a')
            await self._assert_no_events()

    async def test_watch_unwatch_before_drain(self):
        """Watches can be removed, no events occur afterwards."""
        self.watcher.watch(self.testdir, aionotify.Flags.CREATE)
        async with self.watcher:

            # Touch a file before unwatching
            self._touch('a')
            self.watcher.unwatch(self.testdir)

            # We shouldn't see anything.
            await self._assert_no_events()

    async def test_rename_detection(self):
        """A file rename can be detected through event cookies."""
        self.watcher.watch(self.testdir, aionotify.Flags.MOVED_FROM | aionotify.Flags.MOVED_TO)
        async with self.watcher:
            self._touch('a')

            # Rename a file => two events
            self._rename('a', 'b')
            event1 = await self.watcher.get_event()
            event2 = await self.watcher.get_event()

            # We got moved_from then moved_to; they share the same cookie.
            self._assert_file_event(event1, 'a', aionotify.Flags.MOVED_FROM)
            self._assert_file_event(event2, 'b', aionotify.Flags.MOVED_TO)
            assert event1.cookie == event2.cookie

            # And it's over.
            await self._assert_no_events()


class TestErrors(AIONotifyTestCase):
    """Test error cases."""

    async def test_watch_nonexistent(self):
        """Watching a non-existent directory raises an OSError."""
        badpath = self.testdir / 'nonexistent'
        self.watcher.watch(badpath, aionotify.Flags.CREATE)
        with pytest.raises(OSError):
            async with self.watcher:
                pass

    async def test_watch_nonexistent2(self):
        """Watching a non-existent directory raises an OSError."""
        badpath = self.testdir / 'nonexistent'
        async with self.watcher:
            with pytest.raises(OSError):
                self.watcher.watch(badpath, aionotify.Flags.CREATE)

    async def test_unwatch_bad_alias(self):
        self.watcher.watch(self.testdir, aionotify.Flags.CREATE)
        async with self.watcher:
            with pytest.raises(ValueError):
                self.watcher.unwatch('blah')
