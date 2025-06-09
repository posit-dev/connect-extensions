# Connect Insights Dashboard

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
   Additionally, `CONNECT_API_KEY` must be set to authenticate on the instance specified in `CONNECT_SERVER`.

## Disclaimer

Posit Connect usage data is most accurate for applications accessed by authenticated users.
Unauthenticated users cannot be distinguished, and will be seen in the app as "Unknown user".

Read more: [_Why You Should Use Posit Connect Authentication And How to Set It Up_][rsconnect-auth].

## Troubleshooting

### Posit Connect does not appear to have `CONNECT_SERVER` and `CONNECT_API_KEY` set

Per the [Configuration appendix] in the Posit Connect Admin Guide, these variables are set by default.  
However, this behavior can be overridden via [DefaultServerEnv] and [DefaultAPIKeyEnv].

Check with your Posit Connect administrator if that's the case.

### The API connection fails due to a timeout after deploying the User Metrics application

If the connection times out using the default environment variables, the issue may be that the server cannot resolve its own fully qualified domain name.

To fix this, go to the User Metrics [application Vars][User Guide Vars] and set `CONNECT_SERVER` to a local address, e.g. `http://localhost:3939`.

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
