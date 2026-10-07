# .Rprofile - Auto-initialization for Finance Research Agents in RStudio
local({
  message("=================================================================")
  message("  🚀 Finance Research Agents & Antigravity - RStudio Workspace")
  message("=================================================================")
  
  proj_dir <- getwd()
  python_venv <- file.path(proj_dir, ".venv", "Scripts", "python.exe")
  if (file.exists(python_venv)) {
    Sys.setenv(RETICULATE_PYTHON = python_venv)
    message(paste("  ✓ Python Virtualenv Active:", python_venv))
  }
  
  bridge_script <- file.path(proj_dir, "r_studio", "agent_bridge.R")
  if (file.exists(bridge_script)) {
    source(bridge_script)
    message("  ✓ Agent Bridge Loaded (r_studio/agent_bridge.R)")
    message("  ✓ Available R Functions:")
    message("      - run_agent_pipeline('AAPL', workflow = 1)")
    message("      - fetch_sec_financials('AAPL')")
    message("      - calc_dcf(base_fcf, growth_rates, discount_rate, ...)")
    message("      - run_skeptic_adversarial('AAPL')")
    message("      - r_monte_carlo_dcf('AAPL', iterations = 1000)")
  }
  message("=================================================================\n")
})
