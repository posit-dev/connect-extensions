# R Shiny: Portfolio Dashboard

## About this example

An interactive R Shiny dashboard that computes the rolling Sortino ratio (a
downside-risk-adjusted measure of return) across conservative, balanced, and
aggressive portfolios. It's a finance example, but the underlying pattern, an
app that lets people ask and answer questions in real time without touching
code, applies to any domain. It ships with synthetic sample monthly returns you can swap
for your own.

## How it works

Pick a portfolio, a starting date, a Minimum Acceptable Rate (MAR), and a
rolling-window length in the sidebar, and four linked plots update:

- **Rolling Sortino**: the Sortino ratio over the rolling window, with a range
  selector.
- **Scatterplot**: monthly returns, colored by whether they land above or below
  the MAR.
- **Histogram**: the distribution of returns, with the MAR marked.
- **Density**: the return density, with the downside (below-MAR) region shaded.

The Sortino ratio measures return per unit of *downside* volatility (returns
below the MAR), so unlike the Sharpe ratio it doesn't penalize upside swings.

## Customize it

Replace `returns.csv` (columns: `date`, `portfolio`, `returns`) with your own
monthly returns. The portfolio names in the file populate the selector, so you
can use any set of portfolios or strategies.

## Deploy it

Deploy it straight from the Connect Gallery to get a copy running. To publish
your own version, deploy the directory with the
[rsconnect R package](https://rstudio.github.io/rsconnect/reference/deployApp.html)
(`rsconnect::deployApp()`) or a
[git-backed deployment](https://docs.posit.co/connect/user/git-backed/). Requires
R 4.4 or newer.

## Learn more

- [Shiny](https://shiny.posit.co/)
- [Gallery of example Shiny apps](https://shiny.posit.co/r/gallery/)
