import feedparser
from datetime import datetime, timedelta

def catch_179rss():
    """抓取179的RSS"""
    rss = feedparser.parse('https://blog.xzadudu179.top/atom.xml')
    rss_list = [{'title': entry['title'], 'link':entry['link'], 'published':(datetime.strptime(str(entry['published']), "%Y-%m-%dT%H:%M:%S.%fZ") + timedelta(hours=8)).strftime("%Y年%m月%d日 %H:%M:%S"), 'tags': entry['tags']} for entry in rss['entries']]
    return rss_list

def show_rss(rss_list, k):
    result = ""
    for i, rss in enumerate(rss_list):
        if i >= k:
            break
        result += f"{i + 1}. 《{rss['title']}》\n\t发布时间: {rss['published']}\n\t链接: {rss['link']}\n\t标签: {', '.join([tag['term'] for tag in rss['tags']])}\n\n"
        # print(rss)
    return result.strip()

if __name__ == "__main__":
    print(show_rss(catch_179rss(), 5))
