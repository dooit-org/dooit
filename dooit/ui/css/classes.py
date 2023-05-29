"""
CSS file for property `class`
"""

from . import conf

LIT = conf.get("BORDER_LIT")

classes = f"""
.dim {{
    opacity: 70%;
}}

.highlight {{
    text-style: bold;
}}

.editing{{
    text-style: bold;
}}

.focus {{
    border: #88c;
}}

.no-border {{
    border: none;
}}

.sort-hide {{
    display: none;
}}

.hide {{
    display: none;
}}

.padding {{
    padding-right: 1;
}}
"""