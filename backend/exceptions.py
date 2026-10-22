"""
FinStream AI - API Exceptions & Handlers
Provides domain-specific exceptions and global exception handlers for standardized error responses.
"""

from typing import Optional
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError


class FinStreamApiException(Exception):
    """Base exception for all FinStream API errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "api_error",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.detail = detail


class ResourceNotFoundException(FinStreamApiException):
    """Raised when a requested transaction, risk assessment, or account does not exist."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            message=f"{resource_type} '{resource_id}' was not found.",
            error_code=f"{resource_type.lower()}_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ValidationException(FinStreamApiException):
    """Raised when input parameters fail domain validation rules."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            message=message,
            error_code="invalid_request_parameters",
            status_code=422,
            detail=detail,
        )


class ServiceUnavailableException(FinStreamApiException):
    """Raised when a required external service or database is unavailable."""

    def __init__(self, service_name: str, message: Optional[str] = None):
        super().__init__(
            message=message or f"Underlying service '{service_name}' is currently unavailable.",
            error_code="service_unavailable",
            status_code=503,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers on the FastAPI application."""

    @app.exception_handler(FinStreamApiException)
    async def fms_exception_handler(request: Request, exc: FinStreamApiException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Input validation failed.",
                "detail": str(exc),
            },
        )
