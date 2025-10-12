

from pathlib import Path

from svgtranslate import svg_extract_and_inject


def test():

    parkinsons_Dir = Path(__file__).parent / "parkinsons"
    input_file = parkinsons_Dir / "ar.svg"
    inject_files = [x for x in parkinsons_Dir.glob("*.svg") if x != input_file]
    _data = svg_extract_and_inject(input_file, inject_files[0])


if __name__ == '__main__':
    test()
