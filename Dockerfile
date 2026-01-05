FROM ubuntu:20.04

RUN \
    apt-get update && \
    apt-get upgrade -y &&\
    DEBIAN_FRONTEND=noninteractive TZ=Europe/Paris apt-get -y install tzdata && \
    apt-get install -y \
        timidity \
    	python3-pip \
    	python3-pil \
    	git \
    	curl \
    	ffmpeg \
    	vim

ARG BASE_PATH
ARG SCORE_PATH

# Check for mandatory build arguments
RUN \
    : "${BASE_PATH:?mandatory build argument is missing}"
RUN \
    : "${SCORE_PATH:?mandatory build argument is missing}"

RUN mkdir -p ${BASE_PATH}/ly2video

WORKDIR ${BASE_PATH}

RUN curl -o lilypond-2.24.3-linux-x86_64.tar.gz https://gitlab.com/api/v4/projects/lilypond%2Flilypond/packages/generic/lilypond/2.24.3/lilypond-2.24.3-linux-x86_64.tar.gz

RUN tar -xzf lilypond-2.24.3-linux-x86_64.tar.gz && cp -r lilypond-2.24.3/* /usr/

WORKDIR ${BASE_PATH}/ly2video

COPY . .

RUN pwd
RUN ls
RUN pip3 install -r requirements.txt
RUN pip3 install .

WORKDIR ${SCORE_PATH}

CMD ["/bin/bash"]
