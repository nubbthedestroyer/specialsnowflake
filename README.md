## SpecialSnowflake
###### A cloudwatch ingester for custom metrics
###### "Hey baby, do you need monitoring?  Because I could hit your endpoint all day long!"


#### Intro 

> This script grabs metrics with a bash command that you specify and uploads it with the parameters you specify into Cloudwatch.  Also creates and manages alarms defined in each flake file.  Requires AWS credentials or IAM Role to run.


#### Requirements

> * AWS Credentials with Cloudwatch R/W access
>   * also configured under the linux account that will be running the script OR at the AWS Instance Role level.
> * See the Dockerfile for a list of required packages, add any you need for the flakes.
> * Terraform installed on the machine that is running the script (install into "/usr/local/bin/")
>   * Dockerfile and standard docker environment installs this by default.
> * There is a docker file and related scripts included in this repo that you can use to test a flake.  Run this command to start a test.
>   * ```./test-a-flake.sh <your-flake-name>```
>     * This will pull in credentials from infra/scipts/credentials (requires awscli and appropriate permissions), build the docker, and run any flake(s) that match(es) the string you pass to the shell script.  

#### Operation

> The script loops through each file in the flakes directory, sourcing the variables within.  Then runs the flakeCommand string and puts the output of the command into Cloudwatch using the configuration you specify in the flake file.  It will also log errors into individual log files for each flake based on the flakeName which can then be ingested by any log retention system like logstash.


#### Tips

> * Ensure that the command run in the flakeCommand variable returns naked data and does not include quotes or warnings.  Should only be a single integer or float.
>   * That being said, you can use the shell file that the flakeCommand points to for advanced calculations and ratios between multiple query return values, including external scripts like php.
> * You cannot make notes in the json files, but you can add fields (like '_comment1', '_comment2', etc) and use those to store comments or important info.
>   * You definitely can add comments to the resource scripts.
> * Use mysql accounts that are locked down and very specific to the use case.  Where possible, do not store creds in the script, rather create mysql users that allow with no password from IP address.
> * Snowflake runs as a docker container in production, so its possible to test a newly written flake before deploying it into a production environment.  Here's how to do it.
>   * Get docker running on your system (boot2docker, Kitematic, docker-machine, etc)
>   * Write your flake file and associated external scripts and place them in appropriate folders relevant to the task.
>   * run this command
>   * ```./test-a-flake.sh <name-of-flake>```
>     * If you exclude your flake name it will just run an example flake.  Run multiple flakes by including matching text.  So to run all flakes that begin with "zq-" put "zq-" for name of flake.
>   * This will build the container, install dependencies, and put everything where it needs to be.  Fortunately, it does this with the exact same architecture and environment as it would in production, so you get a pretty good test for your flake as it would run in prod.
>     * Might take a while the first time as the docker container has to build.
>     * This will post real data and real alarms to AWS.  Be prepared for alerts if your threshold is breached and you've defined Cloudwatch Alarms.
>   * If you get an HTTP 200 from Cloudwatch then your flake should be good.

#### Default config

> See the below default config file at flakes/example-perminute.flake.json for an example of a full configuration.
> 
    {
      "flakeName": "example-perminute",
      "flakeCronstring": "* * * * *",
      "flakeCommand": "./res/test3/test3.sh",
      "flakeType": "metric",
      "flakeUnit": "Count",
      "flakeMetricNamespace": "test3/KPIs",
      "flakeRegion": "us-east-1",
      "flakeAlarms": [
        {
          "alarmName": "TestHighThreshold",
          "alarmDescription": "Alarm if the metric is too high",
          "alarmThreshold": "3",
          "alarmOperator": "GreaterThanThreshold",
          "alarmPeriodLength": "60",
          "alarmPeriods": "1",
          "alarmStatistic": "Average",
          "alarmEndpoints": {
            "ok": "arn:aws:sns:us-east-1:123456789012:PagerDuty-IT-Only",
            "alarm": "arn:aws:sns:us-east-1:123456789012:PagerDuty-IT-Only"
          }
        },
        {
          "alarmName": "TestLowThreshold",
          "alarmDescription": "Alarm if the metric is too low",
          "alarmThreshold": "3",
          "alarmOperator": "LessThanThreshold",
          "alarmPeriodLength": "60",
          "alarmPeriods": "1",
          "alarmStatistic": "Average",
          "alarmEndpoints": {
            "ok": "arn:aws:sns:us-east-1:123456789012:PagerDuty-IT-Only",
            "alarm": "arn:aws:sns:us-east-1:123456789012:PagerDuty-IT-Only"
          }
        }
      ]
    }

> See the below example of a resource file for the script to collect the metric.
> It is very important that this script return only a number and no errors or other characters or formatting.

    #!/usr/bin/env bash
    mysql -Ns -h mysqlhost.example.com -u${user1} -p${pass1} -e "SHOW STATUS;" 2>&1 | grep -v 'Warning' | grep Uptime | sed 's/[^0-9]*//g'  | head -n 1

#### Flake file reference

> * flakeName
>   * Name of the flake, must be unique.
> * flakeConstring
>   * Linux crontab style time string that signifies the frequency with which this flake should run.
> * flakeCommand
>   * Shell command you want to run for this flake.  Recommend that this be a separate executable stored under the "res/" directory to avoid having to escape and stringify special characters due to JSON syntax constraints.
> * flakeType
>   * Can be "metric" or "job".  The idea with this is that a job won't trigger a failure flag on non-numerical output, it will just log it.  Job types will also not send data to Cloudwatch.  Metric type is expecting a number and will fail if output is non-numerical.
> * flakeUnit
>   * See Cloudwatch documentation for the different types of Units.  Count is usually fine.
>   * http://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#Unit
> * flakeMetricNamespace
>   * Another Cloudwatch specific field.  Allows you to create custom categories for gathers metrics.
>   * http://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#Namespace
> * flakeRegion
>   * AWS region for Cloudwatch reporting.
> * flakeAlarms
>   * List of alarms to create and maintain for this metric.  Each time this flake is run it determines the configuration of the alarm in AWS and corrects it to this standard if differences are found.  Uses Terraform on the backend to manage alarms, so whatever AWS creds or IAM role you use for SpecialSnowflake must have Cloudwatch write access.
>     * alarmName
>       * Name of the alarm.  Alarms are created like this in Cloudwatch:
>         * "FL-${flakeName}-${alarmName}"
>     * alarmDescription
>       * Description for the alarm.  This should be fairly descriptive, as it will be sent with the SNS alarms to whatever endpoints you want.
>     * alarmThreshold
>       * Point at which the alarm is set to trigger.  Refer to CloudWatch documentation.
>       * http://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ConsoleAlarms.html
>     * alarmOperator
>       * Standard operator for the threshold.  Refer to CloudWatch documentation.
>       * http://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricAlarm.html
>     * alarmPeriodLength
>       * Length of time to count metrics againts the threshold.  For example, if your alarmStatistic is Sum and: 
>         * If your flake is returning "2" every minute, and your period is 60, your alarm will see "2".
>         * If your flake is returning "2" every minute, and your period is 300, your alarm will see "10" because it counts 10 in 5 minutes.
>       * This is different if your alarmStatistic is "Average" as it will just take the average of all the datapoints in the period.
>       * See Documentation for more info: http://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#CloudWatchPeriods
>     * alarmStatistic
>       * Basically how you want to aggregate multiple datapoints.  "Sum" or "Average" are best in most cases, but you can refer to the documentation for further info:
>         * http://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/cloudwatch_concepts.html#Statistic
>     * alarmEndpoints
>       * SNS arns that you want alarms to send data to when they are triggered.
>       * Must be a valid SNS topic, but beyond that the topic can post anywhere, making integrations with any application that supports incoming RESTful webhooks fairly straight forward.
>       * http://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/US_SetupSNS.html

#### Future Improvements

> * I would like to eventually get all the flakes to reference Dockerfiles to run instead of native scripts.  As flakes are added each more and more packages and dependencies will be added to the environment, which I think will cause problems at scale.  This can be achieved via Docker D-in-D, but we would need to translate this to an ECS cluster I think for load balancing.
> * There is a small memory leak somewhere in the storm.py threading loop that I can't pinpoint.  Might be the way I'm threading.  I expect python to know to garbage collect after each cycle finishes, but maybe it's not.