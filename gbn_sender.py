import logging
import os
import socket
import sys
from collections import deque
from threading import *
from time import sleep

import coloredlogs
import verboselogs

import packet
from timer import Timer

# Configure logging
verboselogs.install()
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", fmt="%(asctime)s - %(message)s", datefmt="%H:%M:%S")

sock = None

# A double ended queue is better for pbuffer
pbuffer = deque([], maxlen=packet.GBN_WINDOW_SIZE)

# S_base is the start of region where packets are sent but not ACK'ed yet
# S_next is the start of region which can be sent
# Both S_base and S_next lie inside the window

S_base, S_next = 0, 0
message, msglen = "", 0

# Check if received ACK is the ack expected
def is_valid_ackno(ack_no):

    # Obvious check
    if len(pbuffer) <= 0:
        return False

    t = (S_base + 1) % (packet.MAX_SEQ_NO + 1)
    while t != S_next:
        if t == ack_no:
            return True
        t = (t + 1) % (packet.MAX_SEQ_NO + 1)
    return ack_no == S_next


def sender():

    global pbuffer
    pbuffer = deque([], maxlen=packet.GBN_WINDOW_SIZE)

    # For use in is_valid_ackno()
    global S_next, S_base

    # Create instance of Timer class
    timer = Timer()

    # Index of letter to packet and send
    next_msg_index = 0

    while True:

        # We need to check 2 connditions:
        # 1) We check if current buffer length is less than our specified window size.
        # 2) we check if the message index doesn't exceed message length

        while len(pbuffer) < packet.GBN_WINDOW_SIZE and next_msg_index < msglen:

            # There is space in window so create packet
            pack = packet.Packet(S_next, data=message[next_msg_index])
            packet.send_packet(client, pack)
            logger.info("[SEND]: Sending %s." % pack)
            pbuffer.append(pack)

            # Increment S_next as current packet is sent successfully
            S_next = (S_next + 1) % (packet.MAX_SEQ_NO + 1)

            # Start timer
            if not timer.is_running():
                timer.start(packet.ACK_WAIT_TIME)
            next_msg_index += 1

            sleep(0.2)

        # Receiving response
        resp = packet.recv_packet_nblock(client)

        # Check if received response from receiver is not corrupt (Random simulation)
        if resp is not None and not resp.is_corrupt():

            # Check if ACK is valid or not
            if not is_valid_ackno(resp.seq_no):
                logger.error("[EACK]: Invalid ACK %s." % resp)

            else:
                # Remove packets from buffer
                tmp = []
                while len(pbuffer) > 0 and pbuffer[0].seq_no != resp.seq_no:

                    # For logging
                    tmp.append(str(pbuffer.popleft().seq_no))

                    # Increment S_base as current packet is sent successfully
                    S_base = (S_base + 1) % (packet.MAX_SEQ_NO + 1)
                logger.debug(
                    ("[ACK]: Ack received %s. Packets (%s) " + "are acknowledged.")
                    % (resp, ",".join(tmp))
                )

        sleep(0.2)

        # Resend all outstanding packets if timeout occurs:
        if timer.has_timeout_occured():
            for p in pbuffer:
                logger.error("[TIMEOUT]: Resending %s." % p)
                packet.send_packet(client, p)
            timer.start(packet.ACK_WAIT_TIME)

        # Check if buffer is empty and next_msg_index exceeds message length (terminating condition)
        if len(pbuffer) == 0 and next_msg_index >= msglen:

            # EOF
            pack = packet.Packet(-1, data=None)
            packet.send_packet(client, pack)

            logger.success("[SEND]: Transfer complete. Sending EOF")
            break
        # else
        sleep(0.2)


if __name__ == "__main__":

    # Create socket instance
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((socket.gethostname(), 3300 if len(sys.argv) <= 1 else int(sys.argv[1])))
    sock.listen(5)

    client, addr = sock.accept()
    logger.debug("Connected.")

    # Set vars if given (Default set in packet module)
    if len(sys.argv) >= 3:
        packet.SEQ_NO_BIT_WIDTH = int(sys.argv[2])
        packet.LOSS_PROB = float(sys.argv[3])
        packet.GBN_WINDOW_SIZE = (2 ** packet.SEQ_NO_BIT_WIDTH) - 1
        packet.MAX_SEQ_NO = packet.GBN_WINDOW_SIZE
        packet.ACK_WAIT_TIME = int(sys.argv[4])
        message = sys.argv[5]
        msglen = len(message)

    logger.verbose(
        "SEQ_NO_BIT_WIDTH: {0}, LOSS_PROB: {1}, GBN_WINDOW_SIZE: {2}, MAX_SEQ_NO: {3},"
        " ACK_WAIT_TIME: {4}, MESSAGE: {5}".format(
            packet.SEQ_NO_BIT_WIDTH,
            packet.LOSS_PROB,
            packet.GBN_WINDOW_SIZE,
            packet.MAX_SEQ_NO,
            packet.ACK_WAIT_TIME,
            message,
        )
    )

    sender()
    sock.close()
    client.close()
