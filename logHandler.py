import logging


def setup_logging():
    # Create a logger
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.DEBUG)

    # Create a file handler that writes log messages to a text file
    file_handler = logging.FileHandler("log_file.txt")
    file_handler.setLevel(logging.DEBUG)

    # Create a log format
    log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(log_format)

    # Add the file handler to the logger
    logger.addHandler(file_handler)

    return logger
