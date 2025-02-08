from zhipuai import ZhipuAI
from nonebot import on_command, CommandSession
from nonebot.argparse import ArgumentParser
import traceback
from json import JSONDecodeError
import keys
from xme.xmetools.command_tools import send_session_msg
import xme.xmetools.text_tools as t
from xme.xmetools.doc_tools import CommandDoc, shell_like_usage
import json

alias = ['翻译', 'trans']
arg_usage = shell_like_usage("OPTION", [
    {
        "name": "help",
        "abbr": "h",
        "desc": "查看帮助"
    },
    {
        "name": "language",
        "abbr": "l",
        "desc": "指定要翻译成的语言"
    }
])

__plugin_name__ = 'translate'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='翻译内容',
    introduction='使用 ChatGLM-4 模型进行文本翻译，参数可填如英语 法语 俄语 中文等\n注意：该指令可能将会在不久后删除',
    usage=f'(需要翻译的文本内容) [OPTION]\n{arg_usage}',
    permissions=[],
    alias=alias
))

@on_command('translate', aliases=alias, only_to_me=False, shell_like=True, permission=lambda x: x.is_groupchat)
async def _(session: CommandSession):
    parser = ArgumentParser(session=session, usage=__plugin_usage__)
    parser.add_argument('-l', '--language')
    parser.add_argument('text', nargs='+')
    args = parser.parse_args(session.argv)
    print(args)
    # return
    # arg = session.current_arg_text.strip()
    try:
        client = ZhipuAI(api_key=keys.GLM_API_KEY)
        # print("翻译")
        # text = (await session.aget(prompt="请在下面发送你想要翻译的内容吧~"))
        text = ' '.join(args.text)
        # 如果中文字符大于等于 30% 则说明是中文，翻译成英文
        lan = "中文"
        if not args.language:
            if t.chinese_proportion(text) >= 0.3:
                lan = "英文"
        else:
            lan = args.language
        print(f"请求翻译成 {lan} 中")
        text_content = f"``` {lan}\n{text}\n```"
        print(text_content)
        response = client.chat.completions.create(
            model="glm-4",  # 请填写您要调用的模型名称
            messages=[
                {"role": "system", "content": "你是一个翻译程序，你所做的是提取文本框的所有内容并且将它们翻译成文本框注释的语言，作为json字典。格式是 {\"text\":\"翻译后的文本\"} 例如：``` 英文\n这是一段话```，你需要输出例如：{\"text\":\"This is a paragraph\"}。如果你不知道指定的语言是什么例如``` 外星文\n这是一段话```请直接输出 {\"text\":\"|NONE|\"}，除此之外不要输出任何内容。"},
                {"role": "user", "content": text_content},
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content
        print(content)
        content = json.loads(content)['text']
        if content.strip() == "|NONE|":
            await send_session_msg(session, f"无法翻译哦，因为你先前指定了一个未知的语言 \"{lan}\"，或是ChatGLM并不知道你要翻译的内容的语言是什么 xwx")
            return
        await send_session_msg(session, f"以下是 GLM-4 输出结果：\n{content}")
    except JSONDecodeError as ex:
        await send_session_msg(session, f"json 解析出错，原 AI 返回内容为：\n{content}")
    except Exception as ex:
        print(f"执行出错：{ex}\n{traceback.format_exc()}")
        await send_session_msg(session, f"呜呜呜，执行出错了，以下是错误信息：{ex}")