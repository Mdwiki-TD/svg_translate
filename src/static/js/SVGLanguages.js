
const API_AGENT = "Copy SVG Translations/1.0 (https://copy-svg-langs.toolforge.org; tools.copy-svg-langs@toolforge.org)";

class Api {
    async get(params) {
        // const end_point = 'https://commons.wikimedia.org/w/api.php';
        const end_point = 'https://ar.wikipedia.org/w/api.php';
        const url = new URL(end_point);
        for (const [key, value] of Object.entries(params)) {
            url.searchParams.append(key, value);
        }
        url.searchParams.append('origin', '*'); // required for CORS in browser

        const res = await fetch(url, {
            headers: {
                'Api-User-Agent': API_AGENT
            }
        });
        if (!res.ok) {
            throw new Error(`HTTP error ${res.status}`);
        }
        return res.json();
    }
}

async function getFileTranslations(fileName) {
    // return object { error, langs }
    if (!fileName) return { error: 'Empty fileName', langs: null };

    const normalizedName = fileName.replace(/^File:/i, '').trim();
    const api = new Api();
    let data;
    try {
        data = await api.get({
            action: 'query',
            titles: `File:${normalizedName}`,
            prop: 'imageinfo',
            iiprop: 'metadata',
            formatversion: "latest",
            format: 'json'
        });

    } catch (err) {
        console.error('Api error:', err);
        return { error: 'API error', langs: null };
    }

    const pages = data && data.query && data.query.pages;
    if (!pages) return { error: 'Unexpected API response', langs: null };

    // pages is an object keyed by pageid; pick the first value
    const page = Array.isArray(pages) ? pages[0] : Object.values(pages)[0];

    if (!page) return { error: 'Page not found in API response', langs: null };

    // If the file does not exist locally or on Commons
    if (page.missing && !page.known) {
        return { error: `File ${page.title} does not exist.`, langs: null };
    }

    // If the file exists on Commons (shared repository)
    console.log(`ℹ️ File ${page.title} exists on Wikimedia Commons.`);

    const metadata = page.imageinfo && page.imageinfo[0] && page.imageinfo[0].metadata;

    // [ { "name": "version", "value": 2 }, { "name": "width", "value": 512 },
    if (!metadata) {
        return { error: `Metadata not found for ${page.title}`, langs: null };
    }

    // change list of name, value to {name:value}
    const meta = Object.fromEntries(metadata.map(m => [m.name, m.value]));

    const translations = meta["translations"];

    if (translations && translations.length) {
        // [{"name":"ca","value":2},{"name":"hr","value":2},{"name":"es","value":2}]
        const langs_keys = translations.map(t => t.name);
        return { error: null, langs: langs_keys || ["en"] };
    }

    return { error: null, langs: ["en"] };
}

// Main per-item worker. Accepts jQuery-wrapped element
async function oneFile(item) {
    // const itemSpan = item.find("span") || item;
    const itemSpan = item;
    itemSpan.text("");
    const fileName = item.attr('data-file');

    if (!fileName || fileName === "" || fileName === "{{{1}}}") {
        itemSpan.text('Error: Could not find file name');
        return;
    }

    itemSpan.text('Loading languages');

    const { error, langs } = await getFileTranslations(fileName);
    if (!langs || langs.length === 0) {
        console.error(error);
        itemSpan.text(error || 'Error: Could not find file langs');
        return;
    }

    const result = (!langs || langs.length === 0)
        ? 'No languages found'
        : ' ' + langs.join(', ');

    itemSpan.text(result);
}

// Initialize: process all .get_languages elements concurrently but wait for all
async function initGetLanguages() {
    const divs = $('.get_languages');
    console.log('start initGetLanguages, get_languages divs: ', divs.length);

    if (!divs.length) return;

    // convert to array of promises and run them concurrently
    const promises = divs.toArray().map(el => oneFile($(el)));
    await Promise.allSettled(promises);
}

// Document ready and load MediaWiki modules, then init
$(document).ready(function () {
    initGetLanguages();
});
