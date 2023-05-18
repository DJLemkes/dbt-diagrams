from datetime import datetime
import itertools
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from dbt_diagrams.domain import Relation, Table


from dbt_diagrams.input_validators import (
    DbtArtifactType,
    extract_invocation_id,
    verify_and_read,
)


def _add_generation_header(diagram_name, diagram: str) -> str:
    return f"""
    %% generated_at: {datetime.now().isoformat()}
    %% name: {diagram_name}
    {diagram}
    """


def _mermaid_erd_from_relations(relations: List[Relation], include_cols: bool = True) -> str:
    mentioned_tables = {
        t.model_name: t for t in itertools.chain(*([r.source, r.target] for r in relations))
    }
    tables_section = "\n".join(
        (f"\t{t.as_mermaid_table(include_cols)}\n" for t in mentioned_tables.values())
    )

    relation_section = ""
    for rel in relations:
        relation_section += f"\t{rel.as_mermaid_relation()}\n"

    return f"erDiagram\n{relation_section}\n{tables_section}"


def mermaid_erds_from_manifest_and_catalog(
    manifest: Dict[str, Any], catalog: Optional[Dict[str, Any]], include_cols: bool = True
) -> Dict[str, str]:
    catalog_nodes = catalog["nodes"] if catalog else {}

    # TODO can be optimized by not parsing all tables but just the ones we need from the
    # relations that reference them. Not a real important optimisation though.
    tables = {
        t.model_name: t
        for t in (
            Table.from_manifest_catalog_nodes(node, catalog_nodes.get(node_id))
            for node_id, node in manifest["nodes"].items()
        )
    }
    relations = list(
        itertools.chain(
            *(Relation.from_manifest_node(n, tables) for n in manifest["nodes"].values())
        )
    )

    relations_by_diagram = itertools.groupby(relations, key=lambda r: r.diagram)

    return {
        diagram_name: _add_generation_header(
            diagram_name, _mermaid_erd_from_relations(list(relations), include_cols)
        )
        for diagram_name, relations in relations_by_diagram
    }


def update_docs_with_rendered_mermaid_erds(manifest: Dict[str, Any], rendered_erds: Dict[str, str]):
    """
    In all table and overview doc pages, insert a rendered mermaid ERD in any
    ```mermaid[erd='my_erd']``` location that refers to one of the rendered ERD's.

    TODO: this currently mutates the provided manifest in place. Pretty ugly but
    more efficient as the manifest files can get pretty big (20+ MBs).
    """
    erd_diagram_regex = re.compile("\[.*[,erd|erd]=[\"|']([^\"']*)[\"|'].*\].*```")

    def insert_rendered_erds_in_doc_blocks_as_mermaid(doc_block: str) -> str:
        """
        Strings arriving here can be any text that may contain ```mermaid```
        Markdown code blocks that our potential candidates.
        """
        mermaid_splitter = "```mermaid["
        if len(splitted := doc_block.split(mermaid_splitter)) > 1:
            # Split on ```mermaid so that every element in splitted is a potential
            # ERD candiate containing a "[erd="foo"]```" like string.
            included_erds = [
                x
                if (erd_name := erd_diagram_regex.match(f"[{x}")) is None
                else f"```mermaid\n{rendered_erds.get(erd_name.group(1), '')}\n```"
                for x in splitted
            ]

            return "".join(included_erds)
        else:
            return doc_block

    for k, v in manifest["nodes"].items():
        manifest["nodes"][k]["description"] = insert_rendered_erds_in_doc_blocks_as_mermaid(
            v["description"]
        )

    for k, v in manifest["docs"].items():
        manifest["docs"][k]["block_contents"] = insert_rendered_erds_in_doc_blocks_as_mermaid(
            v["block_contents"]
        )


def to_mermaid_erds_from_file(
    manifest_path: Path, catalog_path: Optional[Path], include_cols: bool = True
) -> Dict[str, str]:
    """
    Render all ERD inside manifest meta statements and return a dict with
    ERD name as key and Mermaid definition as value. Use catalog to add column info.
    """
    manifest = verify_and_read(manifest_path, DbtArtifactType.MANIFEST)
    catalog = None if not catalog_path else verify_and_read(catalog_path, DbtArtifactType.CATALOG)

    if manifest and catalog and (extract_invocation_id(manifest) == extract_invocation_id(catalog)):
        return mermaid_erds_from_manifest_and_catalog(manifest, catalog, include_cols)
    elif manifest and catalog:
        raise Exception("Provided manifest and catalog have different invocation id's.")
    elif manifest:
        return mermaid_erds_from_manifest_and_catalog(manifest, None, include_cols)
    elif not manifest:
        raise Exception("Provided manifest is not supported")
    else:
        raise Exception("Internal error.")


def to_mermaid_erds_from_dbt_target_dir(
    input_dir: Path, include_cols: bool = True
) -> Dict[str, str]:
    """
    Same as `to_mermaid_erd_from_file` but takes dbt target dir and tries
    to discover manifest and catalog by itself.
    """
    manifest_path = input_dir / "manifest.json"
    catalog_path = input_dir / "catalog.json"
    if manifest_path.exists() and catalog_path.exists():
        return to_mermaid_erds_from_file(manifest_path, catalog_path, include_cols)
    elif manifest_path.exists():
        return to_mermaid_erds_from_file(manifest_path, None, include_cols)
    else:
        raise ValueError(f"{manifest_path} doesn't exists and is required as a minimum.")


def add_mermaid_lib_to_html(target_dir: Path):
    source_index_path = f"{target_dir}/index.html"
    target_index_path = f"{target_dir}/new_index.html"

    with open(source_index_path, "r") as index_html, open(
        target_index_path, "w"
    ) as new_index_html, open(
        Path(__file__).parent / "resources" / "mermaid_snippet.html", "r"
    ) as mermaid_snippet_f:
        mermaid_snippet = mermaid_snippet_f.read()
        new_index_html.seek(0)

        for line in index_html:
            if "</body>" in line:
                new_index_html.write(line.replace("</body>", f"{mermaid_snippet}</body>"))
            else:
                new_index_html.write(line)

    os.remove(source_index_path)
    os.rename(target_index_path, source_index_path)
