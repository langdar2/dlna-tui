from textual.widgets import Static

from ui.app import HELP_TEXT, DlnaApp, HelpScreen, help_rows


def test_every_binding_is_explained():
    """A key added to BINDINGS must get a real explanation, not fall back to
    its terse footer label."""
    missing = [action for _, action, _ in DlnaApp.BINDINGS if action not in HELP_TEXT]
    assert missing == []


def test_rows_follow_binding_order_with_readable_keys():
    rows = help_rows([("space", "toggle", "Play/Pause"), ("slash", "search", "Filter"),
                      ("z", "unknown", "Zzz")])
    assert rows[0] == ("Leertaste", HELP_TEXT["toggle"])
    assert rows[1][0] == "/"
    assert rows[2] == ("z", "Zzz")  # unknown action falls back to its label


async def test_question_mark_opens_and_closes_help():
    class T(DlnaApp):
        async def on_mount(self):
            pass

    app = T(store=None, requester=None, event_handler=None)
    async with app.run_test() as pilot:
        await pilot.press("question_mark")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        text = "\n".join(str(s.render()) for s in app.screen.query(Static))
        assert "Tastenbelegung" in text and "CrateMind" in text

        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, HelpScreen)
