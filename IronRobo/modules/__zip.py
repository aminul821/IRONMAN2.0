import asyncio
import os
import shutil
import tempfile
import zipfile

from IronRobo import telethn as client
from IronRobo.events import register

MAX_FILES = 50


async def is_register_admin(event, user_id):
    try:
        perms = await event.client.get_permissions(event.chat_id, user_id)
    except Exception:
        return False
    return perms.is_admin or perms.is_creator


async def _check(event, what):
    if not event.is_reply:
        await event.reply(f"Reply to {what}.")
        return False
    if event.is_group and not await is_register_admin(event, event.sender_id):
        await event.reply(
            "Hey, You are not admin. You can't use this command, But you can use in my pm 🙂"
        )
        return False
    return True


@register(pattern="^/zip$")
async def zip_cmd(event):
    if event.fwd_from or not await _check(event, "a file to compress it"):
        return
    reply_message = await event.get_reply_message()
    if not reply_message.media:
        await event.reply("Reply to a file to compress it.")
        return
    mone = await event.reply("⏳️ Please wait...")
    workdir = tempfile.mkdtemp(prefix="zip_")
    try:
        downloaded = await event.client.download_media(reply_message, workdir)
        archive = downloaded + ".zip"

        def _zip():
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(downloaded, os.path.basename(downloaded))

        await asyncio.get_running_loop().run_in_executor(None, _zip)
        await event.client.send_file(
            event.chat_id,
            archive,
            force_document=True,
            allow_cache=False,
            reply_to=event.message.id,
        )
        await mone.delete()
    except Exception as e:
        await mone.edit(f"Failed: {e}")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@register(pattern="^/unzip$")
async def unzip_cmd(event):
    if event.fwd_from or not await _check(event, "a zip file"):
        return
    reply_message = await event.get_reply_message()
    if not reply_message.file or not (reply_message.file.name or "").lower().endswith(".zip"):
        await event.reply("Reply to a .zip file.")
        return
    mone = await event.reply("Processing...")
    workdir = tempfile.mkdtemp(prefix="unzip_")
    extracted = os.path.join(workdir, "extracted")
    try:
        downloaded = await client.download_media(reply_message, workdir)

        def _extract():
            files = []
            with zipfile.ZipFile(downloaded, "r") as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    target = os.path.realpath(os.path.join(extracted, member.filename))
                    # refuse entries that would escape the extraction folder
                    if not target.startswith(os.path.realpath(extracted) + os.sep):
                        continue
                    zf.extract(member, extracted)
                    files.append(target)
            return sorted(files)

        try:
            files = await asyncio.get_running_loop().run_in_executor(None, _extract)
        except zipfile.BadZipFile:
            await mone.edit("That isn't a valid zip file.")
            return
        if not files:
            await mone.edit("The archive is empty.")
            return
        await mone.edit(f"Unzipping now 😌 ({len(files)} files)")
        for single_file in files[:MAX_FILES]:
            try:
                await client.send_file(
                    event.chat_id,
                    single_file,
                    force_document=True,
                    allow_cache=False,
                    reply_to=event.message.id,
                    caption=os.path.relpath(single_file, extracted),
                )
            except Exception as e:
                await client.send_message(
                    event.chat_id,
                    "{} caused `{}`".format(os.path.basename(single_file), str(e)),
                    reply_to=event.message.id,
                )
        if len(files) > MAX_FILES:
            await event.reply(f"Only the first {MAX_FILES} files were sent.")
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


__help__ = """
 • `/zip`*:* Reply to a file to compress it into a zip
 • `/unzip`*:* Reply to a zip file to extract it
"""
__mod_name__ = "Zip"
