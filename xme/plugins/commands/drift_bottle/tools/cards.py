from xme.xmetools.templates import FONTS_STYLE
CARD_SKINS = {
    "默认卡片": {
        "colors": {
            "text-color": "#eee",
            "primary-color": "#3cd3d8",
            "code-color": "#ff4da6",
            "code-bg": "#292b33",
            "date-color": "#aaa",
            "comments-bg": "#292b33",
            "background-color": "#1B1F26",
            "hr-color": "#444",
            "sender-color": "#ddd",
        },
        "str_len": 30,
        "comment_name_len": 12,
        "styles": """

        body {
            word-break: break-all;
            font-family: "Helvetica Neue", "Segoe UI", sans-serif;
            background-color: transparent;
            color: var(--text-color);
            margin: 0;
            padding: 20px;
        }

        main {
            background-color: var(--background-color);
            color: var(--text-color);
            max-width: 600px;
            margin: auto;
            border-radius: 12px;
            padding: 20px;
        }

        .main_content {
            font-size: 1.2em;
            text-indent: 2em;
            word-wrap: normal;
            font-weight: bold;
            max-width: 100%;
            overflow: hidden;
        }

        .small {
        font-size: 0.9em;
        display: flex;
        justify-content: space-between;
        align-items: center;
        }

        .info {
        font-weight: bold;
        color: var(--primary-color);
        }

        hr {
        border: none;
        border-top: 1px solid var(--hr-color);
        margin: 15px 0;
        }

        p {
        line-height: 1.6;
        margin: 10px 0;
        }

        .colored {
        color: var(--primary-color);
        font-weight: 500;
        }

        .infoul, .operateul {
        list-style: none;
        padding: 0;
        margin: 0;
        }

        .infoul {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--sender-color);
        }

        .small-like {
            font-size: 0.9em;
            padding-top: 2px;
            padding-right: 10px;
        }

        .operateul li {
        margin-bottom: 8px;
        }

        .infoul li.colored {
            font-weight: bold;
            color: var(--primary-color);
        }

        .comments div {
            background: var(--comments-bg);
            padding: 7px 12px;
            border-radius: 8px;
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: start;
            font-size: 0.95em;
        }

        .comment-main {
            max-width: calc(100% - 10rem);
        }

        .comments span.colored {
            color: var(--primary-color);
            font-weight: 500;
        }

        .code {
            font-family: "Courier New", monospace;
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 6px;
            color: var(--code-color);
        }

        .operateul {
            padding: 0 10px;
        }

        .operateul li {
            display: flex;
            justify-content: space-between;
        }

        .operateul li p:first-child {
        margin-bottom: 4px;
        }

        .operateul li p {
        margin: 0;
        font-size: 0.95em;
        }

        .operateul span {
        display: inline-block;
        }""",
        "html_body": """<body>
            <main>
                <p style="padding: 0 10px;" class="small">
                    <span class="info">{info0}</span>
                    <span
                        style="color: var(--date-color); float: right; padding: 2px 5px;">{info1}</span>
                </p>
                <hr>
                {info2}
                <hr>
                <ul class="infoul">
                    <li>{info3}</li>
                    <li class="colored">{info4}</li>
                </ul>
                <hr>
                <p class="colored">{info5}</p>
                <div class="comments">
                    {comments}
                </div>
                <hr>
                {suffix}
            </main>
        </body>""",
        "operate_tip": """
            <p class="colored">- 发送下面的消息来执行对应操作 -</p>
            <ul class="operateul">
                <li>
                    <p>
                        <span class="code">-like</span> /
                        <span class="code">-rep</span> /
                        <span class="code">-pure</span>
                    </p>
                    <p>点赞 / 举报 / 申请纯净</p>
                </li>
                <li>
                    <p>
                        <span class="code">
                            -say
                            <span class="colored">
                                (留言内容)
                            </span>
                        </span>
                        /
                        <span class="code">
                            -likesay
                            <span class="colored">
                                (留言编号)
                            </span>
                        </span>
                    </p>
                    <p>
                        留言 / 点赞留言
                    </p>
                </li>
            </ul>
        """,
        "comment": """<div>
                        <p class="comment-main">
                            <span class="colored">{info0}</span>
                            {info1}
                        </p>
                        <p class="colored small-like">
                            {info2}
                        </p>
                    </div>""",
        "comment_content": '："{comment_content}"',
        "comment_suffix": """<div><p style="color: #bbb;">{info3}</p></div>""",
        "no_comment": '<div><p style="color: #bbb;">{content}</p></div>',
        "comment_message": "- 漂流瓶留言 -",
    },
    "基础黄色": {
        "colors": {
            "text-color": "#eee",
            "primary-color": "#ffd752",
            "code-color": "#caff67",
            "code-bg": "#332b29",
            "date-color": "#aaa",
            "comments-bg": "#2b2922",
            "background-color": "#1c1b26",
            "hr-color": "#444",
            "sender-color": "#ddd",
        }
    },
    "基础漠月": {
        "colors": {
            "text-color": "#ffffff",
            "primary-color": "#FFA953",
            "code-color": "#AAFCDC",
            "code-bg": "#3C424E",
            "date-color": "#CDD6EA",
            "comments-bg": "#333842",
            "background-color": "#222330",
            "hr-color": "#3C424E",
            "sender-color": "#CDD6EA",
        }
    },
    "基础九镹": {
        "colors": {
            "text-color": "#f4f7ff",
            "primary-color": "#46CFF1",
            "primary-color2": "#7AEBCD",
            "code-color": "#FBE261",
            "code-bg": "#3D3D57",
            "date-color": "#c0c4d8",
            "comments-bg": "#2f2f44",
            "background-color": "#222333",
            "hr-color": "#3C424E",
            "sender-color": "#c0c4d8",
        },
        "styles": """
            body {
                font-family: "Helvetica Neue", "Segoe UI", sans-serif;
                background-color: transparent;
                color: var(--text-color);
                margin: 0;
                padding: 20px;
            }

            main {
                background-color: var(--background-color);
                color: var(--text-color);
                max-width: 600px;
                margin: auto;
                border-radius: 20px;
                padding: 20px;
            }

            .main_content {
                font-size: 1.2em;
                font-weight: bold;
                text-indent: 2em;
                word-wrap: normal;
                max-width: 100%;
                overflow: hidden;
            }

            .small {
            font-size: 0.9em;
            display: flex;
            justify-content: space-between;
            align-items: center;
            }

            .info {
                font-weight: bold;
                color: var(--primary-color);
            }

            hr {
            border: none;
            border-top: 1px solid var(--hr-color);
            margin: 15px 0;
            }

            p {
            line-height: 1.6;
            margin: 10px 0;
            }

            .colored {
            color: var(--primary-color);
            font-weight: 500;
            }

            .infoul, .operateul {
            list-style: none;
            padding: 0;
            margin: 0;
            }

            .infoul {
                display: flex;
                align-items: center;
                justify-content: space-between;
                color: var(--sender-color);
            }

            .small-like {
                font-size: 0.9em;
                padding-top: 2px;
                padding-right: 10px;
                color: var(--primary-color2);
            }

            .operateul li {
            margin-bottom: 8px;
            }

            .infoul li.colored {
                font-weight: bold;
                color: var(--primary-color2);
            }

            .comments div {
                background: var(--comments-bg);
                padding: 7px 12px;
                border-radius: 8px;
                margin: 6px 0;
                display: flex;
                justify-content: space-between;
                align-items: start;
                font-size: 0.95em;
            }

            .comment-main {
                max-width: calc(100% - 10rem);
            }

            .comments span.colored {
                color: var(--primary-color);
                font-weight: 500;
            }

            .code {
            font-family: "Courier New", monospace;
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 6px;
            color: var(--code-color);
            }

            .operateul {
                padding: 0 10px;
            }

            .operateul li {
                display: flex;
                justify-content: space-between;
            }

            .operateul li p:first-child {
            margin-bottom: 4px;
            }

            .operateul li p {
            margin: 0;
            font-size: 0.95em;
            }

            .operateul span {
            display: inline-block;
            }
        """,
        "comment_suffix": """<div><p style="color: #c0c4d8;">{info3}</p></div>""",
        "no_comment": '<div><p style="color: #c0c4d8;">{content}</p></div>',
    },
    "基础幼龙云": {
        "colors": {
            "text-color": "#f4f7ff",
            "primary-color": "#F36F80",
            "primary-color2": "#F9D1A4",
            "code-color": "#CEF3E9",
            "code-bg": "#3f374b",
            "date-color": "#c2c0d8",
            "comments-bg": "#3e3847",
            "background-color": "#1d1a24",
            "hr-color": "#3e3c4e",
            "sender-color": "#c2c0d8",
        },
        "styles": """
            body {
                font-family: "Helvetica Neue", "Segoe UI", sans-serif;
                background-color: transparent;
                color: var(--text-color);
                margin: 0;
                padding: 20px;
            }

            main {
                background-color: var(--background-color);
                color: var(--text-color);
                max-width: 600px;
                margin: auto;
                border-radius: 20px;
                padding: 20px;
            }

            .main_content {
                font-size: 1.2em;
                font-weight: bold;
                text-indent: 2em;
                word-wrap: normal;
                max-width: 100%;
                overflow: hidden;
            }

            .small {
            font-size: 0.9em;
            display: flex;
            justify-content: space-between;
            align-items: center;
            }

            .info {
                font-weight: bold;
                color: var(--primary-color);
            }

            hr {
            border: none;
            border-top: 1px solid var(--hr-color);
            margin: 15px 0;
            }

            p {
            line-height: 1.6;
            margin: 10px 0;
            }

            .colored {
            color: var(--primary-color);
            font-weight: 500;
            }

            .infoul, .operateul {
            list-style: none;
            padding: 0;
            margin: 0;
            }

            .infoul {
                display: flex;
                align-items: center;
                justify-content: space-between;
                color: var(--sender-color);
            }

            .small-like {
                font-size: 0.9em;
                padding-top: 2px;
                padding-right: 10px;
                color: var(--primary-color2);
            }

            .operateul li {
            margin-bottom: 8px;
            }

            .infoul li.colored {
                font-weight: bold;
                color: var(--primary-color2);
            }

            .comments div {
                background: var(--comments-bg);
                padding: 7px 12px;
                border-radius: 8px;
                margin: 6px 0;
                display: flex;
                justify-content: space-between;
                align-items: start;
                font-size: 0.95em;
            }

            .comment-main {
                max-width: calc(100% - 10rem);
            }

            .comments span.colored {
                color: var(--primary-color);
                font-weight: 500;
            }

            .code {
            font-family: "Courier New", monospace;
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 6px;
            color: var(--code-color);
            }

            .operateul {
                padding: 0 10px;
            }

            .operateul li {
                display: flex;
                justify-content: space-between;
            }

            .operateul li p:first-child {
            margin-bottom: 4px;
            }

            .operateul li p {
            margin: 0;
            font-size: 0.95em;
            }

            .operateul span {
            display: inline-block;
            }
        """,
        "comment_suffix": """<div><p style="color: #c2c0d8;">{info3}</p></div>""",
        "no_comment": '<div><p style="color: #c2c0d8;">{content}</p></div>',
    },
    "基础漠星": {
        "colors": {
            "text-color": "#FFFFFF",
            "primary-color": "#fa4134",
            "primary-color2": "#ffa545",
            "code-color": "#4bff84",
            "code-bg": "#333440",
            "date-color": "#c0c0d8",
            "comments-bg": "#333440",
            "background-color": "#1a1a24",
            "hr-color": "#333440",
            "sender-color": "#c0c0d8",
            "light-color": "#ffdf4eab",
            "light-color2": "#4bff84d2",
        },
        "styles": """

        body {
            font-family: "Helvetica Neue", "Segoe UI", sans-serif;
            background-color: transparent;
            color: var(--text-color);
            margin: 0;
            padding: 20px;
        }

        main {
            background-color: var(--background-color);
            color: var(--text-color);
            max-width: 600px;
            margin: auto;
            border-radius: 20px;
            padding: 20px;
        }

        .main_content {
            font-size: 1.2em;
            font-weight: bold;
            text-indent: 2em;
            word-wrap: normal;
            max-width: 100%;
            overflow: hidden;
        }

        .small {
        font-size: 0.9em;
        display: flex;
        justify-content: space-between;
        align-items: center;
        }

        .info {
            font-weight: bold;
            color: var(--primary-color);
        }

        hr {
        border: none;
        border-top: 1px solid var(--hr-color);
        margin: 15px 0;
        }

        p {
        line-height: 1.6;
        margin: 10px 0;
        }

        .colored {
        color: var(--primary-color);
        font-weight: 500;
        }

        .infoul, .operateul {
        list-style: none;
        padding: 0;
        margin: 0;
        }

        .infoul {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--sender-color);
        }

        .small-like {
            font-size: 0.9em;
            padding-top: 2px;
            padding-right: 10px;
            color: var(--primary-color2);
            text-shadow: 0 0 10px var(--light-color);
        }

        .operateul li {
        margin-bottom: 8px;
        }

        .infoul li.colored {
            font-weight: bold;
            color: var(--primary-color2);
            text-shadow: 0 0 10px var(--light-color);
        }

        .comments div {
            background: var(--comments-bg);
            padding: 7px 12px;
            border-radius: 8px;
            margin: 6px 0;
            display: flex;
            justify-content: space-between;
            align-items: start;
            font-size: 0.95em;
        }

        .comment-main {
            max-width: calc(100% - 10rem);
        }

        .comments span.colored {
            color: var(--primary-color);
            font-weight: 500;
        }

        .code .colored {
            text-shadow: none;
            color: var(--code-color);
            text-shadow: 0 0 10px var(--light-color2);
        }

        .code {
            font-family: "Courier New", monospace;
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 6px;
            text-shadow: 0 0 10px var(--light-color);
            color: var(--primary-color2);
        }

        .operateul {
            padding: 0 10px;
        }

        .operateul li {
            display: flex;
            justify-content: space-between;
        }

        .operateul li p:first-child {
        margin-bottom: 4px;
        }

        .operateul li p {
        margin: 0;
        font-size: 0.95em;
        }

        .operateul span {
        display: inline-block;
        }
        """,
        "comment_suffix": """<div><p style="color: #c0c0d8;">{info3}</p></div>""",
        "no_comment": '<div><p style="color: #c0c0d8;">{content}</p></div>',
    },
    "基础红色": {
        "colors": {
            "text-color": "#eee",
            "primary-color": "#f56363",
            "code-color": "#ffb24d",
            "code-bg": "#332b29",
            "date-color": "#aaa",
            "comments-bg": "#24222b",
            "background-color": "#1c1b26",
            "hr-color": "#444",
            "sender-color": "#ddd",
        }
    },
    "基础绿色": {
        "colors": {
            "text-color": "#eee",
            "primary-color": "#91ff87",
            "code-color": "#55c1ff",
            "code-bg": "#29332c",
            "date-color": "#aaa",
            "comments-bg": "#222b28",
            "background-color": "#1b1c26",
            "hr-color": "#444",
            "sender-color": "#ddd",
        }
    },
    "基础蓝色": {
        "colors": {
            "text-color": "#eee",
            "primary-color": "#87ddff",
            "code-color": "#fff781",
            "code-bg": "#292b33",
            "date-color": "#aaa",
            "comments-bg": "#22242b",
            "background-color": "#1b1c26",
            "hr-color": "#444",
            "sender-color": "#ddd",
        }
    },
    "基础粉色": {
        "colors": {
            "text-color": "#eee",
            "primary-color": "#fca8ff",
            "code-color": "#7bb4ff",
            "code-bg": "#312933",
            "date-color": "#aaa",
            "comments-bg": "#28222b",
            "background-color": "#1b1c26",
            "hr-color": "#444",
            "sender-color": "#ddd",
        }
    },
    "基础白色": {
        "colors": {
            "text-color": "#000000",
            "primary-color": "#3040ca",
            "code-color": "#b93075",
            "code-bg": "#c9d2f7",
            "date-color": "#525252",
            "comments-bg": "#cacedb",
            "background-color": "#ebedf0",
            "hr-color": "#cecece",
            "sender-color": "#19191b",
        },
        "comment_suffix": """<div><p style="color: #333;">{info3}</p></div>""",
        "no_comment": '<div><p style="color: #333;">{content}</p></div>',
    },
    "星际工业": {
        "colors": {
            "text-color" : "#E7ECFF",
            "primary-color" : "#97DAFF",
            "border-color" : "#8187AA",
            "code-color" : "#ffc578",
            "code-bg" : "#292b33",
            "date-color" : "#8187AA",
            "comments-bg" : "#292b33",
            "background-color" : "#11121d",
            "hr-color" : "#4440",
            "border-inner-color": "#424660",
            "sender-color" : "#B6BCDB",
        },
        "styles": FONTS_STYLE + r"""
        body {
            font-family: "Helvetica Neue", "Segoe UI", sans-serif;
            background-color: transparent;
            color: var(--text-color);
            margin: 0;
            word-break: break-all;
            padding: 20px;
        }

        main {
            position: relative;
            background-color: var(--background-color);
            color: var(--text-color);
            clip-path: polygon(0% 40px, 40px 0%, 100% 0%, 100% calc(100% - 40px), calc(100% - 40px) 100%, 0% 100%);
            max-width: 600px;
            margin: auto;
            /* border-radius: 12px; */
            z-index: 1;
            border-radius: 0;
            padding: 25px;
            /* margin: 2px; */
            margin-bottom: 0;
            /* border: 2px solid var(--border-color); */
        }

        .border {
            background: var(--border-color);
            max-width: 600px;
            margin: auto;
            padding: 2px;
            clip-path: polygon(0% 40px, 40px 0%, 100% 0%, 100% calc(100% - 40px), calc(100% - 40px) 100%, 0% 100%);
        }

        .main_content {
            font-size: 1.2em;
            font-weight: bold;
            text-indent: 2em;
            word-wrap: normal;
            max-width: 100%;
            overflow: hidden;
        }

        .small {
        font-size: 0.9em;
        display: flex;
        justify-content: space-between;
        align-items: center;
        }

        .info {
        font-weight: bold;
        color: var(--primary-color);
        }

        hr {
        border: none;
        border-top: 1px solid var(--hr-color);
        margin: 15px 0;
        }

        p {
        line-height: 1.6;
        margin: 10px 0;
        }

        .colored {
        color: var(--primary-color);
        font-weight: 500;
        }

        .infoul, .operateul {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .infoul {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--sender-color);
        }

        .infoul li:nth-child(1) {
            max-width: 370px;
        }

        .small-like {
            font-size: 0.9em;
            padding-top: 2px;
            margin: 3px 0;
            padding-right: 10px;
        }

        .operateul li {
        margin-bottom: 8px;
        }

        .infoul li.colored {
            font-weight: bold;
            color: var(--primary-color);
        }

        .comments {
            border-radius: 12px;
            border: 2px solid var(--border-inner-color);
            border-top: 0;
            margin: 0 10px;
            padding: 5px 0;
            border-bottom: 0;
        }

        .comments div:nth-last-child(1) {
            border-bottom: none;
        }

        .comments>div {
            position: relative;
            padding: 5px 20px;
            display: flex;
            justify-content: space-between;
            align-items: start;
            font-size: 0.95em;
        }

        .comment-main {
            max-width: calc(100% - 14rem);
            display: flex;
            /* margin: 5px 0; */
            flex-direction: column;
        }

        .comment-main p {
            margin: 3px 0;
        }

        .comments p.colored {
            color: var(--primary-color);
            font-weight: 500;
        }

        .code {
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 6px;
            color: var(--code-color);
        }

        .operateul {
            padding: 0 10px;
        }

        .operateul li {
            display: flex;
            justify-content: space-between;
        }

        .operateul li p:first-child {
        margin-bottom: 4px;
        }

        .operateul li p {
        margin: 0;
        font-size: 0.95em;
        }

        .operateul span {
            display: inline-block;
        }

        """,
        "html_body": """<body>
            <div class="border">
                <main class="orbitron">
                    <p style="padding: 0 10px;" class="small">
                        <span class="info">{info0}</span>
                        <span
                            style="color: var(--date-color); float: right; padding: 2px 5px;">{info1}</span>
                    </p>
                    <hr>
                    {info2}
                    <hr>
                    <ul class="infoul">
                        <li>{info3}</li>
                        <li class="colored">{info4}</li>
                    </ul>
                    <hr>
                    <p class="colored">{info5}</p>
                    <div class="comments">
                        {comments}
                    </div>
                    <hr>
                    {suffix}
                </main>
            </div>
        </body>""",
        "comment_suffix": """<div><p style="color: #B6BCDB;">{info3}</p></div>""",
        "comment": """<div>
                        <div class="comment-main">
                            <p class="colored">{info0}</p>
                            <p>{info1}</p>
                        </div>
                        <p class="colored small-like">
                            {info2}
                        </p>
                    </div>""",
        "no_comment": '<div><p style="color: #B6BCDB;">{content}</p></div>',
        "comment_message": "- MESSAGES -",
        "operate_tip": """
            <p class="colored">- OPERATIONS -</p>
            <ul class="operateul">
                <li>
                    <p>
                        <span class="code">-like</span> /
                        <span class="code">-rep</span> /
                        <span class="code">-pure</span>
                    </p>
                    <p>点赞 / 举报 / 申请纯净</p>
                </li>
                <li>
                    <p>
                        <span class="code">
                            -say
                            <span class="colored">
                                (留言内容)
                            </span>
                        </span>
                        /
                        <span class="code">
                            -likesay
                            <span class="colored">
                                (留言编号)
                            </span>
                        </span>
                    </p>
                    <p>
                        留言 / 点赞留言
                    </p>
                </li>
            </ul>
        """,
        "str_len": 30,
        "comment_name_len": 18,
        "comment_content": '"{comment_content}"',
    },
    "流浪地球": {
        "colors": {
            "text-color" : "#000000",
            "primary-color" : "#db1515",
            "border-color" : "#45494E",
            "code-color" : "#393b3f",
            "code-bg" : "#CCCDD1",
            "date-color" : "#38383a",
            "comments-bg" : "#d7d7dd",
            "background-color" : "#E9EAEE",
            "hr-color" : "#c0bcbc",
            "border-inner-color": "#8B8F95",
            "sender-color" : "#3e4047",
        },
        "styles": FONTS_STYLE + r"""
        body {
            font-family: "Helvetica Neue", "Segoe UI", sans-serif;
            background-color: transparent;
            color: var(--text-color);
            margin: 0;
            word-break: break-all;
            padding: 20px;
        }

        main {
            position: relative;
            background-color: var(--background-color);
            color: var(--text-color);
            clip-path: polygon(0px 0%, calc(100% - 30px) 0%, 100% 30px, 100% calc(100% - 30px), calc(100% - 30px) 100%, 30px 100%, 0% calc(100% - 30px), 0% 30px);
            max-width: 600px;
            margin: auto;
            /* border-radius: 12px; */
            z-index: 1;
            border-radius: 0;
            padding: 25px;
            /* margin: 2px; */
            margin-bottom: 0;
            /* border: 2px solid var(--border-color); */
        }

        .border {
            background: var(--border-color);
            max-width: 600px;
            margin: auto;
            padding: 4px;
            clip-path: polygon(0px 0%, calc(100% - 30px) 0%, 100% 30px, 100% calc(100% - 30px), calc(100% - 30px) 100%, 30px 100%, 0% calc(100% - 30px), 0% 30px);
        }

        .main_content {
            font-size: 1.2em;
            font-weight: bold;
            text-indent: 2em;
            word-wrap: normal;
            max-width: 100%;
            overflow: hidden;
        }

        .small {
        font-size: 0.9em;
        display: flex;
        justify-content: space-between;
        align-items: center;
        }

        .info {
        font-weight: bold;
        color: var(--primary-color);
        }

        hr {
        border: none;
        border-top: 1px solid var(--hr-color);
        margin: 15px 0;
        }

        p {
        line-height: 1.6;
        margin: 10px 0;
        }

        .colored {
        color: var(--primary-color);
        font-weight: 500;
        }

        .infoul, .operateul {
        list-style: none;
        padding: 0;
        margin: 0;
        }

        .infoul {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--sender-color);
        }

        .small-like {
            font-size: 0.9em;
            padding-top: 2px;
            padding-right: 10px;
        }

        .operateul li {
            margin-bottom: 8px;
        }

        .infoul li.colored {
            font-weight: bold;
            color: var(--primary-color);
        }

        .infoul li:nth-child(1) {
            max-width: 370px;
        }

        .comments {
            /* background: var(--comments-bg); */
            /* border-radius: 12px; */
            /* clip-path: polygon(30px 0%, calc(100% - 30px) 0%, 100% 30px, 100% calc(100% - 30px), calc(100% - 30px) 100%, 30px 100%, 0% calc(100% - 30px), 0% 30px); */
            clip-path: polygon(0 0%, calc(100% - 30px) 0%, 100% 30px, 100% calc(100% - 30px), calc(100% - 30px) 100%, 30px 100%, 0% 100%);
            margin: 0 10px;
            padding: 5px 0;
        }

        .comments div:nth-last-child(1) {
            border-bottom: none;
        }

        .comments div {
            border-left: 3px solid var(--border-inner-color);
            background: var(--comments-bg);
            /* border-bottom: 1px solid var(--comments-bg); */
            position: relative;
            padding: 0px 15px;
            margin: 10px 0;
            /* border-radius: 8px; */
            /* margin: 5px 0; */
            display: flex;
            justify-content: space-between;
            align-items: start;
            font-size: 0.95em;
        }

        .comments div p {
            margin: 8px 0;
        }

        .comment-main {
            max-width: calc(100% - 11rem);
        }

        .comments span.colored {
            color: var(--primary-color);
            font-weight: 500;
        }

        .code {
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 6px;
            color: var(--code-color);
        }

        .operateul {
            padding: 0 10px;
        }

        .operateul li {
            display: flex;
            justify-content: space-between;
        }

        .operateul li p:first-child {
        margin-bottom: 4px;
        }

        .operateul li p {
        margin: 0;
        font-size: 0.95em;
        }

        .operateul span {
        display: inline-block;
        }

        """,
        "html_body": """<body>
            <div class="border">
                <main class="orbitron">
                    <p style="padding: 0 10px;" class="small">
                        <span class="info">{info0}</span>
                        <span
                            style="color: var(--date-color); float: right; padding: 2px 5px;">{info1}</span>
                    </p>
                    <hr>
                    {info2}
                    <hr>
                    <ul class="infoul">
                        <li>{info3}</li>
                        <li class="colored" style="margin-bottom: 0;">{info4}</li>
                    </ul>
                    <hr>
                    <p class="colored">{info5}</p>
                    <div class="comments">
                        {comments}
                    </div>
                    <hr>
                    {suffix}
                </main>
            </div>
        </body>""",
        "comment_suffix": """<div><p style="color: #4d4f5a;">{info3}</p></div>""",
        "no_comment": '<div><p style="color: #4d4f5a;">{content}</p></div>',
        "comment_message": "- 留言消息 -",
        "operate_tip": """
            <p class="colored">- 操作选项 -</p>
            <ul class="operateul">
                <li>
                    <p>
                        <span class="code">-like</span> /
                        <span class="code">-rep</span> /
                        <span class="code">-pure</span>
                    </p>
                    <p>点赞 / 举报 / 申请纯净</p>
                </li>
                <li>
                    <p>
                        <span class="code">
                            -say
                            <span class="colored">
                                (留言内容)
                            </span>
                        </span>
                        /
                        <span class="code">
                            -likesay
                            <span class="colored">
                                (留言编号)
                            </span>
                        </span>
                    </p>
                    <p>
                        留言 / 点赞留言
                    </p>
                </li>
            </ul>
        """,
        "str_len": 30,
    },
    "联合矿业": {
        "colors": {
            "text-color" : "#fafafa",
            "primary-color" : "#ffce72",
            "border-color" : "#adacb3",
            "code-color" : "#ff9e78",
            "code-bg" : "#292b33",
            "date-color" : "#86899c",
            "comments-bg" : "#212430",
            "background-color" : "#11121d",
            "hr-color" : "#4440",
            "border-inner-color": "#7c6d50",
            "sender-color" : "#b8bac9",
        },
        "styles": FONTS_STYLE + r"""
        body {
            font-family: "Helvetica Neue", "Segoe UI", sans-serif;
            background-color: transparent;
            color: var(--text-color);
            margin: 0;
            word-break: break-all;
            padding: 20px;
        }

        main {
            position: relative;
            background-color: var(--background-color);
            color: var(--text-color);
            clip-path: polygon(0% 30px, 30px 0%, 100% 0%, 100% 100%, calc(100% - 30px) 100%, 0% 100%);
            max-width: 600px;
            margin: auto;
            /* border-radius: 12px; */
            z-index: 1;
            border-radius: 0;
            padding: 25px;
            /* margin: 2px; */
            margin-bottom: 0;
            /* border: 2px solid var(--border-color); */
        }

        .border {
            background: var(--border-color);
            max-width: 600px;
            margin: auto;
            padding: 2px;
        }

        .main_content {
            font-size: 1.2em;
            font-weight: bold;
            text-indent: 2em;
            word-wrap: normal;
            max-width: 100%;
            overflow: hidden;
        }

        .small {
        font-size: 0.9em;
        display: flex;
        justify-content: space-between;
        align-items: center;
        }

        .info {
        font-weight: bold;
        color: var(--primary-color);
        }

        hr {
        border: none;
        border-top: 1px solid var(--hr-color);
        margin: 15px 0;
        }

        p {
        line-height: 1.6;
        margin: 10px 0;
        }

        .colored {
        color: var(--primary-color);
        font-weight: 500;
        }

        .infoul, .operateul {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .infoul {
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: var(--sender-color);
        }

        .infoul li:nth-child(1) {
            max-width: 370px;
        }

        .small-like {
            font-size: 0.9em;
            padding-top: 2px;
            margin: 3px 0;
            padding-right: 10px;
        }

        .operateul li {
        margin-bottom: 8px;
        }

        .infoul li.colored {
            font-weight: bold;
            color: var(--primary-color);
        }

        .comments {
            /* background: var(--comments-bg); */
            /* border-radius: 12px; */
            margin: 0 10px;
            padding: 5px 0;
        }

        .comments div:nth-last-child(1) {
            border-bottom: none;
        }

        .comments>div {
            border-left: 2px solid var(--border-inner-color);
            background: var(--comments-bg);
            /* border-bottom: 1px solid var(--comments-bg); */
            position: relative;
            padding: 5px 20px;
            /* border-radius: 8px; */
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: start;
            font-size: 0.95em;
        }

        /* .comments div p { */
            /* margin: 10px 0; */
        /* } */

        .comment-main {
            max-width: calc(100% - 14rem);
            display: flex;
            /* margin: 5px 0; */
            flex-direction: column;
        }

        .comment-main p {
            margin: 3px 0;
        }

        .comments p.colored {
            color: var(--primary-color);
            font-weight: 500;
        }

        .code {
            background: var(--code-bg);
            padding: 2px 6px;
            border-radius: 6px;
            color: var(--code-color);
        }

        .operateul {
            padding: 0 10px;
        }

        .operateul li {
            display: flex;
            justify-content: space-between;
        }

        .operateul li p:first-child {
        margin-bottom: 4px;
        }

        .operateul li p {
        margin: 0;
        font-size: 0.95em;
        }

        .operateul span {
            display: inline-block;
        }

        """,
        "html_body": """<body>
            <div class="border">
                <main class="orbitron">
                    <p style="padding: 0 10px;" class="small">
                        <span class="info">{info0}</span>
                        <span
                            style="color: var(--date-color); float: right; padding: 2px 5px;">{info1}</span>
                    </p>
                    <hr>
                    {info2}
                    <hr>
                    <ul class="infoul">
                        <li>{info3}</li>
                        <li class="colored">{info4}</li>
                    </ul>
                    <hr>
                    <p class="colored">{info5}</p>
                    <div class="comments">
                        {comments}
                    </div>
                    <hr>
                    {suffix}
                </main>
            </div>
        </body>""",
        "comment_suffix": """<div><p style="color: #b8bac9;">{info3}</p></div>""",
        "comment": """<div>
                        <div class="comment-main">
                            <p class="colored">{info0}</p>
                            <p>{info1}</p>
                        </div>
                        <p class="colored small-like">
                            {info2}
                        </p>
                    </div>""",
        "no_comment": '<div><p style="color: #b8bac9;">{content}</p></div>',
        "comment_message": "/// MESSAGES ///",
        "operate_tip": """
            <p class="colored">/// OPERATIONS ///</p>
            <ul class="operateul">
                <li>
                    <p>
                        <span class="code">-like</span> /
                        <span class="code">-rep</span> /
                        <span class="code">-pure</span>
                    </p>
                    <p>点赞 / 举报 / 申请纯净</p>
                </li>
                <li>
                    <p>
                        <span class="code">
                            -say
                            <span class="colored">
                                (留言内容)
                            </span>
                        </span>
                        /
                        <span class="code">
                            -likesay
                            <span class="colored">
                                (留言编号)
                            </span>
                        </span>
                    </p>
                    <p>
                        留言 / 点赞留言
                    </p>
                </li>
            </ul>
        """,
        "str_len": 30,
        "comment_name_len": 18,
        "comment_content": '"{comment_content}"',
    },

}