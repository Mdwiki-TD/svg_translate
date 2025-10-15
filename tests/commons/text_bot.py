
from svg_translate import get_wikitext


title = "Template:OWID/Parkinsons prevalence"

text = get_wikitext(title)
if text:
    print(text[:500])  # print first 500 chars
else:
    print("Page not found or empty.")
