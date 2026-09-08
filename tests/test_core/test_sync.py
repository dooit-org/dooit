"""
The change detection the db poller runs on

Dooit polls the database file's mtime once a second and refreshes every pane
when it moves — that is how an edit made in a second dooit (or straight in
the database) shows up in a running one.
"""

import os
import tempfile
from pathlib import Path

from dooit.api import Project, manager


def test_has_changed_notices_an_outside_write():
    with tempfile.TemporaryDirectory() as folder:
        db = Path(folder) / "dooit.db"
        manager.connect(str(db))

        p = Project(description="test")
        p.save()

        # Our own writes keep the recorded mtime current, so nothing looks
        # like it changed underneath us
        assert not manager.has_changed()

        # An outside write moves the file's mtime; the poller must see it
        # exactly once, and then treat the new state as the known one
        outside = os.path.getmtime(db) + 10
        os.utime(db, (outside, outside))

        assert manager.has_changed()
        assert not manager.has_changed()

        manager.session.close()
        manager.engine.dispose()
