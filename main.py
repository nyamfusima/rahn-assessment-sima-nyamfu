"""Entry point for the FitDesk enquiry assistant.

Usage:
    python main.py                      (prompts for the customer message)
    python main.py "How much is the 12-session pack?"
"""

if __name__ == "__main__":
    try:
        from fitdesk.cli import main

        exit_code = main()
    except KeyboardInterrupt:  # e.g. Ctrl+C while modules are still loading
        print("\nCancelled. Nothing was recorded.")
        exit_code = 130
    raise SystemExit(exit_code)
