import discord

from custom_queue import Queue
from server import Server

intents = discord.Intents.default()
intents.members = True
intents.messages = True
client = discord.Client(intents=intents)  # Client initialization
guild_collection = dict()
mentor_categories = dict()


async def help_manager(message):
    """
    Prints help command
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    if len(divided) == 1:
        help_embed = discord.Embed()
        help_embed.title = "Help"
        help_embed.type = "rich"
        help_embed.colour = discord.colour.Color.blue()
        if server.validate_on_duty(message.author):
            if server.admin_check(message.author):
                help_embed.add_field(name="**ADMIN ONLY COMMANDS**", value="*[role: botsmith]*", inline=False)
                help_embed.add_field(name="💜 \"-add (name) [-h | parent_name]\"",
                                     value="Create a new queue", inline=False)
                help_embed.add_field(name="💜 \"-delete (name)\"",
                                     value="Delete the queue", inline=False)
                help_embed.add_field(name="💜 \"-empty\"",
                                     value="Empty all queues", inline=False)
                help_embed.add_field(name="💜 \"-forceshift (name)\"",
                                     value="Force toggle mentioned mentor's shift", inline=False)
                help_embed.add_field(name="💜 \"-reload\"",
                                     value="Reload all configurations and reset queues)", inline=False)
            help_embed.add_field(name="**MENTOR ONLY COMMANDS**", value="*[role: on-duty mentor, off-duty mentor]*",
                                 inline=False)
            help_embed.add_field(name="💜 \"-done\"", value="Removes previous voice channel", inline=False)
            help_embed.add_field(name="💜 \"-ready (queue_name)\"",
                                 value="Take the next person off the specified queue", inline=False)
            help_embed.add_field(name="💜 \"-remove (@student)\"",
                                 value="Remove the mentioned student from all queues", inline=False)
            help_embed.add_field(name="💜 \"-shift\"",
                                 value="Toggle your availability", inline=False)
        help_embed.add_field(name="**GENERAL COMMANDS**", value="*[available for all to use]*",
                             inline=False)
        help_embed.add_field(name="💜 \"-leave\"", value="Leave all queues", inline=False)
        help_embed.add_field(name="💜 \"-show [ queue_name ]\"",
                             value="\t Show all queues or the specified queue", inline=False)
        help_embed.add_field(name="💜 \"-queue (queue_name)\"", value="Join the selected queue",
                             inline=False)
        help_embed.add_field(name="💜 \"-queues\"", value="Show all queues", inline=False)
        help_embed.add_field(name="💜 \"-who\"", value="Shows all on-duty mentors", inline=False)
        await message.channel.send(embed=help_embed)
    # Incorrect arguments
    else:
        await message.channel.send("Usage: `-help`")
        return


async def add(message):
    """
    Add queue to the mentoring system
    Admin only command
    :param Discord message:
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    # Check if a user is an admin
    if not server.admin_check(message.author):
        return
    # Add a new queue to the system
    if len(divided) == 2:
        name = divided[1].lower()
        # User tried to add a queue that already exists
        if name in server.queues:
            await message.channel.send("This queue already exists")
            return
        # Successful addition
        else:
            server.queues[name] = Queue(True, name)
            await message.channel.send("New queue has been added to the system")
            server.save()
    # Incorrect arguments
    else:
        await message.channel.send("Usage: `-add (queue)`")
        return


async def enqueue(message):
    """
    Queue a user for a mentoring queue
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    # Invalid arguments
    if len(divided) != 2:
        await message.channel.send("Please specify a valid queue (" + server.get_help() + ") after a space")
        return
    destination = divided[1].lower()
    # If the queue can be joined...
    if destination in server.queues and server.queues[destination].joinable:
        if message.author in server.current_students:
            # Already in desired queue
            if message.author in server.queues[destination].students:
                await message.channel.send("You are already in the " + destination + " queue")
                return
            # Already in a different queue
            else:
                await message.channel.send("You are already in a queue. Use `-show` to see which queue you are in" +
                                           " or `-leave` to leave all queues")
                return
        # No on duty mentors to queue
        else:
            # Added to queue
            await server.queues[destination].join_queue(message)
            server.current_students.append(message.author)
            server.students_queued += 1
            # Get number of mentors available for this queue
            mentors = server.get_role("on-duty mentor").members
            # No mentors online
            if len(mentors) == 0:
                await message.channel.send("Please note that there are currently no mentors on duty. " +
                                           "You may experience long queueing times. " +
                                           "You can use the `-leave` command to exit the queue for now if desired.")
                return
            on_duty = False
            # Check if there are any mentors on-duty for a queue
            for mentor in mentors:
                for role in mentor.roles:
                    if role.name.lower() == f"Mentor - {destination}".lower():
                        on_duty = True
                        break
            # Check if hacker is joining general queue, do not add them to general queue twice since there
            # is not a "Mentor - general" role.
            if destination == "general":
                return
            # No mentors on-duty for this queue, long queue time warning
            if not on_duty:
                await message.channel.send("Please note that there are currently no mentors on duty for this queue. " +
                                           "You will be added to the general queue. " +
                                           "You can use the `-leave` command to exit the queue for now if desired.")
                await server.queues["general"].join_queue(message)
                server.current_students.append(message.author)
                server.students_queued += 1
            return
    # Invalid queue
    if destination not in server.queues or destination in server.queues and not server.queues[destination].joinable:
        await message.channel.send("Please specify a valid queue (" + server.get_help() + ") after a space")
        return


async def leave(message):
    """
    Leave all user queues
    :param message: Discord message
    """
    server = guild_collection[message.guild.id]
    divider = message.content.strip().split()
    # Incorrect arguments provided
    if len(divider) != 1:
        await message.channel.send("The `-leave` command takes no arguments")
        return
    server.leave_queues(message.author)
    await message.channel.send("You have left all queues")


def find_mentor_category(guild):
    """
    Find the category mentor belongs to
    TODO: verify with Alex
    :param guild: Collection of users and channels
    """
    category = mentor_categories.get(guild)
    if category is not None:
        return category
    categories = guild.categories
    for category in categories:
        if category.name.lower() == "mentoring":
            mentor_categories[guild] = category
            return category
    return


async def done(message):
    """
    Removes previous voice channel
    Mentor only command
    :param message: Discord message
    """
    server = guild_collection[message.guild.id]
    mentor = message.author
    # Check if user is a mentor
    if not server.validate_mentor(mentor):
        return
    # Notify Alex to resolve this issue
    # TODO: If this bot is used after WiCHacks 2022, please change user to be mentioned to current Logistics head
    if not await server.remove_mentor_channel(mentor):
        await message.channel.send(f"Channel Removal failure, {mentor.mention} please continue with the queue.\n"
                                   f"@GenCusterJrB#0723, please resolve this issue")


async def ready(message):
    """
    Take the next person off the specified queue
    Mentor only command
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    mentor = message.author
    # Check if user is a mentor
    if not server.validate_mentor(mentor):
        return
    # Incorrect arguments
    if len(divided) > 2 or len(divided) == 0:
        await message.channel.send("Usage: `-ready (queue)`")
        return
    await server.remove_mentor_channel(mentor)
    # 1 arg "-ready", will check any of the mentors category queues + all
    if len(divided) == 1:
        # For each role in the mentor's roles...
        does_anyone_need_help = False
        for topic in message.author.roles:
            # Check mentor category roles only
            if topic.name.startswith("Mentor - "):
                queue = get_queue_from_role(topic.name)  # Get topic from role
                target = server.queues[queue]  # Get queue
                if len(target.students) != 0:  # If not empty
                    does_anyone_need_help = True
                    await help_hacker_from_queue(mentor, target, server, message)
        # Check general queue
        target = server.queues["general"]  # Get general queue
        if len(target.students) != 0:
            does_anyone_need_help = True
            await help_hacker_from_queue(mentor, target, server, message)
        # None of the queues checked had anyone who needed help
        if not does_anyone_need_help:
            await message.channel.send("No students are currently queued")
            return
    # 2 args "-ready <queue>"
    else:
        # Check desired queue name
        destination = divided[1].lower()
        # If queue exists...
        if destination in server.queues:
            target = server.queues[destination]
            # Queue that mentor ready'd for is empty
            if len(target.students) == 0:
                await message.channel.send("No students are currently queued.")
                return
            else:
                await help_hacker_from_queue(mentor, target, server, message)
        # Invalid queue provided
        else:
            await message.channel.send("Invalid queue specified. Valid queues are: " + server.get_help())
            return


async def help_hacker_from_queue(mentor, queue, server, message):
    """
    Removes a hacker from the queue and creates a voice channel for mentor and hacker
    :param mentor: Message author (mentor)
    :param queue: Mentoring queue
    :param server: Server
    :param message: Discord message
    """
    # Get first student
    student = queue.get_front()
    # Remove student from all queues
    server.leave_queues(student)
    # Get queue topic
    topic = queue.get_topic()
    # Create a new mentoring table for mentor and hacker to join, assign mentor and notify user
    table_num = queue.new_queue_table()
    voice_channel = await client.get_guild(
        message.guild.id).create_voice_channel(name=f"{topic}-{table_num}",
                                               category=find_mentor_category(message.guild))
    invite = await voice_channel.create_invite(max_age=3 * 60)
    await message.channel.send(f"{mentor.mention} you are now to meet with {student.mention}.\nPlease join "
                               f"{topic}-{table_num} {invite}")
    server.assign_mentor(mentor, voice_channel)
    server.leave_queues(student)


def get_queue_from_role(role):
    """
    Trim role name to return queue name
    :param role: string containing Mentor - <category>
    :return: category name
    """
    return role[9:]


async def empty(message):
    """
    Empty all queues
    Admin only command
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    user = message.author
    if not server.admin_check(user):
        return
    if len(divided) != 1:
        await message.channel.send("The `-empty` command takes no arguments")
        return
    for user in server.current_students:
        server.leave_queues(user)
    await message.channel.send("All queues have been cleared")


async def shift(message):
    """
    Toggle mentor availability
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    user = message.author
    if not server.validate_mentor(user):
        return
    if len(divided) != 1:
        await message.channel.send("The `-shift` command takes no arguments")
        return
    await server.toggle_shift(message, user)
    await who(message)
    return


async def show(message):
    """
    Shows all queues or the specified queue
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    msg_str = ""
    if len(divided) == 1:
        if len(server.current_students) == 0:
            await message.channel.send("All queues are currently empty")
            return
        else:
            for queue in server.queues:
                # For all queues that are able to be joined and not empty
                if server.queues[queue].joinable and len(server.queues[queue].students) != 0:
                    msg_str += str(server.queues[queue])
            if len(msg_str) == 0:
                await message.channel.send("All queues are currently empty")
                return
            else:
                await message.channel.send(msg_str)
                return
    elif len(divided) == 2:
        course = divided[1].lower()
        if course in server.queues:
            await message.channel.send(str(server.queues[course]))
            return
        else:
            await message.channel.send("Please specify a valid queue (" + server.get_help() + ") after a space")
            return
    else:
        await message.channel.send("Usage: `-show [queue]`")
        return


async def delete(message):
    """
    Deletes a queue in mentor system
    :param message: Discord message sent
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    # Command only allowed for admins
    if not server.admin_check(message.author):
        return
    # Incorrect arguments provided
    if len(divided) != 2:
        await message.send("Usage: `-delete (queue)`")
        return
    target = divided[1].lower()  # Queue to be deleted
    # If the queue to be deleted exists...
    if target in server.queues:
        # Delete child queues before parent queue
        if server.queues[target].children:
            await message.send("The specified hidden queue contains children. they must be deleted first")
            return
        else:
            # Remove child queue from its parent if it has one
            if server.queues[target].parent:
                server.queues[target].parent.children.remove(server.queues[target])
            del server.queues[target]
            await message.channel.send("The specified queue has been deleted")
            server.save()
    # Queue does not exist
    else:
        await message.send("Invalid queue")
        return


async def remove(message):
    """
    Removes mentioned user from the queues
    :param message: Discord message sent
    """
    server = guild_collection[message.guild.id]
    if server.validate(message.author):
        # Removes mentioned user
        if len(message.mentions) == 1:
            server.leave_queues(message.mentions[0])
            await message.channel.send(message.mentions[0].name + " was removed from all queues")
        # Incorrect arguments provided
        else:
            await message.channel.send("Usage: `-remove (@user)")


def beautify_mentor_skills(skills):
    """
    Pretty print mentor skills
    :param skills: mentor's listed skills
    """
    if len(skills) == 0:
        return "*"
    skill_string = ""
    double_skill = False
    for role in skills:
        skill_string += role
        if double_skill:
            skill_string += "\n"
        else:
            skill_string += ", "
        double_skill = not double_skill
    if double_skill:
        skill_string = skill_string[:-2]
    else:
        skill_string = skill_string[:-1]
    return skill_string


async def who(message):
    """
    Prints all available mentors for respective queues
    :param message: Discord message
    """
    channel = message.channel
    server = guild_collection[message.guild.id]
    on_duty_role = server.get_role("on-duty mentor")
    on_duty_mentors = on_duty_role.members
    embed = discord.Embed(title="On-Duty Mentors")
    # No mentors on duty
    if len(on_duty_mentors) == 0:
        embed.description = "There are no mentors on duty"
        embed.colour = discord.colour.Color.red()
        await channel.send(embed=embed)
        return
    embed.colour = discord.colour.Color.green()
    for mentor in on_duty_mentors:
        name = mentor.nick
        if name is None:
            name = mentor.name
        embed.add_field(name=name,
                        value=beautify_mentor_skills([topic.name[len("Mentor - "):] for topic in mentor.roles
                                                      if topic.name.startswith("Mentor - ")]),
                        inline=True)
    await channel.send(embed=embed)
    return


async def reload(message):
    """
    Reload all configurations and queues
    Admin only command
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    # Checks if user is an admin
    if not server.admin_check(message.author):
        return
    # Reload
    if len(divided) == 1:
        await server.reload(message.guild)
        await message.channel.send("System reset")
    # Incorrect argument
    else:
        await message.channel.send("`-reload` does not accept any arguments")


async def show_queues(message):
    """
    Show all queues
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    mstr_str = "The Queues are:\n"
    if len(divided) == 1:
        # Print all queues that can be joined
        for queue in server.queues:
            if server.queues[queue].joinable:
                mstr_str += server.queues[queue].get_topic() + "\n"
        await message.channel.send(mstr_str)
        return
    # Incorrect arguments
    else:
        await message.channel.send("Usage: `-queues")
        return


async def forceshift(message):
    """
    Force toggle mentor shift to on-duty/off-duty
    Admin command only
    :param message: Discord message
    """
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    # Checks if user is an admin
    if not server.admin_check(message.author):
        return
    # Validate correct arguments and number of mentioned users
    if len(divided) == 2 and len(message.mentions) == 1:
        user = message.mentions[0]
        # Check if mentioned user is a mentor
        if not server.validate_mentor(user):
            return
        # Toggle shift
        await server.toggle_shift(message, user)
        await who(message)
    # Incorrect arguments
    else:
        await message.channel.send("The `-shift` command takes no arguments")
        return


def get_channel(target, guild):
    """
    Get channel name
    :param target: Discord message
    :param guild: Collection of users and channels
    :return: channel of message
    """
    for channel in guild.channels:
        if channel.name.lower() == target.lower():
            return channel
    return None


def check_muted(message) -> bool:
    """
    Helper method to check if user is muted
    :param message: Discord message
    """
    author = message.author
    if isinstance(author, discord.User):
        return


@client.event
async def on_ready():
    """
    Bot method that runs on successful start up
    """
    for guild in client.guilds:
        if guild.id not in guild_collection:
            guild_collection[guild.id] = Server(guild.id)
            guild_collection[guild.id].load()
            await guild_collection[guild.id].setup(guild)


@client.event
async def on_message(message):
    """
    On message delegation of commands
    TODO: refactor with @client.command tag?
    :param message: Discord message
    """
    # Check if user is muted
    if check_muted(message):
        return
    # Check command prefix
    if not message.content.startswith("-"):
        return
    command = message.content.strip().split()[0].lower()
    if command == "-help":
        await help_manager(message)
    elif command == "-add":
        await add(message)
    elif command == "-queue":
        await enqueue(message)
    elif command == "-leave":
        await leave(message)
    elif command == "-ready":
        await ready(message)
    elif command == "-empty":
        await empty(message)
    elif command == "-shift":
        await shift(message)
    elif command == "-show":
        await show(message)
    elif command == "-delete":
        await delete(message)
    elif command == "-remove":
        await remove(message)
    elif command == "-reload":
        await reload(message)
    elif command == "-queues":
        await show_queues(message)
    elif command == "-done":
        await done(message)
    elif command == "-who":
        await who(message)
    elif command == "-forceshift":
        await forceshift(message)
    elif command == "-bye":
        await message.channel.send(f"Until Next Year...")


def main():
    # who needs security...hardcode all the things
    client.run('ODA3Njc1NzI1MDQ5MTAyMzM2.YB7cog.jY41rZfw9VwXngBpPL8qBnrKWh8')


if __name__ == '__main__':
    main()
