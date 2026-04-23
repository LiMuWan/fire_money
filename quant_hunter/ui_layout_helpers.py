from __future__ import annotations

from typing import Iterable


def _is_widget(widget) -> bool:
    return widget is not None and hasattr(widget, "setVisible") and hasattr(widget, "isVisible")


def _is_layout(layout) -> bool:
    return layout is not None and all(hasattr(layout, name) for name in ("removeWidget", "insertWidget", "indexOf", "count"))


def _content_layout_from_scroll_area(window, scroll_area_attr: str):
    scroll_area = getattr(window, scroll_area_attr, None)
    content = scroll_area.widget() if scroll_area is not None and hasattr(scroll_area, "widget") else None
    layout = content.layout() if content is not None and hasattr(content, "layout") else None
    return layout if _is_layout(layout) else None


def _named_window_widgets(window, attr_names: Iterable[str]) -> list[tuple[str, object]]:
    result: list[tuple[str, object]] = []
    for attr_name in attr_names:
        widget = getattr(window, attr_name, None)
        if _is_widget(widget):
            result.append((attr_name, widget))
    return result


def reorder_layout_sequence(layout, named_widgets: Iterable[tuple[str, object]], *, insert_at: int = 0, stretch_map: dict[str, int] | None = None) -> bool:
    if not _is_layout(layout):
        return False
    stretch_map = dict(stretch_map or {})
    visible_widgets = [(name, widget) for name, widget in named_widgets if _is_widget(widget)]
    if not visible_widgets:
        return False
    for _name, widget in visible_widgets:
        layout.removeWidget(widget)
    current_index = max(int(insert_at), 0)
    for name, widget in visible_widgets:
        layout.insertWidget(current_index, widget, int(stretch_map.get(name, 0) or 0))
        current_index = layout.indexOf(widget) + 1
    return True


def reorder_window_sequence_in_scroll_area(
    window,
    *,
    scroll_area_attr: str,
    sequence_attrs: Iterable[str],
    insert_at: int = 0,
    stretch_map: dict[str, int] | None = None,
) -> bool:
    layout = _content_layout_from_scroll_area(window, scroll_area_attr)
    if not _is_layout(layout):
        return False
    return reorder_layout_sequence(
        layout,
        _named_window_widgets(window, sequence_attrs),
        insert_at=insert_at,
        stretch_map=stretch_map,
    )


def reorder_layout_around_anchor(
    layout,
    *,
    anchor,
    before_widgets: Iterable[tuple[str, object]],
    after_widgets: Iterable[tuple[str, object]],
    stretch_map: dict[str, int] | None = None,
) -> bool:
    if not _is_layout(layout) or not _is_widget(anchor):
        return False
    stretch_map = dict(stretch_map or {})
    before_widgets = [(name, widget) for name, widget in before_widgets if _is_widget(widget)]
    after_widgets = [(name, widget) for name, widget in after_widgets if _is_widget(widget)]
    for _name, widget in before_widgets + after_widgets:
        layout.removeWidget(widget)

    before_index = max(layout.indexOf(anchor), 0)
    for name, widget in before_widgets:
        layout.insertWidget(before_index, widget, int(stretch_map.get(name, 0) or 0))
        before_index = layout.indexOf(widget) + 1

    after_index = layout.indexOf(anchor) + 1 if layout.indexOf(anchor) >= 0 else layout.count()
    for name, widget in after_widgets:
        layout.insertWidget(after_index, widget, int(stretch_map.get(name, 0) or 0))
        after_index = layout.indexOf(widget) + 1
    return True


def move_window_widget_after_first_anchor(
    window,
    *,
    scroll_area_attr: str,
    widget_attr_names: Iterable[str],
    anchor_attr_names: Iterable[str],
    fallback_index: int = 0,
    stretch: int = 0,
) -> bool:
    layout = _content_layout_from_scroll_area(window, scroll_area_attr)
    if not _is_layout(layout):
        return False

    widget = next((item for _name, item in _named_window_widgets(window, widget_attr_names)), None)
    if not _is_widget(widget):
        return False

    anchors = [item for _name, item in _named_window_widgets(window, anchor_attr_names)]
    layout.removeWidget(widget)
    anchor = next((item for item in anchors if layout.indexOf(item) >= 0), None)
    insert_index = layout.indexOf(anchor) + 1 if _is_widget(anchor) and layout.indexOf(anchor) >= 0 else min(int(fallback_index), layout.count())
    layout.insertWidget(max(insert_index, 0), widget, int(stretch))
    return True
