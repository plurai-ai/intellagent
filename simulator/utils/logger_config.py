import logging

# Shared logger instance
logger = None

def setup_logger(log_file="app.log"):
    """
    Initializes the shared logger instance with the specified log file.
    """
    global logger
    if logger is None:  # Only initialize once
        logger = logging.getLogger("shared_logger")
        logger.setLevel(logging.DEBUG)

        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
