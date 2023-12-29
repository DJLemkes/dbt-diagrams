import asyncio
from functools import wraps
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback
import click
import yaml
from dbt_diagrams.input_validators import DbtArtifactType, verify_and_read
from dbt_diagrams import __version__

from dbt_diagrams.mermaid import (
    add_mermaid_lib_to_html,
    to_mermaid_erds_from_dbt_target_dir,
    to_mermaid_erds_from_file,
    update_docs_with_rendered_mermaid_erds,
)
from dbt_diagrams.output_writers import write_as_markdown, write_as_mmd, write_as_svg


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def exit_with_error(msg: str):
    click.secho(msg, fg="red")
    sys.exit(1)


@click.group
@click.option("--debug", "-d", is_flag=True)
@click.version_option(version=__version__)
@click.pass_context
def cli(ctx, debug):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if __name__ == "main"` block below)
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug


@cli.command()
@coro
@click.pass_context
@click.option(
    "--dbt-target-dir",
    "-dbt-td",
    required=False,
    help="Directory containing dbt manifest and optional catalog file(s).",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
)
@click.option(
    "--manifest",
    "-m",
    required=False,
    help="Path to manifest.json file.",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.option(
    "--catalog",
    "-c",
    required=False,
    help="Optional path to catalog.json file.",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.option(
    "--format",
    "-f",
    required=False,
    help="Output format.",
    type=click.Choice(["md", "mmd", "svg"], case_sensitive=False),
)
@click.option(
    "--output-dir",
    "-o",
    required=False,
    help="Output directory.",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    default=Path(),
)
async def render_erds(ctx, dbt_target_dir, manifest, catalog, format, output_dir):
    """
    Generate a Mermaid based ERD from your dbt artifacts that have been annotated
    with the right metadata. Check the code repository README for further instructions
    on metadata config.
    """
    if dbt_target_dir and (manifest or catalog):
        exit_with_error("Either define target dir or manifest but not both.")
    elif not dbt_target_dir and not (manifest or catalog):
        exit_with_error("One of manifest file or target dir has to be specified")
    elif catalog and not manifest:
        exit_with_error(
            "Only catalog provided. Manifest file should be provided at a minimum."
        )
    elif manifest and not catalog:
        click.secho(
            "No catalog file specified. ERD won't have column type annotations.",
            fg="yellow",
        )

    try:
        if manifest:
            diagrams = to_mermaid_erds_from_file(
                Path(manifest), Path(catalog) if catalog else None
            )
        elif dbt_target_dir:
            diagrams = to_mermaid_erds_from_dbt_target_dir(Path(dbt_target_dir))
        else:
            exit_with_error("Neither manifest nor dbt target dir provided.")
    except Exception as e:
        if ctx.obj["debug"]:
            traceback.print_exc()
        exit_with_error(e)

    if format == "md":
        write_as_markdown(diagrams, output_dir)
    elif format == "svg":
        await write_as_svg(diagrams, output_dir)
    else:
        write_as_mmd(diagrams, output_dir)

    click.secho(f"Finished. Output written to {output_dir.cwd()}.", fg="green")


# Disable REST API for now because of multi-ERD support that needs to be built-in.

# @cli.command()
# @click.pass_context
# @click.option("--host", "-h", required=False, type=str, default="0.0.0.0")
# @click.option("--port", "-p", required=False, type=int, default=8000)
# def rest_api(ctx, host, port):
#     """
#     Start REST API that exposes dbt erd generation functionality by uploading dbt artifacts.
#     Visit the `/docs` endpoint for usage instructions.

#     Check the code repository README for further instructions
#     on metadata config.
#     """
#     click.echo("Starting REST API")
#     import uvicorn
#     from dbt_diagrams.rest_api import app

#     uvicorn.run(
#         app, host=host, port=port, workers=1, log_level="debug" if ctx.obj["debug"] else "info"
#     )


@cli.group()
@click.pass_context
def docs(ctx):
    """Wrapping the dbt docs command and adding dbt-diagrams features in the process"""


@docs.command(
    context_settings=dict(
        ignore_unknown_options=True,
    )
)
@click.pass_context
@click.option(
    "--include-columns",
    "--ic",
    required=False,
    help="Include column details in ERD tables.",
    type=bool,
    default=True,
)
@click.argument("docs_args", nargs=-1, type=click.UNPROCESSED)
def generate(ctx, include_columns, docs_args):
    list_docs_args = list(docs_args)
    cli_target_path = next(
        iter(
            [
                p for idx, p in enumerate(list_docs_args)
                if list_docs_args[max(0, idx - 1)] == "--target-path"
                and p != "--target-path"
            ]
        ),
        None,
    )
    env_target_path = os.environ.get("DBT_TARGET_PATH")
    static_docs_page = "--static" in list_docs_args

    # Make sure to strip out --static from the list of args passed to dbt docs generate.
    # We manually mimic the behaviour below. If we let dbt take its normal code path, we
    # can't update the manifest.json with rendered diagrams in time.
    subprocess.run(
        " ".join(["dbt", "docs", "generate"] + [arg for arg in list_docs_args if arg != "--static"]), shell=True, check=True
    )
    click.echo("Finished generating dbt docs. Rendering ERD's and adding Mermaid...")

    with open("./dbt_project.yml", "r") as dbt_project_file:
        dbt_project_target_path = yaml.safe_load(dbt_project_file.read()).get(
            "target-path"
        )

    target_dir = Path(
        next(
            td
            # Precendence as documented at https://docs.getdbt.com/reference/project-configs/target-path
            for td in [
                cli_target_path,
                env_target_path,
                dbt_project_target_path,
                "./target",
            ]
            if td is not None
        )
    )

    try:
        rendered_erds = to_mermaid_erds_from_dbt_target_dir(target_dir, include_columns)
        manifest = verify_and_read(target_dir / "manifest.json", DbtArtifactType.MANIFEST)
        update_docs_with_rendered_mermaid_erds(manifest, rendered_erds)

        with open(target_dir / "manifest.json", "w") as w_manifest:
            json.dump(manifest, w_manifest)

        add_mermaid_lib_to_html(target_dir)

        # Mimic the behaviour of dbt docs generate --static.
        if static_docs_page:
            manifest = verify_and_read(target_dir / "manifest.json", DbtArtifactType.MANIFEST)
            catalog = verify_and_read(target_dir / "catalog.json", DbtArtifactType.CATALOG)
            
            # This setup comes straight from
            # https://github.com/mescanne/dbt-core/blob/e8c8eb2b7fc64e0db2817de0b538780d56c7fd99/core/dbt/task/generate.py#L280
            with open(target_dir / "index.html", "r") as index_html_handle:
                index_html = index_html_handle.read()
            
            index_html = index_html.replace('"MANIFEST.JSON INLINE DATA"', json.dumps(manifest))
            index_html = index_html.replace('"CATALOG.JSON INLINE DATA"', json.dumps(catalog))
            
            with open(target_dir / "static_index.html", "w") as s_index_html_handle:
                s_index_html_handle.write(index_html)


        click.secho("All done.", fg="green")
    except Exception as e:
        if ctx.obj["debug"]:
            traceback.print_exc()
        exit_with_error(e)


if __name__ == "__main__":
    cli()
