# r_studio/agent_bridge.R - RStudio Interface for Finance Research Agents
# Provides native R functions to interact with Antigravity multi-agent research tools

suppressPackageStartupMessages({
  if (!requireNamespace("jsonlite", quietly = TRUE)) {
    warning("jsonlite package not found. Install via: install.packages('jsonlite')")
  } else {
    library(jsonlite)
  }
})

.get_python_path <- function() {
  venv_py <- file.path(getwd(), ".venv", "Scripts", "python.exe")
  if (file.exists(venv_py)) return(venv_py)
  # Fallback to system python
  "python"
}

#' Run Complete Autonomous Multi-Agent Research Pipeline
#' 
#' @param ticker Stock ticker symbol (e.g. "AAPL", "TCS.NS")
#' @param workflow Playbook workflow number (1 = Comprehensive Valuation, 2 = Rapid Screen)
#' @param strict_audit Enforce strict zero-unverified default-deny policy
#' @return List containing execution status, paths to generated reports, and audit summary
run_agent_pipeline <- function(ticker, workflow = 1, strict_audit = FALSE) {
  py_exe <- .get_python_path()
  message(sprintf("🤖 Executing Finance Agents Pipeline for %s (Workflow %d)...", ticker, workflow))
  
  args <- c("run_research.py", "--ticker", ticker, "--workflow", as.character(workflow))
  if (strict_audit) args <- c(args, "--strict")
  
  res <- system2(py_exe, args = args, stdout = TRUE, stderr = TRUE)
  status_code <- attr(res, "status")
  if (is.null(status_code)) status_code <- 0
  
  date_str <- format(Sys.Date(), "%Y-%m-%d")
  report_dir <- file.path(getwd(), "reports", sprintf("%s_%s", ticker, date_str))
  final_report_file <- file.path(report_dir, "final_report.md")
  
  report_text <- if (file.exists(final_report_file)) {
    paste(readLines(final_report_file, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
  } else {
    NULL
  }
  
  list(
    ticker = ticker,
    workflow = workflow,
    exit_code = status_code,
    success = (status_code == 0),
    report_dir = report_dir,
    final_report = report_text,
    raw_output = res
  )
}

#' Fetch Audited Primary SEC Form 10-K / 20-F Financials
#' 
#' @param ticker Company ticker symbol (e.g. "AAPL", "MSFT")
#' @return List of verified financial metrics, period, and accession number
fetch_sec_financials <- function(ticker) {
  py_exe <- .get_python_path()
  code <- sprintf(
    "import json, sys; from tools.data_layer import get_data_layer; dl = get_data_layer(); data = dl.get_fundamentals('%s'); print(json.dumps(data))",
    ticker
  )
  out <- system2(py_exe, args = c("-c", shQuote(code)), stdout = TRUE, stderr = TRUE)
  tryCatch({
    jsonlite::fromJSON(paste(out, collapse = "\n"))
  }, error = function(e) {
    list(error = paste("Failed to parse JSON output:", paste(out, collapse = "\n")))
  })
}

#' Calculate Deterministic Discounted Cash Flow (DCF) Fair Value
#' 
#' @param base_fcf Most recent fiscal year Free Cash Flow
#' @param growth_rates Numeric vector of projected annual growth rates (e.g. c(0.10, 0.08, 0.06, 0.05, 0.04))
#' @param discount_rate WACC / Discount rate (e.g. 0.09)
#' @param terminal_growth_rate Perpetual growth rate (e.g. 0.025)
#' @param shares_outstanding Diluted shares outstanding
#' @param net_debt Total Debt minus liquid cash
#' @param mid_year Boolean for mid-year discounting convention
#' @param currency ISO currency code
#' @return Structured list with fair value per share, PV breakdown, and formula
calc_dcf <- function(base_fcf, growth_rates, discount_rate, terminal_growth_rate,
                     shares_outstanding, net_debt = 0.0, mid_year = FALSE, currency = "USD") {
  py_exe <- .get_python_path()
  g_json <- jsonlite::toJSON(as.numeric(growth_rates))
  code <- sprintf(
    "import json, sys; from tools.calc.dcf import dcf; res = dcf(base_fcf=%f, growth_rates=%s, discount_rate=%f, terminal_growth_rate=%f, shares_outstanding=%f, net_debt=%f, mid_year=%s, currency='%s'); print(json.dumps(res))",
    base_fcf, g_json, discount_rate, terminal_growth_rate, shares_outstanding, net_debt,
    if (mid_year) "True" else "False", currency
  )
  out <- system2(py_exe, args = c("-c", shQuote(code)), stdout = TRUE, stderr = TRUE)
  tryCatch({
    jsonlite::fromJSON(paste(out, collapse = "\n"))
  }, error = function(e) {
    list(error = paste("DCF calculation error:", paste(out, collapse = "\n")))
  })
}

#' Solve Implied FCF Growth Rate via Reverse DCF
#' 
#' @param current_price Current market share price
#' @param base_fcf Most recent fiscal year Free Cash Flow
#' @param shares_outstanding Diluted shares outstanding
#' @param discount_rate WACC / Discount rate
#' @param terminal_growth_rate Perpetual terminal growth rate
#' @param projection_years Number of projection years (default 5)
#' @param net_debt Net debt position
#' @return List with implied annual growth rate (percentage) and solver convergence status
calc_reverse_dcf <- function(current_price, base_fcf, shares_outstanding, discount_rate,
                             terminal_growth_rate, projection_years = 5, net_debt = 0.0) {
  py_exe <- .get_python_path()
  code <- sprintf(
    "import json, sys; from tools.calc.dcf import reverse_dcf; res = reverse_dcf(current_price=%f, base_fcf=%f, shares_outstanding=%f, discount_rate=%f, terminal_growth_rate=%f, projection_years=%d, net_debt=%f); print(json.dumps(res))",
    current_price, base_fcf, shares_outstanding, discount_rate, terminal_growth_rate, as.integer(projection_years), net_debt
  )
  out <- system2(py_exe, args = c("-c", shQuote(code)), stdout = TRUE, stderr = TRUE)
  tryCatch({
    jsonlite::fromJSON(paste(out, collapse = "\n"))
  }, error = function(e) {
    list(error = paste("Reverse DCF calculation error:", paste(out, collapse = "\n")))
  })
}

#' R Native Monte Carlo DCF Simulation
#' Combines R statistical sampling with analytical DCF logic
#' 
#' @param base_fcf Most recent Free Cash Flow
#' @param shares_outstanding Diluted shares outstanding
#' @param net_debt Net debt position
#' @param wacc_mean Expected WACC mean (e.g. 0.09)
#' @param wacc_sd WACC standard deviation uncertainty (e.g. 0.008)
#' @param growth_mean Expected annual growth mean (e.g. 0.08)
#' @param growth_sd Growth rate standard deviation (e.g. 0.02)
#' @param terminal_g Perpetual terminal growth rate (e.g. 0.025)
#' @param n_sim Number of Monte Carlo iterations (default 1000)
#' @return List of simulated fair values, quantiles (5%, 25%, 50%, 75%, 95%), mean, and standard deviation
r_monte_carlo_dcf <- function(base_fcf, shares_outstanding, net_debt = 0.0,
                              wacc_mean = 0.09, wacc_sd = 0.008,
                              growth_mean = 0.08, growth_sd = 0.02,
                              terminal_g = 0.025, n_sim = 1000) {
  set.seed(42)
  # Sample parameters under economic constraints
  sim_wacc <- pmax(terminal_g + 0.005, pmin(0.30, rnorm(n_sim, mean = wacc_mean, sd = wacc_sd)))
  sim_g <- pmax(-0.20, pmin(0.50, rnorm(n_sim, mean = growth_mean, sd = growth_sd)))
  
  fair_values <- numeric(n_sim)
  
  for (i in seq_len(n_sim)) {
    w <- sim_wacc[i]
    g <- sim_g[i]
    
    # 5-year explicit projection
    cf_t <- base_fcf
    pv_explicit <- 0
    for (t in 1:5) {
      cf_t <- cf_t * (1 + g)
      pv_explicit <- pv_explicit + (cf_t / ((1 + w)^t))
    }
    # Terminal value
    tv <- (cf_t * (1 + terminal_g)) / (w - terminal_g)
    pv_tv <- tv / ((1 + w)^5)
    
    ev <- pv_explicit + pv_tv
    equity_val <- ev - net_debt
    fair_values[i] <- equity_val / shares_outstanding
  }
  
  quants <- quantile(fair_values, probs = c(0.05, 0.25, 0.50, 0.75, 0.95))
  
  list(
    simulations = fair_values,
    mean_fair_value = mean(fair_values),
    sd_fair_value = sd(fair_values),
    median_fair_value = median(fair_values),
    quantiles = quants,
    value_at_risk_5pct = quants["5%"],
    upside_95pct = quants["95%"],
    iterations = n_sim
  )
}

#' Check NVIDIA NIM Hardware / API Acceleration Status
#' 
#' @return List indicating configuration status, active model, and supported models
check_nvidia_status <- function() {
  py_exe <- .get_python_path()
  code <- "import json; from tools.nvidia_client import NvidiaNimClient; c = NvidiaNimClient(); print(json.dumps({'configured': c.is_configured(), 'model': c.default_model, 'models': c.get_supported_models()}))"
  out <- system2(py_exe, args = c("-c", shQuote(code)), stdout = TRUE, stderr = TRUE)
  tryCatch({
    jsonlite::fromJSON(paste(out, collapse = "\n"))
  }, error = function(e) {
    list(configured = FALSE, error = paste(out, collapse = "\n"))
  })
}

#' Run NVIDIA NIM Accelerated Adversarial Stress Test from RStudio
#' 
#' @param ticker Stock ticker symbol (e.g. "NVDA", "AAPL")
#' @param thesis_text Investment thesis narrative to stress-test
#' @param growth_pct Assumed annual revenue/FCF growth rate (%)
#' @param margin_pct Assumed operating margin (%)
#' @return Structured critique with model metadata, latency, and provenance ledger citation
run_nvidia_adversarial_stress <- function(ticker, thesis_text = "", growth_pct = 8.0, margin_pct = 25.0) {
  py_exe <- .get_python_path()
  clean_thesis <- gsub("'", "\\\\'", thesis_text)
  code <- sprintf(
    "import json; from agents.nvidia_agent import NvidiaResearchAgent; ag = NvidiaResearchAgent(); res = ag.run_adversarial_critique('%s', {'revenue_growth_pct': %f, 'operating_margin_pct': %f}, '%s'); print(json.dumps(res))",
    ticker, growth_pct, margin_pct, clean_thesis
  )
  out <- system2(py_exe, args = c("-c", shQuote(code)), stdout = TRUE, stderr = TRUE)
  tryCatch({
    jsonlite::fromJSON(paste(out, collapse = "\n"))
  }, error = function(e) {
    list(error = paste("NVIDIA execution error:", paste(out, collapse = "\n")))
  })
}
