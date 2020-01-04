# Required settings (must be changed)
BOT_TOKEN                 = "BOT TOKEN HERE"

# Channel & Misc settings (double check)
BOT_ADMIN_ROLES           = [643983323932262410]
AMBASSADOR_ROLE           = 662537461796438016
AMBASSADOR_MANAGER        = 230484952892964866
APPLICANT_ROLE            = 662564132696096768
APPLICATION_CHANNEL       = 662486019236560927
RECRUIT_ROLE              = 663102488735514645
AMBASSADOR_VOICE_CHANNEL  = 644652633122013195
VOTING_CHANNEL            = 662486040317263872
ARCHIVE_CHANNEL           = 662486055257112616
APPLICANT_TALK_CHANNEL    = 662574332446375966
APPLICANT_INFO_CHANNEL    = 662574839432740875
AMBASSADOR_CHANNEL        = 662586492316549148
APPROVE_THRESHOLD         = 10
DECLINE_THRESHOLD         = 5
AUTOCOMMIT_DELAY_MINUTES = 60
DEFAULT_MESSAGE_DELETE_DELAY = 60
REAPPLY_COOLDOWN_DAYS   = 14
AUTO_VOTE_CLOSE_HOURS   = 24

# Optional settings (may be changed)
BOT_CMD_PREFIX            = "#"
DATABASE_FILENAME         = "database.fs"
SCHEDULER_DB_FILENAME     = "scheduler-db.sqlite"


#####################################
# DO NOT EDIT BELOW
#####################################

import pytz

TIMEZONE = pytz.timezone("US/Eastern")

def init_config(_bot):
    global bot
    bot = _bot
    global application_channel
    application_channel = bot.get_channel(APPLICATION_CHANNEL)
    global voting_channel
    voting_channel = bot.get_channel(VOTING_CHANNEL)
    global archive_channel
    archive_channel = bot.get_channel(ARCHIVE_CHANNEL)
    global ambassador_channel
    ambassador_channel = bot.get_channel(AMBASSADOR_CHANNEL)
    global applicant_talk_channel
    applicant_talk_channel = bot.get_channel(APPLICANT_TALK_CHANNEL)
    global applicant_info_channel
    applicant_info_channel = bot.get_channel(APPLICANT_INFO_CHANNEL)
    global ambassador_manager
    ambassador_manager = bot.get_user(AMBASSADOR_MANAGER)
    global applicant_voice_channel
    applicant_voice_channel = bot.get_channel(AMBASSADOR_VOICE_CHANNEL)

