#!/usr/bin/env python3

import json
from contextlib import contextmanager
from importlib import metadata
from pathlib import Path
from typing import Iterator, List, Literal, Union

import click

from .help import create_layout, user_guide
from .layout import KeyboardLayout, load_layout
from .server import keyboard_server


@click.group()
def cli() -> None: ...


def pretty_json(layout: KeyboardLayout, output_path: Path) -> None:
    """Pretty-print the JSON layout.

    Parameters
    ----------
    layout : KeyboardLayout
        The layout to be exported.
    output_path : Path
        The output file path.
    """
    text = (
        json.dumps(layout.json, indent=2, ensure_ascii=False)
        .replace("\n      ", " ")
        .replace("\n    ]", " ]")
        .replace("\n    }", " }")
    )
    output_path.write_text(text, encoding="utf8")


def make_all(layout: KeyboardLayout, output_dir_path: Path) -> None:
    """Generate all layout output files.

    Parameters
    ----------
    layout : KeyboardLayout
        The layout to process.
    output_dir_path : Path
        The output directory.
    """

    @contextmanager
    def file_creation_context(ext: str = "") -> Iterator[Path]:
        """Generate an output file path for extension EXT, return it and finally echo info."""
        path = output_dir_path / (layout.meta["fileName"] + ext)
        yield path
        click.echo(f"... {path}")

    if not output_dir_path.exists():
        output_dir_path.mkdir(parents=True)

    # AHK driver
    with file_creation_context(".ahk") as ahk_path:
        with ahk_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write("\uFEFF")  # AHK scripts require a BOM
            file.write(layout.ahk)

    # Windows driver
    with file_creation_context(".klc") as klc_path:
        with klc_path.open("w", encoding="utf-16le", newline="\r\n") as file:
            file.write(layout.klc)

    # macOS driver
    with file_creation_context(".keylayout") as osx_path:
        with osx_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(layout.keylayout)

    # Linux driver, user-space
    with file_creation_context(".xkb") as xkb_path:
        with xkb_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(layout.xkb)

    # Linux driver, root
    with file_creation_context(".xkb_custom") as xkb_custom_path:
        with xkb_custom_path.open("w", encoding="utf-8", newline="\n") as file:
            file.write(layout.xkb_patch)

    # JSON data
    with file_creation_context(".json") as json_path:
        pretty_json(layout, json_path)

    # SVG data
    with file_creation_context(".svg") as svg_path:
        layout.svg.write(svg_path, pretty_print=True, encoding="utf-8")


@cli.command()
@click.argument(
    "layout_descriptors",
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--out",
    default="all",
    type=click.Path(),
    help="Keyboard drivers to generate.",
)
@click.option(
    "--angle-mod/--no-angle-mod",
    default=False,
    help="Apply Angle-Mod (which is a [ZXCVB] permutation with the LSGT key (a.k.a. ISO key))",
)
def make(
    layout_descriptors: List[Path], out: Union[Path, Literal["all"]], angle_mod: bool
) -> None:
    """Convert TOML/YAML descriptions into OS-specific keyboard drivers."""

    for input_file in layout_descriptors:
        layout = KeyboardLayout(load_layout(input_file), angle_mod)

        # default: build all in the `dist` subdirectory
        if out == "all":
            make_all(layout, Path("dist"))
            continue

        # quick output: reuse the input name and change the file extension
        if out in ["keylayout", "klc", "xkb", "xkb_custom", "svg"]:
            output_file = input_file.with_suffix(f".{out}")
        else:
            output_file = Path(out)

        # detailed output
        if output_file.suffix == ".ahk":
            with output_file.open("w", encoding="utf-8", newline="\n") as file:
                file.write("\uFEFF")  # AHK scripts require a BOM
                file.write(layout.ahk)

        elif output_file.suffix == ".klc":
            with output_file.open("w", encoding="utf-16le", newline="\r\n") as file:
                file.write(layout.klc)

        elif output_file.suffix == ".keylayout":
            with output_file.open("w", encoding="utf-8", newline="\n") as file:
                file.write(layout.keylayout)

        elif output_file.suffix == ".xkb":
            with output_file.open("w", encoding="utf-8", newline="\n") as file:
                file.write(layout.xkb)

        elif output_file.suffix == ".xkb_custom":
            with output_file.open("w", encoding="utf-8", newline="\n") as file:
                file.write(layout.xkb_patch)

        elif output_file.suffix == ".json":
            pretty_json(layout, output_file)

        elif output_file.suffix == ".svg":
            layout.svg.write(output_file, pretty_print=True, encoding="utf-8")

        else:
            click.echo("Unsupported output format.", err=True)
            return

        # successfully converted, display file name
        click.echo(f"... {output_file}")


# TODO: Provide geometry choices
@cli.command()
@click.argument("output_file", nargs=1, type=click.Path(exists=False, path_type=Path))
@click.option("--geometry", default="ISO", help="Specify keyboard geometry.")
@click.option("--altgr/--no-altgr", default=False, help="Set an AltGr layer.")
@click.option("--1dk/--no-1dk", "odk", default=False, help="Set a custom dead key.")
def create(output_file: Path, geometry: str, altgr: bool, odk: bool) -> None:
    """Create a new TOML layout description."""
    create_layout(output_file, geometry, altgr, odk)
    click.echo(f"... {output_file}")


@cli.command()
@click.argument("filepath", nargs=1, type=click.Path(exists=True, path_type=Path))
def watch(filepath: Path) -> None:
    """Watch a TOML/YAML layout description and display it in a web server."""
    keyboard_server(filepath)


@cli.command()
def guide() -> None:
    """Show user guide and exit."""
    click.echo(user_guide())


@cli.command()
def version() -> None:
    """Show version number and exit."""
    click.echo(f"kalamine { metadata.version('kalamine') }")


if __name__ == "__main__":
    cli()
