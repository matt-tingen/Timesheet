import sys
import re
import json
import datetime

class TaskFormatter:
    def __init__(self, indention='\t', time_format='{hours}:{minutes:02}'):
        self.indention = indention
        self.time_format = time_format

    def format_task_list(self, task_list, indention_level=0):
        list_string = ''

        for task in task_list:
            list_string += indention_level * self.indention
            list_string += self.format_task(task) + '\n'

            if task.sub_tasks:
                list_string += self.format_task_list(task.sub_tasks, indention_level + 1)

        return list_string

    def format_task(self, task):
        time_string = self.format_timedelta(task.duration)

        if task.sub_tasks:
            time_string += '/' + self.format_timedelta(task.total_duration())

        return '{} ({})'.format(task.name, time_string)

    def format_timedelta(self, timedelta):
        # A datetime.timedelta does not have a strptime method
        # and only has days, seconds, and microseconds attributes.
        hours, minutes = divmod(timedelta.seconds // 60, 60)
        return self.time_format.format(hours=hours, minutes=minutes)


class Task:
    def __init__(self, name, duration=None):
        self.name = name
        self.sub_tasks = []
        self.duration = duration or datetime.timedelta(0)

    def total_duration(self):
        return self.duration + sum((t.total_duration() for t in self.sub_tasks), datetime.timedelta(0))

    # task_name is case insensitive
    def get_sub_task(self, task_name):
        task_name = task_name.lower()

        try:
            return next(t for t in self.sub_tasks if t.name.lower() == task_name)
        except StopIteration:
            return None

    def add_sub_task(self, sub_task):
        existing_task = self.get_sub_task(sub_task.name)

        if existing_task is None:
            self.sub_tasks.append(sub_task)
        else:
            existing_task.duration += sub_task.duration

            for grandchild_task in sub_task.sub_tasks:
                existing_task.add_sub_task(grandchild_task)

    def __repr__(self):
        return '<Task({}, {}) with {} sub-tasks>'.format(self.name, self.duration, len(self.sub_tasks))


class TaskParseError(ValueError):
    pass


class TaskParser:
    # blacklisted_task_names is case insensitive
    def __init__(self, delimiter, time_formats, blacklisted_task_names=()):
        self.delimiter = delimiter
        self.time_formats = time_formats
        self.blacklist = {n.lower() for n in blacklisted_task_names}

    def parse(self, input_text):
        input_text = self.remove_block_comments(input_text)
        input_text = self.remove_line_comments(input_text)

        root_task = Task(None)
        previous_end_time = None

        for line in re.split(r'[\r\n]+', input_text):
            line = line.strip()

            if line:
                task, previous_end_time = self.parse_task(line, previous_end_time)

                if task.name.lower() not in self.blacklist:
                    root_task.add_sub_task(task)

        return root_task

    def parse_task(self, line, previous_end_time=None):
        parts = tuple(p for p in line.split(self.delimiter) if p)

        # first_time may correspond to start time or end time.
        first_time = self.parse_time(parts[0])

        try:
            second_time = self.parse_time(parts[1])
        except TaskParseError:
            if previous_end_time is None:
                raise

            start = previous_end_time
            end = first_time
            first_task_index = 1
        else:
            start = first_time
            end = second_time
            first_task_index = 2

        final_index = len(parts) - 1

        if final_index < first_task_index:
            raise TaskParseError("Missing task")

        # Only the deepest subtask will have a duration; higher tasks will
        # reflect the duration in their total_duration.
        get_duration = lambda i: end - start if i == final_index else None
        final_task = root_task = Task(parts[first_task_index], get_duration(first_task_index))

        for i, task_name in enumerate(parts[first_task_index + 1:], first_task_index + 1):
            task = Task(task_name, get_duration(i))
            final_task.add_sub_task(task)
            final_task = task

        return root_task, end

    def parse_time(self, time_string):
        for time_format in self.time_formats:
            try:
                return datetime.datetime.strptime(time_string, time_format)
            except ValueError:
                pass

        raise TaskParseError('Time string did not match any format strings: ' + time_string)

    @staticmethod
    def remove_block_comments(input_text):
        return re.sub(r'/\*.*\*/', '', input_text, flags=re.DOTALL)

    @staticmethod
    def remove_line_comments(input_text):
        return re.sub(r'//.*', '', input_text)


def main():
    try:
        input_filename = sys.argv[1]
    except IndexError:
        print('Must pass a file as argument')
        exit()

    with open('config.json') as config_file:
        config = json.load(config_file)

    parser = TaskParser(**config["parser"])
    formatter = TaskFormatter(**config["formatter"])

    with open(input_filename) as input_file:
        file_contents = input_file.read()

    task = parser.parse(file_contents)

    total_duration = formatter.format_timedelta(task.total_duration())

    print('Total Time: {}\n'.format(total_duration))
    print(formatter.format_task_list(task.sub_tasks))

if __name__ == '__main__':
    main()