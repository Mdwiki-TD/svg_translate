
import sys
sys.argv.append("DEBUG")

from pathlib import Path

from svgtranslate import svg_extract_and_inject


def test1():

    Dir = Path(__file__).parent  # Get the directory path of the current script

    _result = svg_extract_and_inject(Dir / "tests/files1/arabic.svg", Dir / "tests/files1/no_translations.svg")

    print("______________________\n"*5)

    _2 = svg_extract_and_inject(Dir.parent / "big_example/file2.svg", Dir.parent / "big_example/file1.svg")
    print("______________________\n"*5)

    # _3 = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2.svg")

    print("______________________\n"*5)

    _data = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2_raw.svg", overwrite=True)
    _data = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2.svg", overwrite=True)


def test2():

    Dir = Path(__file__).parent  # Get the directory path of the current script

    _data = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2_raw.svg", overwrite=True)
    _data = svg_extract_and_inject(Dir / "tests/files2/from2.svg", Dir / "tests/files2/to2.svg", overwrite=True)


if __name__ == '__main__':
    test2()
