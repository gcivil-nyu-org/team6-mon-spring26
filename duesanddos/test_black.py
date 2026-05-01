import logging

logger = logging.getLogger(__name__)


class Test:
    def method(self):
        try:
            pass
        except Exception as e:  # pragma: no cover
            # fmt: off
            logger.error(f"Token refresh failed for {self.user.username}: {e}")  # pragma: no cover  # noqa: E501
            # fmt: on
            return None  # pragma: no cover
