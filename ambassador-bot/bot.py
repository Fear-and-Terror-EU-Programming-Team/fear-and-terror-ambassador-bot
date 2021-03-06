#!/usr/bin/env python3

import discord
import config
import emojis
import functools
import scheduling
import transaction
import discord.utils as utils
from application import Draft, Application
from discord.ext import commands
from database import db
from datetime import datetime
from synchronization import synchronized

bot = commands.Bot(command_prefix=config.BOT_CMD_PREFIX)

# no need to edit manually, will be populated by decorators
emoji_handlers = {}


def emoji_handler(emoji, channel_id):
    '''Decorator for emoji handlers.'''

    # looks weird. is weird. blame python.
    def decorator(func):
        global emoji_handlers
        if channel_id not in emoji_handlers:
            emoji_handlers[channel_id] = {}
        emoji_handlers[channel_id][str(emoji)] = func
        # don't actually wrap anything
        return func

    return decorator


def restrict_to_channel(channel_id):
    '''Decorator restricting a bot function to the specified channel.

    The functions first argument is assumed to have a `channel` field.
    This is (among others) the case with InvocationContext and Message.'''

    # welcom to mai java tutorial, tudai we learn how to werite boilarplaed cod
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            if ctx.channel.id != channel_id:
                return

            return await func(ctx, *args, **kwargs)

        return wrapper

    return decorator


def restrict_to_author_and_admins(func):
    '''Decorator restricting an emoji function
    to the message author and admins.

    Will make the function immediately return `False` otherwise.'''

    @functools.wraps(func)
    async def wrapper(rp, *args, **kwargs):
        if not is_admin(rp.member) and rp.message.author.id != rp.member.id:
            return False

        return await func(rp, *args, **kwargs)

    return wrapper


def restrict_to_ambassador_manager(func):
    '''Decorator restricting an emoji function
    to the ambassador admin.

    Will make the function immediately return `False` otherwise.'''

    @functools.wraps(func)
    async def wrapper(rp, *args, **kwargs):
        if rp.member.id != config.AMBASSADOR_MANAGER:
            return False

        return await func(rp, *args, **kwargs)

    return wrapper

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    config.init_config(bot)
    scheduling.init_scheduler()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await register_application(message)
    await bot.process_commands(message)
    transaction.commit()


@bot.event
async def on_raw_reaction_add(payload):
    rp = await unwrap_payload(payload)
    if rp.member == bot.user:
        return # ignore bot reactions
    await handle_react(rp)


@bot.command()
@restrict_to_channel(config.AMBASSADOR_CHANNEL)
async def introduction(ctx):
    voice_channel = bot.get_channel(config.AMBASSADOR_VOICE_CHANNEL)
    applicant_role = ctx.guild.get_role(config.APPLICANT_ROLE)
    recruit_role = ctx.guild.get_role(config.RECRUIT_ROLE)
    for m in voice_channel.members:
        if applicant_role in m.roles:
            await m.add_roles(recruit_role)
            await m.send(f"Steam Group: https://steamcommunity.com/groups/FearandTerror \n"
                         f"Community Trailer: https://www.youtube.com/watch?v=kYrxBjMiRG4 \n"
                         f"FaT Gaming Backgrounds: https://imgur.com/a/4didOBv")
            await m.remove_roles(applicant_role)
            # TODO Remove them from applicant database.


@synchronized
async def handle_react(rp):
    '''Executes the correct emoji handler
    for the specified `ReactionPayload`.

    If no appropriate emoji handler exists or the emoji handler returns
    `False`, then the emoji reaction is removed.'''

    if rp.channel.id not in emoji_handlers or \
            str(rp.emoji) not in emoji_handlers[rp.channel.id]:
        await rp.message.remove_reaction(rp.emoji, rp.member)
        return
    # call appropriate handler
    success = await emoji_handlers[rp.channel.id][str(rp.emoji)](rp)
    if success == False: # note that `None` is intentionally treated as True
        await rp.message.remove_reaction(rp.emoji, rp.member)
    transaction.commit()


@restrict_to_channel(config.APPLICATION_CHANNEL)
async def register_application(message):
    '''Turns the posted message into an application draft if the user is
    allowed to apply.

    Otherwise, posts an info message and schedules deletion of the posted
    message and the info message.

    Will completely ignore messages from admins (see `config.BOT_ADMIN_ROLES`).
    '''

    # ignore admin messages
    if is_admin(message.author):
        return

    if db.is_app_blocked(message.author):
        info_msg = await message.channel.send(f"{message.author.mention} "
                f"You are currently not allowed to apply to Fear and Terror. "
                f"Possible reasons:\n"
                f"- You're already a member of FaT\n"
                f"- You already have an active application\n"
                f"- Your last application was denied less than two weeks ago\n"
                f"\n"
                f"Your application and this message will be deleted in "
                f"{config.DEFAULT_MESSAGE_DELETE_DELAY} seconds.")
        scheduling.message_delayed_delete(message)
        scheduling.message_delayed_delete(info_msg)
        return

    if len(message.content) > 1900:
        info_msg = await message.channel.send(f"{message.author.mention} "
                f"Your application is too long. "
                f"Please try to use a maximum of 1900 characters."
                f"\n\n"
                f"Your application and this message will be deleted in "
                f"{config.DEFAULT_MESSAGE_DELETE_DELAY} seconds.")
        scheduling.message_delayed_delete(message)
        scheduling.message_delayed_delete(info_msg)
        return

    await Draft.create(message)


@emoji_handler(emoji=emojis.COMMIT_APPLICATION,
        channel_id=config.APPLICATION_CHANNEL)
@restrict_to_author_and_admins
async def commit_application(rp):
    draft = db.drafts[rp.message.id]
    # deschedule auto-commit
    # Yes, there is a race condition here. I don't care.
    scheduling.deschedule(draft.commit_job_id)
    await Application.create(draft)


@emoji_handler(emoji=emojis.DELETE_APPLICATION,
        channel_id=config.APPLICATION_CHANNEL)
@restrict_to_author_and_admins
async def delete_application(rp):
    draft = db.drafts[rp.message.id]
    # deschedule auto-commit
    # Yes, there is a race condition here. I don't care.
    scheduling.deschedule(draft.commit_job_id)
    await draft.delete()


@emoji_handler(emoji=emojis.UPVOTE,
        channel_id=config.VOTING_CHANNEL)
@emoji_handler(emoji=emojis.DOWNVOTE,
        channel_id=config.VOTING_CHANNEL)
async def handle_vote(rp):
    app = db.applications[rp.message.id]
    await app.check_votes()


@emoji_handler(emoji=emojis.FREEZE_APPLICATION,
        channel_id=config.VOTING_CHANNEL)
@restrict_to_ambassador_manager
async def freeze_vote(rp):
    app = db.applications[rp.message.id]
    await app.freeze()


@emoji_handler(emoji=emojis.FORCE_ACCEPT,
        channel_id=config.VOTING_CHANNEL)
@restrict_to_ambassador_manager
async def force_accept(rp):
    app = db.applications[rp.message.id]
    await app.accept()


@emoji_handler(emoji=emojis.FORCE_DECLINE,
        channel_id=config.VOTING_CHANNEL)
@restrict_to_ambassador_manager
async def force_decline(rp):
    app = db.applications[rp.message.id]
    await app.decline()


async def unwrap_payload(payload):
    rp = ReactionPayload()
    await rp._init(payload)
    return rp


class ReactionPayload():
    # this might be a bit heavy on the API
    async def _init(self, payload):
        self.guild = bot.get_guild(payload.guild_id)
        self.member = await self.guild.fetch_member(payload.user_id)
        self.emoji = payload.emoji
        self.channel = bot.get_channel(payload.channel_id)
        self.message = await self.channel.fetch_message(payload.message_id)


def is_admin(user):
    return any([role.id in config.BOT_ADMIN_ROLES for role in user.roles])


if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)
