# ODBC Integration Test

## About this example

A Quarto report that tests an ODBC integration on Posit Connect.
It runs in the same content runtime as your content, so it tests what your content sees: the drivers, the network path, and the credentials.

The report runs four checks in order:

1. Integration variable: Connect sets `CONNECT_ODBC_CONNECTION_STRING`.
2. ODBC driver manager: Python can load `pyodbc`, so unixODBC is installed.
3. Driver registration: the `DRIVER` in the connection string is registered in `odbcinst.ini`, or the `DSN` is defined in `odbc.ini`.
4. Database connection: the driver connects, and the report shows the database name and version.

If a check fails, the report shows the error from the driver and a hint for the fix.
The report never shows the password.

## Requirements

- A Connect administrator creates an ODBC integration.
  See [ODBC](https://docs.posit.co/connect/admin/integrations/oauth-integrations/odbc/) in the Connect Admin Guide.
- The content runtime has the [Posit Professional Drivers](https://docs.posit.co/data-sources/admin/pro-drivers/installation.html) installed and registered in `odbcinst.ini`.
  With off-host execution, the drivers must be in the content image.

## Run the test

1. Deploy the report from the Connect Gallery.
   The first render reports that `CONNECT_ODBC_CONNECTION_STRING` is not set.
   This is expected.
2. In the content settings, open the **Access** panel and add the ODBC integration.
3. Render the report again.

To test again after you change the integration or the content runtime, render the report again.
Connect sets the integration variable when the render starts, so a render always uses the current integration values.

A content item can use only one ODBC integration.
To test a second integration, change the integration on the report, or deploy a second copy.

With off-host execution, the result applies only to the image that the report ran in.
Deploy the report with the same image as the content that uses the integration.

## Deploy it

Deploy it from the Connect Gallery.
To run a customized version, get the
[example source](https://github.com/posit-dev/connect-extensions/tree/main/extensions/odbc-integration-test),
make your changes, and publish with
[`quarto publish connect`](https://quarto.org/docs/publishing/rstudio-connect.html)
or a [git-backed deployment](https://docs.posit.co/connect/user/git-backed/).
Rendering requires Quarto 1.4 or newer and Python 3.9 or newer.

## Learn more

- [Posit Professional Drivers](https://docs.posit.co/data-sources/admin/pro-drivers/)
- [pyodbc](https://github.com/mkleehammer/pyodbc/wiki)
