"""Tests for the G-4 event bus schema (`src/gleipnir/bus/events.py`).

Plan: `.gleipnir/plans/g4-bus-first-slice.md`, Assemble step 1 / Stress-test
checks 1-3. Written RED-first, before `src/gleipnir/bus/events.py` exists.

Covers:
  1. `Envelope` carries all eight G-4a fields + `version` + `sequence` + `kind`.
  2. `EventKind` has `REVERT_OCCURRED`.
  3. `RevertOccurredEvent` carries `from_state`/`to_state`/`revert_count`/
     `escalated`.
  4. `Event` round-trips through `to_json_line`/`from_json_line` into TYPED
     objects — the read path is attribute access, never prose-parsing.
  5. One JSON line, no embedded newline.
  6. Malformed / unknown-kind lines raise `BusError` (fail-closed on read).
  7. A static check that the read path contains no `.split(`/`re.` usage
     (G-4a's "never parses a human-readable string", enforced as a real
     check, not a comment).
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import textwrap

import pytest

from gleipnir.bus import events as events_module
from gleipnir.bus.events import (
    EVENT_VERSION,
    BusError,
    Envelope,
    Event,
    EventKind,
    GateReachedEvent,
    NeedsHumanRaisedEvent,
    RevertOccurredEvent,
)

SESSION_ID = "session-abc-123"


def _make_envelope(**overrides: object) -> Envelope:
    defaults: dict[str, object] = dict(
        emitter="engine.driver",
        enforcement_surface="engine",
        agent="gleipnir-code",
        action="revert_occurred",
        session_id=SESSION_ID,
        originating_turn=3,
        artifact_ref="pl-test-1",
        timestamp="2026-07-27T00:00:00+00:00",
        version=EVENT_VERSION,
        sequence=1,
        kind=EventKind.REVERT_OCCURRED,
    )
    defaults.update(overrides)
    return Envelope(**defaults)  # type: ignore[arg-type]


def _make_revert_event(**overrides: object) -> Event:
    payload = RevertOccurredEvent(
        from_state="test",
        to_state="spec_review",
        revert_count=1,
        escalated=False,
    )
    envelope = _make_envelope(**overrides)
    return Event(envelope=envelope, payload=payload)


# ---------------------------------------------------------------------------
# 1. Envelope carries all eight G-4a fields + version + sequence + kind.
# ---------------------------------------------------------------------------


class TestEnvelopeSchema:
    def test_envelope_has_all_eight_g4a_fields(self):
        field_names = {f.name for f in dataclasses.fields(Envelope)}
        g4a_fields = {
            "emitter",
            "enforcement_surface",
            "agent",
            "action",
            "session_id",
            "originating_turn",
            "artifact_ref",
            "timestamp",
        }
        assert g4a_fields <= field_names

    def test_envelope_has_version_sequence_and_kind(self):
        field_names = {f.name for f in dataclasses.fields(Envelope)}
        assert {"version", "sequence", "kind"} <= field_names

    def test_envelope_is_frozen(self):
        envelope = _make_envelope()
        with pytest.raises(dataclasses.FrozenInstanceError):
            envelope.action = "tampered"  # type: ignore[misc]

    def test_agent_and_artifact_ref_are_structurally_present_but_nullable(self):
        envelope = _make_envelope(agent=None, artifact_ref=None)
        assert envelope.agent is None
        assert envelope.artifact_ref is None
        # The field exists structurally regardless of value.
        assert "agent" in {f.name for f in dataclasses.fields(envelope)}
        assert "artifact_ref" in {f.name for f in dataclasses.fields(envelope)}


# ---------------------------------------------------------------------------
# 2. EventKind has REVERT_OCCURRED (extensible enum).
# ---------------------------------------------------------------------------


class TestEventKind:
    def test_revert_occurred_member_exists(self):
        assert EventKind.REVERT_OCCURRED.value == "revert_occurred"

    def test_event_kind_is_str_enum(self):
        assert isinstance(EventKind.REVERT_OCCURRED, str)

    def test_needs_human_raised_member_exists_and_is_str(self):
        assert EventKind.NEEDS_HUMAN_RAISED.value == "needs_human_raised"
        assert isinstance(EventKind.NEEDS_HUMAN_RAISED, str)

    def test_gate_reached_member_exists_and_is_str(self):
        assert EventKind.GATE_REACHED.value == "gate_reached"
        assert isinstance(EventKind.GATE_REACHED, str)


# ---------------------------------------------------------------------------
# 3. RevertOccurredEvent payload.
# ---------------------------------------------------------------------------


class TestRevertOccurredEventPayload:
    def test_carries_from_to_count_and_escalated(self):
        payload = RevertOccurredEvent(
            from_state="quality", to_state="code", revert_count=2, escalated=False
        )
        assert payload.from_state == "quality"
        assert payload.to_state == "code"
        assert payload.revert_count == 2
        assert payload.escalated is False

    def test_escalated_defaults_false(self):
        payload = RevertOccurredEvent(
            from_state="test", to_state="spec_review", revert_count=1
        )
        assert payload.escalated is False

    def test_payload_is_frozen(self):
        payload = RevertOccurredEvent(
            from_state="test", to_state="spec_review", revert_count=1
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            payload.revert_count = 99  # type: ignore[misc]

    def test_payload_is_not_a_free_dict(self):
        payload = RevertOccurredEvent(
            from_state="test", to_state="spec_review", revert_count=1
        )
        assert not isinstance(payload, dict)
        assert dataclasses.is_dataclass(payload)


# ---------------------------------------------------------------------------
# 3b. NeedsHumanRaisedEvent / GateReachedEvent payloads.
# ---------------------------------------------------------------------------


class TestNeedsHumanRaisedEventPayload:
    def test_carries_from_state(self):
        payload = NeedsHumanRaisedEvent(from_state="plan")
        assert payload.from_state == "plan"

    def test_payload_is_frozen(self):
        payload = NeedsHumanRaisedEvent(from_state="plan")
        with pytest.raises(dataclasses.FrozenInstanceError):
            payload.from_state = "tampered"  # type: ignore[misc]

    def test_payload_is_not_a_free_dict(self):
        payload = NeedsHumanRaisedEvent(from_state="plan")
        assert not isinstance(payload, dict)
        assert dataclasses.is_dataclass(payload)


class TestGateReachedEventPayload:
    def test_carries_pipeline_id(self):
        payload = GateReachedEvent(pipeline_id="pl-1")
        assert payload.pipeline_id == "pl-1"

    def test_payload_is_frozen(self):
        payload = GateReachedEvent(pipeline_id="pl-1")
        with pytest.raises(dataclasses.FrozenInstanceError):
            payload.pipeline_id = "tampered"  # type: ignore[misc]

    def test_payload_is_not_a_free_dict(self):
        payload = GateReachedEvent(pipeline_id="pl-1")
        assert not isinstance(payload, dict)
        assert dataclasses.is_dataclass(payload)


# ---------------------------------------------------------------------------
# 4 + 5. Round-trip through to_json_line / from_json_line -> TYPED objects.
# ---------------------------------------------------------------------------


class TestSerializationRoundTrip:
    def test_to_json_line_is_exactly_one_line_valid_json(self):
        event = _make_revert_event()
        line = event.to_json_line()
        assert "\n" not in line
        parsed = json.loads(line)  # must not raise
        assert isinstance(parsed, dict)

    def test_round_trip_reconstructs_typed_objects(self):
        event = _make_revert_event()
        line = event.to_json_line()

        reconstructed = Event.from_json_line(line)

        # Typed, not prose: kind is a real EventKind member, payload is a
        # real RevertOccurredEvent, and every field is read by ATTRIBUTE
        # access -- never string/regex/substring parsing.
        assert reconstructed.kind is EventKind.REVERT_OCCURRED
        assert isinstance(reconstructed.payload, RevertOccurredEvent)
        assert reconstructed.payload.from_state == "test"
        assert reconstructed.payload.to_state == "spec_review"
        assert reconstructed.payload.revert_count == 1
        assert reconstructed.payload.escalated is False

        assert reconstructed.envelope.emitter == "engine.driver"
        assert reconstructed.envelope.enforcement_surface == "engine"
        assert reconstructed.envelope.agent == "gleipnir-code"
        assert reconstructed.envelope.action == "revert_occurred"
        assert reconstructed.envelope.session_id == SESSION_ID
        assert reconstructed.envelope.originating_turn == 3
        assert reconstructed.envelope.artifact_ref == "pl-test-1"
        assert reconstructed.envelope.timestamp == "2026-07-27T00:00:00+00:00"
        assert reconstructed.envelope.version == EVENT_VERSION
        assert reconstructed.envelope.sequence == 1

    def test_round_trip_preserves_nullable_agent_and_artifact_ref(self):
        event = _make_revert_event(agent=None, artifact_ref=None)
        reconstructed = Event.from_json_line(event.to_json_line())
        assert reconstructed.envelope.agent is None
        assert reconstructed.envelope.artifact_ref is None

    def test_round_trip_reconstructs_needs_human_raised_event(self):
        payload = NeedsHumanRaisedEvent(from_state="quality")
        envelope = _make_envelope(
            kind=EventKind.NEEDS_HUMAN_RAISED, action="needs_human_raised"
        )
        event = Event(envelope=envelope, payload=payload)

        reconstructed = Event.from_json_line(event.to_json_line())

        assert reconstructed.kind is EventKind.NEEDS_HUMAN_RAISED
        assert isinstance(reconstructed.payload, NeedsHumanRaisedEvent)
        assert reconstructed.payload.from_state == "quality"

    def test_round_trip_reconstructs_gate_reached_event(self):
        payload = GateReachedEvent(pipeline_id="pl-gate-1")
        envelope = _make_envelope(
            kind=EventKind.GATE_REACHED, action="gate_reached"
        )
        event = Event(envelope=envelope, payload=payload)

        reconstructed = Event.from_json_line(event.to_json_line())

        assert reconstructed.kind is EventKind.GATE_REACHED
        assert isinstance(reconstructed.payload, GateReachedEvent)
        assert reconstructed.payload.pipeline_id == "pl-gate-1"

    def test_malformed_json_raises_bus_error(self):
        with pytest.raises(BusError):
            Event.from_json_line("{ not valid json")

    def test_unknown_kind_raises_bus_error(self):
        event = _make_revert_event()
        line = event.to_json_line()
        data = json.loads(line)
        data["kind"] = "some_future_kind_not_yet_registered"
        with pytest.raises(BusError):
            Event.from_json_line(json.dumps(data))

    def test_missing_field_raises_bus_error(self):
        event = _make_revert_event()
        data = json.loads(event.to_json_line())
        del data["session_id"]
        with pytest.raises(BusError):
            Event.from_json_line(json.dumps(data))

    def test_missing_kind_raises_bus_error(self):
        # the KeyError branch when 'kind' itself is absent
        event = _make_revert_event()
        data = json.loads(event.to_json_line())
        del data["kind"]
        with pytest.raises(BusError):
            Event.from_json_line(json.dumps(data))

    def test_non_dict_payload_raises_bus_error(self):
        # the "payload must be a JSON object" branch
        event = _make_revert_event()
        data = json.loads(event.to_json_line())
        data["payload"] = "not-a-dict"
        with pytest.raises(BusError):
            Event.from_json_line(json.dumps(data))

    def test_malformed_payload_dict_raises_bus_error(self):
        # a dict payload for a known kind but with wrong/missing fields
        event = _make_revert_event()
        data = json.loads(event.to_json_line())
        data["payload"] = {"unexpected": "field"}
        with pytest.raises(BusError):
            Event.from_json_line(json.dumps(data))


# ---------------------------------------------------------------------------
# 7. Static check: the read path never string/regex/substring-parses a
#    message field (G-4a's binding constraint, enforced as a real check).
# ---------------------------------------------------------------------------


class TestReadPathIsNotProseParsing:
    def test_events_module_imports_no_regex_module(self):
        source = inspect.getsource(events_module)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                assert all(alias.name != "re" for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module != "re"

    def test_from_json_line_does_not_call_str_split(self):
        source = textwrap.dedent(inspect.getsource(Event.from_json_line))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr == "split":
                pytest.fail(
                    "from_json_line must reconstruct typed objects by field "
                    "access, not by splitting a message string"
                )
