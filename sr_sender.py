#!/usr/bin/python
import socket
import sys
import os
import logging
import pickle
from threading import Lock
from time import sleep

import packet

import verboselogs
import coloredlogs


# Configure logging
verboselogs.install()
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", fmt="%(asctime)s - %(message)s", datefmt="%H:%M:%S")


message, msglen = "", 0
next_msg_char = 0

# Note that each packet has its own timer instead of a timer for single window
pbuffer = [None] * packet.SRP_WINDOW_SIZE
timers = [None] * packet.SRP_WINDOW_SIZE

# S_base is the start of region where packets are sent but not ACK'ed yet
# S_nextext is the start of region which can be sent

S_next, S_base = 0, 0

# out_sd frames track the count of frames not received sucessfully
outsd_frames = 0

sock, client = None, None
client_sync_lock = Lock()

# The timer class with GBN can't be used here as each packet has its own timer in seperate thread
# So it is better to use the inbuilt Timer in threading module
from threading import Timer

# Start the timer for packet with given seqno
def start_timer(index):
    timers[index] = Timer(packet.ACK_WAIT_TIME / 1000, callback_timeout, args=(index,))
    timers[index].start()


def stop_timer(index):
    if timers[index] is None:
        raise Error("Timer %d not running!" % index)
    if timers[index].is_alive():
        timers[index].cancel()
    timers[index] = None


def callback_timeout(index):
    # Resend packet and restart timer
    with client_sync_lock:
        if pbuffer[index] is not None:
            logger.error("[TIMEOUT]:  Resending %s" % pbuffer[index])
            packet.send_packet(client, pbuffer[index])
            start_timer(index)


# Check if received ACK is the ack expected
def is_valid_ackno(ack):

    # Obvious check
    if outsd_frames <= 0:
        return False

    seq = (S_base + 1) % (packet.MAX_SEQ_NO + 1)
    while True:
        if ack == seq:
            return True
        if seq == S_next:
            break
        seq = (seq + 1) % (packet.MAX_SEQ_NO + 1)
    return False


# Add frame to ack'ed frames list and increment S_base if ACK is valid.
def acknowledge_frames(ackno):
    global S_base, outsd_frames

    frames_acknowledged = []
    if is_valid_ackno(ackno):
        while S_base != ackno:
            ind = S_base % packet.SRP_WINDOW_SIZE

            # Clear pbuffer and stop timer
            if pbuffer[ind] is not None:
                pbuffer[ind] = None
                stop_timer(ind)

                frames_acknowledged.append(str(S_base))
                S_base = (S_base + 1) % (packet.MAX_SEQ_NO + 1)
                outsd_frames -= 1
    return frames_acknowledged


# To check if receiver packet is NACK or ACK
def handle_recvd_pkt(pkt_recvd):
    global outsd_frames, S_base
    if pkt_recvd is None:
        return

    if pkt_recvd.is_corrupt():
        logger.error("[ERR]: ACK/NACK corrupt %s", pkt_recvd)
        sleep((packet.ACK_WAIT_TIME / 1000) - 1)

    logger.debug("[RECV]: Received %s.", pkt_recvd)

    # Check if packet is NACK
    if pkt_recvd.ptype == packet.Packet.TYPE_NACK:
        ind = pkt_recvd.seq_no % packet.SRP_WINDOW_SIZE

        # Resend packet corresponding to the NACK
        if pbuffer[ind] and pbuffer[ind].seq_no == pkt_recvd.seq_no:
            logger.warning("[NACK_SEND] : %s.", pbuffer[ind])
            stop_timer(ind)
            packet.send_packet(client, pbuffer[ind])
            start_timer(ind)

    # Check if packet is ACK and call acknowledge_frame if true
    elif pkt_recvd.ptype == packet.Packet.TYPE_ACK:
        ackno = pkt_recvd.seq_no
        frames = acknowledge_frames(ackno)
        logger.debug("[ACK]: %s frames acknowledged", ", ".join(frames))

    # Error Handling
    else:
        raise Error("Unknown packet type - %s", str(pkt_recv.ptype))


def sender():

    global pbuffer, timers

    pbuffer = [None] * packet.SRP_WINDOW_SIZE
    timers = [None] * packet.SRP_WINDOW_SIZE

    global outsd_frames, S_next, next_msg_char

    while True:
        try:
            # We need to check 2 connditions:
            # 1) We check if no of outstanding frames is less than specified window size.
            # 2) we check if the message index doesn't exceed message length

            if outsd_frames < packet.SRP_WINDOW_SIZE and next_msg_char < msglen:
                pkt = packet.Packet(
                    seq_no=S_next,
                    data=message[next_msg_char],
                    ptype=packet.Packet.TYPE_DATA,
                )
                next_msg_char += 1
                ind = S_next % packet.SRP_WINDOW_SIZE
                pbuffer[ind] = pkt
                logger.info("[SEND]: %s", pkt)

                # Acquire lock before writing to client socket.
                with client_sync_lock:
                    packet.send_packet(client, pkt)

                # Start timer for packet and increment S_next
                start_timer(ind)
                S_next = (S_next + 1) % (packet.MAX_SEQ_NO + 1)
                outsd_frames += 1

            sleep(0.5)

            # Check for an incoming packet.
            pkt_recvd = packet.recv_packet_nblock(client)
            handle_recvd_pkt(pkt_recvd)

            # Check if outsd_frames is empty and next_msg_index exceeds message length (terminating condition)
            if outsd_frames == 0 and next_msg_char >= msglen:

                # EOF
                pack = packet.Packet(-1, data=None)
                packet.send_packet(client, pack)

                logger.success("[SEND]: Transfer complete. Sending EOF")
                break

        except KeyboardInterrupt as e:
            break

    client.close()
    sock.close()


if __name__ == "__main__":
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("", 3300 if len(sys.argv) <= 1 else int(sys.argv[1])))
    sock.listen(5)

    client, addr = sock.accept()
    logger.debug("Connected.")

    # Set vars if given (Default set in packet module)
    if len(sys.argv) >= 3:
        packet.SEQ_NO_BIT_WIDTH = int(sys.argv[2])
        packet.LOSS_PROB = float(sys.argv[3])
        packet.SRP_WINDOW_SIZE = 2 ** (packet.SEQ_NO_BIT_WIDTH - 1)
        packet.MAX_SEQ_NO = (2 ** packet.SEQ_NO_BIT_WIDTH) - 1
        packet.ACK_WAIT_TIME = int(sys.argv[4])
        message = sys.argv[5]
        msglen = len(message)

    logger.verbose(
        "SEQ_NO_BIT_WIDTH: {0}, LOSS_PROB: {1}, SRP_WINDOW_SIZE: {2}, MAX_SEQ_NO: {3}, ACK_WAIT_TIME: {4}, MESSAGE: {5}".format(
            packet.SEQ_NO_BIT_WIDTH,
            packet.LOSS_PROB,
            packet.SRP_WINDOW_SIZE,
            packet.MAX_SEQ_NO,
            packet.ACK_WAIT_TIME,
            message,
        )
    )

    sender()
    sock.close()
    client.close()