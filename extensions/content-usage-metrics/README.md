# Content Usage Metrics

A Shiny app that helps you understand content usage patterns on your Connect server. Browse an overview of usage across your published content, and dive into a detailed breakdown of visit-level data for each piece of content.

## Setup

After deploying this app, you'll need to add a Visitor API Key integration.

In the app's control panel on the right of the screen, in the Access tab, click **"Add integration"**, then select a **Visitor API Key** integration.

If you don't see one in the list, an administrator must enable this feature on your Connect server.
See the [Admin Guide](https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/) for setup instructions.

## Viewing usage data

The Content Usage Metrics app shows you usage data for your content on the Connect server where it's published. There are two main views: a table that shows you usage overview across pieces of content, and a detail view that breaks down usage for a selected piece of content by visitor and over time. The app's sidebar contains controls to filter the data and adjust how it is displayed. Some controls affect data across the entire app, and some are only available for the table or the detail views.

### Global controls

- Date Range: Adjust the date range for displayed data. You can select a preset window or custom date range.
- Visit Merge Window (sec): Merges together visits from the same user that occurred rapidly back to back. For example, if the Visit Merge Window control is set to "30", any given user's visits to a piece of content will only count at most once every 30 seconds.

### Usage Overview Table

The overview table shows a table row for each piece of content. You can sort or search the table, and adjust the set of data shown using controls in the sidebar:

- Included Content: Administrators can view all content on the server. Both Administrators and Publishers can also view content they own plus content on which they are collaborators, or just content they own.
- Filter by Content Type: Select one or more content types to show only those types in the table.
- Show GUID: Show or hide the content GUID in the table.
- Export Usage Table: Download the data displayed in the usage table. The data downloaded is specifically the data displayed, *after* filtering by date range, applying the visit merge window, and filtering for ownership and content type.
- Export Raw Visit Data: Export the raw data downloaded from Connect, with a field for `user_guid`, `timestamp`, and `content_guid`.

### Content Detail View

Click on a piece of content in the table to view detailed usage information.

This view include two plots: a histogram aggregating visits by day, and a plot showing each user's visits on a timeline. It also includes two tables: one showing the total visits for each user in the selected date range, and a list of all visits.

Sidebar controls include:

- Filter Visitors: Select the visitors whose data you wish to view. You can also toggle selection for a given user by clicking their name in the Top Visitors table.
- Email Selected Users: Open a `mailto` link populated with the email addresses of the users whose data you're viewing.

### Other controls

- Clear Cache: The app caches data from Connect's API for an hour, to speed up repeated views. Use this button if you need to manually refresh the displayed data.
