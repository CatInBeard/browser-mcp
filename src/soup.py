from bs4 import BeautifulSoup

def attrs_to_pug(tag):
    parts = [tag.name]

    if tag.get("id"):
        parts.append(f"#{tag['id']}")

    classes = tag.get("class") or []
    for cls in classes:
        parts.append(f".{cls}")

    other = []
    for k, v in tag.attrs.items():
        if k in ("id", "class"):
            continue
        other.append(f"{k}='{v}'")
    if other:
        parts.append(f"({', '.join(other)})")

    return "".join(parts)


def node_to_pug(node, indent=0):
    lines = []
    prefix = "  " * indent

    if getattr(node, "name", None):
        head = attrs_to_pug(node)

        text = node.string if node.string and node.string.strip() else None
        if text:
            lines.append(f"{prefix}{head} {text.strip()}")
        else:
            lines.append(f"{prefix}{head}")

        for child in node.children:
            if getattr(child, "name", None) or (getattr(child, "string", None) and child.string.strip()):
                lines.extend(node_to_pug(child, indent + 1))

    else:
        text = str(node).strip()
        if text:
            lines.append(f"{prefix}| {text}")

    return lines


def html_to_pug(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    result_lines = []
    roots = soup.body.children if soup.body else soup.children
    for child in roots:
        if getattr(child, "name", None) or (getattr(child, "string", None) and child.string.strip()):
            result_lines.extend(node_to_pug(child, 0))

    return "\n".join(result_lines)

def links_extractor(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    lines = []

    for a in soup.find_all("a"):
        href = a.get("href")
        text = a.get_text(strip=True)

        if href and text:
            if href != "" and text != "":
                lines.append(f"{href} : {text}")

    return "\n".join(lines)
