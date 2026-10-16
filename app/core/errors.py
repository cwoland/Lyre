import logging
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    validation_error = "validation_error"
    unauthorized = "unauthorized"
    forbidden = "forbidden"
    not_found = "not_found"
    conflict = "conflict"
    limit_exceeded = "limit_exceeded"
    rate_limited = "rate_limited"
    internal_error = "internal_error"


class ErrorBody(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(Exception):
    status_code: int = status.HTTP_400_BAD_REQUEST
    code: ErrorCode = ErrorCode.validation_error

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def body(self) -> ErrorResponse:
        return ErrorResponse(
            error=ErrorBody(code=self.code, message=self.message, details=self.details)
        )


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = ErrorCode.unauthorized


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = ErrorCode.forbidden


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = ErrorCode.not_found


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = ErrorCode.conflict


class LimitExceededError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = ErrorCode.limit_exceeded


_STATUS_TO_CODE: dict[int, ErrorCode] = {
    status.HTTP_401_UNAUTHORIZED: ErrorCode.unauthorized,
    status.HTTP_403_FORBIDDEN: ErrorCode.forbidden,
    status.HTTP_404_NOT_FOUND: ErrorCode.not_found,
    status.HTTP_409_CONFLICT: ErrorCode.conflict,
    status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.validation_error,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.rate_limited,
}


def error_json(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.body().model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return error_json(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            ErrorCode.validation_error,
            "Request validation failed",
            {"errors": jsonable_encoder(exc.errors())},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, ErrorCode.internal_error)
        return error_json(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return error_json(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            ErrorCode.internal_error,
            "Internal server error",
        )
