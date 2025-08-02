import os
import logging
from datetime import datetime
import structlog

class CustomLogger:
    def __init__(self, log_dir='logs'):
        #Esnure logs directory exists
        self.log_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.log_dir, exist_ok=True)

        #Timestamped log file (for persistence)
        log_file = f"{datetime.now().strftime("%m_%d_%Y_%H_%M_%S")}.log"
        self.log_file_path = os.path.join(self.log_dir, log_file)

    def get_logger(self, name = __file__):
        logger_name = os.path.basename(name)

        #configure logging for console + file (both JSON)
        file_handler = logging.FileHandler(self.log_file_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter("%(message)s")) #RAW JSON lines

        #to log messages directly in the terminal while the application is running
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter("%(message)s"))

        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s", #strutclog will handle JSON formatting
            handlers = [console_handler, file_handler]
        )

        #configure structlog for JSON structured logging
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt = "iso", utc=True, key = "timestamp"),
                structlog.processors.add_log_level,
                structlog.processors.EventRenamer(to='event'),
                structlog.processors.JSONRenderer(),
                
            ],
            #Integrates structlog with Python's standard logging module, allowing you to use structlog's features while still using the standard logging interface.
            logger_factory=structlog.stdlib.LoggerFactory(),
            #Ensures that the logger is cached after its first use for performance optimization.
            cache_logger_on_first_use = True,
        )

        return structlog.get_logger(logger_name)
    
if __name__ == "__main__":
    logger = CustomLogger().get_logger(__file__)
    logger.info("Custom logger initialized successfully.")
    logger.error("This is a test error message.")
    logger.debug("Debugging information here.")
    logger.warning("This is a warning message.")
    logger.info({"event": "test_event", "message": "This is a structured log message."})