import BTrees
import config
import persistent
import transaction
import ZODB
from dataclasses import dataclass

class _Database(persistent.Persistent):

    def __init__(self):
        self.applications = persistent.mapping.PersistentMapping()

@dataclass
class Application():

    applicant_id : int
    voting_message_id : int
    archive_message_id : int
    frozen : bool = False

print("Starting database...")
connection = ZODB.connection(config.DATABASE_FILENAME)
root = connection.root
if not hasattr(root, "db"):
    database = _Database()
    root.db = database
    transaction.commit()

db = root.db
