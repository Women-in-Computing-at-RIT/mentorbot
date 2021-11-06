import discord


class Queue:
    """
    Custom queue class created for Mentor Bot
    """

    def __init__(self, joinable, name):
        self.joinable = joinable
        self.parent = None
        self.children = []
        self.students = []
        self.name = name
        self.tables = 1

    async def join_queue(self, message):
        """
        Join queue and its parent queues
        :param message: Discord message
        """
        self.students.append(message.author)
        await message.channel.send("You have joined the " + self.name +
                                   " queue. You are in position #" + str(len(self.students)))
        if self.parent:
            await self.parent.join_queue(message)

    def get_front(self):
        """
        Get the front of the queue
        :return: Hacker in front of queue
        """
        return self.students[0]

    def get_topic(self):
        """
        Get topic name
        :return: Topic name
        """
        return self.name

    def new_queue_table(self):
        """
        Create new queue
        :return: Queue table
        """
        self.tables += 1
        if self.tables > 15:
            self.tables = 2
        return self.tables - 1

    def __str__(self):
        """
        Print hackers in each queue
        :return:
        """
        to_return = "The current queue for " + self.name + ":"
        pos = 1
        for student in self.students:
            to_return += "\n" + str(pos) + ". "
            try:
                if student.nick is not None:
                    to_return += student.nick
                else:
                    to_return += student.name
            except:
                to_return += student.name
            pos += 1
        to_return += "\n"
        return to_return
