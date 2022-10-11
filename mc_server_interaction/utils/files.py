from pathlib import Path

import aiofiles


async def async_copy(source: Path, dest: Path, chunk_size: int = 128 * 1024):
    async def read_in_chunks(infile):
        while True:
            c = await infile.read(chunk_size)
            if c:
                yield c
            else:
                return

    async with aiofiles.open(source, "rb") as source_file, aiofiles.open(
            dest, "wb"
    ) as dest_file:
        async for chunk in read_in_chunks(source_file):
            await dest_file.write(chunk)


async def async_copytree(source: Path, dest: Path, override: bool = False):
    if not source.is_dir():
        raise NotADirectoryError()
    print(dest)
    if not dest.is_dir():
        dest.mkdir()
    elif any(dest.iterdir()) and not override:
        raise OSError(39)
    for entry in source.iterdir():
        temp = dest / entry.name
        if entry.is_dir():
            temp.mkdir()
            await async_copytree(entry, temp, override=override)
        else:
            print(entry, dest)
            await async_copy(entry, temp)