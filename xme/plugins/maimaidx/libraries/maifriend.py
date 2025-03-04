from PIL import Image
from xme.xmetools import imgtools

def gen_maifriend(qq, size=640):
    avatar = imgtools.get_qq_avatar(qq, size).resize((int(size * 0.8), int(size * 0.8))).convert("RGBA")
    frame = Image.open("./xme/plugins/maimaidx/static/mai/frame.png").resize((size, size))
    # 创建一个新的空白画布，大小为最大图片的尺寸
    new_image = Image.new("RGB", (frame.width, frame.height))

    # 计算中心位置
    avatar_x = (frame.width - avatar.width) // 2
    avatar_y = (frame.height - avatar.height) // 2 + int(size * 0.03)

    # 粘贴图片
    new_image.paste(avatar, (avatar_x, avatar_y))
    new_image.paste(frame, (0, 0), frame.convert("RGBA").getchannel('A'))
    # new_image.save(path, "PNG")
    return new_image
