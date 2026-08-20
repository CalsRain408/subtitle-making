import tempfile
from pathlib import Path
from typing import Annotated

import typer

from subtitle_maker.bootstrap import build_pipeline, build_translator
from subtitle_maker.config import Settings
from subtitle_maker.subtitles.srt import SrtReader, SrtWriter

app = typer.Typer(help="Generate bilingual English-Chinese subtitles from a video.")


@app.callback()
def main() -> None:
    """Subtitle Maker command line interface."""


@app.command("create")
def create_subtitles(
    video: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Create a bilingual SRT file for VIDEO."""
    destination = output or video.with_name(f"{video.stem}.bilingual.srt")
    try:
        pipeline = build_pipeline(Settings())
        with tempfile.TemporaryDirectory(prefix="subtitle-maker-") as temp_dir:
            result = pipeline.process(video.resolve(), destination.resolve(), Path(temp_dir))
    except Exception as exc:
        typer.secho(f"Failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho(
        f"Created {result.output_path} ({result.segment_count} subtitle segments)",
        fg=typer.colors.GREEN,
    )


@app.command("translate")
def translate_subtitles(
    subtitles: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
) -> None:
    """Translate an existing English SRT file into a bilingual SRT file."""
    destination = output or subtitles.with_name(f"{subtitles.stem}.bilingual.srt")
    try:
        segments = SrtReader().read(subtitles.resolve())
        if not segments:
            raise ValueError("The input SRT file contains no subtitle segments")
        translated = build_translator(Settings()).translate(segments)
        SrtWriter().write(translated, destination.resolve())
    except Exception as exc:
        typer.secho(f"Failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho(
        f"Created {destination.resolve()} ({len(translated)} subtitle segments)",
        fg=typer.colors.GREEN,
    )


if __name__ == "__main__":
    app()
