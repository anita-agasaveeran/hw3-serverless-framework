#!/bin/bash
url=$1
TOKEN=$2
AUTH_HEADER="Authorization:$TOKEN"
interval_in_seconds=2
result="IN-PROCESS"
printf "\nPolling '$url' every $interval_in_seconds seconds, until '$result'\n"
while true; 
do 
	x=$(curl $url -s -H "$AUTH_HEADER"); 
	
	resp=$(echo $x | python3 -c "import json; import sys; resp=json.load(sys.stdin);sys.stdout.write(resp['status']);");
	
	if [[ "$result" == "$resp" ]]; then 
		printf "\n Order status matches desired result of ${resp}. Polling is complete!\n";
		break;

	fi;
	printf "\nStill waiting for $result status\n";	

	sleep $interval_in_seconds; 
done

