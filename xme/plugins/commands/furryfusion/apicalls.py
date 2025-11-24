from xme.xmetools.reqtools import fetch_data

async def get_countdown() -> dict:
    content = await fetch_data("https://api.furryfusion.net/service/countdown?mode=1")
    return content

async def search(content, mode="name"):
    return await fetch_data(f"https://api.furryfusion.net/service/screen?content={content}&mode={mode}")