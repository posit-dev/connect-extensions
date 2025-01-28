# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "typing_extensions",
# ]
# ///
from __future__ import annotations

import pathlib
import os
import json
from typing_extensions import TypedDict, TypeVar

here = pathlib.Path(__file__).parent
os.chdir(here)

T = TypeVar("T")


class SwaggerOperation(TypedDict, total=False):
    summary: str


class SwaggerDocument(TypedDict):
    paths: dict[str, SwaggerOperation]


class Route(TypedDict):
    method: str
    path: str
    summary: str


def transform_swagger_to_routes(
    swagger_dict: SwaggerDocument,
) -> list[Route]:
    """
    Swagger to routes.

    Transforms the structure of a Swagger object to create a list where each object includes the route method, route path, and route summary.

    Arguments
    ---------
    swagger_dict
        The dictionary representing the Swagger document.

    Returns
    -------
    :
        A list of dictionaries where each dictionary includes the method, path, and summary of an API route.
    """
    routes: list[Route] = []

    if "paths" not in swagger_dict:
        raise ValueError(
            "The Swagger document `swagger_dict=` does not contain a 'paths' key."
        )

    if "paths" in swagger_dict:
        for path, operations in swagger_dict["paths"].items():
            if not isinstance(path, str):
                raise ValueError(
                    f"Expected route to be a string, but got {type(path)}."
                )
            for method, operation in operations.items():
                if not isinstance(method, str):
                    raise ValueError(
                        f"Expected method to be a string, but got {type(method)}."
                    )
                if not isinstance(operation, dict):
                    raise ValueError(
                        f"Expected operation to be a dictionary, but got {type(operation)}."
                    )
                if "summary" not in operation:
                    raise ValueError(
                        f"Expected operation to have a 'summary' key, but got {operation}."
                    )

                summary = operation["summary"]
                if not isinstance(summary, str):
                    raise ValueError(
                        f"Expected summary to be a string, but got {type(summary)}."
                    )

                routes.append(
                    {
                        "method": method,
                        "path": path,
                        "summary": summary,
                    }
                )

    return routes


def main():
    if not (here / "_swagger.json").exists():
        import urllib.request

        urllib.request.urlretrieve(
            "https://docs.posit.co/connect/api/swagger.json",
            here / "_swagger.json",
        )

    swagger = json.loads((here / "_swagger.json").read_text())

    routes = transform_swagger_to_routes(swagger)

    # Write out the swagger portion of the instructions with a preamble and a
    # list of all the API routes and their short summaries.
    with open(here / "_swagger_prompt.md", "w") as f:
        f.write(
            "If an answer can not be resolved, suggest to the user that they can explore calling these API routes themselves. Never produce code that calls these routes as we do not know the return type or successful status codes.\n\nAPI Routes:\n"
            ""
        )

        for route in routes:
            # `"* GET /v1/tasks/{id} Get task details"`
            f.write(
                "* "
                + route["method"].upper()
                + " "
                + route["path"]
                + " "
                + route["summary"].replace("\n", " ").strip()
                + "\n",
            )


if __name__ == "__main__":
    main()
