import socket, errno, select
from . import tube
from .. import log

class sock(tube.tube):
    """Methods available exclusively to sockets."""

    def __init__(self, timeout):
        super(sock, self).__init__(timeout)
        self.closed = {"recv": False, "send": False}

    # Overwritten for better usability
    def recvall(self):
        """recvall() -> str

        Receives data until the socket is closed.
        """

        if hasattr(self, 'type') and self.type == socket.SOCK_DGRAM:
            log.error("UDP sockets does not supports recvall")
        else:
            return super(sock, self).recvall()

    def recv_raw(self, numb):
        if self.closed["recv"]:
            raise EOFError

        go = True
        while go:
            go = False

            try:
                data = self.sock.recv(numb)
            except socket.timeout:
                return None
            except IOError as e:
                if e.errno == errno.EAGAIN:
                    return None
                elif e.errno in [errno.ECONNREFUSED, errno.ECONNRESET]:
                    self.shutdown("recv")
                    raise EOFError
                elif e.errno == errno.EINTR:
                    go = True
                else:
                    raise

        if data == '':
            self.shutdown("recv")
            raise EOFError
        else:
            return data

    def send_raw(self, data):
        if self.closed["send"]:
            raise EOFError

        try:
            self.sock.sendall(data)
        except IOError as e:
            eof_numbers = [errno.EPIPE, errno.ECONNRESET, errno.ECONNREFUSED]
            if e.message == 'Socket is closed' or e.errno in eof_numbers:
                self.shutdown("send")
                raise EOFError
            else:
                raise

    def settimeout_raw(self, timeout):
        if not self.sock:
            return

        if timeout != None and timeout <= 0:
            self.sock.setblocking(0)
        else:
            self.sock.setblocking(1)
            self.sock.settimeout(timeout)

    def can_recv_raw(self, timeout):
        if not self.sock or self.closed["recv"]:
            return False

        return select.select([self.sock], [], [], timeout) == ([self.sock], [], [])

    def connected_raw(self, direction):
        if not self.sock:
            return False

        if direction == 'any':
            return True
        elif direction == 'recv':
            return not self.closed['recv']
        elif direction == 'send':
            return not self.closed['send']

    def close(self):
        if not self.sock:
            return

        # Call shutdown without triggering another call to close
        self.closed['hack'] = False
        self.shutdown('recv')
        self.shutdown('send')
        del self.closed['hack']

        self.sock.close()
        self.sock = None
        self._close_msg()

    def _close_msg(self):
        log.info('Closed connection to %s port %d' % (self.rhost, self.rport))

    def fileno(self):
        if not self.sock:
            log.error("A closed socket does not have a file number")

        return self.sock.fileno()

    def shutdown_raw(self, direction):
        if self.closed[direction]:
            return

        self.closed[direction] = True

        if direction == "send":
            try:
                self.sock.shutdown(socket.SHUT_WR)
            except IOError as e:
                if e.errno == errno.ENOTCONN:
                    pass
                else:
                    raise

        if direction == "recv":
            try:
                self.sock.shutdown(socket.SHUT_RD)
            except IOError as e:
                if e.errno == errno.ENOTCONN:
                    pass
                else:
                    raise

        if False not in self.closed.values():
            self.close()
