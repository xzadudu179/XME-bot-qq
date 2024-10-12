"""
Demonstrates how to display a tree of files / directories with the Tree renderable.
"""

import os
import pathlib
import sys

from rich import print
from rich.filesize import decimal
from rich.markup import escape
from rich.text import Text
from rich.tree import Tree
import json

with open("./icon_dict.json", encoding="utf-8") as file:
    ICON_DICT = json.load(file)


def walk_directory(directory: pathlib.Path, tree: Tree) -> None:
    """Recursively build a Tree with directory contents."""
    # Sort dirs first then by filename
    paths = sorted(
        pathlib.Path(directory).iterdir(),
        key=lambda path: (path.is_file(), path.name.lower()),
    )
    for path in paths:
        # Remove hidden files
        if path.name.startswith("."):
            continue
        if path.is_dir():
            style = "dim" if path.name.startswith("__") else ""
            branch = tree.add(
                f"[bold magenta]:open_file_folder: [link file://{path}]{escape(path.name)}",
                style=style,
                guide_style=style,
            )
            walk_directory(path, branch)
        else:
            text_filename = Text(path.name, "cyan")
            text_filename.highlight_regex(r"\.[^.]*$", "green")
            text_filename.stylize(f"link file://{path}")
            file_size = path.stat().st_size
            text_filename.append(f" ({decimal(file_size)})", "blue")
            icon = ICON_DICT.get(path.suffix, "📄") + " "
            tree.add(Text(icon) + text_filename)



def get_tree(path) -> str:
    """获取文件夹树

    Args:
        path (str): 根节点路径

    Returns:
        str: 文件夹树字符串
    """
    try:
        directory = path
    except IndexError:
        print("[b]Usage:[/] python tree.py <DIRECTORY>")
    else:
        tree = Tree(
            f":open_file_folder: [link file://{directory}]{directory}",
            guide_style="bright_yellow",
            style="bold yellow"
        )
        walk_directory(pathlib.Path(directory), tree)
        return str(tree)