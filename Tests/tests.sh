#!/bin/bash
# set PROJECT HOME
HOME="/Users/jtooley2/dev/alexaWine"
Echo "Running tests local with JSON files"
lambda-local -l $HOME/index.js -h handler -e $HOME/tests/WineSearchIntent.json
echo "completed test, pause 5 sec"
sleep 5
lambda-local -l $HOME/index.js -h handler -e $HOME/tests/getWineDetailsIntent.json
echo "completed test, pause 5 sec"
sleep 5
lambda-local -l $HOME/index.js -h handler -e $HOME/tests/getPriceIntent.json
echo "completed test, pause 5 sec"
echo "DONE with tests"