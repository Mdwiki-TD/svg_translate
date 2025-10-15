
# Usage

```python

title = "Template:OWID/Parkinsons prevalence"

new_data_paths = start_on_template_title(title, output_dir=None, titles_limit=None)

for file_name, file_path in new_data_paths.items():
    upload_file(file_name, file_path)

```
