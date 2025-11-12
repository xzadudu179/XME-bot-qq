from xme.xmetools.filetools import b64_encode_file

HIUN_COLORS = """
:root {
    --color-primary: #97DAFF;
    --color-primary2: #78B9FF;
    --bg-color: #020211;
    --text-color: #E7ECFF;
    --grey-color: #8187AA;
    --code-color: #8187AA55;
    --border-color: #5D617D;
}
"""
FONTS_STYLE = f"""
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Regular.otf')}) format('opentype');
    font-weight: normal;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Light.otf')}) format('opentype');
    font-weight: 300;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-UltraLight.otf')}) format('opentype');
    font-weight: 100;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Medium.otf')}) format('opentype');
    font-weight: 500;
    font-style: normal;
}}
@font-face {{
    font-family: 'Melete';
    src: url(data:font/otf;base64,{b64_encode_file('./static/fonts/Melete/Melete-Bold.otf')}) format('opentype');
    font-weight: 600;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Medium.ttf')}) format('truetype');
    font-weight: normal;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Light.ttf')}) format('truetype');
    font-weight: 300;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Bold.ttf')}) format('truetype');
    font-weight: 600;
    font-style: normal;
}}
@font-face {{
    font-family: 'Orbitron';
    src: url(data:font/ttf;base64,{b64_encode_file('./static/fonts/Orbitron/Orbitron Black.ttf')}) format('truetype');
    font-weight: 700;
    font-style: normal;
}}
.orbitron {{
    font-family: "Orbitron", "Noto Sans CJK SC", "Noto Sans SC";
    letter-spacing: 0.05em;
}}
.electrolize {{
    font-family: "Electrolize", "Noto Sans CJK SC", "Noto Sans SC";
}}
.melete {{
    font-family: "Melete", "Noto Sans CJK SC", "Noto Sans SC";
}}
"""
