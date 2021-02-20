class Stat:
    def __init__(self):
        self.hour_set = []
        self.total_hours = None

    def add_hours(self, hours):
        self.hour_set.append(hours)

    def update(self):
        self.hour_set[-1].update()
        self.update_total()

    def update_total(self):
        if self.total_hours is None:
            self.total_hours = self.hour_set[-1].hours
        else:
            self.total_hours += self.hour_set[-1].hours

    def clear(self):
        self.total_hours = None
        for hour in self.hour_set:
            if hour.end_time is not None:
                self.hour_set.remove(hour)

    def __str__(self):
        to_return = ""
        for block in self.hour_set:
            if block.end_time is not None:
                to_return += str(block) + "\n"
        to_return += "Total Hours: " + str(self.total_hours).split(".")[0] + "```"
        return to_return
