import asyncio


async def bash(command: str) -> tuple[int | None, str, str]:
    """
    Runs a bash command and returns (returncode, stdout, stderr)
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout.decode(), stderr.decode()
