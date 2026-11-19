"""RAM-only original owner admission, captured only by a hybrid invocation.

Owners register their existing validity check. This module creates no source,
Session or media policy and never persists a callback or a result body.
"""

from contextlib import contextmanager
from contextvars import ContextVar
import asyncio
import inspect
import weakref

_admissions = ContextVar("djconnect_transport_delivery_admissions", default=None)


@contextmanager
def capture_delivery_admissions():
    admissions = []
    scope = {"task": weakref.ref(asyncio.current_task()), "admissions": admissions}
    token = _admissions.set(scope)
    try:
        yield admissions
    finally:
        # Background tasks inherit ContextVars. Detach their shared scope from
        # private callbacks while the returned in-flight result keeps its own copy.
        scope["admissions"] = None
        _admissions.reset(token)


def register_delivery_admission(validate):
    scope = _admissions.get()
    if scope is not None and scope["admissions"] is not None:
        try:
            owner_task = asyncio.current_task() is scope["task"]()
        except RuntimeError:
            return
        if owner_task:
            scope["admissions"].append(validate)


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
