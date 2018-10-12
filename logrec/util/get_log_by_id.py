#!/usr/bin/env python

from logrec.util import io_utils

__author__ = 'hlib'

# id = sys.argv[1]
id = "mapbox_161506"
pp_logs_gen = io_utils.load_preprocessed_logs()
for log in pp_logs_gen:
    if log.id == id:
        print(log.text)
        print(log.level)
        print(log.context.context_before)
        exit(0)
print("Id " + str(id) + " not found")
exit(1)
