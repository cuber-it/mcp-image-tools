"""The tools as a catalogue a server can publish.

:func:`catalogue` binds every tool to one shared workspace and returns them by
the name they are published under. It knows no server and imports no SDK:
whatever publishes the catalogue, the MCP SDK in :mod:`.app` or a server
library of our own, takes it from here.

A tool that shows a picture returns a :class:`~mcp_image_tools.pictures.Picture`;
the publisher turns it into what its protocol calls an image. **The docstring of
a wrapper is the description that lands in the client's catalogue.** Each has
an English paragraph, a German one, and a closing line of German search words.

Names carry no prefix. Putting one in front is the publisher's business.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from mcp_image_tools import pictures
from mcp_image_tools.pictures import Picture
from mcp_image_tools.workspace import Workspace

Tool = Callable[..., Any]
Catalogue = dict[str, Tool]


def catalogue(space: Workspace) -> Catalogue:
    """Return every tool bound to the workspace, by its published name."""

    def read(path: str, max_edge: int = 0) -> Picture:
        """Show a picture: open an image file and return it as a picture.

        Use this to look at a screenshot, photo, diagram, chart, scan or
        rendering. Formats are whatever Pillow reads, among them PNG, JPEG,
        WebP, GIF, BMP and TIFF. The longest edge is limited to 1024 pixels
        unless the server is set to another limit, and a larger picture is
        scaled down to fit. Pass max_edge to raise or lower that; 0 uses the
        limit. The aspect ratio is kept and the file is not changed.

        Zeigt ein Bild: öffnet eine Bilddatei und gibt sie als Bild zurück.
        Für Screenshots, Fotos, Diagramme, Scans oder Renderings; lesbar ist,
        was Pillow liest, darunter PNG, JPEG, WebP, GIF, BMP und TIFF. Die
        längste Kante ist auf 1024 Pixel begrenzt, sofern der Server keine
        andere Grenze hat, und ein größeres Bild wird verkleinert. max_edge
        hebt oder senkt die Grenze; 0 nimmt sie. Das Seitenverhältnis bleibt,
        die Datei wird nicht verändert.

        Stichworte: Bild ansehen, anzeigen, öffnen, Foto, Screenshot, Diagramm.
        """
        return pictures.read(space, path, max_edge)

    def facts(path: str) -> dict[str, str | int | bool]:
        """Describe a picture without showing it: format, size, colour, bytes.

        Returns format, width and height in pixels, colour mode, whether it
        has transparency, and the size of the file. Cheaper than reading it.

        Beschreibt ein Bild, ohne es zu zeigen: Format, Breite und Höhe in
        Pixeln, Farbmodus, Transparenz und Dateigröße. Günstiger als es zu
        lesen.

        Stichworte: Bildinfo, Metadaten, Auflösung, Abmessungen, Format, Größe.
        """
        return asdict(pictures.facts(space, path))

    def resize(path: str, max_edge: int) -> Picture:
        """Scale a picture down and return it: shrink, resize, thumbnail.

        The longest edge becomes max_edge pixels, the aspect ratio is kept, a
        smaller picture is not enlarged, and the file is not changed.

        Verkleinert ein Bild und gibt es zurück. Die längste Kante wird
        max_edge Pixel lang, das Seitenverhältnis bleibt, ein kleineres Bild
        wird nicht vergrößert, die Datei wird nicht verändert.

        Stichworte: Bild verkleinern, skalieren, Vorschaubild, Thumbnail.
        """
        return pictures.resize(space, path, max_edge)

    def convert(path: str, target: str, into: str = "", max_edge: int = 0) -> str:
        """Convert a picture to another format: PNG, JPEG, WebP, GIF, BMP.

        Writes the result to into, or beside the original with the new format
        as suffix when into is empty. Transparency is laid on white where the
        format cannot carry it. Pass max_edge to scale while converting; 0
        keeps the size.

        Wandelt ein Bild in ein anderes Format um und schreibt es nach into,
        oder neben das Original mit dem neuen Format als Endung, wenn into
        leer ist. Transparenz wird auf Weiß gelegt, wo das Format sie nicht
        tragen kann. max_edge skaliert dabei; 0 behält die Größe.

        Stichworte: Bild umwandeln, konvertieren, Format ändern, als JPEG.
        """
        return (
            f"wrote {pictures.convert(space, path, target, into, max_edge).describe()}"
        )

    def write(path: str, data: str) -> str:
        """Write a picture from base64 data to a file: save, store an image.

        The data is the encoded picture itself, base64 as in an image content
        block. Missing directories are created. Data that is not a picture is
        refused before anything is written.

        Schreibt ein Bild aus base64-Daten in eine Datei. Die Daten sind das
        kodierte Bild selbst, wie in einem Bild-Inhaltsblock. Fehlende
        Verzeichnisse werden angelegt; Daten, die kein Bild sind, werden
        abgelehnt, bevor etwas geschrieben wird.

        Stichworte: Bild schreiben, speichern, ablegen, Datei anlegen.
        """
        return f"wrote {pictures.write(space, path, data).describe()}"

    return {tool.__name__: tool for tool in (read, facts, resize, convert, write)}
