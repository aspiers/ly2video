# Set filepath to your scores that you want to convert with ly2video
LILY_FILES := /path/to/your/scores

BASE_PATH := /opt/lily
SCORE_PATH := ${BASE_PATH}/scores

build:
	SCORE_PATH=${SCORE_PATH} BASE_PATH=${BASE_PATH} docker-compose -p ly2video-build -f docker-compose.yml up --build

run:
	docker run -it -v ${LILY_FILES}:/opt/lily/scores ly2video

.PHONY:
	build
	run
