#!/usr/bin/env python3

import discord
import config
import emojis
import functools
import scheduling
import transaction
from discord.ext import commands
from discord.utils import get
from database import db, Application

bot = commands.Bot(command_prefix=config.BOT_CMD_PREFIX)

# no need to edit manually, will be populated by decorators
emoji_handlers = {}


def emoji_handler(emoji, channel_id):
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
    @functools.wraps(func)
    async def wrapper(rp, *args, **kwargs):

        if not is_admin(rp.member) and rp.message.author.id != rp.member.id:
            return False

        return await func(rp, *args, **kwargs)
    return wrapper

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')
    global voting_channel
    voting_channel = bot.get_channel(config.VOTING_CHANNEL)
    global archive_channel
    archive_channel = bot.get_channel(config.ARCHIVE_CHANNEL)
    global ambassador_channel
    ambassador_channel = bot.get_channel(config.AMBASSADOR_CHANNEL)
    global applicant_talk_channel
    applicant_talk_channel = bot.get_channel(config.APPLICANT_TALK_CHANNEL)
    global applicant_info_channel
    applicant_info_channel = bot.get_channel(config.APPLICANT_INFO_CHANNEL)
    global ambassador_manager
    ambassador_manager = bot.get_user(config.AMBASSADOR_MANAGER)


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

# TODO do we even need?
#async def on_raw_reaction_remove(payload):
#    rp = await unwrap_payload(payload)
#    if is_admin(rp.member):
#        await handle_react(rp)
#    else:
#        await rp.message.remove_reaction(rp.emoji, rp.member)


async def handle_react(rp):
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
    print(message.content.encode())
    await message.channel.send(f"{message.author.mention} "
            f"Thanks for applying to Fear and Terror. "
            f"You now have the chance to edit your application before sending "
            f"it to our review team. "
            f"Once you're done, click the {emojis.COMMIT_APPLICATION} emoji. "
            f"If you want to retract your application and delete your "
            f"message, click the {emojis.DELETE_APPLICATION} emoji."
            f"\n\n"
            f"Otherwise, your application will be sent off automatically in "
            f"{config.AUTOCOMMIT_DELAY_MINUTES} minutes.")
    await message.add_reaction(emojis.COMMIT_APPLICATION)
    await message.add_reaction(emojis.DELETE_APPLICATION)
    # TODO schedule commit
    # TODO schedule info message delete


@emoji_handler(emoji=emojis.COMMIT_APPLICATION,
        channel_id=config.APPLICATION_CHANNEL)
@restrict_to_channel(config.APPLICATION_CHANNEL)
@restrict_to_author_and_admins
async def commit_application(rp):
    applicant = rp.message.author
    ambassador_role = rp.guild.get_role(config.AMBASSADOR_ROLE)


    app_content = rp.message.content
    app_content = app_content.replace("```", "") # strip code block formatting
    voting_content = (f"{ambassador_role.mention}\n{applicant.mention}\n"
                      f"```{app_content}```")
    archive_content = (f"{applicant.mention}\n"
                       f"```{app_content}```")

    # Re-post message in voting and archive channel
    voting_message = await voting_channel.send(voting_content)
    archive_message = await archive_channel.send(archive_content)

    await voting_message.add_reaction(emojis.UPVOTE)
    await voting_message.add_reaction(emojis.DOWNVOTE)

    app = Application(applicant.id, voting_message.id, archive_message.id)
    db.applications[voting_message.id] = app

    await rp.channel.send(f"Application from "
                          f"{rp.message.author.mention} committed.")


@emoji_handler(emoji=emojis.DELETE_APPLICATION,
        channel_id=config.APPLICATION_CHANNEL)
@restrict_to_channel(config.APPLICATION_CHANNEL)
@restrict_to_author_and_admins
async def delete_application(rp):
    await rp.message.delete()


@emoji_handler(emoji=emojis.UPVOTE,
        channel_id=config.VOTING_CHANNEL)
@emoji_handler(emoji=emojis.DOWNVOTE,
        channel_id=config.VOTING_CHANNEL)
@restrict_to_channel(config.VOTING_CHANNEL)
async def handle_vote(rp):

    upvotes, downvotes = count_votes(rp.message)

    # -1 so we don't count bot's reaction as vote
    accepted = upvotes - 1 >= config.APPROVE_THRESHOLD
    denied = downvotes - 1 >= config.DECLINE_THRESHOLD

    if accepted or denied:
        app = db.applications[rp.message.id]
        applicant = rp.guild.get_member(app.applicant_id)
        archive_message = \
                await archive_channel.fetch_message(app.archive_message_id)
        voting_message = \
                await voting_channel.fetch_message(app.voting_message_id)

        del db.applications[rp.message.id]

    if accepted:
        await voting_message.edit(f"{emojis.ARCHIVE_ACCEPTED} Application "
                                  f"has been accepted!")
        scheduling.message_delayed_delete(voting_message)
        await archive_message.add_reaction(emojis.ARCHIVE_ACCEPTED)
        applicant_role = rp.guild.get_role(config.APPLICANT_ROLE)
        await applicant.add_roles(applicant_role)
        await applicant_talk_channel.send(f"{applicant.mention} "
                f"Congratulations, your application has been accepted! "
                f"Please check {applicant_info_channel.mention} to find out "
                f"how to proceed.")

        # TODO add applicants to some kind of DB

    if denied:
        await voting_message.edit(f"{emojis.ARCHIVE_DENIED} Application "
                                  f"has been denied!")
        scheduling.message_delayed_delete(voting_message)

        # "Message Plague" TODO change? clarify requirements
        await ambassador_channel.send(f"{ambassador_manager.mention} "
                                      f"Denied {applicant.mention}")

        await archive_message.add_reaction(emojis.ARCHIVE_DENIED)
        await applicant.send(f"Hey {applicant.mention}, thank you for "
                f"applying to Fear and Terror. "
                f"Unfortunately, your application has been denied. "
                # TODO specific date/time
                f"Feel free to re-apply in two weeks.\n\n"
                f"We don't collect statements from the individual voters but "
                f"the most common reasons for denying an application are "
                f"a perceived lack of effort or being underage. "
                f"If you decide to re-apply, make sure to give thorough "
                f"responses to all the questions so we know you're serious "
                f"about joining FaT.")


def count_votes(message):
    upvotes = 0
    downvotes = 0
    for r in message.reactions:
        if str(r.emoji) == emojis.UPVOTE:
            upvotes = r.count
        elif str(r.emoji) == emojis.DOWNVOTE:
            downvotes = r.count

    return (upvotes, downvotes)


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
