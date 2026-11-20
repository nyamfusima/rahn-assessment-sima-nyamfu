"""Human approval gate: prints the draft and asks "Send? (y/n)" (FR-05, Playbook Rule 2).

Only an explicit "y" approves. Any other answer repeats the prompt (SRS section 7).
End of input or Ctrl+C is treated as "not approved", never as "y".
"""

from typing import Callable

PROMPT = "Send? (y/n) "


def ask_for_approval(
    draft_text: str,
    is_escalation: bool,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> bool:
    output_fn("")
    output_fn("Draft reply:")
    output_fn(f"  {draft_text}")
    if is_escalation:
        output_fn("Note: this draft is an escalation; some or all facts are not in the approved data.")
    while True:
        try:
            answer = input_fn(PROMPT)
        except (EOFError, KeyboardInterrupt):
            output_fn("")
            output_fn("No answer received. Treating as not approved.")
            return False
        answer = answer.strip().lower()
        if answer == "y":
            return True
        if answer == "n":
            return False
        output_fn("Please answer y or n.")
