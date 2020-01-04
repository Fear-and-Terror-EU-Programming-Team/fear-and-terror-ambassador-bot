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
        # check if user
        # - has active application
        # - has active draft
        # - was accepted
        # - was denied (record is deleted after 2 weeks)
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
