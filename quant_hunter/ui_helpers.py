from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout


def build_workspace_badge(value: str, caption: str) -> QFrame:
    frame = QFrame()
    frame.setObjectName("workspaceBadge")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(2)

    value_label = QLabel(value)
    value_label.setObjectName("workspaceBadgeValue")
    caption_label = QLabel(caption)
    caption_label.setObjectName("workspaceBadgeCaption")

    layout.addWidget(value_label)
    layout.addWidget(caption_label)
    return frame


def build_workspace_hero(
    eyebrow: str,
    title: str,
    subtitle: str,
    badges: list[tuple[str, str]] | None = None,
) -> QFrame:
    frame = QFrame()
    frame.setObjectName("workspaceHero")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(18, 16, 18, 16)
    layout.setSpacing(16)

    text_layout = QVBoxLayout()
    text_layout.setSpacing(4)

    eyebrow_label = QLabel(eyebrow)
    eyebrow_label.setObjectName("workspaceEyebrow")
    text_layout.addWidget(eyebrow_label)

    title_label = QLabel(title)
    title_label.setObjectName("workspaceTitle")
    text_layout.addWidget(title_label)

    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("workspaceSubtitle")
    subtitle_label.setWordWrap(True)
    text_layout.addWidget(subtitle_label)

    layout.addLayout(text_layout, stretch=1)

    if badges:
        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)
        for value, caption in badges:
            badge_row.addWidget(build_workspace_badge(value, caption))
        badge_row.addStretch(1)
        layout.addLayout(badge_row)

    return frame


def set_button_role(button: QPushButton, role: str = "ghost") -> None:
    button.setObjectName("accentButton" if role == "accent" else "ghostButton")
    button.style().unpolish(button)
    button.style().polish(button)


def style_terminal_panel(*boxes: QGroupBox) -> None:
    for box in boxes:
        box.setObjectName("terminalPanel")


def style_terminal_console(*widgets: QTextEdit) -> None:
    for widget in widgets:
        widget.setObjectName("terminalConsole")
