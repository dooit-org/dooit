from sqlalchemy import MetaData
from sqlalchemy.orm import Session


def delete_all_data(session: Session):
    """Delete all data from every table in the database."""
    meta = MetaData()
    meta.reflect(bind=session.get_bind())
    for table in reversed(meta.sorted_tables):
        session.execute(table.delete())
    session.commit()
