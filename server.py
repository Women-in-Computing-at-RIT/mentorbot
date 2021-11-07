import discord
from custom_queue import Queue


class Server:
    """
    Server class for Mentor Bot
    """

    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.roles = dict()
        self.current_students = []
        self.valid_classes = []
        self.queues = dict()
        self.on_duty = []
        self.stat_set = dict()
        self.students_queued = 0
        self.students_helped = 0
        self.mentor_channels = dict()

    async def setup(self, guild):
        """
        Create roles that bot uses for logic
        :param guild: collection of users and channels
        """
        for role in guild.roles:
            if "off-duty mentor" in role.name.lower():
                self.roles["off-duty mentor"] = role
            elif "on-duty mentor" in role.name.lower():
                self.roles["on-duty mentor"] = role
            elif "botsmith" in role.name.lower():
                self.roles["botsmith"] = role
        if len(self.roles) != 3:
            if "off-duty mentor" not in self.roles:
                self.roles["off-duty mentor"] = await guild.create_role(name="off-duty mentor")
            if "on-duty mentor" not in self.roles:
                self.roles["on-duty mentor"] = await guild.create_role(name="on-duty mentor")
            if "botsmith" not in self.roles:
                self.roles["botsmith"] = await guild.create_role(name="botsmith")

    def get_role(self, target):
        """
        Get user roles
        :param target: user roles
        :return: Roles user belongs to, else None if no roles
        """
        if target in self.roles:
            return self.roles[target]
        else:
            return None

    def load(self):
        """
        Load server
        """
        try:
            file = open(str(self.guild_id), "r")
            for line in file:
                line = line.strip()
                if len(line.split(",")) == 1:  # If it doesn't have a parent
                    if line.startswith("!"):  # If it is not able to be joined
                        name = line[1:].strip()
                        self.queues[name.lower()] = Queue(False, name)
                    else:
                        name = line.strip()
                        self.queues[name.lower()] = Queue(True, name)
                else:
                    temp = line.strip().split(",")
                    name = temp[0]
                    parent = temp[1]
                    self.queues[name.lower()] = Queue(True, name)
                    self.queues[parent].children.append(self.queues[name.lower()])
                    self.queues[name.lower()].parent = self.queues[parent]
            file.close()
        except FileNotFoundError:
            pass

    def save(self):
        """
        Save changes to server
        """
        file = open(str(self.guild_id), "w+")
        for q in self.queues:
            if self.queues[q].children:
                file.write("!" + self.queues[q].name + "\n")
        for q in self.queues:
            if not self.queues[q].children and not self.queues[q].parent:
                file.write(self.queues[q].name + "\n")
        for q in self.queues:
            if not self.queues[q].children and self.queues[q].parent:
                file.write(self.queues[q].name + "," + self.queues[q].parent.name + "\n")
        file.close()

    async def reload(self, guild):
        """
        Reload server
        :param guild: Collection of users and channels
        """
        self.roles = dict()
        self.current_students = []
        self.valid_classes = []
        self.queues = dict()
        self.on_duty = []
        self.stat_set = dict()
        await self.setup(guild)
        self.load()

    def get_help(self):
        res = ""
        for queue in self.queues:
            if not self.queues[queue].children:
                res += self.queues[queue].name + " | "
        return res[:-3]

    def get_help_mentor(self):
        res = ""
        for queue in self.queues:
            res += self.queues[queue].name + " | "
        return res[:-3]

    def validate_on_duty(self, user):
        """
        Check if a user is an on-duty mentor
        :param user: user to be checked
        :return: true if an on-duty mentor, false otherwise
        """
        return self.roles["on-duty mentor"] in user.roles

    def validate_mentor(self, user):
        """
        Check if a user is a mentor
        :param user: user to be checked
        :return: true if a user is a mentor, false otherwise
        """
        return self.roles["on-duty mentor"] in user.roles \
               or self.roles["off-duty mentor"] in user.roles

    def validate(self, user):
        """
        Check if a user is a mentor or bot
        :param user: user to be checked
        :return: true if a user is a mentor or bot, false otherwise
        """
        return self.roles["on-duty mentor"] in user.roles \
               or self.roles["botsmith"] in user.roles \
               or self.roles["off-duty mentor"] in user.roles

    def admin_check(self, user):
        """
        Check if a user is an admin ("botsmith") role
        :param user: user to be checked
        :return: true if admin, false otherwise
        """
        return self.roles["botsmith"] in user.roles

    def leave_queues(self, user):
        """
        Remove a user from queues
        :param user: User to be removed
        """
        for queue in self.queues:
            if user in self.queues[queue].students:
                self.queues[queue].students.remove(user)
        if user in self.current_students:
            self.current_students.remove(user)

    def assign_mentor(self, mentor, channel):
        """
        Assign a mentor role to a user
        :param mentor: user to be assigned
        :param channel: collection of channels and users
        """
        self.mentor_channels[mentor] = channel
        return

    async def remove_mentor_channel(self, mentor):
        """
        Delete a mentoring channel after it has finished being used
        # TODO: make to voice channel created in a category instead of at top of server
        :param mentor: Mentor user
        :return: true if successful, false otherwise
        """
        channel = self.mentor_channels.get(mentor)
        if channel is None:
            return False
        try:
            await channel.delete()
        except discord.errors.NotFound:
            return False
        return True

    async def toggle_shift(self, message, user):
        """
        Toggle mentor shifts
        :param message: Discord message
        :param user: mentor to toggle shift
        """
        # Off-duty
        if self.roles["on-duty mentor"] in user.roles:
            await user.add_roles(self.get_role("off-duty mentor"))
            await user.remove_roles(self.get_role("on-duty mentor"))
            await message.channel.send(f"{message.author.mention} you are now off-duty, thank you for your help")
        # On-duty
        else:
            await user.add_roles(self.get_role("on-duty mentor"))
            await user.remove_roles(self.get_role("off-duty mentor"))
            await message.channel.send(f"{message.author.mention} you are now on-duty, good luck :smiley:")
        return
