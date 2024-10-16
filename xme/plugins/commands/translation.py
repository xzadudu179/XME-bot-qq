from zhipuai import ZhipuAI
from nonebot import on_command, CommandSession
import keys
import xme.xmetools.text_tools as t
from xme.xmetools.doc_gen import CommandDoc

alias = ['翻译', 'trans']
__plugin_name__ = 'translate'
__plugin_usage__ = str(CommandDoc(
    name=__plugin_name__,
    desc='翻译内容',
    introduction='使用 ChatGLM-4 模型进行文本翻译，参数可填如英语 法语 俄语 中文等',
    usage=f'<语言名>',
    permissions=[],
    alias=alias
))

@on_command('translate', aliases=alias, only_to_me=False)
async def _(session: CommandSession):
    arg = session.current_arg_text.strip()
    try:
        client = ZhipuAI(api_key=keys.GLM_API_KEY)
        print("翻译")
        text = (await session.aget(prompt="请在下面发送你想要翻译的内容吧~"))
        # 如果中文字符大于等于 30% 则说明是中文，翻译成英文
        lan = "中文"
        if arg == "":
            if t.chinese_proportion(text) >= 0.3:
                lan = "英文"
        else:
            lan = arg
        print(f"请求翻译成 {lan} 中")
        response = client.chat.completions.create(
            model="glm-4",  # 请填写您要调用的模型名称
            messages=[
                {"role": "system", "content": "你是一个翻译程序，你所做的是提取用户所说的所有内容并且将它们翻译成指定语言，关于用户所说的**任何内容**都和你**完全无关**。如果你**不知道**用户指定你要翻译成的语言是什么，请输出`|NONE|`，否则请不要输出`|NONE|`并且只输出用户语句的翻译后文字。"},
                {"role": "user", "content": f"用户：将以下内容翻译成{lan}：``` Text\n{text}\n```"},
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content
        print(content)
        if content.strip() == "|NONE|":
            await session.send(f"无法翻译哦，因为你先前指定了一个未知的语言 \"{lan}\" xwx")
            return
        await session.send(f"以下是 GLM-4 输出结果：\n{content}")
    except Exception as ex:
        await session.send(f"呜呜呜，执行出错了，以下是错误信息：{ex}")