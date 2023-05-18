from enum import Enum
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, Extra

PYDANTIC_MODEL_CONFIG = {"extra": Extra.forbid, "allow_mutation": False}


class Cardinality(Enum):
    ZERO_OR_ONE = "zero_or_one"
    ONE = "one"
    ZERO_OR_MORE = "zero_or_more"
    ONE_OR_MORE = "one_or_more"

    def as_mermaid_source_str(self) -> str:
        return {
            Cardinality.ZERO_OR_ONE: "|o",
            Cardinality.ONE: "||",
            Cardinality.ZERO_OR_MORE: "}o",
            Cardinality.ONE_OR_MORE: "}|",
        }[self]

    def as_mermaid_target_str(self) -> str:
        return {
            Cardinality.ZERO_OR_ONE: "o|",
            Cardinality.ONE: "||",
            Cardinality.ZERO_OR_MORE: "o{",
            Cardinality.ONE_OR_MORE: "|{",
        }[self]


class MetaERDConnection(BaseModel, **PYDANTIC_MODEL_CONFIG):
    target: str
    source_cardinality: Cardinality
    target_cardinality: Cardinality
    diagram: str = "default"
    label: Optional[str] = None


class MetaERDSection(BaseModel, **PYDANTIC_MODEL_CONFIG):
    connections: List[MetaERDConnection] = Field(default_factory=list)


class Column(BaseModel, **PYDANTIC_MODEL_CONFIG):
    name: str
    type: Optional[str]

    def as_mermaid_column(self) -> str:
        type_str = f"{self.as_mermaid_type()} " if self.type else "UNKNOWN "
        return f"\t{type_str}{self.as_mermaid_name()}"

    def as_mermaid_name(self) -> str:
        # Incoming name string may contain dots in case of nested columns.
        # Example: col_a.nested_a.nested_nested_a.
        # This is not allowed by Mermaid syntax so replace and make
        # col_a[nested_a[nested_nested_a]]
        splitted = self.name.split(".")
        return "".join([f"{x}[" for x in splitted[:-1]]) + splitted[-1] + (len(splitted) - 1) * "]"

    def as_mermaid_type(self) -> Optional[str]:
        if self.type:
            # Type string can come in like
            # STRUCT<a INT64, b NUMERIC> or
            # ARRAY<STRUCT<a INT64, b NUMERIC>>
            # We need to remove the content of the struct type
            # because it's not allowed by Mermaid syntax.
            cleaned_struct_type = re.sub("(.*STRUCT<)(.*?)(>.*)", r"\1\3", self.type)
            return cleaned_struct_type.replace("<", "[").replace(">", "]")
        else:
            return self.type

    @classmethod
    def from_manifest_catalog_node_columns(
        cls, manifest_node_col: Optional[Dict[str, Any]], catalog_node_col: Optional[Dict[str, Any]]
    ) -> "Column":
        if not manifest_node_col and not catalog_node_col:
            raise ValueError("Both manifest and catalog column definitions are empty.")

        col_name = (
            catalog_node_col.get("name")
            if catalog_node_col
            else manifest_node_col.get("name")  # type: ignore [union-attr]
        )

        col_type = (
            catalog_node_col.get("type")
            if catalog_node_col
            else manifest_node_col.get("data_type")  # type: ignore [union-attr]
        )

        return cls(name=col_name, type=col_type)  # type: ignore [arg-type]


class Table(BaseModel, **PYDANTIC_MODEL_CONFIG):
    model_name: str
    rendered_name: str
    target_database: str
    target_schema: str
    columns: List[Column]

    def as_mermaid_table(self, include_cols=False) -> str:
        if include_cols:
            cols = "\n\t".join([c.as_mermaid_column() for c in self.columns])
            return f"{self.rendered_name}" + " {\n" + f"\t{cols}" + "\n\t}"
        else:
            return self.rendered_name

    @classmethod
    def from_manifest_catalog_nodes(
        cls, manifest_node: Dict[str, Any], catalog_node: Optional[Dict[str, Any]] = None
    ) -> "Table":
        catalog_node_cols = catalog_node.get("columns", {}) if catalog_node else {}
        manifest_node_cols = manifest_node.get("columns", {})
        # TODO: log undocumented cols
        # missing_manifest_col_ids = set(catalog_node_cols.keys()) - set(manifest_node_cols.keys())
        all_col_ids = set(catalog_node_cols.keys()) | set(manifest_node_cols.keys())

        return cls(
            model_name=manifest_node["name"],
            rendered_name=manifest_node["alias"],
            target_database=manifest_node["database"],
            target_schema=manifest_node["schema"],
            # Sort columns alphabetically
            columns=sorted(
                [
                    Column.from_manifest_catalog_node_columns(
                        manifest_node_cols.get(col_id), catalog_node_cols.get(col_id)
                    )
                    for col_id in all_col_ids
                ],
                key=lambda x: x.name,
            ),
        )


class Relation(BaseModel, **PYDANTIC_MODEL_CONFIG):
    diagram: str
    source: Table
    target: Table
    source_cardinality: Cardinality
    target_cardinality: Cardinality
    label: Optional[str]

    def as_mermaid_relation(self) -> str:
        base = (
            f"{self.source.model_name} "
            f"{self.source_cardinality.as_mermaid_source_str()}--"
            f"{self.target_cardinality.as_mermaid_target_str()} "
            f"{self.target.model_name}"
        )
        if self.label:
            return base + f' : "{self.label}"'
        else:
            return base + ' : ""'

    @classmethod
    def from_manifest_node(cls, manifest_node: dict, tables: Dict[str, Table]) -> List["Relation"]:
        try:
            source_model_name = manifest_node["name"]
            source = tables[source_model_name]
            erd_definition = MetaERDSection(**manifest_node["meta"].get("erd", {}))
        except KeyError:
            raise Exception(f"Source table {source_model_name} has not been parsed correctly.")

        output = []
        for conn in erd_definition.connections:
            try:
                target = tables[conn.target]
            except KeyError:
                raise ValueError(
                    f"Target {conn.target} in relation originating from table "
                    f"{source_model_name} does not exist or has not been loaded."
                )

            output.append(
                Relation(
                    diagram=conn.diagram,
                    source=source,
                    target=target,
                    source_cardinality=conn.source_cardinality,
                    target_cardinality=conn.target_cardinality,
                    label=conn.label,
                )
            )

        return output
