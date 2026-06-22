# Run a Python Script using Quarto

## About this example

This example is a short Python script that Quarto runs as a report. It reads the
`palmerpenguins` dataset, filters out two groups (female Gentoo and male Adelie
penguins), and writes each group to a JSON file and a CSV file that viewers can
download. It also sends an email with the two CSV files attached.

It is meant to run on a schedule, so it is a starting point for any recurring
job that imports data, transforms it, and publishes or emails the results.

## Run it on a schedule

Once published, you can run the script on a schedule from the content's settings
in Connect. Each run re-renders the report, refreshes the downloadable files, and
resends the email. See the [Scheduling](https://docs.posit.co/connect/user/scheduling/)
guide for the steps.

## Email

The email and its attachments are set in the `format: email` block at the top of
`script.py`. Connect can only send it if an administrator has configured a mail
server. If none is configured, the script still runs and produces the files, but
no email is sent.

## Adapt this example

To use your own data, replace the `palmerpenguins` data with your own source (a
database query, an API call, or a file), then adjust the filters, the output file
names, and the attachment list in the email block.

## Learn more

* [Quarto](https://quarto.org)
* [Quarto: Rendering Script Files](https://quarto.org/docs/computations/render-scripts.html)

## Requirements

* Quarto version 1.4 or higher
* Python version 3.9 or higher
