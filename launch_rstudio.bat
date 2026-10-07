@echo off
REM launch_rstudio.bat - Launches RStudio IDE directly configured for Finance Agents
echo =================================================================
echo   Launching RStudio IDE for Finance Research Agents
echo =================================================================

set R_HOME=D:\rstudio\R-4.6.1
set PATH=D:\rstudio\R-4.6.1\bin;%PATH%
set RETICULATE_PYTHON=%~dp0.venv\Scripts\python.exe

start "" "D:\RStudio-IDE\rstudio.exe" "%~dp0finance-agents.Rproj"
echo   RStudio launched successfully with finance-agents.Rproj!
