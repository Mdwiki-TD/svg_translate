

from pathlib import Path

from svgtranslate import svg_extract_and_inject


def test():

    Dir = Path(__file__).parent  # Get the directory path of the current script

    _data = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2_raw.svg")


if __name__ == '__main__':
    test()
