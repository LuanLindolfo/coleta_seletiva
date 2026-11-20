import base64
import mimetypes
import os
import streamlit as st

st.set_page_config(page_title="Coleta Seletiva - Streamlit", layout="centered")
st.title("♻️ Coleta Seletiva (Modo 1: HTML5 Canvas no Streamlit)")
st.caption("Usa ESPAÇO para iniciar, Setas ou A/D para mover e teclas 1 a 5 para trocar a lixeira.")

PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_ASSETS = os.path.join(PASTA_RAIZ, "dependencias")

arquivos_em_falta = []
arquivos_carregados = 0


def asset_to_data_uri(nome_arquivo):
    global arquivos_carregados
    caminho = os.path.join(PASTA_ASSETS, nome_arquivo)
    if not os.path.exists(caminho):
        arquivos_em_falta.append(nome_arquivo)
        return ""
    mime, _ = mimetypes.guess_type(caminho)
    if nome_arquivo.lower().endswith(".svg"):
        mime = "image/svg+xml"
    elif nome_arquivo.lower().endswith(".wav"):
        mime = "audio/wav"
    elif not mime:
        mime = "application/octet-stream"

    with open(caminho, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    arquivos_carregados += 1
    return f"data:{mime};base64,{b64}"


cenario_jogo_nome = (
    "693507866d39d7257377845b34fa7426.png"
    if os.path.exists(os.path.join(PASTA_ASSETS, "693507866d39d7257377845b34fa7426.png"))
    else "693507866d39d7257377845b34fa7426.jpg"
)

assets_uri = {
    "bg_instrucoes": asset_to_data_uri("49c8433626dd2759e7cea2697335b886.svg"),
    "bg_jogo": asset_to_data_uri(cenario_jogo_nome),
    "bg_fim": asset_to_data_uri("1c3010490bfc4f7d96f7f1756c21f9de.svg"),
    "bg_vitoria": asset_to_data_uri("7e15832ed1b37bd73d3418030b27bc8e.svg"),
    "botao_iniciar": asset_to_data_uri("83289741ad14f2292187479156d68b15.svg"),
    "lixeira": [
        asset_to_data_uri("e0abe584a75ba6c8c5dbff995d9be90a.svg"),  # 1: papel
        asset_to_data_uri("4bfcb0e25246a5ac747ae14778b9e751.svg"),  # 2: plastico
        asset_to_data_uri("d610b30c19b7e082ed98d0597592531b.svg"),  # 3: vidro
        asset_to_data_uri("d388958fbb03f3ac73d464126f2b11f8.svg"),  # 4: metal
        asset_to_data_uri("506b5e3fb9f22601584dd04468c217c7.svg"),  # 5: organico
    ],
    "lixo": [
        asset_to_data_uri("750b6d248d55e43f035febc2ee61b693.svg"),  # lixo1
        asset_to_data_uri("b2946c689f98c56cc2ada16de60018b6.svg"),  # lixo2
        asset_to_data_uri("b5ac32ca01d749ce3b57e19b1ebcf8b0.svg"),  # lixo3
        asset_to_data_uri("9e6a1febff68f2f7427c406b27a378c8.svg"),  # lixo4
        asset_to_data_uri("d08c060f34f414e5d4274a1fe74c57c3.svg"),  # lixo5
        asset_to_data_uri("a380e70730f191243ddb989d1be972ea.svg"),  # lixo6
        asset_to_data_uri("c4f8588495bad0fb9cf808597db39fc3.svg"),  # lixo7
        asset_to_data_uri("e78af7aec183657375aff54ad57fefa9.svg"),  # lixo8
        asset_to_data_uri("80a6400b5fd9929c929a52b0aba67957.svg"),  # lixo9
        asset_to_data_uri("b8b976c0e35ef9fe7d816751c09aabc5.svg"),  # lixo10
    ],
    "dica": [
        asset_to_data_uri("943525abb609ad165c88c55dd37bc555.svg"),  # dica1
        asset_to_data_uri("561f2c58021e4ec10b58f009ef391431.svg"),  # dica2
        asset_to_data_uri("77c71fc36e7f8d5e6f9b239f1aa6ef0a.svg"),  # dica3
        asset_to_data_uri("7f683ab17ac6b7aac94b7af86074fbaa.svg"),  # dica4
        asset_to_data_uri("a7b7b55ac7696e64f8dfcd5102922329.svg"),  # dica5
    ],
    "som_acerto": asset_to_data_uri("cfc50a412483f6aadb83adeff596052e.wav"),
    "som_erro": asset_to_data_uri("768bd6a764ab62a6a6764e4147c3e615.wav"),
    "som_fim": asset_to_data_uri("e3635ab50a93193e53cd16f047446add.wav"),
    "som_vitoria": asset_to_data_uri("b8251bb11c300af3582aba1239082d41.wav"),
}

if not os.path.isdir(PASTA_ASSETS):
    st.error(f"Pasta 'dependencias' não encontrada em: {PASTA_ASSETS}")
elif arquivos_em_falta:
    st.warning(
        f"Foram carregados {arquivos_carregados} ficheiros, mas {len(arquivos_em_falta)} não foram encontrados em 'dependencias/': "
        + ", ".join(arquivos_em_falta)
    )

html_jogo = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  body {{
    margin: 0;
    background: #111;
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: Arial, sans-serif;
  }}
  canvas {{
    border: 2px solid #444;
    border-radius: 6px;
    background: #1b2a1e;
    outline: none;
  }}
</style>
</head>
<body>
<canvas id="game" width="480" height="360" tabindex="0"></canvas>
<script>
const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");
canvas.focus();
canvas.addEventListener("click", () => canvas.focus());

const W = 480, H = 360;
const URIS = {assets_uri};

function loadImg(src) {{
  const img = new Image();
  if (src) img.src = src;
  return img;
}}

function loadAudio(src) {{
  if (!src) return null;
  const a = new Audio(src);
  return a;
}}

function playSound(aud) {{
  if (!aud) return;
  try {{
    aud.currentTime = 0;
    aud.play().catch(() => {{}});
  }} catch (e) {{}}
}}

const imgs = {{
  bg: {{
    instrucoes: loadImg(URIS.bg_instrucoes),
    jogo: loadImg(URIS.bg_jogo),
    fim: loadImg(URIS.bg_fim),
    vitoria: loadImg(URIS.bg_vitoria),
  }},
  botao: loadImg(URIS.botao_iniciar),
  lixeira: URIS.lixeira.map(loadImg),
  lixo: URIS.lixo.map(loadImg),
  dica: URIS.dica.map(loadImg),
}};

const sons = {{
  acerto: loadAudio(URIS.som_acerto),
  erro: loadAudio(URIS.som_erro),
  fim: loadAudio(URIS.som_fim),
  vitoria: loadAudio(URIS.som_vitoria),
}};

function scratchToCanvas(x, y, w, h, rotCenter = null) {{
  if (rotCenter) {{
    return [W / 2 + x - rotCenter[0], H / 2 - y - rotCenter[1]];
  }}
  return [W / 2 + x - w / 2, H / 2 - y - h / 2];
}}

function imagemPronta(img) {{
  return Boolean(img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0);
}}

let estado = "instrucoes";
let pontos = 0;
let vidas = 5;
let velocidade = 3.0;
let ultimoTipo = 1;

let lixeiraX = 0;
let lixeiraY = -135;
let lixeiraFantasia = 1;
let lixeiraVisivel = false;

let dicaVisivel = false;
let dicaFantasia = 1;
let dicaAte = 0;

let clones = [];
let proximoSpawn = 0;
let ultimoAumentoVel = 0;
let encerrarEm = 0;

const teclas = {{}};

window.addEventListener("keydown", (e) => {{
  teclas[e.code] = true;
  if (["Space", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.code)) {{
    e.preventDefault();
  }}
  if (estado === "instrucoes" && e.code === "Space") {{
    iniciarPartida();
  }} else if (estado === "jogo") {{
    if (e.key === "1") lixeiraFantasia = 1;
    if (e.key === "2") lixeiraFantasia = 2;
    if (e.key === "3") lixeiraFantasia = 3;
    if (e.key === "4") lixeiraFantasia = 4;
    if (e.key === "5") lixeiraFantasia = 5;
  }}
}});

window.addEventListener("keyup", (e) => {{
  teclas[e.code] = false;
}});

function iniciarPartida() {{
  const agora = performance.now();
  estado = "jogo";
  pontos = 0;
  vidas = 5;
  velocidade = 3.0;
  ultimoTipo = 1;
  lixeiraX = 0;
  lixeiraY = -135;
  lixeiraFantasia = 1;
  lixeiraVisivel = true;
  dicaVisivel = false;
  clones = [];
  ultimoAumentoVel = agora;
  proximoSpawn = agora + 1000 + (1100 + Math.random() * 900);
}}

function dispararErro(tipoErrado) {{
  if (vidas > 0) {{
    vidas -= 1;
    ultimoTipo = tipoErrado;
  }}
  playSound(sons.erro);
  dicaFantasia = ultimoTipo;
  dicaVisivel = true;
  dicaAte = performance.now() + 2600;
}}

function rectsColidem(a, b) {{
  return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
}}

function loop(agora) {{
  if (estado === "jogo") {{
    if (agora - ultimoAumentoVel >= 6000) {{
      velocidade += 0.4;
      ultimoAumentoVel = agora;
    }}

    if (teclas["ArrowLeft"] || teclas["KeyA"]) lixeiraX -= 14;
    if (teclas["ArrowRight"] || teclas["KeyD"]) lixeiraX += 14;
    if (lixeiraX > 205) lixeiraX = 205;
    if (lixeiraX < -205) lixeiraX = -205;

    if (agora >= proximoSpawn) {{
      const item = Math.floor(Math.random() * 10) + 1;
      const tipo = ((item - 1) % 5) + 1;
      clones.push({{
        x: Math.floor(Math.random() * 401) - 200,
        y: 175,
        item,
        tipo
      }});
      proximoSpawn = agora + (1100 + Math.random() * 900);
    }}

    const imgL = imgs.lixeira[lixeiraFantasia - 1];
    const lw = (imgL && imgL.naturalWidth) || 80;
    const lh = (imgL && imgL.naturalHeight) || 84;
    const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);
    const rectLixeira = {{ x: lx, y: ly, w: lw, h: lh }};

    const restantes = [];
    for (const c of clones) {{
      c.y -= velocidade;
      const imgC = imgs.lixo[c.item - 1];
      const cw = (imgC && imgC.naturalWidth) || 50;
      const ch = (imgC && imgC.naturalHeight) || 50;
      const [cx, cy] = scratchToCanvas(c.x, c.y, cw, ch);
      const rectItem = {{ x: cx, y: cy, w: cw, h: ch }};

      if (rectsColidem(rectItem, rectLixeira)) {{
        if (lixeiraFantasia === c.tipo) {{
          pontos += 1;
          playSound(sons.acerto);
        }} else {{
          dispararErro(c.tipo);
        }}
        continue;
      }}

      if (c.y < -170) {{
        vidas -= 1;
        playSound(sons.erro);
        continue;
      }}

      restantes.push(c);
    }}
    clones = restantes;

    if (dicaVisivel && agora >= dicaAte) {{
      dicaVisivel = false;
    }}

    if (vidas < 1) {{
      estado = "fim";
      lixeiraVisivel = false;
      dicaVisivel = false;
      clones = [];
      playSound(sons.fim);
      encerrarEm = agora + 2500;
    }} else if (pontos > 19) {{
      estado = "vitoria";
      lixeiraVisivel = false;
      dicaVisivel = false;
      clones = [];
      playSound(sons.vitoria);
      encerrarEm = agora + 2500;
    }}
  }} else if (estado === "fim" || estado === "vitoria") {{
    if (agora >= encerrarEm) {{
      estado = "instrucoes";
    }}
  }}

  // Renderização
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = "#1b2a1e";
  ctx.fillRect(0, 0, W, H);

  const bgAtual = imgs.bg[estado];
  if (imagemPronta(bgAtual)) {{
    ctx.drawImage(bgAtual, 0, 0, W, H);
  }} else if (estado === "instrucoes") {{
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 20px Arial";
    ctx.textAlign = "center";
    ctx.fillText("COLETA SELETIVA", W / 2, 110);
    ctx.font = "15px Arial";
    ctx.fillText("Clica aqui e prime ESPAÇO para começar", W / 2, 155);
    ctx.fillText("Setas / A-D: mover | 1 a 5: escolher lixeira", W / 2, 185);
    ctx.textAlign = "left";
  }}

  if (estado === "instrucoes" && imagemPronta(imgs.botao)) {{
    const escala = Math.floor(agora / 300) % 2 === 1 ? 1.1 : 1.0;
    const bw = imgs.botao.naturalWidth * escala;
    const bh = imgs.botao.naturalHeight * escala;
    const [bx, by] = scratchToCanvas(36, 28, bw, bh, [147.5 * escala, -121.4 * escala]);
    ctx.drawImage(imgs.botao, bx, by, bw, bh);
  }} else if (estado === "jogo") {{
    if (lixeiraVisivel) {{
      const imgL = imgs.lixeira[lixeiraFantasia - 1];
      const lw = (imgL && imgL.naturalWidth) || 80;
      const lh = (imgL && imgL.naturalHeight) || 84;
      const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);
      if (imagemPronta(imgL)) {{
        ctx.drawImage(imgL, lx, ly, lw, lh);
      }} else {{
        ctx.fillStyle = "#2e7d32";
        ctx.fillRect(lx, ly, lw, lh);
      }}
    }}

    for (const c of clones) {{
      const imgC = imgs.lixo[c.item - 1];
      const cw = (imgC && imgC.naturalWidth) || 50;
      const ch = (imgC && imgC.naturalHeight) || 50;
      const [cx, cy] = scratchToCanvas(c.x, c.y, cw, ch);
      if (imagemPronta(imgC)) {{
        ctx.drawImage(imgC, cx, cy, cw, ch);
      }} else {{
        ctx.fillStyle = "#fbc02d";
        ctx.fillRect(cx, cy, cw, ch);
      }}
    }}

    if (dicaVisivel) {{
      const imgD = imgs.dica[dicaFantasia - 1];
      const dw = (imgD && imgD.naturalWidth) || 440;
      const dh = (imgD && imgD.naturalHeight) || 60;
      const [dx, dy] = scratchToCanvas(0, 95, dw, dh, [220, 30]);
      if (imagemPronta(imgD)) {{
        ctx.drawImage(imgD, dx, dy, dw, dh);
      }}
    }}

    ctx.fillStyle = "rgba(30, 30, 30, 0.85)";
    ctx.fillRect(5, 5, 115, 24);
    ctx.fillRect(5, 32, 115, 24);
    ctx.fillStyle = "#fff";
    ctx.font = "bold 15px Arial";
    ctx.fillText(`Pontos: ${{pontos}}`, 12, 22);
    ctx.fillText(`Vidas: ${{vidas}}`, 12, 49);
  }}

  requestAnimationFrame(loop);
}}

requestAnimationFrame(loop);
</script>
</body>
</html>
"""

if hasattr(st, "iframe"):
    try:
        st.iframe(html_jogo, height=400, width=520)
    except TypeError:
        import streamlit.components.v1 as components
        components.html(html_jogo, height=400, width=520)
else:
    import streamlit.components.v1 as components
    components.html(html_jogo, height=400, width=520)
