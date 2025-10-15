# -*- coding: utf-8 -*-
import re
import copy
from pathlib import Path
from typing import List
from lxml import etree

from ...log import logger

SVG_NS = "http://www.w3.org/2000/svg"
XMLNS_ATTR = "{http://www.w3.org/2000/xmlns/}xmlns"


class SvgStructureException(Exception):
    """Raised when SVG structure is unsuitable for translation."""

    def __init__(self, code: str, element=None, extra=None):
        self.code = code
        self.element = element
        self.extra = extra
        msg = code
        if extra:
            msg += ": " + str(extra)
        super().__init__(msg)


def normalize_lang(lang: str) -> str:
    """
    Normalize a language tag to a simple IETF-like form.
    This is a lightweight normalizer not a full BCP47 parser.
    Examples:
      'en_us' -> 'en-US'
      'EN' -> 'en'
      'pt-br' -> 'pt-BR'
    """
    if not lang:
        return lang
    pieces = re.split(r'[_\s]+', lang.strip())
    primary = pieces[0].lower()
    if len(pieces) > 1:
        rest = "-".join(p.upper() if len(p) == 2 else p.title() for p in pieces[1:])
        return f"{primary}-{rest}"
    return primary


def get_text_content(el: etree._Element) -> str:
    """Return concatenated text content of element (like DOM textContent)."""
    return "".join(el.itertext())


def clone_element(el: etree._Element) -> etree._Element:
    """Deep-clone an element."""
    return copy.deepcopy(el)


def reorder_texts(root: etree._Element):
    """
    Simple deterministic reordering: for every <switch>, sort child <text> elements
    by numeric part of their id if present, otherwise keep original order.
    'fallback' (no systemLanguage) will be placed last.
    """
    switches = root.findall(".//{%s}switch" % SVG_NS)
    for sw in switches:
        texts = [c for c in sw if isinstance(c.tag, str) and c.tag in ({f"{{{SVG_NS}}}text", "text"})]

        def sort_key(el):
            lang = el.get("systemLanguage") or "fallback"
            m = re.search(r'trsvg(\d+)', (el.get("id") or ""))
            num = int(m.group(1)) if m else 10**9
            return (0 if lang == "fallback" else 1, num, lang)
        texts_sorted = sorted(texts, key=sort_key)
        # re-append in sorted order, leaving non-text children (if any) as-is
        for t in texts_sorted:
            sw.remove(t)
        for t in texts_sorted:
            sw.append(t)


def make_translation_ready(svg_file_path: Path, write_back: bool = False) -> etree._ElementTree:
    """
    Prepare an SVG file for translation.
    If write_back is True the file will be overwritten with modifications.
    Returns the parsed ElementTree.
    """
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(svg_file_path), parser)
    root = tree.getroot()
    if root is None:
        raise SvgStructureException('structure-error-no-doc-element')

    # Ensure default namespace (xmlns) exists and is sane
    default_ns = root.nsmap.get(None)
    if default_ns is None or re.match(r'^(&[^;]+;)+$', str(default_ns)):
        root.set(XMLNS_ATTR, SVG_NS)
        default_ns = SVG_NS

    ns = {"svg": SVG_NS}

    # Check for any <text> elements
    texts = root.findall(".//{%s}text" % SVG_NS)
    if len(texts) == 0:
        logger.warning("File %s has nothing to translate", svg_file_path)
        return tree, root

    # Check <style> elements for IDs and syntactic complexity
    styles = root.findall(".//{%s}style" % SVG_NS)
    css_simple_re = re.compile(r'^([^{]+\{[^}]*\})*[^{]+$')
    for s in styles:
        css = (s.text or "")
        if '#' in css:
            if not css_simple_re.match(css):
                raise SvgStructureException('structure-error-css-too-complex', s)
            # split selectors roughly and ensure no '#' in selectors portion
            selectors = re.split(r'\{[^}]*\}', css)
            for selector in selectors:
                if '#' in selector:
                    raise SvgStructureException('structure-error-css-has-ids', s)

    # tref not supported
    trefs = root.findall(".//{%s}tref" % SVG_NS)
    if len(trefs) != 0:
        raise SvgStructureException('structure-error-contains-tref', trefs[0])

    # Collect translatable nodes and prepare idsInUse
    ids_in_use: List[int] = [0]
    translatable_nodes: List[etree._Element] = []

    # Process tspans
    tspans = root.findall(".//{%s}tspan" % SVG_NS)
    for tspan in tspans:
        # nested content check: tspan should not have element children
        element_children = [c for c in tspan if isinstance(c.tag, str)]
        if len(element_children) == 0:
            translatable_nodes.append(tspan)
        # else:
            # Nested tspans or children not supported
            raise SvgStructureException('structure-error-nested-tspans-not-supported', tspan)

    # Process text elements: wrap raw text nodes into <tspan>
    texts = root.findall(".//{%s}text" % SVG_NS)
    for text in texts:
        # handle text before first child
        if (text.text or "").strip():
            tspan = etree.Element("{%s}tspan" % SVG_NS)
            tspan.text = text.text
            text.text = None
            text.insert(0, tspan)
            translatable_nodes.append(tspan)

        # handle tails after children
        children = list(text)
        for idx, child in enumerate(children):
            if (child.tail or "").strip():
                new_tspan = etree.Element("{%s}tspan" % SVG_NS)
                new_tspan.text = child.tail
                child.tail = None
                # insert after child
                insert_index = list(text).index(child) + 1
                text.insert(insert_index, new_tspan)
                translatable_nodes.append(new_tspan)

        # accumulate the text element itself as translatable node
        translatable_nodes.append(text)

    # Clean ids and remove empty nodes
    for node in list(translatable_nodes):
        node_id = node.get("id")
        if node_id is not None:
            node_id = node_id.strip()
            node.set("id", node_id)
            if "|" in node_id or "/" in node_id:
                raise SvgStructureException('structure-error-invalid-node-id', node)
            m = re.match(r'^trsvg([0-9]+)$', node_id)
            if m:
                ids_in_use.append(int(m.group(1)))
            if node_id.isdigit():
                node.attrib.pop("id", None)
        # remove empty nodes with no children and no text
        if (not list(node)) and (not (node.text and node.text.strip())):
            parent = node.getparent()
            if parent is not None:
                parent.remove(node)
            # also remove from translatable_nodes list
            try:
                translatable_nodes.remove(node)
            except ValueError:
                pass

    # Rebuild translatable_nodes after removals
    translatable_nodes = []
    translatable_nodes.extend(root.findall(".//{%s}tspan" % SVG_NS))
    translatable_nodes.extend(root.findall(".//{%s}text" % SVG_NS))

    # Assign new ids where missing
    for node in translatable_nodes:
        if node.get("id") is None:
            new_id = max(ids_in_use) + 1
            node.set("id", f"trsvg{new_id}")
            ids_in_use.append(new_id)

    # Second pass on text elements for extra checks and switch creation
    texts = root.findall(".//{%s}text" % SVG_NS)
    for text in texts:
        content = get_text_content(text)
        if re.search(r'\$[0-9]+', content):
            raise SvgStructureException('structure-error-text-contains-dollar', text, [content])

        # normalize systemLanguage if present
        if text.get("systemLanguage"):
            text.set("systemLanguage", normalize_lang(text.get("systemLanguage")))

        parent = text.getparent()
        if parent is None or (parent.tag not in ({f"{{{SVG_NS}}}switch", "switch"})):
            # Create a switch element in the SVG namespace and move the text into it
            switch = etree.Element("{%s}switch" % SVG_NS)
            parent_of_text = parent
            if parent_of_text is None:
                raise SvgStructureException('structure-error-no-parent-for-text', text)
            # insert switch before text
            idx = list(parent_of_text).index(text)
            parent_of_text.insert(idx, switch)
            switch.append(text)

        # move style from text to switch (parent)
        if text.get("style"):
            switch_parent = text.getparent()
            if switch_parent is not None:
                switch_parent.set("style", text.get("style"))

        # verify that children of text are only tspans or text nodes
        for child in text:
            if child.tag not in ({f"{{{SVG_NS}}}tspan", "tspan"}):
                raise SvgStructureException('structure-error-non-tspan-inside-text', child)

    # Process all switches: split comma-separated systemLanguage values
    switches = root.findall(".//{%s}switch" % SVG_NS)
    for sw in switches:
        # gather existing languages for duplicate detection
        existing_langs = []
        # collect children first to avoid modifying while iterating
        children = list(sw)
        for child in children:
            if not isinstance(child.tag, str):
                # ignore comments etc, but if there's text content outside elements, check whitespace
                if (child.text or "").strip():
                    raise SvgStructureException('structure-error-switch-text-content-outside-text', child)
                continue
            if child.tag not in ({f"{{{SVG_NS}}}text", "text"}):
                raise SvgStructureException('structure-error-switch-child-not-text', child)

            text_lang = child.get("systemLanguage") or "fallback"
            if text_lang in existing_langs:
                raise SvgStructureException('structure-error-multiple-text-same-lang', sw, [text_lang])
            existing_langs.append(text_lang)

            language_attr = child.get("systemLanguage") or "fallback"
            real_langs = re.split(r',\s*', language_attr)
            languages_present = []
            for real in real_langs:
                if real in languages_present:
                    raise SvgStructureException('structure-error-multiple-lang-in-text', child, [real])
                languages_present.append(real)

            if len(real_langs) == 1:
                continue

            # For multiple languages in one node, clone for each language and append
            for real in real_langs:
                cloned = clone_element(child)
                cloned.set("systemLanguage", real)
                sw.append(cloned)
            # remove the original multi-language node
            sw.remove(child)

    # Final reorder
    reorder_texts(root)

    # Optionally write back to file
    if write_back:
        tree.write(str(svg_file_path), pretty_print=True, xml_declaration=True, encoding="utf-8")

    return tree, root
