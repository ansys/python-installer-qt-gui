import logging
import sys


def enable_logging():
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                if not self.stream.closed:
                    super().emit(record)
            except (ValueError, AttributeError):
                pass

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create a console handler that writes to stdout
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)
