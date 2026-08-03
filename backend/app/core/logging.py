import logging
import sys

def setup_logging():
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # Configure specific loggers if necessary
    logging.getLogger("uvicorn.access").handlers = [logging.StreamHandler(sys.stdout)]
