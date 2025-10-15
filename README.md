
# Usage

```python
from pathlib import Path
from svg_translate import start_on_template_title

title = "Template:OWID/Parkinsons prevalence"

output_dir = Path(__file__).parent / "svg_data"

new_data_paths = start_on_template_title(title, output_dir=output_dir, titles_limit=None)

for file_name, file_path in new_data_paths.items():
    upload_file(file_name, file_path)

```
