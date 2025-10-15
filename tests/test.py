
import sys
from pathlib import Path
sys.argv.append("DEBUG")
from svgpy.svgtranslate import svg_extract_and_inject


def test1():

    Dir = Path(__file__).parent  # Get the directory path of the current script

    _result = svg_extract_and_inject(Dir / "files1/arabic.svg", Dir / "files1/no_translations.svg")

    print("______________________\n"*5)

    _2 = svg_extract_and_inject(Dir / "big_example/file2.svg", Dir / "big_example/file1.svg")
    print("______________________\n"*5)

    # _3 = svg_extract_and_inject(Dir / "files2/from2.svg", Dir / "files2/to2.svg")

    print("______________________\n"*5)

    _data = svg_extract_and_inject(Dir / "files2/from2.svg", Dir / "files2/to2_raw.svg", overwrite=True)
    _data = svg_extract_and_inject(Dir / "files2/from2.svg", Dir / "files2/to2.svg", overwrite=True)


def test2():

    Dir = Path(__file__).parent  # Get the directory path of the current script

    # _data = svg_extract_and_inject(Dir / "files2/from2.svg", Dir / "files2/to2_raw.svg", overwrite=False)
    _data = svg_extract_and_inject(Dir / "files2/from2.svg", Dir / "files2/to2.svg", overwrite=False)
    _data = svg_extract_and_inject(Dir / "files2/from2.svg", Dir / "files2/to2_overwrite.svg", overwrite=True)


if __name__ == '__main__':
    test2()
