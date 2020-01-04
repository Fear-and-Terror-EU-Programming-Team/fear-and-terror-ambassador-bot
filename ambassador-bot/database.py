import BTrees
import config
import persistent
import transaction
import ZODB
from dataclasses import dataclass

class _Database(persistent.Persistent):

    def __init__(self):
        self.applications = persistent.mapping.PersistentMapping()
        self.drafts = persistent.mapping.PersistentMapping()

        self.accepted = persistent.mapping.PersistentMapping()
        self.denied = persistent.mapping.PersistentMapping()

    def is_app_blocked(self, member):
        '''Returns `True` iff the specified member

        - has an active application
        - has an active draft
        - was accepted
        - was denied less than `config.REAPPLY_COOLDOWN_DAYS` days ago
        '''

        return any([app.applicant_id == member.id
               for app in self.applications.values()]) \
        or any([draft.applicant_id == member.id
           for draft in self.drafts.values()]) \
        or member.id in self.accepted \
        or member.id in self.denied


print("Starting database...")
connection = ZODB.connection(config.DATABASE_FILENAME)
root = connection.root
if not hasattr(root, "db"):
    database = _Database()
    root.db = database
    transaction.commit()

db = root.db
