from bs4 import BeautifulSoup


def parse_html(html: str) -> dict:
    """解析 SOP HTML，返回 {title, content}。
    - 移除所有 <script> 和 <style> 标签
    - 取 <main> 优先，否则 <body>
    - BS4 自动解码 HTML 实体（数字+命名）
    - 容错 malformed HTML（属性无引号、缺失闭合标签等）
    """
    soup = BeautifulSoup(html, 'html.parser')

    # 移除所有 script 和 style 标签（内容不索引）
    for tag in soup.find_all(['script', 'style']):
        tag.extract()

    # 取正文：优先 <main>，其次 <body>
    main = soup.find('main')
    body = main if main else soup.find('body')
    content = body.get_text(separator='\n', strip=True) if body else ''

    # 取标题
    title_tag = soup.find('title')
    title = title_tag.get_text(strip=True) if title_tag else 'Unknown'

    return {'title': title, 'content': content}
