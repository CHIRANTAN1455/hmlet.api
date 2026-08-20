"""A single, predictable error envelope for the whole API.

DRF's default error bodies change shape depending on what went wrong: a field
validation failure is a dict of lists, a permission failure is
``{"detail": "..."}``, and an unhandled database error is a 500 HTML page.
Clients then need three code paths. Everything here is normalised to:

    {
      "error": {
        "code": "validation_error",
        "message": "Request payload failed validation.",
        "details": {"end_date": ["End date must be after start date."]}
      }
    }

``details`` is omitted when there is nothing structured to report.
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class Conflict(APIException):
    """The request is well-formed but collides with existing state.

    Used for double-booking: the payload is valid in isolation, it just cannot
    coexist with a contract that is already in the database.
    """

    status_code = status.HTTP_409_CONFLICT
    default_detail = "The request conflicts with the current state of the resource."
    default_code = "conflict"


def _build_error(code, message, details=None):
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return {"error": payload}


def api_exception_handler(exc, context):
    """DRF ``EXCEPTION_HANDLER``. Wired up in settings.REST_FRAMEWORK."""

    # Django's ValidationError can escape from model.full_clean() calls; DRF
    # does not understand it and would let it become a 500.
    if isinstance(exc, DjangoValidationError):
        return Response(
            _build_error(
                "validation_error",
                "Request payload failed validation.",
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

    # A database constraint fired that the application layer did not anticipate.
    # For this service that is almost always the contract overlap exclusion
    # constraint losing a race, which is a conflict rather than a server fault.
    if isinstance(exc, IntegrityError):
        logger.warning("IntegrityError surfaced to the API layer: %s", exc)
        return Response(
            _build_error(
                "conflict",
                "The request conflicts with existing data.",
                {"database": [str(exc)]},
            ),
            status=status.HTTP_409_CONFLICT,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        # Genuinely unhandled -- let Django's own 500 handling take over so the
        # traceback is not swallowed in DEBUG.
        return None

    if isinstance(exc, Http404):
        code, message = "not_found", "The requested resource does not exist."
    elif isinstance(exc, PermissionDenied):
        code, message = "permission_denied", "You do not have permission to do that."
    else:
        code = getattr(exc, "default_code", "error")
        message = _summarise(exc.detail) if hasattr(exc, "detail") else str(exc)

    details = None
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        code = "validation_error" if response.status_code == 400 else code
        message = "Request payload failed validation." if response.status_code == 400 else message
        details = response.data
    elif isinstance(detail, list):
        details = {"non_field_errors": response.data}

    response.data = _build_error(code, message, details)
    return response


def _summarise(detail):
    """Reduce a DRF detail (str / list / dict) to one human-readable sentence."""
    if isinstance(detail, dict):
        first_key = next(iter(detail), None)
        return _summarise(detail[first_key]) if first_key else "Request failed."
    if isinstance(detail, (list, tuple)):
        return _summarise(detail[0]) if detail else "Request failed."
    return str(detail)
