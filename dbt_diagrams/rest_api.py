from playwright.async_api import Browser

rest_api_browser: Browser | None = None


# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     global rest_api_browser
#     async with get_browser() as _browser:
#         rest_api_browser = _browser
#         yield


# app = FastAPI(lifespan=lifespan)

# output_mime_types = {
#     OutputFormat.MERMAID: "text/plain",
#     OutputFormat.MARKDOWN: "text/plain",
#     OutputFormat.SVG: "image/svg",
# }


# @app.post("/generate")
# async def generate(
#     manifest: Annotated[UploadFile, File()],
#     catalog: Annotated[Union[UploadFile, None], File()] = None,
#     output_format: Annotated[OutputFormat, Form()] = OutputFormat.MERMAID,
#     as_json_response: Annotated[bool, Form()] = False,
# ):
#     try:
#         manifest_json = verify_and_read_f(manifest.file, DbtArtifactType.MANIFEST)
#         catalog_json = verify_and_read_f(catalog.file, DbtArtifactType.CATALOG) if catalog else {}
#     except ValueError as ve:
#         raise HTTPException(status_code=400, detail=str(ve))

#     mermaid_diagram = mermaid_erds_from_manifest_and_catalog(manifest_json, catalog_json)

#     if output_format == OutputFormat.MERMAID:
#         result = mermaid_diagram
#     elif output_format == OutputFormat.MARKDOWN:
#         result = as_markdown(mermaid_diagram)
#     else:
#         result = await as_svg(mermaid_diagram, rest_api_browser)

#     if as_json_response:
#         return {"result": result}
#     else:
#         return Response(
#             content=result, status_code=200, media_type=output_mime_types[output_format]
#         )
