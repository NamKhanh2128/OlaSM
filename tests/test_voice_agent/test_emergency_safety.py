from pathlib import Path
from types import SimpleNamespace

import pytest
from livekit.agents import StopResponse, llm

from src.voice_agent.agent import AloSMAgent
from src.voice_agent.safety import (
    DEFAULT_SAFETY_POLICY_PATH,
    SafetyClassifier,
    SafetyPolicy,
    assess_user_safety,
    load_safety_policy,
)
from src.voice_agent.session_data import AloSMSessionData
from src.voice_agent.tools.handoffs import HandoffToolsService


class _SpeechHandle:
    def add_done_callback(self, callback: object) -> None:
        self._callback = callback

class _AudioControl:
    def __init__(self) -> None:
        self.enabled: list[bool] = []

    def set_audio_enabled(self, enabled: bool) -> None:
        self.enabled.append(enabled)



class _SafetySession:
    def __init__(self) -> None:
        self.input = _AudioControl()
        self.output = _AudioControl()
        self.acknowledgements: list[tuple[str, bool]] = []

    def say(self, text: str, *, allow_interruptions: bool) -> _SpeechHandle:
        self.acknowledgements.append((text, allow_interruptions))
        return _SpeechHandle()


class _DurableHandoff:
    def __init__(self, session: _SafetySession) -> None:
        self.session = session
        self.saw_guidance_before_create = False

    async def create_handoff_durable(self, payload: dict[str, object]) -> dict[str, object]:
        self.saw_guidance_before_create = bool(self.session.acknowledgements)
        return {**payload, "handoff_id": "emergency-handoff", "status": "pending"}


@pytest.mark.asyncio
async def test_emergency_question_gets_immediate_safety_guidance_before_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    session = _SafetySession()
    durable_handoff = _DurableHandoff(session)
    agent = AloSMAgent(
        session_data=userdata,
        handoffs=HandoffToolsService(durable_handoff),
    )
    agent._activity = SimpleNamespace(session=session)  # type: ignore[assignment]
    monkeypatch.setattr("src.voice_agent.agent.publish_booking_state", _noop_publish)

    with pytest.raises(StopResponse):
        await agent.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["Tôi nên đặt xe đi viện hay gọi cấp cứu?"]),
        )

    assert len(session.acknowledgements) == 1
    response, allow_interruptions = session.acknowledgements[0]
    assert "115" in response
    assert allow_interruptions is False
    assert durable_handoff.saw_guidance_before_create
    assert userdata.handoff is not None
    assert userdata.handoff.reason_code == "EMERGENCY"


async def _noop_publish(*_: object) -> None:
    return None


@pytest.mark.parametrize(
    ("utterance", "expected_emergency"),
    [
        ("Cấp cứu giúp tôi", True),
        ("Mẹ tôi bất tỉnh", True),
        ("Tôi đang gặp nguy hiểm", True),
        ("Tôi muốn đặt xe đến bệnh viện", False),
        ("Tôi muốn gặp tổng đài viên", False),
    ],
)
def test_safety_classifier_uses_risk_signals_not_complete_sentences(
    utterance: str, expected_emergency: bool
) -> None:
    assert assess_user_safety(utterance).is_emergency is expected_emergency


class _FailingDurableHandoff:
    async def create_handoff_durable(self, payload: dict[str, object]) -> dict[str, object]:
        raise RuntimeError("handoff unavailable")


@pytest.mark.asyncio
async def test_emergency_keeps_safety_guidance_when_handoff_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    userdata = AloSMSessionData(
        app_session_id="session",
        call_id="call",
        user_id="user",
        participant_identity="participant",
    )
    session = _SafetySession()
    agent = AloSMAgent(
        session_data=userdata,
        handoffs=HandoffToolsService(_FailingDurableHandoff()),
    )
    agent._activity = SimpleNamespace(session=session)  # type: ignore[assignment]
    monkeypatch.setattr("src.voice_agent.agent.publish_booking_state", _noop_publish)

    with pytest.raises(StopResponse):
        await agent.on_user_turn_completed(
            llm.ChatContext.empty(),
            llm.ChatMessage(role="user", content=["Tôi đang gặp nguy hiểm, cần gọi cấp cứu"]),
        )

    assert len(session.acknowledgements) == 1
    assert "115" in session.acknowledgements[0][0]
    assert userdata.handoff is None


def test_classifier_uses_signals_from_policy_interface() -> None:
    policy = SafetyPolicy.model_validate(
        {
            "schema_version": "1.0.0",
            "policy_version": "test-policy",
            "status": "APPROVED",
            "emergency": {
                "reason_code": "EMERGENCY",
                "risk_level": "CRITICAL",
                "priority": 100,
                "severity": "CRITICAL",
                "queue": "EMERGENCY_OPERATOR",
                "requires_immediate_transfer": True,
                "signals": ["trieu chung nguy kich"],
                "guidance": "Gọi 115 ngay.",
            },
        }
    )

    assert SafetyClassifier(policy).assess("Tình trạng của tôi có triệu chứng nguy kịch").is_emergency


def test_default_safety_policy_is_versioned_and_loaded_from_data() -> None:
    policy = load_safety_policy()

    assert DEFAULT_SAFETY_POLICY_PATH == Path("data/safety/emergency_policy.yaml").resolve()
    assert policy.policy_version
    assert policy.emergency.signals
    assert "115" in policy.emergency.guidance
