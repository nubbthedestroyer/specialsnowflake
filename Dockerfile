FROM ubuntu:16.04

WORKDIR /etc/scripts/specialsnowflake
RUN mkdir -p /var/log/snowflake

RUN apt-get update --fix-missing

# Because aptitude is better, don't judge me
RUN apt-get -y install --fix-missing aptitude apt-utils

# To suppress annoying debconf errors.
ENV DEBIAN_FRONTEND=noninteractive

#######################################################
# Be sure to add any packages the flakes need in here.
ENV apt_list="wget \
    curl \
    git \
    unzip \
    python-pip \
    python3-pip \
    libssl-dev \
    libffi-dev \
    jq \
    openssh-client"
RUN bash -c 'for p in ${apt_list[@]}; do aptitude -y install $p; done'
#######################################################

#######################################################
# Install Terraform
RUN wget -q https://releases.hashicorp.com/terraform/0.7.4/terraform_0.7.4_linux_amd64.zip
RUN unzip -o terraform_0.7.4_linux_amd64.zip -d /usr/local/bin/
RUN rm terraform_0.7.4_linux_amd64.zip
RUN mkdir -p /etc/scripts
#######################################################

#######################################################
# Pip install block
#ENV package_list="awscli \
#    boto3 \
#    boto \
#    botocore \
#    requests \
#    HTMLParser \
#    cffi \
#    cryptography \
#    docutils \
#    enum34 \
#    futures \
#    idna \
#    ipaddress \
#    jmespath \
#    pyasn1 \
#    pycparser \
#    python-dateutil \
#    simplejson \
#    six \
#    sh"
ENV package_list="awscli \
    boto3 \
    botocore \
    requests \
    HTMLParser \
    cffi \
    cryptography \
    docutils \
    enum34 \
    futures \
    idna \
    ipaddress \
    jmespath \
    paramiko \
    pyasn1 \
    pycparser \
    pysftp \
    python-dateutil \
    simplejson \
    six \
    sh"
RUN pip2 install --upgrade pip
RUN bash -c 'for p in ${package_list[@]}; do pip2 install --upgrade $p; done'
RUN pip3 install --upgrade pip
RUN bash -c 'for p in ${package_list[@]}; do pip3 install --upgrade $p; done'
#######################################################

#######################################################
# Prevent caching from this point on
ARG CACHE_DATE='not_a_date'
#######################################################

#######################################################
# ADD codebase
ADD . .
#######################################################

#######################################################
# Install credentials
ADD infra/scripts/credentials ./
RUN mkdir -p ${HOME}/.aws
RUN rm -rf ${HOME}/.aws/config
RUN cp infra/scripts/credentials ${HOME}/.aws/config
RUN cp ${HOME}/.aws/config ${HOME}/.aws/credentials
#######################################################

#######################################################
# Ensure that the resource files can execute
RUN chmod -R +x res/
#######################################################

#######################################################
# Start
ENTRYPOINT ["python3", "-u", "storm.py"]
#######################################################