from werkzeug.datastructures import MultiDict

from app.tasks.routes import parse_args


def test_parse_args_includes_manual_title():
    form = MultiDict({
        "titles_limit": "25",
        "overwrite": "1",
        "manual_main_title": " File:Manual Example.svg ",
    })

    args = parse_args(form)

    assert args.manual_main_title == "Manual Example.svg"


def test_parse_args_manual_title_defaults_to_none():
    form = MultiDict()

    args = parse_args(form)

    assert args.manual_main_title is None
