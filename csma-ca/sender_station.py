import logging
import random
import socket
import sys
import time

import coloredlogs
import frame
import verboselogs

# Configure logging
verboselogs.install()
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", fmt="%(asctime)s - %(message)s", datefmt="%H:%M:%S")


def carrier_sense():
    check_pkt = frame.Frame(0, ftype=frame.Frame.TYPE_CHANNEL_REQ)
    logger.notice("[CHECK]: Sensing carrier")
    frame.send_frame(client, check_pkt)
    sense = frame.recv_frame(client, timeout=frame.ACK_WAIT_TIME / 1000)

    if sense.seq_no == -2:
        # BUSY
        time.sleep(1)
        carrier_sense()

    else:
        # fREE => WAIT IFS
        logger.notice("[WAIT]: Waiting IFS time")
        time.sleep(IFS_TIME / 1000)
        check_pkt = frame.Frame(0, ftype=frame.Frame.TYPE_CHANNEL_REQ)
        logger.notice("[CHECK]: Sensing carrier")
        frame.send_frame(client, check_pkt)
        sense = frame.recv_frame(client, timeout=frame.ACK_WAIT_TIME / 1000)
        if sense.seq_no == -2:
            # BUSY
            time.sleep(1)
            carrier_sense()

        else:
            # ALL CLEAR
            return 1


# Just frame every character in message as there are no windows needed
def sender_station():

    next_seq_no = 0
    k = 0

    for char in message:

        # Carrier Sense
        _ = carrier_sense()

        # Contention time
        con_time = random.randint(0, (2 ** k) - 1)
        logger.debug(
            "[PASS]: Channel Free. Waiting for contention time: %d slots", con_time
        )
        time.sleep(con_time)

        # Create frame
        pkt = frame.Frame(next_seq_no, ftype=frame.Frame.TYPE_DATA, data=char)
        logger.info("[SEND]: Sending %s." % pkt)

        # Send frame
        frame.send_frame(client, pkt)
        next_seq_no = (next_seq_no + 1) % 2
        ack = frame.recv_frame(client, timeout=frame.ACK_WAIT_TIME / 1000)

        # Check if frame is corrupt or not the expected one
        while (
            ack is None
            or ack.is_corrupt()
            or ack.ftype != frame.Frame.TYPE_ACK
            or ack.seq_no != next_seq_no
        ):
            if k < MAX_K:
                k = k + 1
            else:
                logger.critical("[ERR]: Max retries reached. Aborting Transmission.")
                return 0

            if ack is None:
                logger.error("[TIMEOUT]: Sending %s again" % pkt)
            elif ack.is_corrupt():
                logger.error("[ERR]: ACK not received.")
                logger.info("Sending %s again." % pkt)

            _ = carrier_sense()
            con_time = random.randint(0, (2 ** k) - 1)
            logger.debug(
                "[PASS]: Channel Free. Waiting for contention time: %d slots", con_time
            )
            time.sleep(con_time)

            frame.send_frame(client, pkt)
            ack = frame.recv_frame(client, timeout=frame.ACK_WAIT_TIME / 1000)

        logger.debug("[ACK]: Received %s" % ack)
        time.sleep(1)
        k = 0

    # EOF
    pkt = frame.Frame(-1, data=None)
    frame.send_frame(client, pkt)
    logger.success("[SEND]: Transfer complete. Sending EOF")


if __name__ == "__main__":

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((socket.gethostname(), 3300 if len(sys.argv) <= 1 else int(sys.argv[1])))
    sock.listen(1)

    client, _addr = sock.accept()

    # Set vars if given (Default set in frame module)
    if len(sys.argv) >= 3:
        frame.LOSS_PROB = float(sys.argv[2])
        frame.ACK_WAIT_TIME = int(sys.argv[3])
        frame.CHANNEL_BUSY_PROB = float(sys.argv[4])
        IFS_TIME = int(sys.argv[5])
        MAX_K = int(sys.argv[6])
        message = sys.argv[7]

    logger.verbose(
        "LOSS_PROB: {0}, ACK_WAIT_TIME: {1}, CHANNEL_BUSY_PROB: {2}, IFS: {3}, MAX_K: {4}, MESSAGE: {5}".format(
            frame.LOSS_PROB,
            frame.ACK_WAIT_TIME,
            frame.CHANNEL_BUSY_PROB,
            IFS_TIME,
            MAX_K,
            message,
        )
    )

    sender_station()
    client.close()
    sock.close()
    sys.exit(0)
