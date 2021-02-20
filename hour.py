import datetime


class Hour:
    def __init__(self, start_time):
        self.start_time = start_time
        self.end_time = None
        self.hours = None

    def update(self):
        self.end_time = datetime.datetime.now()
        self.hours = self.end_time - self.start_time

    def __str__(self):
        return "Start: " + str(self.start_time).split(".")[0] + "\n" + \
            "End: " + str(self.end_time).split(".")[0] + "\n" + \
            "Time on Clock: " + str(self.hours).split(".")[0] + "\n"
