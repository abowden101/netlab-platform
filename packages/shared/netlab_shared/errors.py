"""Shared error types for netlab-platform."""


class NetlabError(Exception):
    """Base error for all platform failures."""


class UnknownDriverError(NetlabError):
    """A topology references a NOS driver that is not registered."""


class ImageNotConfiguredError(NetlabError):
    """A driver that requires a BYO image was used without one configured."""


class LabNotFoundError(NetlabError):
    """A referenced lab slug or session id does not exist."""


class QuotaExceededError(NetlabError):
    """Host capacity or per-lab quotas refuse a new deploy."""


class SessionExpiredError(NetlabError):
    """A lab session passed its TTL or idle timeout."""


class RunnerError(NetlabError):
    """Containerlab / Docker invocation failed."""


class ValidationError(NetlabError):
    """A topology or lab definition failed validation."""
