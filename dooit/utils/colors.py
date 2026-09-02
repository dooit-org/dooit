def blend(color: str, other: str, factor: float) -> str:
    """
    Mix `color` towards `other`: factor 0 keeps it, factor 1 returns `other`.

    Both colors are hex strings of the `#rrggbb` shape the themes are written in.
    """

    src = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    dest = [int(other[i : i + 2], 16) for i in (1, 3, 5)]

    return "#" + "".join(
        f"{round(a + (b - a) * factor):02x}" for a, b in zip(src, dest)
    )
