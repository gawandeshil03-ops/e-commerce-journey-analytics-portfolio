from __future__ import annotations

import ast
import base64
import contextlib
import io
import os
import traceback
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_output

from .config import NOTEBOOK_PATH, PROJECT_ROOT


def _mime_bundle(value: Any) -> dict[str, str]:
    data: dict[str, str] = {"text/plain": repr(value)}

    if isinstance(value, plt.Figure):
        buffer = io.BytesIO()
        value.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
        data["image/png"] = base64.b64encode(buffer.getvalue()).decode("ascii")
        plt.close(value)
        return data

    html_method = getattr(value, "_repr_html_", None)
    if callable(html_method):
        html = html_method()
        if html:
            data["text/html"] = html
    elif value.__class__.__name__ == "Styler":
        data["text/html"] = value.to_html()

    return data


def _execute_in_process(notebook: nbformat.NotebookNode) -> nbformat.NotebookNode:
    import IPython.display as ipython_display

    namespace: dict[str, Any] = {
        "__name__": "__main__",
        "__file__": str(NOTEBOOK_PATH),
    }
    original_display = ipython_display.display
    execution_count = 0

    try:
        for cell in notebook.cells:
            if cell.cell_type != "code":
                continue

            execution_count += 1
            cell.execution_count = execution_count
            cell.outputs = []
            stdout = io.StringIO()
            stderr = io.StringIO()

            def capture_display(*values: Any, **_: Any) -> None:
                for value in values:
                    cell.outputs.append(
                        new_output(
                            output_type="display_data",
                            data=_mime_bundle(value),
                            metadata={},
                        )
                    )

            ipython_display.display = capture_display
            source = cell.source

            try:
                tree = ast.parse(source, filename=f"cell_{execution_count}")
                final_expression = None
                if tree.body and isinstance(tree.body[-1], ast.Expr):
                    final_expression = ast.Expression(tree.body.pop().value)

                with (
                    contextlib.redirect_stdout(stdout),
                    contextlib.redirect_stderr(stderr),
                ):
                    if tree.body:
                        exec(
                            compile(tree, f"cell_{execution_count}", "exec"),
                            namespace,
                        )
                    result = (
                        eval(
                            compile(
                                final_expression,
                                f"cell_{execution_count}",
                                "eval",
                            ),
                            namespace,
                        )
                        if final_expression is not None
                        else None
                    )

                if stdout.getvalue():
                    cell.outputs.append(
                        new_output(
                            output_type="stream",
                            name="stdout",
                            text=stdout.getvalue(),
                        )
                    )
                if stderr.getvalue():
                    cell.outputs.append(
                        new_output(
                            output_type="stream",
                            name="stderr",
                            text=stderr.getvalue(),
                        )
                    )
                if result is not None:
                    cell.outputs.append(
                        new_output(
                            output_type="execute_result",
                            execution_count=execution_count,
                            data=_mime_bundle(result),
                            metadata={},
                        )
                    )
            except Exception as error:
                cell.outputs.append(
                    new_output(
                        output_type="error",
                        ename=type(error).__name__,
                        evalue=str(error),
                        traceback=traceback.format_exc().splitlines(),
                    )
                )
                raise
    finally:
        ipython_display.display = original_display
        connection = namespace.get("connection")
        if connection is not None:
            connection.close()

    return notebook


def execute_notebook(notebook_path: Path = NOTEBOOK_PATH) -> Path:
    notebook = nbformat.read(notebook_path, as_version=4)
    if os.environ.get("ECOMMERCE_NOTEBOOK_IN_PROCESS") == "1":
        notebook = _execute_in_process(notebook)
        nbformat.write(notebook, notebook_path)
        return notebook_path

    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(PROJECT_ROOT)}},
        allow_errors=False,
    )
    try:
        client.execute()
    except RuntimeError as error:
        if "Kernel died before replying" not in str(error):
            raise
        notebook = nbformat.read(notebook_path, as_version=4)
        notebook = _execute_in_process(notebook)
    nbformat.write(notebook, notebook_path)
    return notebook_path
