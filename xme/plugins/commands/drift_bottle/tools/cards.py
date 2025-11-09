
CARD_SKINS = {
    "default": {
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
                        style="color: #aaa; float: right; padding: 2px 5px;">{info1}</span>
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
        "comment_suffix": """<div><p style="color: #bbb;">{info3}</p></div>""",
        "no_comment": '<div><p style="color: #bbb;">{content}</p></div>',
    },
    "漂流瓶卡片-基础黄色": {
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
    "漂流瓶卡片-基础红色": {
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
}