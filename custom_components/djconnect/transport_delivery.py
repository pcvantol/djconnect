"""RAM-only original owner admission, captured only by a hybrid invocation.

Owners register their existing validity check. This module creates no source,
Session or media policy and never persists a callback or a result body.
"""

from contextlib import contextmanager
from contextvars import ContextVar
import inspect

_admissions = ContextVar("djconnect_transport_delivery_admissions", default=None)


@contextmanager
def capture_delivery_admissions():
    admissions = []
    token = _admissions.set(admissions)
    try:
        yield admissions
    finally:
        _admissions.reset(token)


def register_delivery_admission(validate):
    admissions = _admissions.get()
    if admissions is not None:
        admissions.append(validate)


class OwnerDeliveryResult(dict):
    """Internal result with non-JSON admissions; exists only for in-flight delivery."""

    def __init__(self, body, admissions):
        super().__init__(body)
        self._admissions = tuple(admissions)

    async def admitted_body(self):
        admitted = False
        if self._admissions:
            try:
                for validate in self._admissions:
                    result = validate()
                    if inspect.isawaitable(result):
                        await result
            except Exception:
                # An owner rejection or unavailable validity check withdraws
                # rich content; retain only the separately committed outcome.
                admitted = False
            else:
                admitted = True
        if admitted:
            return {
                **self,
                "result_available": True,
                "operation_receipt": {**self["operation_receipt"], "result_available": True},
            }
        # A known semantic outcome survives loss of rich-content delivery rights.
        # Never re-invoke a mutating/generating handler to recreate its body.
        receipt = self["operation_receipt"]
        body = {
            "success": receipt["phase"] == "confirmed",
            "operation_receipt": receipt,
            "result_available": False,
        }
        if receipt["phase"] in {"rejected", "unknown", "cancelled"}:
            body["error"] = receipt.get("error") or "operation_" + receipt["phase"]
        return body
