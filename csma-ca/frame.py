import socket
import pickle
import random

# Corruption probability
LOSS_PROB = 0.1

# Channel busy probability
CHANNEL_BUSY_PROB = 0.3

# Timeout in ms
ACK_WAIT_TIME = 8000


class Frame:

    # Type of transmitted data
    TYPE_DATA, TYPE_ACK, TYPE_CHANNEL_REQ = range(3)

    # frame construcktor
    def __init__(self, seq_no, data="", ftype=TYPE_DATA):
        self.seq_no = seq_no
        self.data = data
        self.ftype = ftype
        self.channel_busy = 0
        self.corrupt = 0

    def is_channel_busy(self):
        if not self.channel_busy:
            self.channel_busy = random.random()
        return self.channel_busy > CHANNEL_BUSY_PROB

    def is_corrupt(self):
        if not self.corrupt:
            self.corrupt = random.random()
        return self.corrupt < LOSS_PROB

    # frame string description
    def __str__(self):
        if self.ftype == Frame.TYPE_DATA:
            return "Frame[SEQ_NO={0} DATA={1}]".format(self.seq_no, str(self.data))
        elif self.ftype == Frame.TYPE_CHANNEL_REQ:
            return "Checking state of channel"
        return "Frame[ACK={0}]".format(self.seq_no)


## Helper functions


def read_k_bytes(sock, remaining=0):
    """
    Read exactly `remaining` bytes from the socket.
    Blocks until the required bytes are available and
    return the data read as raw bytes. Call to this
    function blocks until required bytes are available
    in the socket.

    Arguments
    ---------
    sock  : Socket to inspect
    remaining : Number of bytes to read from socket.
    """
    ret = b""  # Return byte buffer
    while remaining > 0:
        d = sock.recv(remaining)
        ret += d
        remaining -= len(d)
    return ret


def send_frame(sock, frm):
    """
    Send a frame to remote socket. We first send
    the size of frame in bytes followed by the
    actual frame. frame is serialized using
    cPickle module.

    Arguments
    ---------
    sock  : Destination socket
    frm  : Instance of class frame.
    """
    if frm is None or (sock is None or type(sock) != socket.socket):
        return  # Nothing to send
    frm_raw_bytes = pickle.dumps(frm)
    dsize = len(frm_raw_bytes)
    sock.sendall(dsize.to_bytes(4, byteorder="big"))
    sock.sendall(frm_raw_bytes)
    return True


def recv_frame(sock, timeout=None):
    """
    Receive a frame from the socket.
    Reads the size of frame first followed by the actual data.
    frame is then de-serialized and returned as an instance
    of class frame.

    Arguments
    ----------
    sock    :- The socket to read from.
    timeout :- If None, the call will block till a frame is
               available. Else it will wait for specified seconds for
               a frame.

    Return None if no frame has arrived.
    """
    if sock is None or type(sock) != socket.socket:
        raise TypeError("Socket expected!")
    # Read the size from the channel first
    if timeout is not None:
        # Do not wait for more that `timeout`  seconds
        sock.settimeout(timeout)
    try:
        frm_len = int.from_bytes(read_k_bytes(sock, 4), "big")
        # Switch to blocking mode
        sock.settimeout(None)
        frm = pickle.loads(read_k_bytes(sock, frm_len))
    except socket.timeout:
        frm = None
    finally:
        # Blocking mode
        sock.settimeout(None)
    return frm
