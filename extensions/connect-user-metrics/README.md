# Connect Insights Dashboard
Expected output: repository with ready-to-use tool. Deploy, set env vars, and enjoy!  
Repository for a reproducible tool to share user metrics for Posit Connect deployed applications.

Expected deployment time: only 5 minutes!

## Quickstart
To get insights about applications deployed by you, simply deploy the application to Posit Connect.

If you wish to run the application locally, set the required [Environment Variables](#environment-variables),  
and run `shiny::runApp()` from the root of this repository.

## Environment Variables
This application requires the following environment variables to be set:
 - `CONNECT_API_KEY`
 - `CONNECT_SERVER`

By default, Posit Connect provides values for these variables, as outlined in the [Vars (Environment Variables) Section][User Guide Vars].  
However, there are cases where you might want to set these variables manually:
 - If you want to retrieve data for applications deployed by a different Publisher than the one
   deploying the User Metrics application, set `CONNECT_API_KEY` with that Publisher's API key.
 - If you want to retrieve data from a different Posit Connect instance than the one where the User
   Metrics application is deployed, set `CONNECT_SERVER` with the URL of that instance.
   Additionally, `CONNECT_API_KEY` must be set to authenticate on the instance specified in
   `CONNECT_SERVER`.

Additionally, if only selected applications should be included, use the `GUIDS` environment variable and provide the GUIDs of all the apps to be measured, separated by a single comma (no spaces):
```r
GUIDS=4203ee4b-16c5-452d-9509-712e29a0d3fb,d358a2e9-e166-4239-978c-d26e9ba82f71
```

### Deployment with an API Key
To deploy an app using the RSConnect API Key, use the following code:

```r
rsconnect::connectApiUser(server = "connect.appsilon.com", apiKey = "<token>", account = "support")
rsconnect::accounts() # list accounts
rsconnect::deployApp(account = "support", appName = "appName")
```

## Default inputs configuration [with optional parameters]
By default, this application selects all users and all applications to be displayed in the summary charts and tables when launched.  
The applications and users to include, as well as the aggregation level, can be configured without the need to manually set these options through the UI.  
To do this, specify the parameters in a `config.yml` file located in the root directory, using the following structure:

```yaml
default:
  apps: "app1, app2"
  users: "user1, user2, user3"
  agg_levels: "user_guid, start_date"
  agg_time: "day"
  min_time: "00:02:00"
  unique_users_goal: "10"
  sessions_goal: "50"
```

* **apps***: The app title as shown in Posit Connect.
* **users***: The publisher's username.
* **agg_levels**: The aggregation level — can be: content_guid, user_guid, and/or start_date.
* **agg_time**: The aggregation frequency — can be: day, week, or month.
* **min_time**: The minimum session duration to filter data and plots. Use format "hh:mm:ss".
* **unique_users_goal***: Y-axis value for the goal line in the Unique Users plot.
* **sessions_goal***: Y-axis value for the goal line in the Total Sessions plot.
* **week_start**: The day to be used as the start of the week.

_* Optional YAML parameters._

Multiple parameters can be listed and separated by commas. For example, the `config.yml` above specifies two apps (*app1*, *app2*), three users (*user1*, *user2*, *user3*), and two aggregation levels (*user_guid* and *start_date*).

### Specifying goals
You can specify the goal in three different ways for both `unique_users_goal` and `sessions_goal`.

1. Not specified — no goal is displayed:
```yaml
default:
  apps: ""
  users: ""
  agg_levels: "start_date" # can be one of content_guid,user_guid,start_date
  agg_time: "day" # can be one of day,week,month
  min_time: "00:02:00"
  week_start: "monday"
```

2. Single value for all aggregation levels (e.g., date and combinations like app, user, date):
```yaml
default:
  apps: ""
  users: ""
  agg_levels: "start_date" # can be one of content_guid,user_guid,start_date
  agg_time: "day" # can be one of day,week,month
  min_time: "00:02:00"
  unique_users_goal: "20"
  sessions_goal: "10"
  week_start: "monday"
```

3. Individual goals as a YAML list:
```yaml
default:
  apps: ""
  users: ""
  agg_levels: "start_date"
  agg_time: "day"
  min_time: "00:02:00"
  unique_users_goal:
    - freq: "day"
      per: "start_date"
      goal: "7"
    - freq: "day"
      per: "start_date,content_guid"
      goal: "14"
    - freq: "week"
      per: "start_date"
      goal: "10"
  sessions_goal:
    - freq: "day"
      per: "start_date"
      goal: "27"
    - freq: "day"
      per: "start_date,content_guid"
      goal: "84"
    - freq: "week"
      per: "start_date"
      goal: "30"
  week_start: "monday"
```

Note: You can mix and match — for example, define `unique_users_goal` and leave `sessions_goal` unspecified:
```yaml
default:
  apps: ""
  users: ""
  agg_levels: "start_date" # can be one of content_guid,user_guid,start_date
  agg_time: "day" # can be one of day,week,month
  min_time: "00:02:00"
  unique_users_goal: "20"
  week_start: "monday"
```

## Features

### Filtering users
You can exclude specific users from appearing in any part of the application by listing them in the `constants/filter_users.yml` file:

```yaml
users:
  - user_1 # will not appear in the app
  - user_2 # will not appear in the app
```

### Branding
You can use the default branding provided by Appsilon or customize your own by modifying `_brand.yml` in the root directory.  
This file controls the application's metadata, logo, colors, and typography.  
Note: `_brand.yml` cannot be empty. All sections below must be defined for the app to work correctly.

#### Metadata
Controls the application's title and credits. You can disable credits by setting `enabled` to `FALSE`:

```yaml
meta:
  app_title: "Posit Connect User Metrics"
  credits:
    enabled: FALSE
```

_* While disabling credits is possible, we encourage you to keep them as a token of appreciation for the developers and contributors. Supporting open-source helps sustain these efforts._

#### Logo
Add your logo to `app/static/images` and set the file name:

```yaml
logo: "your_file.png"
```

#### Colors
Customize the color palette inside the `palette` section. Hex colors are recommended:

```yaml
color:
  palette:
    white: "#FFFFFF"
    mint: "#00CDA3"
    blue: "#0099F9"
    yellow: "#E8C329"
    purple: "#994B9D"
    black: "#000000"
    gray: "#15354A"
  foreground: gray
  background: white
  primary: blue
```

#### Typography
Define fonts used in the app under the `typography` section. The required keys are `base` and `headings`:

```yaml
typography:
  fonts:
    - family: Maven Pro
      source: google
      weight: [400, 500, 600, 700]
      style: normal
    - family: Roboto
      source: google
      weight: [400, 500, 600]
      style: normal
  base:
    Roboto
  headings:
    Maven Pro
```

Refer to the detailed [guide](https://posit-dev.github.io/brand-yml/) for advanced UI customization.

## Disclaimer
Posit Connect usage data is most accurate for applications accessed by authenticated users.  
Unauthenticated users cannot be distinguished, so user-level aggregation is not possible in such cases.

Read more: [_Why You Should Use Posit Connect Authentication And How to Set It Up_][rsconnect-auth].

## Troubleshooting

### Posit Connect does not appear to have `CONNECT_SERVER` and `CONNECT_API_KEY` set
Per the [Configuration appendix] in the Posit Connect Admin Guide, these variables are set by default.  
However, this behavior can be overridden via [DefaultServerEnv] and [DefaultAPIKeyEnv].

Check with your Posit Connect administrator if that's the case.

### The API connection fails due to a timeout after deploying the User Metrics application
If the connection times out using the default environment variables, the issue may be that the server cannot resolve its own fully qualified domain name.

To fix this, go to the User Metrics [application Vars][User Guide Vars] and set `CONNECT_SERVER` to a local address, e.g.:
```
http://localhost:3939
```
(Note: the scheme in the URL is required by `connectapi::connect()`.)

### There is no usage data for my application
As with environment variables, the [Instrumentation] feature is also configurable.

Confirm with your Posit Connect admin that instrumentation is enabled.

<!-- Links -->
[User Guide Vars]: https://docs.posit.com/connect/user/content-settings/#content-vars  
[rsconnect-auth]: https://appsilon.com/why-use-rstudio-connect-authentication/  
[Configuration appendix]: https://docs.posit.co/connect/admin/appendix/configuration/  
[DefaultServerEnv]: https://docs.posit.co/connect/admin/appendix/configuration/#Applications.DefaultServerEnv  
[DefaultAPIKeyEnv]: https://docs.posit.co/connect/admin/appendix/configuration/#Applications.DefaultAPIKeyEnv  
[Instrumentation]: https://docs.posit.co/connect/admin/appendix/configuration/#Metrics.Instrumentation
