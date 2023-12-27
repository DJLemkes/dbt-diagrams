from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
import subprocess
import tempfile
from typing import Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api._generated import Playwright
    from playwright.async_api import Browser


class OutputFormat(Enum):
    MERMAID = "mermaid"
    SVG = "svg"
    MARKDOWN = "markdown"


def write_as_markdown(mermaid_diagrams: Dict[str, str], out: Path):
    for diagram_name, diagram in mermaid_diagrams.items():
        with open(f"{out}/{diagram_name}.md", "w") as f:
            f.write(as_markdown(diagram))


def as_markdown(mermaid_diagram) -> str:
    return f"```mermaid\n{mermaid_diagram}\n```"


def write_as_mmd(mermaid_diagrams: Dict[str, str], out: Path):
    for diagram_name, diagram in mermaid_diagrams.items():
        with open(f"{out}/{diagram_name}.mmd", "w") as f:
            f.write(diagram)


async def _launch_browser(async_pw_context_manager: "Playwright") -> "Browser":
    retries = 0
    while retries <= 1:
        try:
            print("Launching browser")
            return await async_pw_context_manager.chromium.launch()
        except Exception as e:
            print("Could not launch Chromium browser", e)
            retries += 1
            subprocess.run("playwright install chromium".split(" "))

    raise Exception("Could not install required dependencies.")


@asynccontextmanager
async def get_browser():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        tag_selector = """
            {
                // Returns the first element matching given selector in the root's subtree.
                query(root, selector) {
                    return root.querySelector(selector);
                },
                // Returns all elements matching given selector in the root's subtree.
                queryAll(root, selector) {
                    return Array.from(root.querySelectorAll(selector));
                }
            }"""
        await p.selectors.register("tag", tag_selector)
        browser = await _launch_browser(p)
        yield browser
        await browser.close()


async def as_svg(mermaid_diagram: str, provided_browser: Optional["Browser"] = None) -> str:
    async def _inner(tmp_html_path: str, browser: Browser) -> str:
        page = await browser.new_page(viewport={"width": 800, "height": 450})
        await page.goto(f"file://{tmp_html_path}")
        await page.wait_for_load_state("load")
        svg = page.locator("tag=pre[data-processed='true']").filter(
            has=page.locator("tag=svg[aria-roledescription='er']")
        )
        await svg.screenshot(path="screenshot.png")
        svg_str = await svg.inner_html()
        await page.close()
        return svg_str

    # Creating a temp file requires manually seeking to 0 again before passing around the
    # open file handler to other functions. Creating a temp dir leaves us free to create
    # file and close them in one context, while still benefiting from automatic cleanup
    # after we're done.
    with tempfile.TemporaryDirectory(prefix="dbt_diagrams") as tmp_dir:
        tmp_html_path = f"{tmp_dir}/tmp.html"
        with open(tmp_html_path, "w") as tmp_html:
            html = """
                        <!DOCTYPE html>
                        <html lang="en">
                        <body>
                            <pre class="mermaid">
                            {}
                            </pre>

                            <script type="module">
                            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                            </script>
                        </body>
                        </html>
                        """.format(
                mermaid_diagram
            )
            tmp_html.write(html)

        if provided_browser:
            return await _inner(tmp_html_path, provided_browser)
        else:
            async with get_browser() as browser:
                return await _inner(tmp_html_path, browser)


async def write_as_svg(
    mermaid_diagrams: Dict[str, str], out: Path, provided_browser: Optional["Browser"] = None
):
    for diagram_name, diagram in mermaid_diagrams.items():
        svg_str = await as_svg(diagram, provided_browser)
        with open(f"{out}/{diagram_name}.svg", "w") as f:
            f.write(svg_str)
