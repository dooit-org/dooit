import os
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from ._vars import DATABASE_FILE


class Manager:
    """
    Class for managing sqlalchemy sessions
    """

    def connect(self, path: Optional[str] = None):
        """
        Connect to database using a file path

        Args:
            path: Path to SQLite database file. Can include ~ for home directory.
        """

        from dooit.api import BaseModel

        path = path or DATABASE_FILE
        path = os.path.expanduser(path)
        connection_string = f"sqlite:///{path}"
        self.engine = create_engine(connection_string)
        self.session = Session(self.engine)

        BaseModel.metadata.create_all(bind=self.engine)
        self._db_last_modified = self._get_db_last_modified()

    def _get_db_last_modified(self) -> Optional[float]:
        database = self.engine.url.database
        assert database is not None

        try:
            return os.path.getmtime(database)
        except OSError:
            return None

    def has_changed(self) -> bool:
        """
        Check if the database file has been modified since the last known state.
        """

        current_last_modified = self._get_db_last_modified()
        if current_last_modified and self._db_last_modified != current_last_modified:
            self._db_last_modified = current_last_modified
            manager.session.expire_all()
            return True
        return False

    def delete(self, obj):
        """
        Delete an object from the database and commit the change.
        """

        self.session.delete(obj)
        self.commit()

    def save(self, obj):
        """
        Add an object to the session and commit the change.
        """

        self.session.add(obj)
        self.commit()

    def commit(self):
        """
        Commit the current session and update the last-modified timestamp.
        """

        self.session.commit()
        self._db_last_modified = self._get_db_last_modified()


manager = Manager()
