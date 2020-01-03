import config
import persistent
import transaction
import ZODB

class _Database(persistent.Persistent):
    pass


connection = ZODB.connection(config.DATABASE_FILENAME)
root = connection.root
if not hasattr(root, "database"):
    database = _Database()
    root.db = database
    transaction.commit()

db = root.db
