from dbt_diagrams.domain import Column


def test_column_type_mermaid_output():
    col = Column(name="foo", type="INT64")
    struct_col = Column(name="foo", type="STRUCT<bar INT64>")
    array_struct_col = Column(name="foo", type="ARRAY<STRUCT<bar INT64>>")

    assert col.as_mermaid_type() == "INT64"
    assert struct_col.as_mermaid_type() == "STRUCT[]"
    assert array_struct_col.as_mermaid_type() == "ARRAY[STRUCT[]]"


def test_column_name_mermaid_output():
    col = Column(name="foo", type="INT64")
    nested_col = Column(name="foo.nested.bar", type="INT64")

    assert col.as_mermaid_name() == "foo"
    assert nested_col.as_mermaid_name() == "foo[nested[bar]]"
