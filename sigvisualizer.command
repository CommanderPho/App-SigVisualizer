#!/usr/bin/env bash
PROGNAME=SIGVISUALIZER	#PROGRAM NAME MUST BE SET
PROGDATE=$(date +"%m-%d-%Y")
PROGTIME=$(date +"%r")
UNIQUE_ID=$PROGTIME_$PROGDATE_$PROGNAME
#Formatting Directives
TIER1=">>>>---->    "
TIER2=">>>>-------->>    "
TIER3=">>>>------------>>>    "
#	Description: 
##		Launches the Sigvisualizer.py python script
#
#
#

#	Static Parameters Definitions:
##		Parameters that are set directly by editing this file, and are never modified within the script.
DEBUG_MODE=false


#	Function Definitions:
##		Functions called by Main.
function launchScript {
	python sigvisualizer.py
}

function configureEnv {
	echo "$TIER2 Configuring active conda environment for running script:"
	echo "$TIER3 Changing active conda environment to : base"
	conda activate base
}

#	Main:
##		Body of code for execution.
echo
echo "Launching SigVisualizer:"
#configureEnv
launchScript
echo "Script Complete."
echo

#	End of Program
exit