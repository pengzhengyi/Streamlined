# syntax=docker/dockerfile:1

#! **dev** stage is suitable for code development without building the package
FROM continuumio/anaconda3 AS dev

# setup PATH
ENV PATH=/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH}

# http://bugs.python.org/issue19846
# > At the moment, setting "LANG=C" on a Linux system *fundamentally breaks Python 3*, and that's not OK.
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ARG DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install common dependencies
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
	apt-utils \
	git \
	openssh-client \
	gnupg2 \
	iproute2 \
	procps \
	lsof \
	htop \
	net-tools \
	psmisc \
	curl \
	wget \
	rsync \
	ca-certificates \
	unzip \
	zip \
	gzip \
	nano \
	vim \
	less \
	jq \
	lsb-release \
	apt-transport-https \
	dialog \
	libc6 \
	libgcc1 \
	libkrb5-3 \
	libgssapi-krb5-2 \
	libicu[0-9][0-9] \
	liblttng-ust0 \
	libstdc++6 \
	zlib1g \
	locales \
	sudo \
	ncdu \
	graphviz \
	man-db \
	strace \
	build-essential \
	libssl-dev \
	zlib1g-dev \
	libsqlite3-dev \
	libbluetooth-dev \
	libffi-dev \
	tk-dev \
	uuid-dev \
	manpages \
	manpages-dev && \
	apt-get clean && \
	rm -rf /var/lib/apt/lists/*

# Copy files and Define working directory.
COPY . .

RUN	. ~/.bashrc && \
	pip install --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt && \
	pip install -e . && \
	pre-commit && \
	pre-commit autoupdate; exit 0

# Define default command.
CMD ["bash"]