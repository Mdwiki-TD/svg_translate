# SVG Translation Tool

This tool extracts multilingual text pairs from SVG files and applies translations to other SVG files by inserting missing `<text systemLanguage="XX">` blocks.

## Features

- Extract translations from SVG files with multilingual content
- Inject translations into SVG files that lack them
- Preserve original formatting and attributes
- Create backups before modifying files
- Support for dry-run mode to preview changes
- Case-insensitive matching option
- Comprehensive logging

## Installation

This tool requires Python 3.10+ and the following dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Extracting Translations

To extract translations from an SVG file:

```bash
python svgtranslate.py extract <svg_file> [--output <json_file>] [--verbose] [--case-insensitive]
```

Example:
```bash
python svgtranslate.py extract arabic.svg --verbose
```

This will create a file named `arabic.svg.json` containing the extracted translations.

### Injecting Translations

To inject translations into SVG files:

```bash
python svgtranslate.py inject <svg_files...> --mapping <json_file> [--output-dir <dir>] [--overwrite] [--dry-run] [--verbose] [--case-insensitive]
```

Example:
```bash
python svgtranslate.py inject no_translations.svg --mapping arabic.svg.json --verbose
```

You can specify multiple mapping files:
```bash
python svgtranslate.py inject no_translations.svg --mapping arabic.svg.json --mapping french.svg.json
```

### Command Line Options

#### Global Options

- `--verbose`, `-v`: Enable verbose logging
- `--case-insensitive`: Normalize case when matching strings

#### Extract Command

- `svg_file`: Path to the SVG file to extract translations from
- `--output`, `-o`: Output JSON file path (defaults to `<svg_file>.svg.json`)

#### Inject Command

- `svg_files`: One or more SVG files to inject translations into
- `--mapping`, `-m`: JSON mapping file (can be specified multiple times)
- `--output-dir`, `-d`: Output directory for modified SVG files (defaults to same directory as input)
- `--overwrite`: Overwrite existing translations
- `--dry-run`: Report changes without writing files

## Data Model

The translation data is stored in JSON format with the following structure:

```json
{
  "english source string (trimmed)": {
    "ar": "Arabic text",
    "fr": "French text",
    ...
  }
}
```

## Example

### Input SVG (arabic.svg)

```xml
<switch style="font-size:30px;font-family:Bitstream Vera Sans">
    <text x="259.34814" y="927.29651" style="font-size:30px;font-family:Bitstream Vera Sans"
        id="text2213-ar"
        xml:space="preserve" systemLanguage="ar">
        <tspan x="259.34814" y="927.29651" id="tspan2215-ar">لكنها موصولة بمرحلتين متعاكستين.</tspan>
    </text>
    <text x="259.34814" y="927.29651" style="font-size:30px;font-family:Bitstream Vera Sans"
        id="text2213"
        xml:space="preserve">
        <tspan x="259.34814" y="927.29651" id="tspan2215">but are connected in anti-phase</tspan>
    </text>
</switch>
```

### Extracted JSON (arabic.svg.json)

```json
{
  "but are connected in anti-phase": {
    "ar": "لكنها موصولة بمرحلتين متعاكستين."
  }
}
```

### Output SVG after Injection

```xml
<switch style="font-size:30px;font-family:Bitstream Vera Sans">
    <text x="259.34814" y="927.29651" style="font-size:30px;font-family:Bitstream Vera Sans"
        id="text2213-ar"
        xml:space="preserve" systemLanguage="ar">
        <tspan x="259.34814" y="927.29651" id="tspan2215-ar">لكنها موصولة بمرحلتين متعاكستين.</tspan>
    </text>
    <text x="259.34814" y="927.29651" style="font-size:30px;font-family:Bitstream Vera Sans"
        id="text2213"
        xml:space="preserve">
        <tspan x="259.34814" y="927.29651" id="tspan2215">but are connected in anti-phase</tspan>
    </text>
</switch>
```

## Testing

Run the unit tests:

```bash
python -m pytest test_svgtranslate.py -v
```

## Implementation Details

### Text Normalization

The tool normalizes text by:
- Trimming leading and trailing whitespace
- Replacing multiple internal whitespace characters with a single space
- Optionally converting to lowercase for case-insensitive matching

### ID Generation

When adding new translation nodes, the tool generates unique IDs by:
- Taking the existing ID and appending the language code (e.g., `text2213` becomes `text2213-ar`)
- If the generated ID already exists, appending a numeric suffix until unique (e.g., `text2213-ar-1`)

## Error Handling

The tool includes comprehensive error handling for:
- Missing input files
- Invalid XML structure
- Missing required attributes
- File permission issues
