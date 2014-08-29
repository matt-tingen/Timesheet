Timesheet
=========

This is a simple timesheet parser with support for hierachical tasks

To use, call `python timesheet.py input_file`

The input file should have line-delimited tasks where a task consists of a start time (implied or explicit), and end time, and a hierarchy of descriptors.
Each token in the task must be separated by whitespace containing at least one tab.
For example,
  
    10:30	11:30	Meeting	Code review
will create a task from 10:30 AM to 11:30 AM with the hierarchy `Meeting > Code Review`.
Now if you were to create another task with the parent of `Meeting`, they would be lumped together.

The start time for a task other than the first can be omitted and it will use the previous task's end time as it's start time:
    
    13:00	15:00	Meeting	Code review
    		16:00	Meeting	Sprint kickoff
Here, two tasks will be created under the parent `Meeting`: `Code review` which runs from 1pm-3pm and `Sprint kickoff` which runs from 3pm-4pm. The indention at the beginning of the second line is not necessary but makes it easier to understand.

Times can be in a number of formats that will be configurable in the future. Currently the following are supported:
* `%I:%M %p` (01:45 PM, 09:23 AM, 8:55 am, etc.)
* `%H:%M` (13:45, 09:23, 08:55, etc.)
* `%H.%M` (13.45, 09.23, 08.55, etc.)

Parent task can be excluded from the display and total time by including them in the line-delimited `blacklist` file.

Tasks can have any number of levels to their hierarchy, but more than three or four is probably not practical.

C-style comments (`//` and `/* */`) are supported.

Task descriptors are case-insensitive.

Here's a sample timesheet with output:

    /*	
    Example timesheet
    Thursday, August 28, 2014
    */
    09:00	9:30	Issue #1422	discussing with Patrick
    		10.20	meeting	daily stand up	
    		10.25	break	Coffee time // This task will be ignored because it is blacklisted
    		10:41	Issue #1422	restarting server
    10:44	10:56	issue #1372	reviewing
    		11:53	Issue #1372	Merging code
    		12:47	lunch // blacklisted
    		1:00 pm	Issue #1372	Merging code
    		16:03	meeting	code review
    		16:21	Issue #1372	Merging code
    		16:40	issue #1372

    // ...
    
Yields

    Total time: 6:19
    
    issue #1422 (0:00/0:46)
        discussing with patrick (0:30)
        restarting server (0:16)
    meeting (0:00/3:53)
        daily stand up (0:50)
        code review (3:03)
    issue #1372 (0:19/1:59)
        reviewing (0:12)
        merging code (1:28)
