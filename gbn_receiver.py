import socket
import sys
import random
import logging
import verboselogs
import coloredlogs

import packet

# Configure logging
verboselogs.install()
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG", fmt="%(asctime)s - %(message)s", datefmt="%H:%M:%S")



def receiver():
    print(packet.SEQ_NO_BIT_WIDTH, packet.LOSS_PROB)
    expected_seq_no = 0

    # To store received message
    data_recvd = []

    while True:
        try:
            # Wait for packet
            pkt = packet.recv_packet(sock)

            # EOF
            if pkt.seq_no == -1:
                logger.debug("[RECV]: Received EOF")
                break

            # If packet is corrupt, consecutive frames will be discarded
            if pkt.is_corrupt():
                logger.error("[ERR]: %s is corrupt. Discarding" % pkt)

            # Packet Acknowledgement
            elif pkt.seq_no == expected_seq_no:
                logger.debug("[RECV]: Received %s." % pkt)

                # Increment expected_seq_no as current frame is received successfully
                expected_seq_no = (expected_seq_no + 1) % (packet.MAX_SEQ_NO + 1)

                # Add paket data to list
                data_recvd.append(pkt.data)
            else:
                logger.error("[ERR]: %s arrived out of order. Discarding." % pkt)

            ack_pkt = packet.Packet(expected_seq_no, ptype=packet.Packet.TYPE_ACK)
            logger.info("[ACK]: %s" % ack_pkt)
            packet.send_packet(sock, ack_pkt)

        except socket.error as e:
            logger.critical(str(e))
            break

        except KeyboardInterrupt as e:
            sock.close()
            sys.exit(0)

    logger.success('Transfer complete. Data received = "%s"' % "".join(data_recvd))



if __name__ == "__main__":

    # Socket for listening for incoming connections
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("", 3300 if len(sys.argv) <= 1 else int(sys.argv[1])))
    logger.debug("Connected to server.")

    # Set vars if given (Default set in packet module)
    if len(sys.argv) >= 3:
        packet.SEQ_NO_BIT_WIDTH = int(sys.argv[2])
        packet.LOSS_PROB = float(sys.argv[3])
        packet.GBN_WINDOW_SIZE = (2 ** packet.SEQ_NO_BIT_WIDTH) - 1
        packet.MAX_SEQ_NO = packet.GBN_WINDOW_SIZE

    receiver()
    sock.close()
    sys.exit(0)