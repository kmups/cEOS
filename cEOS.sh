#!/bin/bash
# import and configure Arista EOS container

function Help (){
    printf "import and configure arista eos container image\n"
    printf "\n"
    printf "syntax: bash cEOS.sh [-h] IMAGE IMAGE_TAG\n"
    printf "\n"
    printf "options:\n"
    printf "%s    print this help\n" "%h"
}

function Error (){
    printf "Error!\n"
    Help
    exit 1
}

function Validate (){
    if [ $? -ne 0 ]; then
    Error
    fi
}

while getopts h: option
do
    case $option in
    h) Help
       exit
    esac
done

if [ $# -lt 2 ]; then
    Error
fi

CEOS_PATH=$1
CEOSBASE_TAG=$2
CEOSBASE=ceosbase_$(date +%d_%m_%y_%H_%M_%S)

docker image import $CEOS_PATH $CEOSBASE:$CEOSBASE_TAG
Validate

docker image build --tag ceos:$CEOSBASE_TAG --build-arg CEOSBASE=${CEOSBASE} --build-arg CEOSBASE_TAG=${CEOSBASE_TAG} .
Validate

docker image rm --force $CEOSBASE:${CEOSBASE_TAG}
Validate
