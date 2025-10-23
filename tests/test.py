
import sys
from CopySvgTranslate import svg_extract_and_inject

from pathlib import Path
tests_files_dir = Path(__file__).parent.parent / "tests_files"


def test1():

    _result = svg_extract_and_inject(tests_files_dir / "files1/arabic.svg", tests_files_dir / "files1/no_translations.svg")

    print("______________________\n"*5)

    _2 = svg_extract_and_inject(tests_files_dir / "big_example/file2.svg", tests_files_dir / "big_example/file1.svg")
    print("______________________\n"*5)

    # _3 = svg_extract_and_inject(tests_files_dir / "files2/from2.svg", tests_files_dir / "files2/to2.svg")

    print("______________________\n"*5)

    _data = svg_extract_and_inject(tests_files_dir / "files2/from2.svg", tests_files_dir / "files2/to2_raw.svg", overwrite=True)
    _data = svg_extract_and_inject(tests_files_dir / "files2/from2.svg", tests_files_dir / "files2/to2.svg", overwrite=True)


def test2():

    # _data = svg_extract_and_inject(tests_files_dir / "files2/from2.svg", tests_files_dir / "files2/to2_raw.svg", overwrite=False)
    _data = svg_extract_and_inject(tests_files_dir / "files2/from2.svg", tests_files_dir / "files2/to2.svg", overwrite=False)
    _data = svg_extract_and_inject(tests_files_dir / "files2/from2.svg", tests_files_dir / "files2/to2_overwrite.svg", overwrite=True)


if __name__ == '__main__':
    test2()
