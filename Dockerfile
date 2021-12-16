FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    timidity \
    python3-pip \
    python3-pil \
    swig \
    libasound-dev \
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

RUN curl -o lilypond.sh https://lilypond.org/download/binaries/linux-64/lilypond-2.22.1-1.linux-64.sh

RUN ls -l

RUN chmod +x lilypond.sh

RUN sh lilypond.sh --batch

WORKDIR ${BASE_PATH}/ly2video

COPY . .


RUN pwd
RUN ls

RUN pip3 install -r requirements.txt
RUN pip3 install .

WORKDIR ${SCORE_PATH}

CMD ["/bin/bash"]
