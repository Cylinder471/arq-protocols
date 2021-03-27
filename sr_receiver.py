#!/usr/bin/python
import socket
import sys
import os
import logging
from time import sleep

import packet
import verboselogs
import coloredlogs

# Configure logging
verboselogs.install()
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", fmt="%(asctime)s - %(message)s", datefmt="%H:%M:%S")


sock = None

# R_next is the sequence number of expected frame in receiver window
R_next = 0

# Same pbuffer format as in sr_sender
pbuffer = [None] * packet.SRP_WINDOW_SIZE

# To track ACK and NACk
nack_sent, ack_needed = False, False

# To store received message
data_recvd = []


def send_nack():
    pkt = packet.Packet(seq_no=R_next, data=b"", ptype=packet.Packet.TYPE_NACK)
    packet.send_packet(sock, pkt)
    logger.warning("[NACK]:  %s" % pkt)


def send_ack():
    pkt = packet.Packet(seq_no=R_next, ptype=packet.Packet.TYPE_ACK)
    packet.send_packet(sock, pkt)
    logger.info("[ACK]:  %s" % pkt)


# Checks if the received ACK is expected
def is_valid_seqno(seqno):
    return seqno in [
        (R_next + i) % (packet.MAX_SEQ_NO + 1) for i in range(packet.SRP_WINDOW_SIZE)
    ]


def receiver():
    global nack_sent, ack_needed, R_next
    while True:
        pkt = packet.recv_packet(sock)
        # print('--received %s', pkt)

        # EOF
        if pkt.seq_no == -1:
            logger.debug("[RECV]: Received EOF")
            break

        # If packet is corrupt, NACK will be sent (if not already sent)
        if pkt.is_corrupt():
            if not nack_sent:
                logger.error("[ERR]: %s is corrupt. Sending NACK" % pkt)
                send_nack()
                nack_sent = True
            continue

        # If expected packet doesn't arrive, NACK will be sent (if not already sent)
        if pkt.seq_no != R_next and not nack_sent:
            logger.error("[ERR]: %s not expected. Sending NACK" % pkt)
            send_nack()
            nack_sent = True

        # Packet Acknowledgement
        if is_valid_seqno(pkt.seq_no):

            # Checking if receiving window already hasn't received the frame
            if pbuffer[pkt.seq_no % packet.SRP_WINDOW_SIZE] is None:
                pbuffer[pkt.seq_no % packet.SRP_WINDOW_SIZE] = pkt
                logger.debug("[RECV]: Received %s" % pkt)

                # If R_next in pbuffer is not None, then packet is received, so it can be added to data_recvd
                while pbuffer[R_next % packet.SRP_WINDOW_SIZE]:
                    data_recvd.append(pbuffer[R_next % packet.SRP_WINDOW_SIZE].data)

                    # Clear buffer
                    pbuffer[R_next % packet.SRP_WINDOW_SIZE] = None
                    R_next = (R_next + 1) % (packet.MAX_SEQ_NO + 1)
                    ack_needed = True

                # Send ACK
                if ack_needed:
                    send_ack()
                    ack_needed = False
                    nack_sent = False

        elif nack_sent:
            send_ack()
        sleep(0.3)


if __name__ == "__main__":
    # Socket for listening for incoming connections
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("", 3300 if len(sys.argv) <= 1 else int(sys.argv[1])))
    logger.debug("Connected to server.")

    # Set vars if given (Default set in packet module)
    if len(sys.argv) >= 3:
        packet.SEQ_NO_BIT_WIDTH = int(sys.argv[2])
        packet.LOSS_PROB = float(sys.argv[3])
        packet.SRP_WINDOW_SIZE = 2 ** (packet.SEQ_NO_BIT_WIDTH - 1)
        packet.MAX_SEQ_NO = (2 ** packet.SEQ_NO_BIT_WIDTH) - 1

    logger.verbose(
        "SEQ_NO_BIT_WIDTH: {0}, LOSS_PROB: {1}, SRP_WINDOW_SIZE: {2}, MAX_SEQ_NO: {3}".format(
            packet.SEQ_NO_BIT_WIDTH,
            packet.LOSS_PROB,
            packet.SRP_WINDOW_SIZE,
            packet.MAX_SEQ_NO,
        )
    )

    receiver()
    logger.success('Transfer complete. Data received = "%s"' % "".join(data_recvd))
    sock.close()
    sys.exit(0)
