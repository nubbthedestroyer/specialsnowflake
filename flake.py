#!/bin/python

from common import *
import subprocess as sub
import boto3
import tempfile
import shutil
import os
import simplejson as json
import time
import croner
import re
import sys
import requests
import datetime
from datetime import datetime as dater


class Configer:
    def __init__(self, one_run=''):
        self.Flakes = {}
        cwd = os.path.dirname(os.path.realpath(sys.argv[0]))
        if one_run is None:
            for root, dirs, files in os.walk(cwd + "/flakes"):
                for f in files:
                    self.Flakes[f] = json.loads(open(root + "/" + f).read())
                    if 'flakeAlarms' not in self.Flakes[f]:
                        self.Flakes[f]['flakeAlarms'] = []
        else:
            for root, dirs, files in os.walk(cwd + "/flakes"):
                for f in files:
                    if one_run in f:
                        self.Flakes[f] = json.loads(open(root + "/" + f).read())
                        if 'flakeAlarms' not in self.Flakes[f]:
                            self.Flakes[f]['flakeAlarms'] = []

    def metricConfig(self):
        metricFlakes = {}
        for f in self.Flakes:
            if str(self.Flakes[f]['flakeType']) == str('metric'):
                metricFlakes[f] = self.Flakes[f]

        return metricFlakes

    def jobConfig(self):
        jobFlakes = {}
        for f in self.Flakes:
            if str(self.Flakes[f]['flakeType']) == str('job'):
                jobFlakes[f] = self.Flakes[f]

        return jobFlakes


class CheckCron:
    def __init__(self, cronstring="* * * * *"):
        job = croner.CronExpression(cronstring)
        self.yesno = job.check_trigger((dater.now().year,
                                   dater.now().month,
                                   dater.today().day,
                                   dater.now().hour,
                                   dater.now().minute))

    def check(self):
        return self.yesno


class FlakeMetric:
    client = boto3.client('cloudwatch')

    def __init__(self, config):
        self.ff = config
        self.metric = ""
        ff = config
        # log("Loaded flake: " + config["flakeName"], "info", ff['flakeName'])
        if CheckCron(str(self.ff['flakeCronstring'])).check() is True:
            log("Running flake: " + ff["flakeName"], "info", ff['flakeName'])
            try:
                starttime = time.time()
                creds = json.loads(open('creds.json').read())
                env = os.environ.copy()
                env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games' + \
                              env["PATH"]
                env.update(creds)
                pop = sub.Popen(ff['flakeCommand'], env=env, stdout=sub.PIPE, stderr=sub.PIPE, shell=True)
                p = ''
                pe = ''
                try:
                    while True:
                        out = pop.stdout.readline()
                        if out.decode() is not None:
                            # log(out.decode(), "info", ff['flakeName'])
                            p += str(out.decode())
                        if pop.poll() is not None:
                            break
                    while True:
                        err = pop.stdout.readline()
                        if err.decode() is not None:
                            # log(err.decode(), "error", ff['flakeName'])
                            pe += str(err.decode())
                        if pop.poll() is not None:
                            break
                except Exception as e:
                    log('Error while grabbing output of subprocess. ' + str(e), "error", ff['flakeName'])
                self.metric = p
                log("Returned Value is: \"" + str(p) + "\"", "info", ff['flakeName'])
                if pe:
                    log("Returned Error is: \"" + str(pe) + "\"", "error", ff['flakeName'])
                endtime = time.time()
                runtime = float(endtime) - float(starttime)
            except sub.CalledProcessError as cp:
                log("Flake " + ff['flakeName'] + " failed", "error", ff['flakeName'])
                log(str(cp), "error", ff['flakeName'])
            except Exception as e:
                log("Flake " + ff['flakeName'] + " failed", "error", ff['flakeName'])
                log(str(e), "error", ff['flakeName'])
            else:
                log("Flake " + ff['flakeName'] + " ran in [" + str(runtime) + "] seconds...",
                    "info",
                    ff['flakeName'])
        else:
            log("Not running flake " + ff["flakeName"] + " because the flakeCronstring is not true", "info", ff['flakeName'])

    def submit(self):
        if CheckCron(str(self.ff['flakeCronstring'])).check() is True:
            try:
                metric_val = float(self.metric)
            except:
                log('Metric is not a number, so not submitting', "error", self.ff['flakeName'])
            else:
                try:
                    re.search('[a-zA-Z]', self.metric)
                except Exception:
                    if not self.metric:
                        self.metric = "Didnt grab any data"
                else:
                    if not re.search('[a-zA-Z]', self.metric):
                        datapoints = []
                        datapoint = {
                            'MetricName': self.ff['flakeName'],
                            'Value': float(self.metric),
                            'Unit': self.ff['flakeUnit']
                        }
                        datapoints.append(datapoint)
                        response = self.client.put_metric_data(Namespace=self.ff['flakeMetricNamespace'], MetricData=datapoints)
                        log("Return from metric put: " + str(response), "info", self.ff['flakeName'])
                    else:
                        log("Metric data came back as a string.  Logging below...", "error", self.ff['flakeName'])
                        log(self.metric, "error", self.ff['flakeName'])
            # Submit the value to elasticsearch for kibana visualization
            # try:
            #     esd = {
            #         'post_date': datetime.datetime.utcnow().isoformat(),
            #         'MetricName': self.ff['flakeName'],
            #         'Value': float(self.metric),
            #         'Unit': self.ff['flakeUnit'],
            #     }
            #     esresponse = requests.post('http://search-itu-es-domain2-qcirqn7amfnwul2ijnmrqstu4y.us-east-1.es.amazonaws.com/flake/metric/', json=esd)
            # except Exception as ex:
            #     log(ex)
            # else:
            #     log("Submitted to ES cluster...", "info", self.ff['flakeName'])
            #     log("Output from ES insert:" + str(esresponse), "info", self.ff['flakeName'])

    def build_alarms(self):
        if self.ff['flakeAlarms']:
            if CheckCron(str(self.ff['flakeCronstring'])).check() is True:
                tfdoc = {
                    'provider': {
                        'aws': {
                            'region': self.ff['flakeRegion']
                        }
                    },
                    'resource': {
                        'aws_cloudwatch_metric_alarm': {}
                    }
                }
                for a in self.ff['flakeAlarms']:
                    alarm = {
                        'alarm_name': 'FL-' + self.ff['flakeName'] + '-' + a['alarmName'],
                        "comparison_operator": a['alarmOperator'],
                        "evaluation_periods": a['alarmPeriods'],
                        "metric_name": self.ff['flakeName'],
                        "namespace": self.ff['flakeMetricNamespace'],
                        "period": a['alarmPeriodLength'],
                        "statistic": a['alarmStatistic'],
                        "threshold": a['alarmThreshold'],
                        "alarm_description": a['alarmDescription']
                    }
                    if 'alarm' in a['alarmEndpoints']:
                        alarm["alarm_actions"] = [
                            a['alarmEndpoints']['alarm']
                        ]
                    if 'ok' in a['alarmEndpoints']:
                        alarm["ok_actions"] = [
                            a['alarmEndpoints']['ok']
                        ]
                    if 'insufficient_data' in a['alarmEndpoints']:
                        alarm['insufficient_data_actions'] = [
                            a['alarmEndpoints']['insufficient_data']
                        ]
                    tfdoc['resource']['aws_cloudwatch_metric_alarm']['FL-' + self.ff['flakeName'] +
                                                                     '-' +
                                                                     a['alarmName']] = alarm
                tempd = tempfile.mkdtemp()
                if not os.path.exists(tempd):
                    os.mkdir(tempd)
                tfjson = open(tempd + '/' + 'infra.tf.json', 'w')
                tfjson.write(json.dumps(tfdoc))
                tfjson.seek(0)
                tfjson.close()
                cwd = os.getcwd()
                try:
                    tfresponse = sub.check_output(
                        'cd ' + tempd + ' && /usr/local/bin/terraform apply -refresh=False -no-color -state=' + cwd + "/states/" +
                        self.ff['flakeName'] + ".tfstate", shell=True)
                except Exception as e:
                    log("Attempted to run terraform but got: " + str(e), "error", self.ff['flakeName'] + ".tf")
                else:
                    log(str(tfresponse.decode()), "info", self.ff['flakeName'] + ".tf")
                shutil.rmtree(tempd)


class FlakeJob:
    client = boto3.client('cloudwatch')

    def __init__(self, config):
        self.ff = config
        self.metric = ""
        ff = config
        # log("Loaded flake: " + config["flakeName"], "info", ff['flakeName'])
        if CheckCron(str(self.ff['flakeCronstring'])).check() is True:
            log("Running flake: " + ff["flakeName"], "info", ff['flakeName'])
            try:
                starttime = time.time()
                creds = json.loads(open('creds.json').read())
                env = os.environ.copy()
                env['PATH'] = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games' + \
                              env["PATH"]
                env.update(creds)
                pop = sub.Popen(ff['flakeCommand'], env=env, stdout=sub.PIPE, stderr=sub.PIPE, shell=True, bufsize=1)
                p = ''
                pe = ''
                try:
                    while True:
                        out = pop.stdout.readline()
                        if out.decode() is not None:
                            log(out.decode(), "info", ff['flakeName'])
                            p += str(out.decode())
                        if pop.poll() is not None:
                            break
                    while True:
                        err = pop.stdout.readline()
                        if err.decode() is not None:
                            log(err.decode(), "error", ff['flakeName'])
                            pe += str(err.decode())
                        if pop.poll() is not None:
                            break
                except Exception as e:
                    log('Error while grabbing output of subprocess. ' + str(e), "error", ff['flakeName'])
                self.metric = p
                log("Returned Value is: " + str(p), "info", ff['flakeName'])
                if pe:
                    log("Returned Error is: " + str(pe), "info", ff['flakeName'])
                endtime = time.time()
                runtime = float(endtime) - float(starttime)
            except sub.CalledProcessError as cp:
                log("Flake " + ff['flakeName'] + " failed", "error", ff['flakeName'])
                log(str(cp), "error", ff['flakeName'])
            except Exception as e:
                log("Flake " + ff['flakeName'] + " failed", "error", ff['flakeName'])
                log(str(e), "error", ff['flakeName'])
            else:
                log("Flake " + ff['flakeName'] + " ran in [" + str(runtime) + "] seconds...",
                    "info",
                    ff['flakeName'])

        else:
            log("Not running flake " + ff["flakeName"] + " because the flakeCronstring is not true", "info", ff['flakeName'])

    def submit(self):
        if CheckCron(str(self.ff['flakeCronstring'])).check() is True:
            try:
                metric_val = float(self.metric)
            except:
                log('Metric is not a number, so not submitting', "info", self.ff['flakeName'])
            else:
                try:
                    re.search('[a-zA-Z]', self.metric)
                except Exception:
                    if not self.metric:
                        self.metric = "Didnt grab any data"
                else:
                    if not re.search('[a-zA-Z]', self.metric):
                        datapoints = []
                        datapoint = {
                            'MetricName': self.ff['flakeName'],
                            'Value': float(self.metric),
                            'Unit': self.ff['flakeUnit']
                        }
                        datapoints.append(datapoint)
                        response = self.client.put_metric_data(Namespace=self.ff['flakeMetricNamespace'], MetricData=datapoints)
                        log("Return from metric put: " + str(response), "info", self.ff['flakeName'])
                    else:
                        log("Metric data came back as a string.  Logging below...", "info", self.ff['flakeName'])
                        log(self.metric, "info", self.ff['flakeName'])

    def build_alarms(self):
        if self.ff['flakeAlarms']:
            if CheckCron(str(self.ff['flakeCronstring'])).check() is True:
                tfdoc = {
                    'provider': {
                        'aws': {
                            'region': self.ff['flakeRegion']
                        }
                    },
                    'resource': {
                        'aws_cloudwatch_metric_alarm': {}
                    }
                }
                for a in self.ff['flakeAlarms']:
                    alarm = {
                        'alarm_name': 'FL-' + self.ff['flakeName'] + '-' + a['alarmName'],
                        "comparison_operator": a['alarmOperator'],
                        "evaluation_periods": a['alarmPeriods'],
                        "metric_name": self.ff['flakeName'],
                        "namespace": self.ff['flakeMetricNamespace'],
                        "period": a['alarmPeriodLength'],
                        "statistic": a['alarmStatistic'],
                        "threshold": a['alarmThreshold'],
                        "alarm_description": a['alarmDescription']
                    }
                    if 'alarm' in a['alarmEndpoints']:
                        alarm["alarm_actions"] = [
                            a['alarmEndpoints']['alarm']
                        ]
                    if 'ok' in a['alarmEndpoints']:
                        alarm["ok_actions"] = [
                            a['alarmEndpoints']['ok']
                        ]
                    if 'insufficient_data' in a['alarmEndpoints']:
                        alarm['insufficient_data_actions'] = [
                            a['alarmEndpoints']['insufficient_data']
                        ]
                    tfdoc['resource']['aws_cloudwatch_metric_alarm']['FL-' + self.ff['flakeName'] +
                                                                     '-' +
                                                                     a['alarmName']] = alarm

                tempd = tempfile.mkdtemp()
                if not os.path.exists(tempd):
                    os.mkdir(tempd)
                tfjson = open(tempd + '/' + 'infra.tf.json', 'w')
                tfjson.write(json.dumps(tfdoc))
                tfjson.seek(0)
                tfjson.close()
                cwd = os.getcwd()
                try:
                    tfresponse = sub.check_output(
                        'cd ' + tempd + ' && /usr/local/bin/terraform apply -refresh=False -no-color -state=' + cwd + "/states/" +
                        self.ff['flakeName'] + ".tfstate", shell=True)
                except Exception as e:
                    log("Attempted to run terraform but got: " + str(e), "error", self.ff['flakeName'] + ".tf")
                else:
                    log(str(tfresponse.decode()), "info", self.ff['flakeName'] + ".tf")
                shutil.rmtree(tempd)

