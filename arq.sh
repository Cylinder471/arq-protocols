#!/bin/zsh
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
  echo -e "${REV}-a ${NORM}  Type of ARQ protocol. ${NORY}Required field\n	${NORR}sw${NORM} for Stop and Wait\n	${NORR}sr${NORM} for Selective Repeat\n	${NORR}gb${NORM} for Go Back N"
  echo -e "${REV}-s ${NORM}  Sets bit width m of sequence number.\n     This is used to calulate window size. Default is ${NORR}3${OFF}"
  echo -e "${REV}-l ${NORM}  Sets probability pf packet corruption. Default is ${NORR}0.1${OFF}"
  echo -e "${REV}-t ${NORM}  Sets value for ACK timeout (in ms). Default is ${NORR}8000${OFF}"
  echo -e "${REV}-m ${NORM}  Message to be transmitted. ${NORY}Required field"
  echo -e "${REV}-h${NORM}  Displays this help message."\\n
  
  echo -e "${NORM}Example: ${REV}$SCRIPT ./arq.sh  -a gb -p 3310 -s 4 -l 0.3 -t 10000 ${OFF}"\\n
  exit 1
}

TYPE=""
MESSAGE=""
PORT=3300
SEQ_NO_BIT_WIDTH=3
PACKET_LOSS_PROB=0.1
TIMEOUT=8000

while getopts a:p:s:l:t:m:h FLAG; do
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
    		echo "\nInitiating...\nPort: $PORT \nSequence bit width: $SEQ_NO_BIT_WIDTH \nPacket Loss Probability: $PACKET_LOSS_PROB \nTimeout: $TIMEOUT\nType: Selective repeat"
   		gnome-terminal --window --geometry 80x24+150+300 -- zsh -c "python sr_sender.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB $TIMEOUT $MESSAGE && read" && gnome-terminal --window --geometry 80x24+1000+300 -- zsh -c "python sr_receiver.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB && read"
    	elif [ "$TYPE" = "gb" ]; then
    		echo "\nInitiating...\nPort: $PORT \nSequence bit width: $SEQ_NO_BIT_WIDTH \nPacket Loss Probability: $PACKET_LOSS_PROB \nTimeout: $TIMEOUT\nType: Go Back N"
   		gnome-terminal --window --geometry 80x24+150+300 -- zsh -c "python gbn_sender.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB $TIMEOUT $MESSAGE && read" && gnome-terminal --window --geometry 80x24+1000+300 -- zsh -c "python gbn_receiver.py $PORT $SEQ_NO_BIT_WIDTH $PACKET_LOSS_PROB && read"
    	elif [ "$TYPE" = "sw" ]; then
    		echo "\nInitiating...\nPort: $PORT \nSequence bit width: $SEQ_NO_BIT_WIDTH \nPacket Loss Probability: $PACKET_LOSS_PROB \nTimeout: $TIMEOUT\nType: Stop and Wait"
 		gnome-terminal --window --geometry 80x24+150+300 -- zsh -c "python sw_sender.py $PORT $PACKET_LOSS_PROB $TIMEOUT $MESSAGE && read" && gnome-terminal --window --geometry 80x24+1000+300 -- zsh -c "python sw_receiver.py $PORT $PACKET_LOSS_PROB && read"
    	else
    		echo "Unknown type: $TYPE"
    		HELP
    	fi
else
    echo "No type specified."
    HELP
fi

