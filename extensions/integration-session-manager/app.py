# TRIGGER WORKFLOW
from posit.connect.client import Client
from shiny import App, reactive, render, ui
import pandas as pd
from matplotlib.ticker import MaxNLocator 
import seaborn as sns

sns.set_theme(style="ticks")


client = Client()

app_ui = ui.page_sidebar(
    ui.sidebar(
        ui.output_text("delete_helper"),
        ui.input_action_button("delete_session", "Delete", class_="btn-danger"),
    ),
    ui.layout_column_wrap(
        ui.value_box(
            "Active session count",
            ui.output_text("session_count"),
            theme="bg-gradient-orange-red",
        ),
        ui.value_box(
            "Integration count",
            ui.output_text("integration_count"),
            theme="bg-gradient-blue-purple",
        ),
        ui.value_box(
            "User count",
            ui.output_text("user_count"),
            theme="bg-gradient-blue-purple",
        ),
        fill=False
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Active Sessions"),
            ui.output_data_frame("session_df"),
        ),
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Integrations"),
            ui.layout_columns(
                ui.output_data_frame("integration_table"),
                ui.output_plot("integration_plot"),
            ),
        ),
    ),
    ui.layout_columns(
        ui.card(
            ui.card_header("Users"),
            ui.layout_columns(
                ui.output_data_frame("user_table"),
                ui.output_plot("user_plot"),
            ),
        ),
    ),
    title="Connect OAuth Session Manager"
)



def server(input): 
  
    # don't query _active_sessions directly - use the reactive calc
    # sorted_active_sessions() to ensure consistent row ids in various UI
    # elements.
    _active_sessions = reactive.value(client.oauth.sessions.find(all=True))


    @render.text
    def session_count():
        return str(len(sorted_active_sessions()))


    @render.text
    def integration_count():
        return str(len(compute_integration_summary().index))

    @render.text
    def user_count():
        return str(len(compute_user_summary().index))


    @render.data_frame
    def session_df():
        df = compute_joined_df()
        if df.empty:
            empty_df = pd.DataFrame(columns=["Session Guid", "User Guid", "User Name", "Integration Guid", "Integration Name", "Created Time", "Updated Time"])
            return render.DataGrid(empty_df, width="100%")
        df = compute_joined_df().rename(columns={
            "guid": "Session Guid",
            "user_guid": "User Guid",
            "user_name": "User Name",
            "integration_guid": "Integration Guid",
            "integration_name": "Integration Name",
            "created_time": "Created Time",
            "updated_time": "Updated Time",
        })
        return render.DataGrid(df, filters=True, selection_mode="rows", width="100%") 

    @render.text
    def delete_helper():
        rows = session_df.cell_selection()["rows"]
        if len(rows) == 0:
            return "Select session records to delete."
        else:
            return f"Delete {len(rows)} active session(s)."


    @reactive.effect
    @reactive.event(input.delete_session)
    def delete():
        current_active_sessions = sorted_active_sessions()
        current_join_data = compute_joined_dataset()

        # collect session indexes to delete
        rows = session_df.cell_selection()["rows"]
        to_delete = []
        for i in range(len(rows)):
            idx = rows[i]
            to_delete.append(idx)

        # recreate active_sessions, collecting the join dataset's representation of what to delete
        # as we go so we can display user / integration info 
        # in the delete confirmation modal 
        join_sessions_to_delete = []
        new_active_sessions = []
        for i in range(len(current_active_sessions)):
            if i in to_delete:
                join_sessions_to_delete.append(current_join_data[i])
            else:
                new_active_sessions.append(current_active_sessions[i])
        _active_sessions.set(new_active_sessions)
       

        if len(join_sessions_to_delete) == 0:
            m = ui.modal(
                "Select some rows in the \"Active Sessions\" panel first.",
                title="No sessions selected for delete."
            )
            ui.modal_show(m)
        else:
            
            # execute delete
            for join_session in join_sessions_to_delete:
                session = client.oauth.sessions.get(guid=join_session["guid"])
                session.delete()

            # render deletion confirmation modal
            deleted_df = pd.DataFrame.from_records(join_sessions_to_delete)
            deleted_df = deleted_df.rename(columns={
                "guid": "Session Guid",
                "user_guid": "User Guid",
                "user_name": "User Name",
                "integration_guid": "Integration Guid",
                "integration_name": "Integration Name",
            })
            @render.data_frame
            def render_deleted_df():
                return render.DataTable(deleted_df[["Session Guid", "User Guid", "User Name", "Integration Guid", "Integration Name"]], width="100%")

            m = ui.modal(
                render_deleted_df,
                title=f"Deleted {len(join_sessions_to_delete)} Active Session(s)",
                easy_close=True,
                size="xl",
            )
            ui.modal_show(m)
   
    @render.data_frame
    def integration_table():
        df = compute_integration_summary()
        return render.DataTable(compute_integration_summary(), width="100%") 


    @render.plot(alt="Integration Distribution")  
    def integration_plot():  
        df = compute_integration_summary()[["Integration Name", "Session Count"]] 

        ax = sns.barplot(df, x="Integration Name", y="Session Count", hue="Integration Name", legend="full")

        ax.set_xticklabels([])
        ax.set_xticks([])
        ax.set_xlabel("")
        ax.set_ylabel("Session Count")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        sns.despine(ax=ax)

        return ax

    @render.data_frame
    def user_table():
        return render.DataTable(compute_user_summary(), width="100%")

    @render.plot(alt="User Distribution")
    def user_plot():
        df = compute_user_summary()[["User Name", "Session Count"]]

        ax = sns.barplot(df, x="User Name", y="Session Count", hue="User Name", legend="full")
       
        ax.set_xticklabels([])
        ax.set_xticks([])
        ax.set_xlabel("")
        ax.set_ylabel("Session Count")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        sns.despine(ax=ax)

        return ax 

    # to make sure row ids are consistent, get active sessions from 
    # this reactive calc which sorts the data prior to business logic
    # rather than querying the base reactive value and sorting in many places
    @reactive.calc
    def sorted_active_sessions():
        return sorted(_active_sessions.get(), key=lambda session: session["created_time"], reverse=True)


    @reactive.calc
    def compute_joined_dataset():
        data = []
        for session in sorted_active_sessions():
            integration = client.oauth.integrations.get(session["oauth_integration_guid"])
            user = client.users.get(session["user_guid"])
            record = {
                "guid": session["guid"],
                "user_guid": user["guid"],
                "user_name": user["username"],
                "integration_guid": integration["guid"],
                "integration_name": integration["name"],
                "created_time": session["created_time"],
                "updated_time": session["updated_time"],
            }
            data.append(record)
        return data

    @reactive.calc
    def compute_joined_df():
        return pd.DataFrame.from_records(compute_joined_dataset())

    @reactive.calc
    def compute_integration_summary():
        df = compute_joined_df()
        if df.empty:
            return pd.DataFrame(columns=["Integration Guid", "Integration Name", "Session Count"])

        summary = compute_joined_df()[["integration_guid", "integration_name"]].value_counts().reset_index()
        return summary.rename(columns={
            "integration_guid": "Integration Guid",
            "integration_name": "Integration Name", 
            "count": "Session Count"
        })

    @reactive.calc
    def compute_user_summary():
        df = compute_joined_df()
        if df.empty:
            return pd.DataFrame(columns=["User Guid", "User Name", "Session Count"])

        summary = compute_joined_df()[["user_guid", "user_name"]].value_counts().reset_index()
        return summary.rename(columns={
            "user_guid": "User Guid",
            "user_name": "User Name", 
            "count": "Session Count",
        })


app = App(app_ui, server)
