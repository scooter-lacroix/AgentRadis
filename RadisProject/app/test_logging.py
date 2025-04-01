import logging
from app.logger import setup_root_logger, setup_logger


def test_logging():
    # Test root logger
    root_logger = logging.getLogger()
    root_logger.debug(
        "Root logger DEBUG message - should not appear at default INFO level"
    )
    root_logger.info("Root logger INFO message")
    root_logger.warning("Root logger WARNING message")
    root_logger.error(
        "Root logger ERROR message with data",
        extra={"data": {"user": "test", "id": 123}},
    )

    # Test named logger
    app_logger = setup_logger("app_test")
    app_logger.info("App logger INFO message")
    app_logger.warning("App logger WARNING message")
    app_logger.error("App logger ERROR message")


if __name__ == "__main__":
    test_logging()
