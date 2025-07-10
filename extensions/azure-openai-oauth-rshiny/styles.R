library(shiny)

# Common CSS styles for the app
app_styles <- tags$style(
  "body {
      padding: 0;
      margin: 0;
      background: linear-gradient(135deg, #f7f8fa 0%, #e2e8f0 100%);
  }

  .setup-container {
      max-width: 800px;
      margin: 0 auto;
      padding: 2rem;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
  }
  .setup-card {
      background: white;
      border-radius: 16px;
      padding: 3rem;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
      width: 100%;
  }
  .setup-title {
      color: #2d3748;
      font-weight: 700;
      margin-bottom: 2rem;
      text-align: center;
      font-size: 2.5rem;
  }
  .setup-section-title {
      color: #4a5568;
      font-weight: 600;
      margin-top: 2.5rem;
      margin-bottom: 1rem;
      font-size: 1.5rem;
  }
  .setup-description {
      color: #718096;
      line-height: 1.6;
      margin-bottom: 1.5rem;
  }
  .setup-code-block {
      background: #f7fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1.5rem;
      font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
      font-size: 0.9rem;
      color: #2d3748;
      margin: 1rem 0;
      overflow-x: auto;
  }
  .setup-link {
      color: #667eea;
      text-decoration: none;
      font-weight: 500;
  }
  .setup-link:hover {
      color: #764ba2;
      text-decoration: underline;
  }
  .setup-integration-section {
      background: #f0f8ff;
      border: 1px solid #b3d8ff;
      border-radius: 8px;
      padding: 1.5rem;
      margin: 2rem 0;
  }
  .setup-button-container {
      display: flex;
      justify-content: center;
      margin-top: 1rem;
  }
  @media (max-width: 768px) {
      .setup-container {
          padding: 1rem;
      }
      .setup-card {
          padding: 2rem;
      }
      .setup-title {
          font-size: 2rem;
      }
  }"
)

# Card container component
setup_container <- function(...) {
  tags$div(
    class = "setup-container",
    tags$div(
      class = "setup-card",
      ...
    )
  )
}