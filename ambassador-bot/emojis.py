# Raw emojis
_WHITE_CHECK_MARK    = b'\xe2\x9c\x85'.decode()
_FAST_FORWARD        = b'\xe2\x8f\xa9'.decode()
_NO_ENTRY_SIGN       = b'\xf0\x9f\x9a\xab'.decode()
_ARROW_UP            = b'\xe2\xac\x86\xef\xb8\x8f'.decode()
_ARROW_DOWN          = b'\xe2\xac\x87\xef\xb8\x8f'.decode()
_FIRE                = b'\xf0\x9f\x94\xa5'.decode()
_OKAY                = b'\xf0\x9f\x86\x97'.decode()
_SNOWFLAKE           = b'\xe2\x9d\x84\xef\xb8\x8f'.decode()
_R_I_H               = b'\xf0\x9f\x87\xad'.decode()
_R_I_O               = b'\xf0\x9f\x87\xb4'.decode()
_R_I_L               = b'\xf0\x9f\x87\xb1'.decode()
_R_I_D               = b'\xf0\x9f\x87\xa9'.decode()

# Function associations

### Application channel
COMMIT_APPLICATION  = _OKAY
DELETE_APPLICATION  = _FIRE

### Voting channel
UPVOTE              = _ARROW_UP
DOWNVOTE            = _ARROW_DOWN
FREEZE_APPLICATION  = _SNOWFLAKE
HOLD_H              = _R_I_H
HOLD_O              = _R_I_O
HOLD_L              = _R_I_L
HOLD_D              = _R_I_D
FORCE_ACCEPT        = _WHITE_CHECK_MARK
FORCE_DECLINE       = _NO_ENTRY_SIGN

### Archive channel
ARCHIVE_ACCEPTED    = _WHITE_CHECK_MARK
ARCHIVE_DENIED      = _NO_ENTRY_SIGN

