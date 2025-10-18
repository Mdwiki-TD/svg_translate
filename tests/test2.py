

from svg_translate import svg_extract_and_injects, extract

from pathlib import Path
tests_files_dir = Path(__file__).parent.parent / "tests_files"


def test():

    parkinsons_Dir = tests_files_dir / "parkinsons"
    input_file = parkinsons_Dir / "ar.svg"

    translations = extract(input_file, case_insensitive=True)

    inject_files = [x for x in parkinsons_Dir.glob("*.svg") if x != input_file]

    output_dir = tests_files_dir / "translated/parkinsons"
    output_dir.mkdir(parents=True, exist_ok=True)

    for file in inject_files:
        _data = svg_extract_and_injects(translations, file, output_dir=output_dir)
        # break


if __name__ == '__main__':
    test()
