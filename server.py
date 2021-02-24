import discord
from custom_queue import Queue


class Server:
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
        for role in guild.roles:
            if "off-duty mentor" in role.name.lower():
                self.roles["off-duty mentor"] = role
            elif "on-duty mentor" in role.name.lower():
                self.roles["on-duty mentor"] = role
            elif "admin" in role.name.lower():
                self.roles["admin"] = role
        if len(self.roles) != 3:
            if "off-duty mentor" not in self.roles:
                self.roles["off-duty mentor"] = await guild.create_role(name="off-duty mentor")
            if "on-duty mentor" not in self.roles:
                self.roles["on-duty mentor"] = await guild.create_role(name="on-duty mentor")
            if "admin" not in self.roles:
                self.roles["admin"] = await guild.create_role(name="admin")

    def get_role(self, target):
        if target in self.roles:
            return self.roles[target]
        else:
            return None

    def load(self):
        try:
            file = open(str(self.guild_id), "r")
            for line in file:
                line = line.strip()
                if len(line.split(",")) == 1:  # If it doesn't have a parent
                    if line.startswith("!"):  # If it is not joinable
                        name = line[1:].strip()
                        self.queues[name] = Queue(False, name)
                    else:
                        name = line.strip()
                        self.queues[name] = Queue(True, name)
                else:
                    temp = line.strip().split(",")
                    name = temp[0]
                    parent = temp[1]
                    self.queues[name] = Queue(True, name)
                    self.queues[parent].children.append(self.queues[name])
                    self.queues[name].parent = self.queues[parent]
            file.close()
        except FileNotFoundError:
            pass

    def save(self):
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
        return self.roles["on-duty mentor"] in user.roles or self.roles["admin"] in user.roles

    def validate(self, user):
        return self.roles["on-duty mentor"] in user.roles \
               or self.roles["admin"] in user.roles \
               or self.roles["off-duty mentor"] in user.roles

    def admin_check(self, user):
        return self.roles["admin"] in user.roles

    def leave_queues(self, user):
        for queue in self.queues:
            if user in self.queues[queue].students:
                self.queues[queue].students.remove(user)
        if user in self.current_students:
            self.current_students.remove(user)

    def assign_mentor(self, mentor, channel):
        self.mentor_channels[mentor] = channel
        return

    async def remove_mentor_channel(self, mentor):
        channel = self.mentor_channels.get(mentor)
        if channel is None:
            return False
        try:
            await channel.delete()
        except discord.errors.NotFound:
            return False
        return True

    async def toggle_shift(self, message, user):
        if self.roles["on-duty mentor"] in user.roles:
            await user.add_roles(self.get_role("off-duty mentor"))
            await user.remove_roles(self.get_role("on-duty mentor"))
            await message.channel.send(f"{message.author.mention} you are now off-duty, thank you for your help")
        else:
            await user.add_roles(self.get_role("on-duty mentor"))
            await user.remove_roles(self.get_role("off-duty mentor"))
            await message.channel.send(f"{message.author.mention} you are now on-duty, good luck :smiley:")
        return
