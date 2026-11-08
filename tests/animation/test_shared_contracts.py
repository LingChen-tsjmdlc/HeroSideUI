"""Cross-component contracts for shared motion, not just helper internals."""

from dataclasses import dataclass

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QPoint, QVariantAnimation
from PySide6.QtWidgets import QWidget
from shiboken6 import delete, isValid

from hero_side_ui import (
    Autocomplete,
    Checkbox,
    CircularProgress,
    Progress,
    Radio,
    Select,
    Skeleton,
    Spinner,
)
from hero_side_ui._shared.selection import SelectorButton
from hero_side_ui.animation import (
    CheckDrawAnimation,
    IndeterminateBarAnimation,
    LoopDriver,
    PhaseDriver,
    SkeletonShimmerAnimation,
    SpinAnimation,
    StripeFlowAnimation,
    stop_tween,
    tween_geometry,
    tween_property,
    tween_value,
)


def flush_deletes():
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_completed_and_cancelled_transitions_release_qt_children(qtbot):
    owner = QObject()
    for _ in range(8):
        tween_value(owner, "motion", 0.0, 1.0, lambda _: None, duration=1)
        qtbot.waitUntil(lambda: owner.motion is None)
    for _ in range(8):
        tween_value(owner, "motion", 0.0, 1.0, lambda _: None, duration=1000)
        stop_tween(owner, "motion")
    flush_deletes()
    assert not owner.findChildren(QVariantAnimation)


def test_equal_request_preempts_a_running_transition(qtbot):
    owner = QObject()
    steps, completed = [], []
    tween_value(
        owner,
        "motion",
        0.0,
        1.0,
        steps.append,
        duration=1000,
        on_finished=lambda: completed.append("old"),
    )
    qtbot.wait(30)
    current = steps[-1]
    assert (
        tween_value(
            owner,
            "motion",
            current,
            current,
            steps.append,
            duration=100,
            on_finished=lambda: completed.append("new"),
        )
        is None
    )
    count = len(steps)
    qtbot.wait(40)
    assert len(steps) == count
    assert owner.motion is None
    assert completed == ["new"]


def test_immediate_request_applies_endpoint_before_completion(qtbot):
    owner = QObject()
    observed = []
    tween_value(owner, "motion", 0, 100, observed.append, duration=1000)
    observed.clear()
    tween_value(
        owner,
        "motion",
        0,
        7,
        observed.append,
        duration=1000,
        animated=False,
        on_finished=lambda: observed.append("done"),
    )
    qtbot.wait(30)
    assert observed == [7, "done"]
    assert owner.motion is None


def test_reentrant_step_does_not_complete_superseded_request(qtbot):
    owner = QObject()
    completed = []

    def replace(value):
        tween_value(
            owner,
            "motion",
            value,
            10,
            lambda _: None,
            duration=20,
            on_finished=lambda: completed.append("replacement"),
        )

    tween_value(
        owner,
        "motion",
        0,
        1,
        replace,
        duration=0,
        on_finished=lambda: completed.append("superseded"),
    )
    qtbot.waitUntil(lambda: completed == ["replacement"])


def test_property_target_destruction_clears_separate_holder(qtbot):
    @dataclass
    class Holder:
        motion: object = None

    holder = Holder()
    target = QWidget()
    completed = []
    tween_property(
        target,
        "motion",
        b"pos",
        QPoint(50, 50),
        owner=holder,
        duration=1000,
        on_finished=lambda: completed.append(True),
    )
    delete(target)
    flush_deletes()
    assert holder.motion is None
    assert completed == []


def test_geometry_immediate_request_stops_previous_motion(qtbot):
    widget = QWidget()
    qtbot.addWidget(widget)
    end = widget.geometry().translated(30, 20)
    tween_geometry(widget, "motion", end, duration=1000)
    target = widget.geometry()
    tween_geometry(widget, "motion", target, duration=50)
    qtbot.wait(40)
    assert widget.geometry() == target
    assert widget.motion is None


def test_destroyed_owner_does_not_receive_completion(qtbot):
    owner = QObject()
    completed = []
    anim = tween_value(
        owner,
        "motion",
        0,
        1,
        lambda _: None,
        duration=100,
        on_finished=lambda: completed.append(True),
    )
    delete(owner)
    qtbot.wait(120)
    assert not isValid(anim)
    assert completed == []
    assert tween_value(owner, "motion", 0, 1, lambda _: None, duration=100) is None


@pytest.mark.parametrize(
    "factory,read,half",
    [
        (PhaseDriver, lambda d: d.value(), 0.5),
        (SpinAnimation, lambda d: d.angle_value(), 180.0),
        (SkeletonShimmerAnimation, lambda d: d.progress_value(), 0.5),
        (StripeFlowAnimation, lambda d: d.offset_value(), 16.0),
        (IndeterminateBarAnimation, lambda d: d.position, 0.3),
    ],
)
def test_all_loop_effects_share_visibility_and_keep_ranges(qtbot, factory, read, half):
    owner = QWidget()
    qtbot.addWidget(owner)
    driver = factory(owner)
    assert isinstance(driver, LoopDriver)
    driver.phase = 0.5
    assert read(driver) == pytest.approx(half)
    driver.start()
    assert not driver.is_running()
    owner.show()
    assert driver.is_running()
    owner.hide()
    assert not driver.is_running()
    driver.set_duration(200)
    assert not driver.is_running()
    owner.show()
    assert driver.is_running()
    owner.hide()
    driver.stop()
    owner.show()
    assert not driver.is_running()


def test_loop_with_external_parent_stops_when_repaint_owner_is_destroyed(qtbot):
    parent = QObject()
    owner = QWidget()
    driver = LoopDriver(owner, parent=parent)
    owner.show()
    driver.start()
    delete(owner)
    assert not driver.is_running()
    delete(parent)


def test_spinner_variant_changes_while_hidden_preserve_requested_motion(qtbot):
    spinner = Spinner()
    qtbot.addWidget(spinner)
    assert not spinner._driver_a.is_running()
    spinner.show()
    assert spinner._driver_a.is_running() and spinner._driver_b.is_running()
    spinner.hide()
    spinner.set_variant("simple")
    assert not spinner._driver_a.is_running() and not spinner._driver_b.is_running()
    spinner.show()
    assert spinner._driver_a.is_running() and not spinner._driver_b.is_running()


@pytest.mark.parametrize(
    "factory,drivers",
    [
        (lambda: Skeleton(), lambda w: [w._shimmer]),
        (
            lambda: Progress(is_indeterminate=True, is_striped=True),
            lambda w: [w._track._indet_loop, w._track._stripe_flow],
        ),
        (lambda: CircularProgress(is_indeterminate=True), lambda w: [w._spin]),
    ],
)
def test_real_loop_consumers_stop_hidden_and_restart_visible(qtbot, factory, drivers):
    widget = factory()
    qtbot.addWidget(widget)
    assert all(not d.is_running() for d in drivers(widget))
    widget.show()
    assert all(d.is_running() for d in drivers(widget))
    widget.hide()
    assert all(not d.is_running() for d in drivers(widget))
    widget.show()
    assert all(d.is_running() for d in drivers(widget))


@pytest.mark.parametrize("factory", [Select, Autocomplete])
def test_real_selector_uses_shared_trigger_and_immediate_preemption(qtbot, factory):
    widget = factory()
    qtbot.addWidget(widget)
    trigger = widget.findChild(SelectorButton)
    assert trigger is not None
    trigger.set_angle(180, animated=True, duration=500)
    qtbot.wait(40)
    assert trigger.angle() > 0
    trigger.set_angle(0, animated=False)
    qtbot.wait(70)
    assert trigger.angle() == 0
    assert trigger._angle_anim_runner is None


def test_checkbox_reselection_cancels_previous_delayed_draw(qtbot):
    checkbox = Checkbox()
    qtbot.addWidget(checkbox)
    assert isinstance(checkbox._check_anim, CheckDrawAnimation)
    checkbox.setChecked(True)
    qtbot.wait(40)
    checkbox.setChecked(False)
    checkbox.setChecked(True)
    qtbot.wait(70)
    assert checkbox.check_draw == 0.0
    qtbot.waitUntil(lambda: checkbox.check_draw > 0)
    checkbox.set_disable_animation(True)
    qtbot.wait(120)
    assert checkbox.check_draw == 1.0
    assert checkbox.fill_progress == 1.0
    assert checkbox._fill_anim is None


def test_skeleton_disabling_motion_settles_both_fade_layers(qtbot):
    skeleton = Skeleton()
    qtbot.addWidget(skeleton)
    skeleton.show()
    skeleton.set_loaded(True)
    qtbot.wait(30)
    skeleton.set_disable_animation(True)
    qtbot.wait(50)
    assert skeleton._skeleton_opacity == 0.0
    assert skeleton._content_opacity == 1.0
    assert not skeleton._shimmer.is_running()


@pytest.mark.parametrize(
    "factory,property_name",
    [
        (Checkbox, "fill_progress"),
        (Radio, "control_progress"),
    ],
)
def test_initial_selected_state_is_visible_with_animation_disabled(qtbot, factory, property_name):
    widget = factory(is_selected=True, disable_animation=True)
    qtbot.addWidget(widget)
    assert widget.isChecked()
    assert widget.property(property_name) == 1.0
    widget.setChecked(False)
    assert widget.property(property_name) == 0.0


def test_property_target_destruction_cancels_separate_qobject_channel(qtbot):
    owner = QObject()
    target = QWidget()
    finished = []
    anim = tween_property(
        target,
        "motion",
        b"pos",
        QPoint(50, 50),
        owner=owner,
        duration=1000,
        on_finished=lambda: finished.append(True),
    )
    delete(target)
    flush_deletes()
    assert owner.motion is None
    assert not isValid(anim)
    assert finished == []
