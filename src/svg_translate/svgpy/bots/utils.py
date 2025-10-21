#!/usr/bin/env python3
"""

from utils import normalize_text, extract_text_from_node

"""

import logging
logger = logging.getLogger(__name__)

def normalize_text(text, case_insensitive=False):
    """Normalize text by trimming whitespace and collapsing internal whitespace."""
    if not text:
        return ""
    # Trim leading/trailing whitespace
    text = text.strip()
    # Replace multiple internal whitespace with single space
    text = ' '.join(text.split())
    # ---
    if case_insensitive:
        text = text.lower()
    # ---
    return text


def extract_text_from_node(node):
    """Extract text from a text node, handling tspan elements."""
    # Try to find tspan elements first
    tspans = node.xpath('./svg:tspan', namespaces={'svg': 'http://www.w3.org/2000/svg'})
    if tspans:
        # Return a list of text from each tspan element
        return [tspan.text.strip() if tspan.text else "" for tspan in tspans]
    # Fall back to direct text content
    return [node.text.strip()] if node.text else [""]
