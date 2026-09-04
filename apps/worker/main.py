import logging
import signal
import threading

from roadeye.jobs import tick

logging.basicConfig(level=logging.INFO, format="%(message)s")
stop = threading.Event()


def shutdown(signum, frame):
    stop.set()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)
    while not stop.is_set():
        if not tick():
            stop.wait(0.25)
