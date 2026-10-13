"""Typed contract between the voice agent and the Green SM mobile host."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_.:-]{1,96}$")
_ERROR_CODE = re.compile(r"^[A-Z][A-Z0-9_]{0,63}$")
_SENSITIVE_KEYS = ("password", "token", "secret", "cvv", "otp", "card_number", "access_key")
class AppScreen(StrEnum):
    HOME = 'HOME'
    SERVICE_SELECTOR = 'SERVICE_SELECTOR'
    CAR_BOOKING = 'CAR_BOOKING'
    BIKE_BOOKING = 'BIKE_BOOKING'
    FOOD_HOME = 'FOOD_HOME'
    EXPRESS_BOOKING = 'EXPRESS_BOOKING'
    INTERCITY = 'INTERCITY'
    ACTIVITY = 'ACTIVITY'
    TRIP_TRACKING = 'TRIP_TRACKING'
    PAYMENTS = 'PAYMENTS'
    PROMOTIONS = 'PROMOTIONS'
    PROFILE = 'PROFILE'
    SETTINGS = 'SETTINGS'
    SUPPORT = 'SUPPORT'
    PRIVACY = 'PRIVACY'
    UNKNOWN = 'UNKNOWN'


class AppActionKind(StrEnum):
    NAVIGATE = 'NAVIGATE'
    GO_BACK = 'GO_BACK'
    READ_SCREEN = 'READ_SCREEN'
    SET_FIELD = 'SET_FIELD'
    SELECT_OPTION = 'SELECT_OPTION'
    SUBMIT = 'SUBMIT'
    OPEN_HELP = 'OPEN_HELP'
    REQUEST_OPEN_APP = 'REQUEST_OPEN_APP'
    END_ASSISTANT = 'END_ASSISTANT'
class AppActionRisk(StrEnum):
    SAFE_NAVIGATION = 'SAFE_NAVIGATION'
    USER_CONFIRMATION = 'USER_CONFIRMATION'
    APP_CONFIRMATION = 'APP_CONFIRMATION'
    BIOMETRIC_REQUIRED = 'BIOMETRIC_REQUIRED'
    OS_MANAGED = 'OS_MANAGED'


class AppActionResultStatus(StrEnum):
    EXECUTED = 'EXECUTED'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'
    REQUIRES_CONFIRMATION = 'REQUIRES_CONFIRMATION'
    NOT_SUPPORTED = 'NOT_SUPPORTED'


class SessionControl(StrEnum):
    ACTIVE = 'ACTIVE'
    APP_OPEN_REQUIRED = 'APP_OPEN_REQUIRED'
    APP_CONFIRMATION_REQUIRED = 'APP_CONFIRMATION_REQUIRED'
    BIOMETRIC_REQUIRED = 'BIOMETRIC_REQUIRED'
    ENDED = 'ENDED'


def _normalize_identifier(value: str) -> str:
    normalized = value.strip()
    if not _IDENTIFIER.fullmatch(normalized):
        raise ValueError('value must be a bounded app identifier')
    return normalized


def _reject_sensitive_keys(value: dict[str, Any]) -> dict[str, Any]:
    for key in value:
        normalized = str(key).casefold()
        if any(sensitive in normalized for sensitive in _SENSITIVE_KEYS):
            raise ValueError('screen_state cannot contain secrets or payment credentials')
    return value
class AppActionResult(BaseModel):
    '''Result sent by the mobile host after it attempts one app action.'''

    model_config = ConfigDict(extra='forbid')

    action_id: str = Field(min_length=1, max_length=96)
    status: AppActionResultStatus
    message: str | None = Field(default=None, max_length=500)
    error_code: str | None = Field(default=None, max_length=64)
    resulting_screen: AppScreen | None = None
    context_revision: int | None = Field(default=None, ge=0)

    _normalize_action_id = field_validator('action_id')(_normalize_identifier)

    @field_validator('error_code')
    @classmethod
    def validate_error_code(cls, value: str | None) -> str | None:
        if value is not None and not _ERROR_CODE.fullmatch(value.strip()):
            raise ValueError('error_code must be an uppercase error identifier')
        return value.strip() if value is not None else None


class AppContext(BaseModel):
    '''Safe, bounded context provided by the Green SM mobile host each turn.'''

    model_config = ConfigDict(extra='forbid')

    schema_version: Literal['1'] = '1'
    app: Literal['GREEN_SM'] = 'GREEN_SM'
    screen: AppScreen = AppScreen.UNKNOWN
    service: str | None = Field(default=None, max_length=64)
    platform: Literal['IOS', 'ANDROID', 'UNKNOWN'] = 'UNKNOWN'
    app_version: str | None = Field(default=None, max_length=32)
    locale: str = Field(default='vi-VN', min_length=2, max_length=16)
    foreground: bool = True
    available_actions: list[str] = Field(default_factory=list, max_length=64)
    screen_summary: str | None = Field(default=None, max_length=1000)
    screen_state: dict[str, Any] = Field(default_factory=dict)
    last_action_result: AppActionResult | None = None

    @field_validator('available_actions')
    @classmethod
    def validate_capabilities(cls, values: list[str]) -> list[str]:
        normalized = [_normalize_identifier(value) for value in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError('available_actions cannot contain duplicates')
        return normalized

    _reject_secrets = field_validator('screen_state')(_reject_sensitive_keys)
ScalarValue = str | int | float | bool | None


class AppAction(BaseModel):
    '''One allowlisted instruction for the mobile host.'''

    model_config = ConfigDict(extra='forbid')

    action_id: str = Field(min_length=1, max_length=96)
    kind: AppActionKind
    target: str | None = None
    value: ScalarValue = None
    parameters: dict[str, ScalarValue] = Field(default_factory=dict, max_length=16)
    risk: AppActionRisk = AppActionRisk.SAFE_NAVIGATION
    confirmation_required: bool = False
    expires_in_seconds: int = Field(default=30, ge=5, le=120)
    reason: str | None = Field(default=None, max_length=300)

    _normalize_action_id = field_validator('action_id')(_normalize_identifier)

    @field_validator('target')
    @classmethod
    def validate_target(cls, value: str | None) -> str | None:
        return _normalize_identifier(value) if value is not None else None
    @model_validator(mode='after')
    def validate_semantics(self) -> 'AppAction':
        target_required = {
            AppActionKind.NAVIGATE,
            AppActionKind.SET_FIELD,
            AppActionKind.SELECT_OPTION,
            AppActionKind.SUBMIT,
            AppActionKind.OPEN_HELP,
        }
        if self.kind in target_required and self.target is None:
            raise ValueError(f'{self.kind.value} requires a target')
        if self.kind is AppActionKind.NAVIGATE and self.target not in {screen.value for screen in AppScreen}:
            raise ValueError('NAVIGATE target must be a known Green SM screen')
        if self.kind in {AppActionKind.SET_FIELD, AppActionKind.SELECT_OPTION} and self.value is None:
            raise ValueError(f'{self.kind.value} requires a value')
        if self.kind is AppActionKind.SUBMIT:
            if not self.confirmation_required:
                raise ValueError('SUBMIT always requires confirmation in the mobile app')
            if self.risk is AppActionRisk.SAFE_NAVIGATION:
                raise ValueError('SUBMIT cannot be marked as safe navigation')
        if self.risk is AppActionRisk.BIOMETRIC_REQUIRED and not self.confirmation_required:
            raise ValueError('biometric actions require confirmation')
        return self


def capability_allowed(context: AppContext, capability: str) -> bool:
    '''Return whether the host explicitly advertised a capability this turn.'''

    return capability in context.available_actions


def new_action_id(prefix: str = 'app') -> str:
    '''Create an opaque action id without exposing user data or route details.'''

    from uuid import uuid4

    return f'{prefix}-{uuid4().hex[:16]}'
