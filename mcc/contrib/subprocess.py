import asyncio


async def bash(command: str) -> str | tuple[int, str, str]:
    """
    Runs a bash command and returns text output if successful. If an error occurs it returns (returncode, stdout, stderr)
    """
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode == 0:
        return stdout.decode()
    return proc.returncode, stdout.decode(), stderr.decode()
