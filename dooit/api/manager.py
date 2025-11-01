import os
from pathlib import Path
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import Session
from dooit.api._vars import DATABASE_CONN_STRING


class Manager:
    """
    Class for managing sqlalchemy sessions
    """

    def __init__(self) -> None:
        self.engine: Engine
        self.session: Session
        self._db_last_modified: float | None = None

    def connect_default(self):
        self.connect(DATABASE_CONN_STRING)

    def connect_to_path(self, path: Path):
        connection_string = f"sqlite:///{path.expanduser().absolute()}"
        self.connect(connection_string)

    def connect(self, conn: str):
        """
        Connect to database using a file path

        Args:
            path: Path to SQLite database file. Can include ~ for home directory.
        """

        from dooit.api import BaseModel

        self.engine = create_engine(conn)
        self.session = Session(self.engine)

        BaseModel.metadata.create_all(bind=self.engine)
        self._db_last_modified = self._get_db_last_modified()

    def _get_db_last_modified(self) -> float | None:
        database = self.engine.url.database
        assert database is not None

        try:
            return os.path.getmtime(database)
        except OSError:
            return None

    def has_changed(self) -> bool:
        current_last_modified = self._get_db_last_modified()
        if current_last_modified and self._db_last_modified != current_last_modified:
            self._db_last_modified = current_last_modified
            manager.session.expire_all()
            return True
        return False

    def delete(self, obj: object):
        self.session.delete(obj)
        self.commit()

    def save(self, obj: object):
        self.session.add(obj)
        self.commit()

    def commit(self):
        self.session.commit()
        self._db_last_modified = self._get_db_last_modified()


manager = Manager()
