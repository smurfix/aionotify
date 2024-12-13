#!/usr/bin/env python
# Copyright (c) 2016 The aionotify project
# This code is distributed under the two-clause BSD License.


import aionotify
import argparse
import anyio


class Example:
    def __init__(self):
        self.loop = None
        self.watcher = None
        self.task = None

    def prepare(self, path):
        self.watcher = aionotify.Watcher()
        self.watcher.watch(path, aionotify.Flags.MODIFY | aionotify.Flags.CREATE | aionotify.Flags.DELETE)

    async def run(self, max_events):
        async with self.watcher:
            i = 0
            async for event in self.watcher:
                print(event.name, aionotify.Flags.parse(event.flags))
                i += 1
                if i >= max_events:
                    return


def main(args):
    example = Example()
    example.prepare(args.path)

    try:
        anyio.run(example.run, args.events)
    except* KeyboardInterrupt:
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path', help="Path to watch")
    parser.add_argument('--events', default=10, type=int, help="Number of arguments before shutdown")

    args = parser.parse_args()
    main(args)
