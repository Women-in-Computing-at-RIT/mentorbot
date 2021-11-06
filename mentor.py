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
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    if len(divided) == 1:
        help_embed = discord.Embed()
        help_embed.title = "Help"
        help_embed.type = "rich"
        help_embed.colour = discord.colour.Color.blue()
        if server.validate_on_duty(message.author):
            if server.admin_check(message.author):
                help_embed.add_field(name="\"-add (name) [-h | parent_name]\"",
                                     value="(Admins Only), create a new queue)", inline=False)
                help_embed.add_field(name="\"-delete (name)\"",
                                     value="(Admins Only), Delete the queue)", inline=False)
                help_embed.add_field(name="\"-reload\"",
                                     value="(Admins Only), reload all configurations and reset queues)", inline=False)
                help_embed.add_field(name="\"-empty\"",
                                     value="(Admins Only), empty all queues)", inline=False)
            help_embed.add_field(name="\"-remove (@student)\"",
                                 value="remove the mentioned student from all queues", inline=False)
            help_embed.add_field(name="\"-shift\"",
                                 value="Toggle your availability", inline=False)
            help_embed.add_field(name="\"-ready (queue_name)\"",
                                 value="Take the next person off the specified queue", inline=False)
            help_embed.add_field(name="\"-done\"", value="Removes previous voice channel", inline=False)
        help_embed.add_field(name="\"-queue (queue_name)\"", value="Join the selected queue",
                             inline=False)
        help_embed.add_field(name="\"-leave\"", value="Leave all queues", inline=False)
        help_embed.add_field(name="\"-show [ queue_name ]\"",
                             value="Show all queues or the specified queue", inline=False)
        help_embed.add_field(name="\"-queues\"", value="Show all queues", inline=False)
        help_embed.add_field(name="\"-who\"", value="Shows all on-duty mentors", inline=False)
        await message.channel.send(embed=help_embed)
    else:
        await message.channel.send("Usage: `-help`")
        return


async def add(message):
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    if not server.admin_check(message.author):
        return
    if len(divided) == 2:
        name = divided[1].lower()
        if name in server.queues:
            await message.channel.send("This queue already exists")
            return
        else:
            server.queues[name] = Queue(True, name)
            await message.channel.send("New queue has been added to the system")
            server.save()
    elif len(divided) == 3:
        name = divided[1].lower()
        if name in server.queues:
            await message.channel.send("This queue already exists")
            return
        if divided[2].lower() == "-h":
            server.queues[name] = Queue(False, name)
            await message.channel.send("New queue has been added to the system")
            server.save()
            return
        else:
            parent = divided[2].lower()
            if parent in server.queues:
                server.queues[name] = Queue(True, name)
                server.queues[name].parent = server.queues[parent]
                server.queues[parent].children.append(server.queues[name])
                await message.channel.send("New queue has been added to the system")
                server.save()
                return
            else:
                await message.channel.send("The specified parent is not in the system")
                return
    else:
        await message.channel.send("Usage: `-add (queue) [-h | parent_queue]`")
        return


async def enqueue(message):
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    if len(divided) != 2:
        await message.channel.send("Please specify a valid queue (" + server.get_help() + ") after a space")
        return
    destination = divided[1].lower()
    if destination in server.queues and server.queues[destination].joinable:
        if message.author in server.current_students:
            if message.author in server.queues[destination].students:
                await message.channel.send("You are already in the " + destination + " queue")
                return
            else:
                await message.channel.send("You are already in a queue. Use `-show` to see which queue you are in" +
                                           " or `-leave` to leave all queues")
                return
        else:
            await server.queues[destination].join_queue(message)
            server.current_students.append(message.author)
            server.students_queued += 1
            mentors = server.get_role("on-duty mentor").members
            if len(mentors) == 0:
                await message.channel.send("Please note that there are currently no mentors on duty. " +
                                           "You may experience long queueing times. " +
                                           "You can use the `-leave` command to exit the queue for now if desired.")
                return
            on_duty = False
            for mentor in mentors:
                for role in mentor.roles:
                    if role.name.lower() == f"Mentor - {destination}".lower():
                        on_duty = True
                        break
            if not on_duty:
                await message.channel.send("Please note that there are currently no mentors on duty for this queue. " +
                                           "You may experience long queueing times. " +
                                           "You can use the `-leave` command to exit the queue for now if desired.")
            return
    if destination not in server.queues or destination in server.queues and not server.queues[destination].joinable:
        await message.channel.send("Please specify a valid queue (" + server.get_help() + ") after a space")
        return


async def leave(message):
    server = guild_collection[message.guild.id]
    divider = message.content.strip().split()
    if len(divider) != 1:
        await message.channel.send("The `-leave` command takes no arguments")
        return
    server.leave_queues(message.author)
    await message.channel.send("You have left all queues")


def find_mentor_category(guild):
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
    server = guild_collection[message.guild.id]
    mentor = message.author
    if not server.validate_mentor(mentor):
        return
    if not await server.remove_mentor_channel(mentor):
        await message.channel.send(f"Channel Removal failure, {mentor.mention} please continue with the queue.\n"
                                   f"@GenCusterJrB#0723, please resolve this issue")


async def ready(message):
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    mentor = message.author
    if not server.validate_mentor(mentor):
        return
    if len(divided) != 2:
        await message.channel.send("Usage: `-ready (queue)`")
        return
    await server.remove_mentor_channel(mentor)
    destination = divided[1].lower()
    if destination in server.queues:
        target = server.queues[destination]
        if len(target.students) == 0:
            await message.channel.send("No students are currently queued")
            return
        else:
            student = target.get_front()
            server.leave_queues(student)
            topic = target.get_topic()
            table_num = target.new_queue_table()
            voice_channel = await client.get_guild(
                message.guild.id).create_voice_channel(name=f"{topic}-{table_num}",
                                                       category=find_mentor_category(message.guild))
            invite = await voice_channel.create_invite(max_age=3 * 60)
            await message.channel.send(f"{mentor.mention} you are now to meet with {student.mention}.\nPlease join "
                                       f"{topic}-{table_num} {invite}")
            server.assign_mentor(mentor, voice_channel)
    else:
        await message.channel.send("Invalid queue specified. Valid queues are: " + server.get_help())
        return


async def empty(message):
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
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    mstr_str = ""
    if len(divided) == 1:
        if len(server.current_students) == 0:
            await message.channel.send("All queues are currently empty")
            return
        else:
            for queue in server.queues:
                if server.queues[queue].joinable and len(server.queues[queue].students) != 0:
                    mstr_str += str(server.queues[queue])
            await message.channel.send(mstr_str)
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
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    if not server.admin_check(message.author):
        return
    if len(divided) != 2:
        await message.send("Usage: `-delete (queue)`")
        return
    target = divided[1].lower()
    if target in server.queues:
        if server.queues[target].children:
            await message.send("The specified hidden queue contains children. they must be deleted first")
            return
        else:
            if server.queues[target].parent:
                server.queues[target].parent.children.remove(server.queues[target])
            del server.queues[target]
            await message.channel.send("The specified queue has been deleted")
            server.save()
    else:
        await message.send("Invalid queue")
        return


async def remove(message):
    server = guild_collection[message.guild.id]
    if server.validate(message.author):
        if len(message.mentions) == 1:
            server.leave_queues(message.mentions[0])
            await message.channel.send(message.mentions[0].name + " was removed from all queues")
        else:
            await message.channel.send("Usage: `-remove (@user)")


def beautify_mentor_skills(skills):
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
    channel = message.channel
    server = guild_collection[message.guild.id]
    on_duty_role = server.get_role("on-duty mentor")
    on_duty_mentors = on_duty_role.members
    embed = discord.Embed(title="On-Duty Mentors")
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
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    if not server.admin_check(message.author):
        return
    if len(divided) == 1:
        await server.reload(message.guild)
        await message.channel.send("System reset")
    else:
        await message.channel.send("`-reload` does not accept any arguments")


async def show_queues(message):
    divided = message.content.strip().split()
    server = guild_collection[message.guild.id]
    mstr_str = "The Queues are:\n"
    if len(divided) == 1:
        for queue in server.queues:
            if server.queues[queue].joinable:
                mstr_str += server.queues[queue].get_topic() + "\n"
        await message.channel.send(mstr_str)
        return
    else:
        await message.channel.send("Usage: `-showqueues")
        return


def get_channel(target, guild):
    for channel in guild.channels:
        if channel.name.lower() == target.lower():
            return channel
    return None


def check_muted(message) -> bool:
    author = message.author
    if isinstance(author, discord.User):
        return


@client.event
async def on_ready():
    for guild in client.guilds:
        if guild.id not in guild_collection:
            guild_collection[guild.id] = Server(guild.id)
            guild_collection[guild.id].load()
            await guild_collection[guild.id].setup(guild)


@client.event
async def on_message(message):
    if check_muted(message):
        return
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
    elif command == "-bye":
        await message.channel.send(f"Until Next Year...")


def main():
    # who needs security...hardcode all the things
    client.run('ODA3Njc1NzI1MDQ5MTAyMzM2.YB7cog.jY41rZfw9VwXngBpPL8qBnrKWh8')


if __name__ == '__main__':
    main()
