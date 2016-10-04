#!/bin/python

import flake
import sys
from multiprocessing.dummy import Pool as ThreadPool
from common import *
import threading
from pympler import tracker


if len(sys.argv) > 1:
    testin = str(sys.argv[1])
else:
    testin = ''


def snowfall():

    def metric_flake_run(fl):
        this = flake.FlakeMetric(metricflakes[fl])
        this.submit()
        this.build_alarms()

    def job_flake_run(fl):
        this = flake.FlakeJob(jobflakes[fl])
        this.submit()
        this.build_alarms()

    # start the multiproccessing pool
    log("Starting flake cycle...")
    if testin is None:
        snow = flake.Configer()
        metricflakes = snow.metricConfig()
    else:
        snow = flake.Configer(testin)
        metricflakes = snow.metricConfig()
    if len(metricflakes) > 0:
        pool = ThreadPool(len(metricflakes))
        pool.map(metric_flake_run, metricflakes)
        pool.close()
        pool.join()
    else:
        log("No flake metrics to run.")

    log("Starting job flake cycle...")
    if testin is None:
        snow = flake.Configer()
        jobflakes = snow.jobConfig()
    else:
        snow = flake.Configer(testin)
        jobflakes = snow.jobConfig()
    if len(jobflakes) > 0:
        pool = ThreadPool(len(jobflakes))
        pool.map(job_flake_run, jobflakes)
        pool.close()
        pool.join()
    else:
        log("No flake jobs to run.")

    log("test end script")


if len(sys.argv) > 1:
    snowfall()
else:
    while True:
        log("Starting next cycle in 60 seconds...")
        time.sleep(60)
        log("Starting snowfall...")
        try:
            snowthread = threading.Thread(target=snowfall)
            snowthread.start()
            log("Initiated cycle and sent to background...")
        except Exception as e:
            log('ERROR while starting flake run this cycle.  Trying again next cycle...')
            log(str(e))
