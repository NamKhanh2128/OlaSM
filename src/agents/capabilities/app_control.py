"""Green SM mobile app-control capabilities.

These tools only create typed intents. The Green SM mobile host remains the
authority that executes navigation, form updates and confirmations.
"""

from __future__ import annotations

from typing import Any

from src.agents.contracts.app_control import (
    AppAction,
    AppActionKind,
    AppActionRisk,
    AppContext,
    AppScreen,
    SessionControl,
    capability_allowed,
    new_action_id,
)
from src.agents.contracts.schemas import ActionType, AgentAction
from src.agents.core.registry import RegisteredTool, ToolRegistry
from src.agents.core.session import TurnSession
from src.agents.core.tools import tool_definition


_BIOMETRIC_TARGETS = {
    "pay",
    "payment",
    "cancel_ride",
    "delete_account",
    "logout",
    "change_security",
    "change_phone",
}


def _context(session: TurnSession) -> AppContext | None:
    raw = session.event.get("app_context")
    if raw is None:
        return None
    try:
        return AppContext.model_validate(raw)
    except ValueError:
        return None


def _blocked(session: TurnSession, message: str) -> AgentAction:
    return AgentAction(
        action_type=ActionType.ASK_USER,
        message=message,
        state_updates=session.updates,
        reason="Mobile host did not advertise the requested app capability.",
    )


def _require_context(session: TurnSession) -> AppContext | AgentAction:
    context = _context(session)
    if context is None:
        return _blocked(
            session,
            "Mình chưa nhận được ngữ cảnh Green SM. Bạn mở ứng dụng Green SM và thử lại giúp mình nhé.",
        )
    if not context.foreground:
        return _blocked(
            session,
            "Green SM chưa ở màn hình đang hoạt động. Mình không thể tự cưỡng chế mở ứng dụng qua phiên voice này.",
        )
    return context


def _record_action(session: TurnSession, action: AppAction) -> dict[str, Any]:
    collected = dict(session.updates.get("collected_data", session.state.collected_data))
    app_control = dict(collected.get("app_control", {}))
    app_control.update(
        {
            "last_action_id": action.action_id,
            "last_action_kind": action.kind.value,
            "last_action_target": action.target,
            "status": "DISPATCHED",
        }
    )
    collected["app_control"] = app_control
    return {**session.updates, "collected_data": collected}


def _dispatch(
    session: TurnSession,
    action: AppAction,
    message: str,
    *,
    session_control: SessionControl | None = None,
    action_type: ActionType = ActionType.RESPOND,
) -> AgentAction:
    return AgentAction(
        action_type=action_type,
        message=message,
        app_actions=[action],
        session_control=session_control,
        state_updates=_record_action(session, action),
        reason="Typed Green SM app action dispatched to the mobile host.",
    )


def _navigate(session: TurnSession, arguments: dict[str, Any]) -> AgentAction:
    result = _require_context(session)
    if isinstance(result, AgentAction):
        return result
    try:
        target = AppScreen(str(arguments.get("screen", "")).strip().upper())
    except ValueError:
        return _blocked(session, "Màn hình này chưa nằm trong danh sách điều khiển được của Green SM.")
    if not capability_allowed(result, f"navigate:{target.value}"):
        return _blocked(session, "Màn hình đó hiện chưa được Green SM cho phép điều khiển bằng voice.")
    action = AppAction(
        action_id=new_action_id("nav"),
        kind=AppActionKind.NAVIGATE,
        target=target.value,
        risk=AppActionRisk.SAFE_NAVIGATION,
        reason="Voice navigation requested by the user.",
    )
    return _dispatch(session, action, f"Mình đã mở màn hình {target.value.lower()} trên Green SM.")


def _go_back(session: TurnSession, _arguments: dict[str, Any]) -> AgentAction:
    result = _require_context(session)
    if isinstance(result, AgentAction):
        return result
    if not capability_allowed(result, "system:back"):
        return _blocked(session, "Màn hình hiện tại không cho phép quay lại bằng voice.")
    action = AppAction(action_id=new_action_id("back"), kind=AppActionKind.GO_BACK)
    return _dispatch(session, action, "Mình đã quay lại màn hình trước.")


def _read_screen(session: TurnSession, _arguments: dict[str, Any]) -> AgentAction:
    result = _require_context(session)
    if isinstance(result, AgentAction):
        return result
    if not capability_allowed(result, "system:read_screen"):
        return _blocked(session, "Green SM chưa cho phép đọc màn hình hiện tại bằng voice.")
    summary = result.screen_summary or f"Bạn đang ở màn hình {result.screen.value.lower()} của Green SM."
    action = AppAction(action_id=new_action_id("read"), kind=AppActionKind.READ_SCREEN)
    return _dispatch(session, action, summary)


def _set_field(session: TurnSession, arguments: dict[str, Any]) -> AgentAction:
    result = _require_context(session)
    if isinstance(result, AgentAction):
        return result
    field = str(arguments.get("field", "")).strip()
    value = str(arguments.get("value", "")).strip()
    if not field or not value:
        return _blocked(session, "Mình cần biết trường nào và giá trị bạn muốn nhập.")
    if not capability_allowed(result, f"field:{field}"):
        return _blocked(session, "Trường này không có trong màn hình hiện tại hoặc chưa được cho phép điều khiển.")
    action = AppAction(
        action_id=new_action_id("field"),
        kind=AppActionKind.SET_FIELD,
        target=field,
        value=value[:500],
        risk=AppActionRisk.USER_CONFIRMATION,
        reason="Voice filled a non-secret field exposed by the mobile host.",
    )
    return _dispatch(session, action, f"Mình đã điền {field} trên Green SM.")


def _select_option(session: TurnSession, arguments: dict[str, Any]) -> AgentAction:
    result = _require_context(session)
    if isinstance(result, AgentAction):
        return result
    field = str(arguments.get("field", "")).strip()
    option_id = str(arguments.get("option_id", "")).strip()
    if not field or not option_id:
        return _blocked(session, "Mình cần biết danh sách nào và lựa chọn nào bạn muốn chọn.")
    if not capability_allowed(result, f"field:{field}"):
        return _blocked(session, "Lựa chọn này không có trong màn hình hiện tại hoặc chưa được cho phép.")
    action = AppAction(
        action_id=new_action_id("select"),
        kind=AppActionKind.SELECT_OPTION,
        target=field,
        value=option_id,
        risk=AppActionRisk.USER_CONFIRMATION,
        reason="Voice selected an option exposed by the mobile host.",
    )
    return _dispatch(session, action, f"Mình đã chọn {option_id}.")


def _submit(session: TurnSession, arguments: dict[str, Any]) -> AgentAction:
    result = _require_context(session)
    if isinstance(result, AgentAction):
        return result
    target = str(arguments.get("target", "")).strip()
    if not target:
        return _blocked(session, "Mình cần biết thao tác nào bạn muốn thực hiện.")
    if not capability_allowed(result, f"submit:{target}"):
        return _blocked(session, "Thao tác này chưa được Green SM cho phép thực hiện bằng voice.")
    risk = AppActionRisk.BIOMETRIC_REQUIRED if target.casefold() in _BIOMETRIC_TARGETS else AppActionRisk.APP_CONFIRMATION
    control = (
        SessionControl.BIOMETRIC_REQUIRED
        if risk is AppActionRisk.BIOMETRIC_REQUIRED
        else SessionControl.APP_CONFIRMATION_REQUIRED
    )
    action = AppAction(
        action_id=new_action_id("submit"),
        kind=AppActionKind.SUBMIT,
        target=target,
        risk=risk,
        confirmation_required=True,
        parameters={"voice_confirmation_requested": bool(arguments.get("confirmed", False))},
        reason="The mobile app must confirm every side-effecting submission.",
    )
    return _dispatch(
        session,
        action,
        "Mình đã chuyển thao tác sang Green SM. Bạn xác nhận trên ứng dụng để tiếp tục.",
        session_control=control,
    )


def _open_help(session: TurnSession, arguments: dict[str, Any]) -> AgentAction:
    result = _require_context(session)
    if isinstance(result, AgentAction):
        return result
    target = str(arguments.get("target", "SUPPORT")).strip() or "SUPPORT"
    if not capability_allowed(result, "support:open"):
        return _blocked(session, "Màn hình hỗ trợ chưa sẵn sàng trong phiên Green SM này.")
    action = AppAction(
        action_id=new_action_id("help"),
        kind=AppActionKind.OPEN_HELP,
        target=target,
        risk=AppActionRisk.SAFE_NAVIGATION,
    )
    return _dispatch(session, action, "Mình đã mở khu vực hỗ trợ Green SM.")


def _end_assistant(session: TurnSession, _arguments: dict[str, Any]) -> AgentAction:
    action = AppAction(
        action_id=new_action_id("end"),
        kind=AppActionKind.END_ASSISTANT,
        risk=AppActionRisk.SAFE_NAVIGATION,
        reason="Stop the voice session and release microphone resources.",
    )
    return _dispatch(
        session,
        action,
        "Mình đã dừng trợ lý voice và nhả quyền microphone. Ứng dụng Green SM vẫn do hệ điều hành quản lý.",
        session_control=SessionControl.ENDED,
        action_type=ActionType.END_SESSION,
    )


def _request_open_app(session: TurnSession, _arguments: dict[str, Any]) -> AgentAction:
    context = _context(session)
    if context is None or context.foreground:
        return AgentAction(
            action_type=ActionType.RESPOND,
            message="Green SM đang mở hoặc chưa gửi trạng thái nền. Mình không thể tự cưỡng chế mở app.",
            state_updates=session.updates,
            reason="OS-level app launch is controlled by the mobile operating system.",
        )
    if not capability_allowed(context, "system:open_app"):
        return _blocked(session, "Hệ điều hành chưa cấp quyền mở Green SM từ phiên voice này.")
    action = AppAction(
        action_id=new_action_id("open"),
        kind=AppActionKind.REQUEST_OPEN_APP,
        target="GREEN_SM",
        risk=AppActionRisk.OS_MANAGED,
        reason="Ask the mobile OS to resume the Green SM app.",
    )
    return _dispatch(
        session,
        action,
        "Mình đã gửi yêu cầu mở Green SM cho hệ điều hành.",
        session_control=SessionControl.APP_OPEN_REQUIRED,
    )


def _available(session: TurnSession) -> bool:
    return _context(session) is not None


def register_app_control(registry: ToolRegistry) -> None:
    registry.register(
        RegisteredTool(
            tool_definition(
                'navigate_app',
                'Navigate only to a Green SM screen advertised by the mobile host.',
                {'screen': {'type': 'string', 'enum': [screen.value for screen in AppScreen if screen is not AppScreen.UNKNOWN]}},
                ['screen'],
            ),
            _navigate,
            _available,
        )
    )
    registry.register(
        RegisteredTool(
            tool_definition('go_back', 'Go back using the host app navigation stack.', {}),
            _go_back,
            _available,
        )
    )
    registry.register(
        RegisteredTool(
            tool_definition('read_current_screen', 'Read the bounded summary of the current Green SM screen.', {}),
            _read_screen,
            _available,
        )
    )
    registry.register(
        RegisteredTool(
            tool_definition(
                'set_app_field',
                'Fill a non-secret field advertised by the current Green SM screen.',
                {'field': {'type': 'string'}, 'value': {'type': 'string'}},
                ['field', 'value'],
            ),
            _set_field,
            _available,
        )
    )
    registry.register(
        RegisteredTool(
            tool_definition(
                'select_app_option',
                'Select an option from a field advertised by the current Green SM screen.',
                {'field': {'type': 'string'}, 'option_id': {'type': 'string'}},
                ['field', 'option_id'],
            ),
            _select_option,
            _available,
        )
    )
    registry.register(
        RegisteredTool(
            tool_definition(
                'submit_app_action',
                'Request a side-effecting app action; the mobile host must show confirmation or biometric UI.',
                {
                    'target': {'type': 'string'},
                    'confirmed': {'type': 'boolean'},
                },
                ['target', 'confirmed'],
            ),
            _submit,
            _available,
        )
    )
    registry.register(
        RegisteredTool(
            tool_definition(
                'open_app_help',
                'Open the Green SM support/help surface exposed by the host.',
                {'target': {'type': 'string'}},
                ['target'],
            ),
            _open_help,
            _available,
        )
    )
    registry.register(RegisteredTool(tool_definition('end_voice_assistant', 'Stop the voice assistant session.', {}), _end_assistant))
    registry.register(
        RegisteredTool(
            tool_definition('request_open_app', 'Ask the mobile OS to resume Green SM when the app is backgrounded.', {}),
            _request_open_app,
        )
    )
