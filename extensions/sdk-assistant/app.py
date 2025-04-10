import os
import pathlib
import tempfile
import urllib.parse

import chatlas
import faicons

from shiny import App, Inputs, reactive, render, ui

app_ui = ui.page_fillable(
    ui.h1(
        "SDK Assistant",
        ui.input_action_link(
            "info_link", label=None, icon=faicons.icon_svg("circle-info")
        ),
        ui.output_text("cost", inline=True),
    ),
    ui.output_ui("new_gh_issue", inline=True),
    ui.chat_ui("chat", placeholder="Ask your posit-SDK questions here..."),
    ui.tags.style(
        """
        #info_link {
            font-size: medium;
            vertical-align: super;
            margin-left: 10px;
        }
        #cost {
            color: lightgrey;
            font-size: medium;
            vertical-align: middle;
        }
        .suggestion {
            display: list-item;
        }
        .external-link {
            cursor: alias;
        }
        #new_gh_issue {
            position: absolute;
            right: 15px;
            top: 15px;
            height: 25px;
        }
        """
    ),
    fillable_mobile=True,
)


def server(input: Inputs):  # noqa: A002
    aws_model = os.getenv("AWS_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    chat = chatlas.ChatBedrockAnthropic(model=aws_model, aws_region=aws_region)

    prompt = pathlib.Path(__file__).parent / "_prompt.xml"
    if not prompt.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt}; run `make shiny` to generate it."
        )

    chat.system_prompt = prompt.read_text()

    chat_ui = ui.Chat("chat")

    @render.text
    @reactive.event(chat_ui.messages)
    def cost():
        tokens = chat.tokens("cumulative")
        if len(tokens) == 0:
            return None

        cost = sum(
            [
                # Input + Output
                (token[0] * 0.003 / 1000.0) + (token[1] * 0.015 / 1000.0)
                for token in tokens
                if token is not None
            ]
        )
        ans = "$%s" % float("%.3g" % cost)
        while len(ans) < 5:
            ans = ans + "0"
        return ans

    @render.ui
    def new_gh_issue():
        messages = chat_ui.messages()
        for message in messages:
            if message["role"] == "assistant":
                break
        else:
            # No LLM response found. Return
            return

        first_message_content: str = str(messages[0].get("content", ""))

        with tempfile.TemporaryDirectory() as tmpdirname:
            export_path = pathlib.Path(tmpdirname) / "chat_export.md"
            chat.export(export_path, content="all", include_system_prompt=False)

            exported_content = export_path.read_text()

        body = f"""
**First message:**
```
{first_message_content}
```

**Desired outcome:**

Please describe what you would like to achieve in `posit-sdk`. Any additional context, code, or examples are welcome!

```python
from posit.connect import Client
client = Client()

# Your code here
```

-----------------------------------------------

<details>
<summary>Chat Log</summary>

````markdown
{exported_content}
````
</details>
"""

        title = (
            "SDK Assistant: `"
            + (
                first_message_content
                if len(first_message_content) <= 50
                else (first_message_content[:50] + "...")
            )
            + "`"
        )

        new_issue_url = (
            "https://github.com/posit-dev/posit-sdk-py/issues/new?"
            + urllib.parse.urlencode(
                {
                    "title": title,
                    "labels": ["template idea"],
                    "body": body,
                }
            )
        )

        return ui.a(
            ui.img(src="new_gh_issue.svg", alt="New GitHub Issue", height="100%"),
            title="Submit script example to Posit SDK",
            class_="external-link",
            href=new_issue_url,
            target="_blank",
        )

    @chat_ui.on_user_submit
    async def _():
        user_input = chat_ui.user_input()
        if user_input is None:
            return
        await chat_ui.append_message_stream(
            await chat.stream_async(
                user_input,
                echo="all",
            )
        )

    @reactive.effect
    async def _init_chat_on_load():
        chat_ui.update_user_input(
            value="What are the pieces of Posit connect and how do they fit together?",
            submit=True,
        )

        # Remove the effect after the first run
        _init_chat_on_load.destroy()

    @reactive.effect
    @reactive.event(input.info_link)
    async def _():
        modal = ui.modal(
            ui.h1("Information"),
            ui.h3("Model"),
            ui.pre(
                f"Model: {aws_model}\nRegion: {aws_region}",
            ),
            ui.h3("System prompt"),
            ui.pre(chat.system_prompt),
            easy_close=True,
            size="xl",
        )
        ui.modal_show(modal)


app = App(
    app_ui,
    server,
    static_assets=pathlib.Path(__file__).parent / "www",
)
