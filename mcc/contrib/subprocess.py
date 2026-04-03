from subprocess import check_output, STDOUT


def shell(command: str) -> str:
    """
    Runs a shell command and returns both stdout/stderror as string output
    """
    return check_output(command, shell=True, text=True, stderr=STDOUT)
