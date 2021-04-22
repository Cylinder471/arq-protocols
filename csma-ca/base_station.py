import socket
import sys
import random
import frame

import logging
import verboselogs
import coloredlogs

# Configure logging
verboselogs.install()
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", fmt="%(asctime)s - %(message)s", datefmt="%H:%M:%S")

def receiver():

    exp_seq_no = 0
    data_recvd = []

    while True:
        try:
            pkt = frame.recv_frame(sock)

            # Channel State
            if pkt.ftype == frame.Frame.TYPE_CHANNEL_REQ:
                if not pkt.is_channel_busy():
                    # BUSY
                    frame.send_frame(sock, frame.Frame(-2, ftype=frame.Frame.TYPE_DATA))
                    logger.info("[STATUS] : Channel Busy")
                # FREE
                else:
                    frame.send_frame(sock, frame.Frame(-3, ftype=frame.Frame.TYPE_DATA))
                    logger.info("[STATUS] : Channel Free")
                continue

            # EOF
            if pkt.seq_no == -1:
                logger.debug("[RECV]: Received EOF")
                break

            if pkt.seq_no != exp_seq_no:
                logger.error("[ERR]: %s already present." % pkt)
                logger.info("[ACK] : Sending ACK %d" % exp_seq_no)
                frame.send_frame(sock, frame.Frame(exp_seq_no, ftype=frame.Frame.TYPE_ACK))
            else:
                if not pkt.is_corrupt():
                    exp_seq_no = (exp_seq_no + 1) % 2
                    data_recvd.append(pkt.data)
                    logger.debug("[RECV] : %s" % pkt)
                    frame.send_frame(sock, frame.Frame(exp_seq_no, ftype=frame.Frame.TYPE_ACK))
                    logger.info("[ACK] : Sending ACK = %d" % exp_seq_no)
                    
                else:
                    # We simply drop the frame. The timer at the sender will timeout and send the frame again.
                    logger.error("[ERR]: %s is corrupt. Dropping." % pkt)
        except ConnectionResetError:
            break
        except KeyboardInterrupt:
            break
        
    logger.success('Transfer complete. Data received = "%s"' % "".join(data_recvd))


if __name__ == "__main__":
    
    # Socket for listening for incoming connections
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((socket.gethostname(), 3300 if len(sys.argv) <= 1 else int(sys.argv[1])))

    # Set vars if given (Default set in frame module)
    if len(sys.argv) >= 3:
        frame.LOSS_PROB = float(sys.argv[2])

    logger.verbose(
        "LOSS_PROB: {0}".format(
            frame.LOSS_PROB,
        )
    )

    receiver()
    sock.close()
    sys.exit(0)