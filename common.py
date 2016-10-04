#!/bin/python

import time
import os
import re
# import datetime
# import requests
# import threading

def log(text, context="info", namespace="run"):
    # To log in var log
    log_path = '/var/log/snowflake/'
    # To log locally
    # log_path = 'logs/
    date = time.strftime("%c")
    if not os.path.exists(log_path):
        os.makedirs(log_path)
    f = open(log_path + namespace + '.log', 'a')
    try:
        for l in iter(text.splitlines()):
            detector = re.compile('\033\[\d+(?:;\d+)?m')
            print("--- [" + str(date) + "] - [" + context + "][" + namespace + "] - " + detector.sub('', l))
            f.write("--- [" + str(date) + "] - [" + context + "][" + namespace + "] - " + detector.sub('', l) + "\n")
            # esthread = threading.Thread(target=es_submit, args=(detector.sub('', l), context, namespace))
            # esthread.start()
    except:
        detector = re.compile('\033\[\d+(?:;\d+)?m')
        print("--- [" + str(date) + "] - [" + context + "][" + namespace + "] - " + detector.sub('', str(text)))
        f.write("--- [" + str(date) + "] - [" + context + "][" + namespace + "] - " + detector.sub('', str(text)) + "\n")
        # esthread = threading.Thread(target=es_submit, args=(detector.sub('', str(text)), context, namespace))
        # esthread.start()
    f.close()


