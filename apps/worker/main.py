import logging
import time

from roadeye.jobs import tick

logging.basicConfig(level=logging.INFO, format="%(message)s")
if __name__ == "__main__":
    while True:
        if not tick():
            time.sleep(0.25)
