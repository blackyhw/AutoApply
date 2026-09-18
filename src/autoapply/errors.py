from __future__ import annotations


class AutoApplyError(Exception):
    """Base error for the agent."""


class ConfigurationError(AutoApplyError):
    pass


class KillSwitchActive(AutoApplyError):
    pass


class DailyApplyLimitReached(AutoApplyError):
    pass


class CollectorError(AutoApplyError):
    pass


class CollectorNotConfigured(CollectorError):
    pass


class LlmError(AutoApplyError):
    pass


class LlmRateLimitError(LlmError):
    pass


class LlmResponseError(LlmError):
    pass


class GuardrailError(AutoApplyError):
    pass


class UnknownCvBlockError(GuardrailError):
    pass


class TemplateError(GuardrailError):
    pass


class ApplyError(AutoApplyError):
    pass
