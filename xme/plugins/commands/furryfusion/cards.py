from xme.xmetools.templates import FONTS_STYLE

STATE = {
    0: "活动结束",
    1: "预告中",
    2: "售票中",
    3: "活动中",
    4: "活动取消"
}

def get_fusion_card(card_data: dict):
    state_class = {
        0: "cancelled",
        1: "",
        2: "",
        3: "on-event",
        4: "cancelled",
    }
    if card_data["state"] in [0, 3, 4]:
        daysleft_str = {
            0: "活动结束",
            3: "正在进行",
            4: "活动取消"
        }[card_data["state"]]
    else:
        daysleft_str = f"剩余 {card_data['time_surplus']} 天"
    time_formatted = ".".join(card_data["time_start"].split(".")[1:]) + " - " + ".".join(card_data["time_end"].split(".")[1:])
    return f"""
        <section class="card">
            <div class="img">
                <div class="cover">
                    <div class="top">
                        <h1 class="title">{card_data['title']}</h1>
                        <div>
                            <p>{card_data['address_province']}·{card_data['address_city']}</p>
                            <p class="{state_class[card_data['state']]}">{STATE[card_data['state']]}</p>
                        </div>
                    </div>
                    <div class="bottom">
                        <div>

                            <p>{card_data['name']}</p>
                            <p>{time_formatted}</p>
                        </div>
                        <div class="btm_right">
                            <p class="remaining daysleft {state_class[card_data['state']]}">
                                {daysleft_str}
                            </p>

                        </div>
                    </div>
                </div>
            </div>
        </section>
    """
def get_countdown_cards(data: list[dict]):
    html_head = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Document</title>
            <style>
    """ + FONTS_STYLE + """
            :root {
                --strong-color: #94d8ff;
                --text-color: #fffef6;
                --background: #BEAD90;
                --info-color: #9696a0;
                --border-color: #36363e;
                --background-color: #1b1b25;
                --primary-color: #78B9FF;
                --error-color: #ff7a85;
                --on-event-color: #7bffb6;
            }

            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-size: 1rem;
                color: var(--text-color);
                font-family: "Helvetica Neue", "Noto Sans CJK SC", "Noto Sans SC", Geist Variable, -apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Heiti SC, WenQuanYi Micro Hei, normal;
            }

            h2 span {
                font-size: 2rem;
            }
            h2 {
                border-bottom: 1px solid var(--border-color);
                padding-bottom: 8px;
                margin-bottom: 20px;
            }

            h4 span {
                font-size: 1.2rem;
                font-weight: normal;
                margin-left: 30px;
            }

            h4 {
                display: flex;
                align-items: center;
                /* flex-direction: row; */
                margin-top: 15px;
            }

            .title {
                overflow: hidden;
                word-break: keep-all;
                max-width: 8em;
            }

            .rec-circsmall {
                width: 12px;
                height: 12px;
                border: 3px solid var(--border-color);
                background: var(--background-color);
                border-radius: 999%;
                margin-left: -32.4px;
                position: relative;
                /* top: 23px; */
            }
            .rec-timeline * {
                font-family: 'Orbitron', "Helvetica Neue", "Noto Sans CJK SC", "Noto Sans SC", Geist Variable, -apple-system, BlinkMacSystemFont, PingFang SC, Microsoft YaHei, Heiti SC, WenQuanYi Micro Hei, normal;
                letter-spacing: 0.06em;
            }
            .rec-timeline {
                width: 96%;
                padding: 0px 0 50px 25px;
                margin: auto;
                border-left: 3px solid;
                border-image: linear-gradient(#0000 0%, var(--border-color) 100px, var(--border-color) 90%, #0000 100%) 1;
            }
            .rec-circbig {
                width: 20px;
                height: 20px;
                border: 3px solid var(--primary-color);
                background: var(--background-color);
                border-radius: 999%;
                margin-left: -36.5px;
                position: relative;
                top: 30px;
                box-shadow: 0 0 50px 5px transparent;
            }
            .rec-circbig + span {
                font-weight: normal;
            }
            .rec-uparrow {
                position: relative;
                top: 20.3px;
                right: 7.9px;
                color: var(--border-color);
                font-size: 25px;
            }

            .card {
                width: 400px;
                margin: 20px;
                border-radius: 20px;
                overflow: hidden;
                border: 4px solid rgba(255, 255, 255, 0.116);
                box-shadow: 0 0 15px #FFF1;
            }

            body {
                background-color: transparent;
            }


            .main-container {
                width: 1500px;
                padding: 25px;
                background: var(--background-color);
                /* background: url("./img/background/1791.png"); */
                /* background-size: cover; */
            }

            .img {
                max-width: 400px;
                height: 150px;
                position: relative;
                background-size: cover;
                background-position: center;
                background-color: #24252e;
            }


            .cover {
                width: 100%;
                height: 100%;
                /* background-color: #0009; */
                backdrop-filter: blur(5px);
                /* padding: 20px; */
                position: relative;
            }

            .top {
                width: 100%;
                display: flex;
                justify-content: space-between;
                padding: 10px 20px;
                align-items: center;
            }

            .top p:nth-child(1) {
                padding-top: 10px;
            }

            .top p {
                text-align: right;
            }

            .bottom {
                position: absolute;
                bottom: 0;
                /* color: white; */
                display: flex;
                justify-content: space-between;
                width: 100%;
                align-items: end;
                padding: 20px;
                /* padding-right: 40px; */
            }


            h1 {
                font-size: 2rem;
                /* color: var(--strong-color); */
            }

            .data {
                padding: 10px;
                padding-top: 0;
            }

            .right {
                position: relative;
            }

            .daysleft {
                color: var(--strong-color);
                font-size: 1.5rem;
                font-weight: 600;
            }

            .btm_right {
                text-align: right;
            }

            .cancelled {
                color: var(--error-color);
            }

            .on-event {
                color: var(--on-event-color);
            }

            .month {
                display: flex;
                flex-wrap: wrap;
                /* justify-content; */
            }
        </style>
    </head>
    <body>
        <div class="main-container">
            <div class="rec-timeline">
    """
    html_bottom = """
                </div>
            </div>
        </body>
    </html>
    """
    html_content = ""
    for year_datas in data:
        year = year_datas["year"]
        html_content += f"""
        <h2>
            <div class="rec-circbig"></div>
            <span>{year}</span>
        </h2>
        """
        for month_datas in year_datas["data"]:
            html_content += f"""
            <h4>
                <div class="rec-circsmall"></div>
                <span>{year}.{month_datas['month']}</span>
            </h4>
            <div class="month">
            """
            for card_data in month_datas['list']:
                html_content += get_fusion_card(card_data)
            html_content += "</div>"
    return html_head + html_content + html_bottom