
from commons.download_bot import download_commons_svgs
from commons.temps_bot import get_files
from commons.text_bot import get_wikitext
from svgpy.svgtranslate import

def start(title):

    text = get_wikitext(title)

    main_title, titles = get_files(text)

    titles2 = titles
    titles2.append(main_title)

    files = download_commons_svgs(titles, out_dir=main_title)
