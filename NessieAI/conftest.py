# Collection guard for any pytest run that walks NessieAI/. Imports nothing,
# declares no fixtures and no pytest_plugins, on purpose.
#   history/       frozen records: never collected, never rewritten
#   docker/        image build contexts; cc-runtime keeps its own tests and
#                  pytest config, run from that directory
#   chat_frontend/ Node package; its vitest and Playwright suites run with npm
collect_ignore = ["history", "docker", "chat_frontend"]
