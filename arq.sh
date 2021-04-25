#!/bin/bash
# author: vigneshdesmond
# date: 25/03/2021
 
REV='\e[1;32m' 
NORM='\e[0;37m'
NORR='\e[0;36m'	      
NORY='\e[0;33m'

#Help function
function HELP {
  echo -e "${NORM}Basic usage:${OFF} ${REV}$SCRIPT ./arq.sh  -a <ARQ_TYPE> -p <PORT>-s <SEQ_NO_BIT_WIDTH> -l <PACKET_LOSS_PROB> -t <TIMEOUT> -m <MESSAGE>${OFF}"\\n
  echo -e "${NORM}Flags:${OFF}"
  echo -e "${REV}-p ${NORM}  Sets Port for server and client. Default is ${NORR}3300${OFF}"
  echo -e "${REV}-a ${NORM}  Type of ARQ protocol. ${NORY}Required field\n	${NORR}sw${NORM} for Stop and Wait\n	${NORR}sr${NORM} for Selective Repeat\n	${NORR}gb${NORM} for Go Back N\n 	${NORR}ca${NORM} for CSMA/CA Simulation\n"
  echo -e "${REV}-s ${NORM}  Sets bit width m of sequence number.\n     This is used to calulate window size. Default is ${NORR}3${OFF}"
  echo -e "${REV}-l ${NORM}  Sets probability of packet corruption. Default is ${NORR}0.3${OFF}"
  echo -e "${REV}-t ${NORM}  Sets value for ACK timeout (in ms). Default is ${NORR}8000${OFF}"
  echo -e "${REV}-c ${NORM}  Sets probability of channel being in busy state. Default is ${NORR}0.3${OFF}"
  echo -e "${REV}-i ${NORM}  Sets IFS time. Default is ${NORR}2000${OFF}"
  echo -e "${REV}-k ${NORM}  Sets max value of K. Default is ${NORR}5${OFF}"
  echo -e "${REV}-m ${NORM}  Message to be transmitted. ${NORY}Required field"
  echo -e "${REV}-h ${NORM}  Displays this help message."\\n
  
  echo -e "${NORM}Example: ${REV}$SCRIPT ./arq.sh  -a gb -p 3310 -s 4 -l 0.3 -t 10000 ${OFF}"\\n
  exit 1
}

TYPE=""
MESSAGE=""
PORT=3300
SEQ_NO_BIT_WIDTH=3
PACKET_LOSS_PROB=0.3
TIMEOUT=8000
CHANNEL_BUSY_PROB=0.3
IFS_TIME=2000
MAX_K=5

while getopts a:p:s:l:t:c:i:k:m:h FLAG; do
  case $FLAG in
    a)
      TYPE=$OPTARG
      ;;
    p)
      PORT=$OPTARG
      ;;
    s)
      SEQ_NO_BIT_WIDTH=$OPTARG
      ;;
    l)
      PACKET_LOSS_PROB=$OPTARG
      ;;
    t)
      TIMEOUT=$OPTARG
      ;;
    c)
      CHANNEL_BUSY_PROB=$OPTARG
      ;;
    i)
      IFS_TIME=$OPTARG
      ;;
    k)
      MAX_K=$OPTARG
      ;;
	m)
      MESSAGE=$OPTARG
      ;;
    h)
      HELP
      ;;
    \?) #unrecognized option - show help
      HELP
      ;;
  esac
done

if [ "$MESSAGE" = "" ]; then
	echo "No message given"
	HELP
	exit 0
fi

if [ "$TYPE" != "" ]; then
		if [ "$TYPE" = "sr" ]; then
    		printf "Initiating...\nPort: $PORT \nSequence bit width: $SEQ_NO_BIT_WIDTH \nPacket Loss Probability: $PACKET_LOSS_PROB \nTimeout: $TIMEOUT \nType: Selective repeat"
   		gnome-terminal --window --geometry 80x24+150+300 -- bash -c "python3 sr_sender.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB $TIMEOUT $MESSAGE && read" && gnome-terminal --window --geometry 80x24+1000+300 -- bash -c "python3 sr_receiver.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB && read"
    	elif [ "$TYPE" = "gb" ]; then
    		printf "\nInitiating...\nPort: $PORT \nSequence bit width: $SEQ_NO_BIT_WIDTH \nPacket Loss Probability: $PACKET_LOSS_PROB \nTimeout: $TIMEOUT \nType: Go Back N"
   		gnome-terminal --window --geometry 80x24+150+300 -- bash -c "python3 gbn_sender.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB $TIMEOUT $MESSAGE && read" && gnome-terminal --window --geometry 80x24+1000+300 -- bash -c "python3 gbn_receiver.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB && read"
    	elif [ "$TYPE" = "sw" ]; then
    		printf "\nInitiating...\nPort: $PORT \nSequence bit width: $SEQ_NO_BIT_WIDTH \nPacket Loss Probability: $PACKET_LOSS_PROB \nTimeout: $TIMEOUT \nType: Stop and Wait"
 		gnome-terminal --window --geometry 80x24+150+300 -- bash -c "python3 sw_sender.py $PORT $PACKET_LOSS_PROB $TIMEOUT $MESSAGE && read" && gnome-terminal --window --geometry 80x24+1000+300 -- bash -c "python3 sw_receiver.py $PORT $PACKET_LOSS_PROB && read"
 		elif [ "$TYPE" = "ca" ]; then
    		printf "\nInitiating...\nPort: $PORT \nSequence bit width: $SEQ_NO_BIT_WIDTH \nPacket Loss Probability: $PACKET_LOSS_PROB \nTimeout: $TIMEOUT \nChannel busy probability: $CHANNEL_BUSY_PROB \nIFS Time: $IFS_TIME \nMax K: $MAX_K \nType: CSMA/CA Simulation"
 		gnome-terminal --window --geometry 80x24+150+300 -- bash -c "python3 csma-ca/sender_station.py $PORT $PACKET_LOSS_PROB $TIMEOUT $CHANNEL_BUSY_PROB $IFS_TIME $MAX_K $MESSAGE && read" && gnome-terminal --window --geometry 80x24+1000+300 -- bash -c "python3 csma-ca/base_station.py $PORT $PACKET_LOSS_PROB && read"
    	else
    		echo "Unknown type: $TYPE"
    		HELP
    	fi
else
    echo "No type specified."
    HELP
fi

