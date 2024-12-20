aionotify
=========

.. image:: https://img.shields.io/pypi/v/aionotify.svg
    :target: https://pypi.python.org/pypi/aionotify/
    :alt: Latest Version

.. image:: https://img.shields.io/pypi/pyversions/aionotify.svg
    :target: https://pypi.python.org/pypi/aionotify/
    :alt: Supported Python versions

.. image:: https://img.shields.io/pypi/wheel/aionotify.svg
    :target: https://pypi.python.org/pypi/aionotify/
    :alt: Wheel status

.. image:: https://img.shields.io/pypi/l/aionotify.svg
    :target: https://pypi.python.org/pypi/aionotify/
    :alt: License


``aionotify`` is a simple, anyio-based inotify library.


Its use is quite simple:

.. code-block:: python

    import anyio
    import aionotify

    # Setup the watcher

    async def work():
        async with aionotify.Watcher() as watcher:
            await watcher.awatch(alias='logs', path='/var/log', flags=aionotify.Flags.MODIFY)
            i = 0
            async for event in watcher:
                # Pick the 10 first events
                print(event)
                i += 1
                if i >= 10:
                    return

    anyio.run(work)

    # alternately:
    # asyncio.run(work())
    # trio.run(work)


Links
-----

* Code at https://github.com/rbarrois/aionotify
* Package at https://pypi.python.org/pypi/aionotify/
* Continuous integration at https://travis-ci.org/rbarrois/aionotify/


Events
------

An event is a simple object with a few attributes:

* ``name``: the path of the modified file
* ``flags``: the modification flag; use ``aionotify.Flags.parse()`` to retrieve a list of individual values.
* ``alias``: the alias of the watch triggering the event
* ``cookie``: for renames, this integer value links the "renamed from" and "renamed to" events.


Watches
-------

``aionotify`` uses a system of "watches", similar to inotify.

A watch may have an alias; by default, it uses the path name:

.. code-block:: python

    watcher = aionotify.Watcher()
    watcher.watch('/var/log', flags=aionotify.Flags.MODIFY)

    # Similar to:
    watcher.watch('/var/log', flags=aionotify.Flags.MODIFY, alias='/var/log')


A watch can be removed by using its alias:

.. code-block:: python

    watcher = aionotify.Watcher()
    watcher.watch('/var/log', flags=aionotify.Flags.MODIFY)

    watcher.unwatch('/var/log')
