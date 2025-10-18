
# Usage

```python
from pathlib import Path
from svg_translate import start_on_template_title, upload_file

title = "Template:OWID/Parkinsons prevalence"

output_dir = Path(__file__).parent / "svg_data"

result = start_on_template_title(title, output_dir=output_dir, titles_limit=None, overwrite=False)
files = result.get("files", {})

for file_name, file_meta in files.items():
    file_path = file_meta.get("file_path")
    if not file_path:
        continue
    upload_file(file_name, file_path)

```
