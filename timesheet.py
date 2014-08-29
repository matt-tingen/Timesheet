import re
import sys
import datetime
from collections import OrderedDict


# TIME_FORMATs is a priority list of formats that will be used for parsing.
# For the syntax of these time strings, see:
# https://docs.python.org/library/time.html#time.strftime
TIME_FORMATS = (
    '%I:%M %p', # 01:45 PM, 09:23 AM, 8:55 am, etc.
    '%H:%M',    # 13:45, 09:23, 08:55, etc.
    '%H.%M',    # 13.45, 09.23, 08.55, etc. (easier to type with numpad)
)

# The path to a line-delimitetedfile contianing tasks which should not count toward clockable time e.g. lunch, break, etc
BLACKLIST_FILE = 'blacklist'

# The string to use for indenting subtasks.
INDENTION_TEXT = '    '

# Format used for task durations. 
# This does not use the same syntax as TIME_FORMAT (see format_timedelta() for why).
# This uses the str.format() method and the keyword args 'hours' and 'minutes'.
DURATION_FORMAT = '{hours}:{minutes:02}' # e.g. 3:45

# Interval and minimum used when rounding times for reporting
TIME_INTERVAL = datetime.timedelta(minutes=15)
TIME_MIN = datetime.timedelta(minutes=15)

#### END CONFIG ####

def format_timedelta(timedelta):
    # A datetime.timedelta does not have a strptime method
    # and only has days, seconds, and microseconds attributes.
    hours, minutes = divmod(timedelta.seconds // 60, 60)
    return DURATION_FORMAT.format(hours=hours, minutes=minutes)


def round_time(time):
    time = round(time / TIME_INTERVAL) * TIME_INTERVAL
    return max(TIME_MIN, time)

def parse_time(time_str):
    for time_format in TIME_FORMATS:
        try:
            return datetime.datetime.strptime(time_str, time_format)
        except ValueError:
            pass
    raise ValueError('Time string did not match any format strings')


class TaskParseError(ValueError):
    pass

class Task:
    def __init__(self, start_time, end_time, task_hierarchy):
        """
        start_time and end_time are datetime objects
        task_hierarchy is a list of strings with the first item being the 
            parent and following items being children, grandchildren, etc.
        """
        self.start = start_time
        self.end = end_time
        self.hierarchy = list(task_hierarchy)

        self.duration = end_time - start_time

    @classmethod
    def from_string(cls, input_string, prev_end_time=None):
        # Split on all (non-linebreak) whitespace that contains at least one tab to allow free spacing
        split_input = [x.strip() for x in re.split(r'\s*\t\s*', input_string) if x.strip()]

        insufficient_items_error = TaskParseError('Insufficient items in task string:\n' + input_string)
        invalid_time_error_msg = lambda s: TaskParseError('Invalid time in task string:\n' + s)

        # Start time can be omitted from input_string if supplied via prev_end_time.
        # If both are present, the value from input_string takes precadence.
        try:
            first_time = parse_time(split_input[0])
        except IndexError:
            raise insufficient_items_error
        except ValueError:
            raise invalid_time_error_msg(split_input[0])

        try:
            second_time = parse_time(split_input[1])
        except IndexError:
            raise insufficient_items_error
        except ValueError:
            if prev_end_time is None:
                raise invalid_time_error_msg(split_input[1])
            else:
                start_time = prev_end_time
                end_time = first_time
                hierarchy = split_input[1:]
        else:
            start_time = first_time
            end_time = second_time
            try:
                hierarchy = split_input[2:]
            except IndexError:
                raise insufficient_items_error

        return cls(start_time, end_time, hierarchy)

    def __str__(self):
        return '{} ({})'.format(self.hierarchy[0], format_timedelta(self.duration))

    def __repr__(self):
        max_length = 10
        abbreviated_hierarchy = [x[:max_length] + '...' if len(x) > max_length else x for x in self.hierarchy]
        return '<Task (duration {}) {})>'.format(format_timedelta(self.duration), abbreviated_hierarchy)


class Timesheet:
    def __init__(self, tasks=None, blacklist=None):
        self.clear()
        self._blacklist = set(blacklist or [])

        for task in (tasks or []):
            self.add_task(task)

    @classmethod
    def from_file(cls, filename, blacklist=None):
        with open(filename) as f:
            text = f.read()

        # Remove block comments
        text = re.sub(r'/\*.*\*/', '', text, flags=re.DOTALL)
        # Remove end-of-line comments
        text = re.sub(r'//.*', '', text)

        tasks = cls(blacklist=blacklist)

        prev_end_time = None
        for line_num, line in enumerate(text.split('\n'), 1):
            if not line.strip():
                continue

            try:
                task = Task.from_string(line, prev_end_time)
            except TaskParseError as err:
                raise TaskParseError('Error on line {} - {}'.format(line_num, err))

            prev_end_time = task.end
            tasks.add_task(task)

        return tasks

    def _new_child_level(self):
        # Each level in the hierarchy keeps track of the time spend on that particular level,
        # the total duration of all tasks at that level and all child levels,
        # as well as its child levels in the order entered.
        return {
            'time': datetime.timedelta(),
            'total_time': datetime.timedelta(),
            'children': OrderedDict()
        }

    def add_level(self, parent_level, child_name):
        child_name = child_name.lower()
        if child_name not in parent_level['children']:
            parent_level['children'][child_name] = self._new_child_level()
        return parent_level['children'][child_name]

    def clear(self):
        self._tasks = []
        self._hierarchy = self._new_child_level()

    def add_task(self, task):
        if task.hierarchy[0] not in self._blacklist:
            self._tasks.append(task)

            current_level = self._hierarchy
            current_level['total_time'] += task.duration
            for level in task.hierarchy:
                current_level = self.add_level(current_level, level)
                current_level['total_time'] += task.duration
            current_level['time'] += task.duration

    def __str__(self):
        def str_from_level(level, level_name, depth):
            string = '{indent}{name} ({time}/{total_time})'.format(
                indent = depth * INDENTION_TEXT,
                name = level_name,
                time = format_timedelta(level['time']),
                total_time = format_timedelta(level['total_time'])
            )
            for sublevel_name, sublevel in level['children'].items():
                string += '\n' + str_from_level(sublevel, sublevel_name, depth + 1)
            return string

        string = 'Total time: {}\n'.format(format_timedelta(self._hierarchy['total_time']))

        for level_name, level in self._hierarchy['children'].items():
            string += '\n' + str_from_level(level, level_name, 0)

        return string


def main():
    try:
        filename = sys.argv[1]
    except IndexError:
        print('Must pass a file as argument')
        exit()

    try:
        with open(BLACKLIST_FILE) as f:
            blacklist = [x.strip() for x in re.split(r'(?:\r?\n)+', f.read()) if x.strip()]
    except OSError:
        blacklist = []
        
    try:
        timesheet = Timesheet.from_file(filename, blacklist)
    except TaskParseError as err:
        print(err)
        exit()
    except OSError:
        print('Unable to read file')
        exit()

    print(timesheet)


if __name__ == '__main__':
    main()