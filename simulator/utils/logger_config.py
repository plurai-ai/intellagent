import logging

# Shared logger instance
logger = None


class ConsoleColor:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    WHITE = "\033[97m"  # Bright white
    GREY = "\033[37m"   # Light gray

class SuppressErrorFilter(logging.Filter):
    def filter(self, record):
        # Suppress messages that contain "Error in chain invoke:"
        return "Error in chain invoke:" not in record.getMessage()

def get_logger():
    """
    Returns the shared logger instance. If not initialized, raises an error.
    """
    global logger
    if logger is None:
        # Return a basic Python logger with default configuration
        default_logger = logging.getLogger("default_logger")
        if not default_logger.handlers:  # Prevent adding multiple handlers
            default_logger.setLevel(logging.WARNING)
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            default_logger.addHandler(console_handler)
        return default_logger
    return logger

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
        console_formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(SuppressErrorFilter())

        # Add handlers to the logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger

def update_logger_file(log_file):
    """
    Updates the log file for the shared logger by replacing the file handler.
    """
    global logger

    # Remove existing file handlers
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)

    # Add a new file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
