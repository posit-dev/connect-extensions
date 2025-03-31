# CHANGE TO FORCE CI
import concurrent.futures
import os

import polars as pl
from dotenv import load_dotenv
from posit import connect
from shiny import App, reactive, render, req, ui

if os.getenv('RSTUDIO_PRODUCT') != 'CONNECT':
    load_dotenv()


client = connect.Client()

def get_content_guids():
    res = client.me.content.find()
    guids = [x["guid"] for x in res]
    return guids


def get_current_jobs():
    guids = get_content_guids()
    with concurrent.futures.ThreadPoolExecutor(max_workers = 8) as executor:
        l = list(executor.map(lambda guid: client.get(f"v1/content/{guid}/jobs/"), guids))
    response = [x.json() for x in l if x is not None]
    df = (
        pl.DataFrame({"guid": guids, "res": response})
        .explode("res")
        .unnest("res")
        .filter(pl.col("status") == 0)
    )
    return df


app_ui = ui.page_fluid(
    ui.h2("My processes"),
    ui.output_data_frame("ps_df"),
    ui.output_ui("show_kill"),
)

def server(input, output, session):

    @reactive.poll(lambda: (get_current_jobs()["key"]).to_list(), 10)
    def list_jobs():
        return get_current_jobs()

    @render.data_frame
    def ps_df():
        return render.DataGrid(list_jobs(), selection_mode="rows")

    @render.ui
    def show_kill():
        rows = ps_df.cell_selection()["rows"]
        req(rows)
        return ui.input_action_button("kill", "🔪 selected")

    @reactive.calc
    def kill_list():
        selected = ps_df.data_view(selected=True)
        req(not selected.is_empty())
        out = [f"v1/content/{row['guid']}/jobs/{row['key']}" for row in selected.iter_rows(named=True)]
        return out

    @reactive.effect
    @reactive.event(input.kill)
    def kill_exec():
        req(kill_list())
        with concurrent.futures.ThreadPoolExecutor(max_workers= 8) as executor:
            l = list(executor.map(lambda job: client.delete(job), kill_list()))
        return l

    @reactive.effect
    @reactive.event(input.kill)
    def _():
        m = ui.modal(
            "🔪",
            title="job kill request sent",
            easy_close=True
        )
        ui.modal_show(m)


app = App(app_ui, server)
