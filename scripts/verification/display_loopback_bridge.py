"""TLS-transparent stdio bridge ONLY to the own isolated browser lab loopback.

No listener, caller-selected host/port, TLS termination, credentials or logs.
Invoked through docker exec by the bounded optional browser verification probe.
"""
import socket
import sys
import threading


def main():
    with socket.create_connection(("127.0.0.1", 18443), timeout=5) as connection:
        connection.settimeout(None)
        def write():
            try:
                while chunk := sys.stdin.buffer.read1(65536):
                    connection.sendall(chunk)
            except OSError:
                pass
            finally:
                try:
                    connection.shutdown(socket.SHUT_WR)
                except OSError:
                    pass
        threading.Thread(target=write, daemon=True).start()
        try:
            while chunk := connection.recv(65536):
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
        except (OSError, BrokenPipeError):
            pass


if __name__ == "__main__":
    main()
