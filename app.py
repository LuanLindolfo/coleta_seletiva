import base64
import json
import mimetypes
import os
import urllib.request
import urllib.error
from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="♻️ Coleta Seletiva",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_ASSETS = os.path.join(PASTA_RAIZ, "dependencias")
ARQUIVO_RANKING_LOCAL = os.path.join(PASTA_RAIZ, "ranking.json")

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "ranking.json"


def ler_ranking_github():
    """Lê o ranking.json da API do GitHub e retorna os 5 melhores. Retorna (lista, sha, erro_str)."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return None, None, "GITHUB_TOKEN ou GITHUB_REPO não configurados nos Secrets."

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}?t={int(datetime.now().timestamp())}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            conteudo_decodificado = base64.b64decode(payload["content"]).decode("utf-8")
            dados = json.loads(conteudo_decodificado)
            if not isinstance(dados, list):
                dados = []
            ordenados = sorted(
                dados,
                key=lambda x: (
                    -int(x.get("pontos", 0)),
                    -int(x.get("fase", 1)),
                    x.get("data", ""),
                ),
            )
            return ordenados[:5], payload["sha"], None
    except urllib.error.HTTPError as e:
        detalhe = e.read().decode("utf-8", errors="ignore")
        if e.code == 404:
            return [], None, None
        return None, None, f"Erro HTTP {e.code}: {detalhe}"
    except Exception as e:
        return None, None, f"Erro de conexão: {e}"


# --- CSS PERSONALIZADO ---
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f2027 0%, #1b3b2b 50%, #132a1e 100%);
        color: #f1f8e9;
    }
    .header-box {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(129, 199, 132, 0.3);
        border-radius: 16px;
        padding: 18px 24px;
        margin-bottom: 18px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }
    .header-box h1 {
        margin: 0;
        font-size: 2.1rem;
        color: #a5d6a7;
    }
    .header-box p {
        margin: 6px 0 0 0;
        color: #dce775;
        font-size: 0.95rem;
    }
    .bin-card {
        border-radius: 10px;
        padding: 8px 6px;
        text-align: center;
        font-weight: bold;
        font-size: 0.85rem;
        color: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        margin-bottom: 10px;
    }
    .ranking-card {
        background: rgba(20, 32, 24, 0.85);
        border: 1px solid rgba(129, 199, 132, 0.35);
        border-radius: 14px;
        padding: 16px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="header-box">
        <h1>♻️ Desafio da Coleta Seletiva</h1>
        <p>📱 <b>Mobile:</b> Arraste o dedo para mover e toque nos botões das lixeiras • 💻 <b>PC:</b> Setas / A-D e teclas 1 a 5</p>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.markdown('<div class="bin-card" style="background:#1565c0;">1 · PAPEL</div>', unsafe_allow_html=True)
c2.markdown('<div class="bin-card" style="background:#c62828;">2 · PLÁSTICO</div>', unsafe_allow_html=True)
c3.markdown('<div class="bin-card" style="background:#2e7d32;">3 · VIDRO</div>', unsafe_allow_html=True)
c4.markdown('<div class="bin-card" style="background:#f9a825; color:#1b1b1b;">4 · METAL</div>', unsafe_allow_html=True)
c5.markdown('<div class="bin-card" style="background:#5d4037;">5 · ORGÂNICO</div>', unsafe_allow_html=True)

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
        asset_to_data_uri("e0abe584a75ba6c8c5dbff995d9be90a.svg"),
        asset_to_data_uri("4bfcb0e25246a5ac747ae14778b9e751.svg"),
        asset_to_data_uri("d610b30c19b7e082ed98d0597592531b.svg"),
        asset_to_data_uri("d388958fbb03f3ac73d464126f2b11f8.svg"),
        asset_to_data_uri("506b5e3fb9f22601584dd04468c217c7.svg"),
    ],
    "lixo": [
        asset_to_data_uri("750b6d248d55e43f035febc2ee61b693.svg"),
        asset_to_data_uri("b2946c689f98c56cc2ada16de60018b6.svg"),
        asset_to_data_uri("b5ac32ca01d749ce3b57e19b1ebcf8b0.svg"),
        asset_to_data_uri("9e6a1febff68f2f7427c406b27a378c8.svg"),
        asset_to_data_uri("d08c060f34f414e5d4274a1fe74c57c3.svg"),
        asset_to_data_uri("a380e70730f191243ddb989d1be972ea.svg"),
        asset_to_data_uri("c4f8588495bad0fb9cf808597db39fc3.svg"),
        asset_to_data_uri("e78af7aec183657375aff54ad57fefa9.svg"),
        asset_to_data_uri("80a6400b5fd9929c929a52b0aba67957.svg"),
        asset_to_data_uri("b8b976c0e35ef9fe7d816751c09aabc5.svg"),
    ],
    "dica": [
        asset_to_data_uri("943525abb609ad165c88c55dd37bc555.svg"),
        asset_to_data_uri("561f2c58021e4ec10b58f009ef391431.svg"),
        asset_to_data_uri("77c71fc36e7f8d5e6f9b239f1aa6ef0a.svg"),
        asset_to_data_uri("7f683ab17ac6b7aac94b7af86074fbaa.svg"),
        asset_to_data_uri("a7b7b55ac7696e64f8dfcd5102922329.svg"),
    ],
    "som_acerto": asset_to_data_uri("cfc50a412483f6aadb83adeff596052e.wav"),
    "som_erro": asset_to_data_uri("768bd6a764ab62a6a6764e4147c3e615.wav"),
    "som_fim": asset_to_data_uri("e3635ab50a93193e53cd16f047446add.wav"),
    "som_vitoria": asset_to_data_uri("b8251bb11c300af3582aba1239082d41.wav"),
}

if not os.path.isdir(PASTA_ASSETS):
    st.error(f"Pasta 'dependencias' não encontrada em: {PASTA_ASSETS}")
elif arquivos_em_falta:
    st.warning(f"Arquivos ausentes ({len(arquivos_em_falta)}): " + ", ".join(arquivos_em_falta))

col_jogo, col_ranking = st.columns([1.45, 1], gap="large")

with col_jogo:
    nome_jogador = st.text_input(
        "👤 Seu nome antes de começar a jogar:",
        value="Jogador",
        max_chars=20,
        placeholder="Digite seu apelido...",
    )
    nome_seguro = (nome_jogador or "Jogador").strip()[:20] or "Jogador"

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <style>
      * {
        box-sizing: border-box;
        -webkit-tap-highlight-color: transparent;
        user-select: none;
      }
      body {
        margin: 0;
        padding: 4px;
        background: transparent;
        display: flex;
        flex-direction: column;
        align-items: center;
        font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
        touch-action: manipulation;
        overflow: hidden;
      }
      .game-wrapper {
        position: relative;
        width: 100%;
        max-width: 520px;
        display: flex;
        flex-direction: column;
        align-items: center;
      }
      canvas {
        width: 100%;
        height: auto;
        aspect-ratio: 4 / 3;
        border: 2px solid #4caf50;
        border-radius: 14px;
        background: #1b2a1e;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.45);
        outline: none;
        touch-action: none;
        display: block;
      }
      #banner-status-podio {
        display: none;
        position: absolute;
        bottom: 112px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(15, 30, 20, 0.95);
        color: #ffe082;
        font-weight: 700;
        font-size: 13px;
        padding: 10px 18px;
        border-radius: 12px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.65);
        border: 2px solid #4caf50;
        z-index: 20;
        white-space: nowrap;
      }
      .lixeiras-touch {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 6px;
        width: 100%;
        margin-top: 10px;
      }
      .btn-lixeira {
        border: 2px solid transparent;
        border-radius: 10px;
        padding: 10px 2px;
        font-weight: 700;
        font-size: 12px;
        color: #fff;
        cursor: pointer;
        transition: transform 0.08s ease, border-color 0.15s ease;
        text-align: center;
        box-shadow: 0 3px 8px rgba(0,0,0,0.3);
      }
      .btn-lixeira:active {
        transform: scale(0.94);
      }
      .btn-lixeira.ativa {
        border-color: #ffffff;
        transform: translateY(-3px);
        box-shadow: 0 0 12px rgba(255, 255, 255, 0.65);
      }
      .b1 { background: #1565c0; }
      .b2 { background: #c62828; }
      .b3 { background: #2e7d32; }
      .b4 { background: #f9a825; color: #1b1b1b; }
      .b5 { background: #5d4037; }

      .barra-inferior {
        margin-top: 10px;
        width: 100%;
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        font-size: 12px;
        color: #c8e6c9;
      }
      .acoes {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
      }
      .btn-mini {
        background: #233327;
        color: #e8f5e9;
        border: 1px solid #4caf50;
        border-radius: 8px;
        padding: 7px 12px;
        font-size: 12px;
        font-weight: 600;
        cursor: pointer;
      }
      .btn-mini:active {
        background: #354f3c;
      }
    </style>
    </head>
    <body>
    <div class="game-wrapper">
      <canvas id="game" width="480" height="360" tabindex="0"></canvas>

      <div id="banner-status-podio">⏳ Salvando no Top 5...</div>

      <div class="lixeiras-touch">
        <button type="button" class="btn-lixeira b1 ativa" data-tipo="1">1·Papel</button>
        <button type="button" class="btn-lixeira b2" data-tipo="2">2·Plást.</button>
        <button type="button" class="btn-lixeira b3" data-tipo="3">3·Vidro</button>
        <button type="button" class="btn-lixeira b4" data-tipo="4">4·Metal</button>
        <button type="button" class="btn-lixeira b5" data-tipo="5">5·Orgân.</button>
      </div>

      <div class="barra-inferior">
        <span id="status-foco">Toque na tela ou aperte ESPAÇO</span>
        <div class="acoes">
          <button class="btn-mini" id="btn-iniciar-top" type="button">▶ Jogar</button>
          <button class="btn-mini" id="btn-pausar" type="button">⏸ Pausar</button>
          <button class="btn-mini" id="btn-mute" type="button">🔊 Som</button>
        </div>
      </div>
    </div>

    <script>
    const canvas = document.getElementById("game");
    const ctx = canvas.getContext("2d");
    const statusFoco = document.getElementById("status-foco");
    const btnPausar = document.getElementById("btn-pausar");
    const btnIniciarTop = document.getElementById("btn-iniciar-top");
    const btnMute = document.getElementById("btn-mute");
    const botoesLixeira = document.querySelectorAll(".btn-lixeira");
    const bannerPodio = document.getElementById("banner-status-podio");

    const W = 480, H = 360;
    const META_VITORIA = 40;
    const URIS = __ASSETS_URI__;
    const STORAGE_KEY = "coleta_seletiva_recorde_v3";
    const NOME_JOGADOR = __NOME_JOGADOR__;
    const GH_TOKEN = __GH_TOKEN__;
    const GH_REPO = __GH_REPO__;

    // Configuração das 5 Fases (todos os 10 itens de lixo caem desde a Fase 1)
    const FASES_CONFIG = [
      {
        numero: 1,
        nome: "Aquecimento",
        descricao: "Todos os tipos de lixo • Ritmo inicial",
        minPts: 0,
        velBase: 2.0,
        spawnMin: 1450,
        spawnMax: 2100,
        ventoAmp: 0,
        maxSimultaneos: 2
      },
      {
        numero: 2,
        nome: "Ritmo Urbano",
        descricao: "Queda mais rápida!",
        minPts: 5,
        velBase: 2.5,
        spawnMin: 1150,
        spawnMax: 1750,
        ventoAmp: 0,
        maxSimultaneos: 3
      },
      {
        numero: 3,
        nome: "Fluxo Intenso",
        descricao: "Mais resíduos caindo juntos!",
        minPts: 12,
        velBase: 2.9,
        spawnMin: 850,
        spawnMax: 1350,
        ventoAmp: 0,
        maxSimultaneos: 4
      },
      {
        numero: 4,
        nome: "Rajadas de Vento",
        descricao: "Cuidado com o balanço no ar!",
        minPts: 20,
        velBase: 3.2,
        spawnMin: 800,
        spawnMax: 1250,
        ventoAmp: 1.4,
        maxSimultaneos: 4
      },
      {
        numero: 5,
        nome: "Desafio Máximo",
        descricao: "Velocidade alta + vento forte!",
        minPts: 30,
        velBase: 3.7,
        spawnMin: 680,
        spawnMax: 1050,
        ventoAmp: 2.1,
        maxSimultaneos: 5
      }
    ];

    function obterConfigFase(pts) {
      let atual = FASES_CONFIG[0];
      for (const f of FASES_CONFIG) {
        if (pts >= f.minPts) atual = f;
      }
      return atual;
    }

    function focarCanvas() {
      canvas.focus();
      statusFoco.textContent = "Controles ativos (Toque ou Teclado)";
    }

    function lerRecorde() {
      try {
        const val = parseInt(localStorage.getItem(STORAGE_KEY) || "0", 10);
        return Number.isNaN(val) ? 0 : Math.max(0, val);
      } catch (e) {
        return 0;
      }
    }

    function salvarRecorde(novoRecorde) {
      try {
        localStorage.setItem(STORAGE_KEY, String(novoRecorde));
      } catch (e) {}
    }

    function utf8ToB64(str) {
      const bytes = new TextEncoder().encode(str);
      let binString = "";
      for (let i = 0; i < bytes.length; i++) {
        binString += String.fromCharCode(bytes[i]);
      }
      return btoa(binString);
    }

    function b64ToUtf8(b64) {
      const binString = atob(b64.replace(/\\s/g, ""));
      const bytes = new Uint8Array(binString.length);
      for (let i = 0; i < binString.length; i++) {
        bytes[i] = binString.charCodeAt(i);
      }
      return new TextDecoder().decode(bytes);
    }

    // Gravação automática mantendo apenas o TOP 5 no ranking.json
    async function registrarAutomaticamenteNoGitHub(ptsFinal, faseFinal) {
      const pts = Math.max(0, Math.min(META_VITORIA, ptsFinal));
      const faseAlcancada = Math.max(1, Math.min(5, faseFinal));

      bannerPodio.style.display = "block";
      bannerPodio.style.borderColor = "#ffb300";
      bannerPodio.style.color = "#ffe082";
      bannerPodio.textContent = "⏳ Salvando " + pts + " pts (Fase " + faseAlcancada + ") no Top 5...";

      if (!GH_TOKEN || !GH_REPO) {
        bannerPodio.style.borderColor = "#ff5252";
        bannerPodio.textContent = "⚠️ Configure GITHUB_TOKEN e GITHUB_REPO nos Secrets";
        return;
      }

      const apiUrl = "https://api.github.com/repos/" + GH_REPO + "/contents/ranking.json";
      const headers = {
        "Authorization": "Bearer " + GH_TOKEN,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28"
      };

      try {
        let listaAtual = [];
        let shaAtual = null;

        const respGet = await fetch(apiUrl + "?t=" + Date.now(), { headers, cache: "no-store" });
        if (respGet.ok) {
          const dataGet = await respGet.json();
          shaAtual = dataGet.sha;
          const textoJson = b64ToUtf8(dataGet.content);
          listaAtual = JSON.parse(textoJson);
          if (!Array.isArray(listaAtual)) listaAtual = [];
        }

        const agora = new Date();
        const dia = String(agora.getDate()).padStart(2, "0");
        const mes = String(agora.getMonth() + 1).padStart(2, "0");
        const hora = String(agora.getHours()).padStart(2, "0");
        const min = String(agora.getMinutes()).padStart(2, "0");

        listaAtual.push({
          nome: NOME_JOGADOR,
          pontos: pts,
          fase: faseAlcancada,
          data: dia + "/" + mes + " " + hora + ":" + min
        });

        // Ordena por pontos (desc), fase (desc) e mantém estritamente os 5 melhores
        listaAtual.sort((a, b) => {
          const diffPts = Number(b.pontos || 0) - Number(a.pontos || 0);
          if (diffPts !== 0) return diffPts;
          return Number(b.fase || 1) - Number(a.fase || 1);
        });
        const top5 = listaAtual.slice(0, 5);

        const bodyPut = {
          message: "chore: atualiza Top 5 (" + NOME_JOGADOR + " - " + pts + " pts)",
          content: utf8ToB64(JSON.stringify(top5, null, 2))
        };
        if (shaAtual) bodyPut.sha = shaAtual;

        const respPut = await fetch(apiUrl, {
          method: "PUT",
          headers,
          body: JSON.stringify(bodyPut)
        });

        if (respPut.ok) {
          bannerPodio.style.borderColor = "#69f0ae";
          bannerPodio.style.color = "#69f0ae";
          bannerPodio.textContent = "✅ " + pts + " pts registrados! Clique em Atualizar →";
        } else {
          const errTxt = await respPut.text();
          bannerPodio.style.borderColor = "#ff5252";
          bannerPodio.style.color = "#ff8a80";
          bannerPodio.textContent = "⚠️ Erro GitHub (" + respPut.status + ")";
          console.error("Erro GitHub:", errTxt);
        }
      } catch (err) {
        bannerPodio.style.borderColor = "#ff5252";
        bannerPodio.style.color = "#ff8a80";
        bannerPodio.textContent = "⚠️ Falha de rede ao salvar";
        console.error(err);
      }
    }

    function loadImg(src) {
      const img = new Image();
      if (src) img.src = src;
      return img;
    }

    function loadAudio(src) {
      if (!src) return null;
      return new Audio(src);
    }

    let mudo = false;
    function alternarMute() {
      mudo = !mudo;
      btnMute.textContent = mudo ? "🔇 Mudo" : "🔊 Som";
      focarCanvas();
    }
    btnMute.addEventListener("click", alternarMute);

    function playSound(aud) {
      if (!aud || mudo) return;
      try {
        aud.currentTime = 0;
        aud.play().catch(() => {});
      } catch (e) {}
    }

    const imgs = {
      bg: {
        instrucoes: loadImg(URIS.bg_instrucoes),
        jogo: loadImg(URIS.bg_jogo),
        fim: loadImg(URIS.bg_fim),
        vitoria: loadImg(URIS.bg_vitoria),
      },
      botao: loadImg(URIS.botao_iniciar),
      lixeira: URIS.lixeira.map(loadImg),
      lixo: URIS.lixo.map(loadImg),
      dica: URIS.dica.map(loadImg),
    };

    const sons = {
      acerto: loadAudio(URIS.som_acerto),
      erro: loadAudio(URIS.som_erro),
      fim: loadAudio(URIS.som_fim),
      vitoria: loadAudio(URIS.som_vitoria),
    };

    function scratchToCanvas(x, y, w, h, rotCenter = null) {
      if (rotCenter) {
        return [W / 2 + x - rotCenter[0], H / 2 - y - rotCenter[1]];
      }
      return [W / 2 + x - w / 2, H / 2 - y - h / 2];
    }

    function imagemPronta(img) {
      return Boolean(img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0);
    }

    function roundRect(x, y, w, h, r) {
      ctx.beginPath();
      ctx.moveTo(x + r, y);
      ctx.arcTo(x + w, y, x + w, y + h, r);
      ctx.arcTo(x + w, y + h, x, y + h, r);
      ctx.arcTo(x, y + h, x, y, r);
      ctx.arcTo(x, y, x + w, y, r);
      ctx.closePath();
    }

    let estado = "instrucoes";
    let pausado = false;
    let pausadoEm = 0;

    let pontos = 0;
    let recorde = lerRecorde();
    let vidas = 5;
    let faseAtual = FASES_CONFIG[0];
    let velocidade = faseAtual.velBase;
    let ultimoTipo = 1;

    let bannerFase = null; // { texto, subtitulo, ate }

    let lixeiraX = 0;
    let lixeiraY = -135;
    let lixeiraFantasia = 1;
    let lixeiraVisivel = false;

    let dicaVisivel = false;
    let dicaFantasia = 1;
    let dicaAte = 0;

    let clones = [];
    let feedbacks = [];
    let flashErroAte = 0;
    let proximoSpawn = 0;
    let ultimoAumentoVel = 0;

    const teclas = {};

    function selecionarLixeira(tipo) {
      lixeiraFantasia = tipo;
      botoesLixeira.forEach((btn) => {
        btn.classList.toggle("ativa", Number(btn.dataset.tipo) === tipo);
      });
    }

    botoesLixeira.forEach((btn) => {
      btn.addEventListener("pointerdown", (e) => {
        e.preventDefault();
        const tipo = Number(btn.dataset.tipo);
        selecionarLixeira(tipo);
        if (estado === "instrucoes") iniciarPartida();
        focarCanvas();
      });
    });

    let arrastando = false;

    function atualizarPosicaoPorPonteiro(clientX) {
      const rect = canvas.getBoundingClientRect();
      const relX = (clientX - rect.left) / rect.width;
      const scratchX = (relX * W) - (W / 2);
      lixeiraX = Math.max(-205, Math.min(205, scratchX));
    }

    canvas.addEventListener("pointerdown", (e) => {
      focarCanvas();
      if (estado === "instrucoes") {
        iniciarPartida();
        return;
      }
      if (estado === "jogo" && !pausado) {
        arrastando = true;
        atualizarPosicaoPorPonteiro(e.clientX);
      }
    });

    canvas.addEventListener("pointermove", (e) => {
      if (arrastando && estado === "jogo" && !pausado) {
        atualizarPosicaoPorPonteiro(e.clientX);
      }
    });

    window.addEventListener("pointerup", () => {
      arrastando = false;
    });

    function atualizarBotaoPausar() {
      btnPausar.textContent = pausado ? "▶ Continuar" : "⏸ Pausar";
    }

    function alternarPausa() {
      if (estado !== "jogo") return;
      const agora = performance.now();
      if (!pausado) {
        pausado = true;
        pausadoEm = agora;
      } else {
        const delta = agora - pausadoEm;
        ultimoAumentoVel += delta;
        proximoSpawn += delta;
        if (dicaVisivel) dicaAte += delta;
        if (flashErroAte > 0) flashErroAte += delta;
        if (bannerFase) bannerFase.ate += delta;
        for (const fb of feedbacks) fb.criadoEm += delta;
        pausado = false;
      }
      atualizarBotaoPausar();
      focarCanvas();
    }

    btnPausar.addEventListener("click", alternarPausa);

    function registrarPonto() {
      pontos += 1;
      if (pontos > recorde) {
        recorde = pontos;
        salvarRecorde(recorde);
      }

      const novaFase = obterConfigFase(pontos);
      if (novaFase.numero > faseAtual.numero && pontos < META_VITORIA) {
        faseAtual = novaFase;
        velocidade = faseAtual.velBase;
        clones = []; // Limpa a tela para transição justa
        const agora = performance.now();
        proximoSpawn = agora + 1500;

        let msgVida = "";
        if (vidas < 5) {
          vidas += 1;
          msgVida = " • +1 ❤️ Bônus!";
        }

        bannerFase = {
          texto: "✨ FASE " + faseAtual.numero + ": " + faseAtual.nome.toUpperCase() + " ✨",
          subtitulo: faseAtual.descricao + msgVida,
          ate: agora + 2200
        };
      }
    }

    function iniciarPartida() {
      const agora = performance.now();
      estado = "jogo";
      pausado = false;
      bannerPodio.style.display = "none";
      atualizarBotaoPausar();
      pontos = 0;
      vidas = 5;
      faseAtual = FASES_CONFIG[0];
      velocidade = faseAtual.velBase;
      ultimoTipo = 1;
      lixeiraX = 0;
      lixeiraY = -135;
      selecionarLixeira(1);
      lixeiraVisivel = true;
      dicaVisivel = false;
      clones = [];
      feedbacks = [];
      flashErroAte = 0;
      ultimoAumentoVel = agora;
      proximoSpawn = agora + 1100;
      bannerFase = {
        texto: "FASE 1: " + faseAtual.nome.toUpperCase(),
        subtitulo: faseAtual.descricao,
        ate: agora + 1800
      };
    }

    btnIniciarTop.addEventListener("click", () => {
      iniciarPartida();
      focarCanvas();
    });

    window.addEventListener("keydown", (e) => {
      teclas[e.code] = true;
      if (["Space", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.code)) {
        e.preventDefault();
      }
      if (e.key && e.key.toLowerCase() === "m") {
        alternarMute();
        return;
      }
      if (e.key && e.key.toLowerCase() === "p") {
        alternarPausa();
        return;
      }
      if (estado === "instrucoes" && e.code === "Space") {
        iniciarPartida();
      } else if (estado === "jogo" && !pausado) {
        if (["1", "2", "3", "4", "5"].includes(e.key)) {
          selecionarLixeira(Number(e.key));
        }
      }
    });

    window.addEventListener("keyup", (e) => {
      teclas[e.code] = false;
    });

    function adicionarFeedback(x, y, texto, cor) {
      feedbacks.push({ x, y, texto, cor, criadoEm: performance.now() });
    }

    function dispararErro(tipoErrado, px = W / 2, py = H / 2) {
      const agora = performance.now();
      if (vidas > 0) {
        vidas -= 1;
        ultimoTipo = tipoErrado;
      }
      flashErroAte = agora + 240;
      adicionarFeedback(px, py, "-1 ❤️", "#ff5252");
      playSound(sons.erro);
      dicaFantasia = ultimoTipo;
      dicaVisivel = true;
      dicaAte = agora + 2600;
    }

    function rectsColidem(a, b) {
      return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
    }

    function loop(agora) {
      const tempoRef = pausado ? pausadoEm : agora;

      if (estado === "jogo" && !pausado) {
        if (agora - ultimoAumentoVel >= 6500) {
          velocidade += 0.15;
          ultimoAumentoVel = agora;
        }

        if (teclas["ArrowLeft"] || teclas["KeyA"]) lixeiraX -= 7.8;
        if (teclas["ArrowRight"] || teclas["KeyD"]) lixeiraX += 7.8;
        if (lixeiraX > 205) lixeiraX = 205;
        if (lixeiraX < -205) lixeiraX = -205;

        // Todos os 10 itens (tipos 1 a 5) sorteados desde a Fase 1
        if (agora >= proximoSpawn && clones.length < faseAtual.maxSimultaneos) {
          const item = Math.floor(Math.random() * 10) + 1;
          const tipo = ((item - 1) % 5) + 1;
          // Itens leves (1=Papel, 2=Plástico) sofrem mais vento nas fases 4 e 5
          const fatorPeso = (tipo === 1 || tipo === 2) ? 1.35 : 0.75;
          clones.push({
            x: Math.floor(Math.random() * 381) - 190,
            y: 175,
            item,
            tipo,
            faseOnda: Math.random() * Math.PI * 2,
            fatorPeso
          });
          const intervalo = faseAtual.spawnMin + Math.random() * (faseAtual.spawnMax - faseAtual.spawnMin);
          proximoSpawn = agora + intervalo;
        }

        const imgL = imgs.lixeira[lixeiraFantasia - 1];
        const lw = (imgL && imgL.naturalWidth) || 80;
        const lh = (imgL && imgL.naturalHeight) || 84;
        const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);
        const rectLixeira = { x: lx, y: ly, w: lw, h: lh };

        const restantes = [];
        for (const c of clones) {
          c.y -= velocidade;

          if (faseAtual.ventoAmp > 0) {
            c.x += Math.sin((agora * 0.004) + c.faseOnda) * faseAtual.ventoAmp * c.fatorPeso;
            c.x = Math.max(-205, Math.min(205, c.x));
          }

          const imgC = imgs.lixo[c.item - 1];
          const cw = (imgC && imgC.naturalWidth) || 50;
          const ch = (imgC && imgC.naturalHeight) || 50;
          const [cx, cy] = scratchToCanvas(c.x, c.y, cw, ch);
          const rectItem = { x: cx, y: cy, w: cw, h: ch };

          if (rectsColidem(rectItem, rectLixeira)) {
            if (lixeiraFantasia === c.tipo) {
              registrarPonto();
              adicionarFeedback(lx + lw / 2, ly - 6, "+1 ♻️", "#69f0ae");
              playSound(sons.acerto);
            } else {
              dispararErro(c.tipo, lx + lw / 2, ly - 6);
            }
            continue;
          }

          if (c.y < -170) {
            dispararErro(c.tipo, cx + cw / 2, H - 30);
            continue;
          }

          restantes.push(c);
        }
        clones = restantes;

        if (dicaVisivel && agora >= dicaAte) dicaVisivel = false;
        if (bannerFase && agora >= bannerFase.ate) bannerFase = null;

        if (vidas < 1) {
          estado = "fim";
          pausado = false;
          atualizarBotaoPausar();
          lixeiraVisivel = false;
          dicaVisivel = false;
          clones = [];
          playSound(sons.fim);
          registrarAutomaticamenteNoGitHub(pontos, faseAtual.numero);
        } else if (pontos >= META_VITORIA) {
          estado = "vitoria";
          pausado = false;
          atualizarBotaoPausar();
          lixeiraVisivel = false;
          dicaVisivel = false;
          clones = [];
          playSound(sons.vitoria);
          registrarAutomaticamenteNoGitHub(pontos, faseAtual.numero);
        }
      }

      ctx.save();
      if (!pausado && tempoRef < flashErroAte) {
        const tremor = Math.sin(tempoRef * 0.08) * 3;
        ctx.translate(tremor, 0);
      }

      ctx.clearRect(-10, -10, W + 20, H + 20);
      ctx.fillStyle = "#1b2a1e";
      ctx.fillRect(0, 0, W, H);

      const bgAtual = imgs.bg[estado];
      if (imagemPronta(bgAtual)) {
        ctx.drawImage(bgAtual, 0, 0, W, H);
      } else if (estado === "instrucoes") {
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 22px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("COLETA SELETIVA", W / 2, 120);
        ctx.font = "15px sans-serif";
        ctx.fillStyle = "#a5d6a7";
        ctx.fillText("Toque na tela ou aperte ESPAÇO", W / 2, 160);
        ctx.textAlign = "left";
      }

      if (estado === "instrucoes") {
        if (imagemPronta(imgs.botao)) {
          const escala = Math.floor(agora / 300) % 2 === 1 ? 1.08 : 1.0;
          const bw = imgs.botao.naturalWidth * escala;
          const bh = imgs.botao.naturalHeight * escala;
          const [bx, by] = scratchToCanvas(36, 28, bw, bh, [147.5 * escala, -121.4 * escala]);
          ctx.drawImage(imgs.botao, bx, by, bw, bh);
        }
        ctx.fillStyle = "rgba(15, 25, 18, 0.88)";
        roundRect(W - 165, 8, 157, 28, 8);
        ctx.fill();
        ctx.fillStyle = "#ffe082";
        ctx.font = "bold 13px sans-serif";
        ctx.fillText("🏆 Recorde: " + recorde + " / " + META_VITORIA, W - 156, 27);
      } else if (estado === "jogo") {
        if (lixeiraVisivel) {
          const imgL = imgs.lixeira[lixeiraFantasia - 1];
          const lw = (imgL && imgL.naturalWidth) || 80;
          const lh = (imgL && imgL.naturalHeight) || 84;
          const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);
          if (imagemPronta(imgL)) {
            ctx.drawImage(imgL, lx, ly, lw, lh);
          } else {
            ctx.fillStyle = "#2e7d32";
            ctx.fillRect(lx, ly, lw, lh);
          }
        }

        for (const c of clones) {
          const imgC = imgs.lixo[c.item - 1];
          const cw = (imgC && imgC.naturalWidth) || 50;
          const ch = (imgC && imgC.naturalHeight) || 50;
          const [cx, cy] = scratchToCanvas(c.x, c.y, cw, ch);
          if (imagemPronta(imgC)) {
            ctx.drawImage(imgC, cx, cy, cw, ch);
          } else {
            ctx.fillStyle = "#fbc02d";
            ctx.fillRect(cx, cy, cw, ch);
          }
        }

        if (dicaVisivel) {
          const imgD = imgs.dica[dicaFantasia - 1];
          const dw = (imgD && imgD.naturalWidth) || 440;
          const dh = (imgD && imgD.naturalHeight) || 60;
          const [dx, dy] = scratchToCanvas(0, 95, dw, dh, [220, 30]);
          if (imagemPronta(imgD)) {
            ctx.drawImage(imgD, dx, dy, dw, dh);
          }
        }

        if (bannerFase && tempoRef < bannerFase.ate) {
          ctx.save();
          ctx.fillStyle = "rgba(12, 28, 18, 0.90)";
          roundRect(W / 2 - 190, H / 2 - 42, 380, 68, 12);
          ctx.fill();
          ctx.strokeStyle = "#81c784";
          ctx.lineWidth = 2;
          ctx.stroke();

          ctx.textAlign = "center";
          ctx.fillStyle = "#ffe082";
          ctx.font = "bold 16px sans-serif";
          ctx.fillText(bannerFase.texto, W / 2, H / 2 - 14);

          ctx.fillStyle = "#c8e6c9";
          ctx.font = "13px sans-serif";
          ctx.fillText(bannerFase.subtitulo, W / 2, H / 2 + 10);
          ctx.restore();
        }

        const proxFeedbacks = [];
        for (const fb of feedbacks) {
          const elapsed = tempoRef - fb.criadoEm;
          if (elapsed < 750) {
            const yAtual = fb.y - (elapsed * 0.04);
            const alpha = 1 - (elapsed / 750);
            ctx.save();
            ctx.globalAlpha = Math.max(0, alpha);
            ctx.font = "bold 16px sans-serif";
            ctx.textAlign = "center";
            ctx.fillStyle = fb.cor;
            ctx.fillText(fb.texto, fb.x, yAtual);
            ctx.restore();
            proxFeedbacks.push(fb);
          }
        }
        feedbacks = proxFeedbacks;

        // HUD Superior
        ctx.fillStyle = "rgba(15, 25, 18, 0.88)";
        roundRect(8, 8, 148, 28, 8);
        ctx.fill();
        roundRect(8, 40, 148, 28, 8);
        ctx.fill();
        roundRect(W - 156, 8, 148, 28, 8);
        ctx.fill();
        roundRect(W - 156, 40, 148, 28, 8);
        ctx.fill();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 14px sans-serif";
        ctx.fillText("♻️ Pontos: " + pontos + "/" + META_VITORIA, 16, 27);
        ctx.fillText("❤️ Vidas: " + vidas, 16, 59);

        ctx.fillStyle = "#ffe082";
        ctx.font = "bold 13px sans-serif";
        ctx.fillText("🏆 Recorde: " + recorde, W - 148, 27);

        ctx.fillStyle = "#81c784";
        ctx.fillText("🚩 Fase " + faseAtual.numero + "/5", W - 148, 59);

        if (pausado) {
          ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
          ctx.fillRect(0, 0, W, H);
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 26px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText("PAUSADO", W / 2, H / 2 - 6);
          ctx.font = "14px sans-serif";
          ctx.fillStyle = "#cfd8dc";
          ctx.fillText("Toque em Continuar ou aperte P", W / 2, H / 2 + 22);
          ctx.textAlign = "left";
        }
      }

      ctx.restore();
      requestAnimationFrame(loop);
    }

    focarCanvas();
    requestAnimationFrame(loop);
    </script>
    </body>
    </html>
    """

    html_jogo = (
        html_template
        .replace("__ASSETS_URI__", json.dumps(assets_uri))
        .replace("__NOME_JOGADOR__", json.dumps(nome_seguro))
        .replace("__GH_TOKEN__", json.dumps(GITHUB_TOKEN))
        .replace("__GH_REPO__", json.dumps(GITHUB_REPO))
    )

    if hasattr(st, "iframe"):
        st.iframe(html_jogo, height=495)
    else:
        import streamlit.components.v1 as components
        components.html(html_jogo, height=495, scrolling=False)

with col_ranking:
    st.markdown('<div class="ranking-card">', unsafe_allow_html=True)
    r_top1, r_top2 = st.columns([1.6, 1])
    with r_top1:
        st.subheader("🏆 Top 5 Oficial")
    with r_top2:
        if st.button("🔄 Atualizar", use_container_width=True):
            st.rerun()

    dados_gh, _, erro_gh = ler_ranking_github()
    if dados_gh is not None:
        st.caption("✅ Conectado ao GitHub • Exibe os 5 melhores jogadores.")
    else:
        st.warning(f"⚠️ Modo local: {erro_gh}")

    ranking_atual = dados_gh if dados_gh is not None else []

    if not ranking_atual:
        st.info("Nenhuma partida finalizada ainda. Jogue para inaugurar o Top 5!")
    else:
        medalhas = ["🥇", "🥈", "🥉"]
        for idx, item in enumerate(ranking_atual[:5]):
            pos = medalhas[idx] if idx < 3 else f"#{idx + 1}"
            fase_item = item.get("fase", 1)
            cor_fundo = (
                "rgba(255, 215, 0, 0.16)"
                if idx == 0
                else "rgba(255, 255, 255, 0.05)"
            )
            st.markdown(
                f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:center;
                    background:{cor_fundo};
                    padding:10px 14px;
                    border-radius:10px;
                    margin-bottom:8px;
                    border: 1px solid rgba(255,255,255,0.08);
                ">
                    <div>
                        <b>{pos} {item['nome']}</b><br/>
                        <small style="color:#a5d6a7;">Fase {fase_item}/5 • {item['data']}</small>
                    </div>
                    <span style="font-weight:bold; color:#ffe082; font-size:1.05rem;">{item['pontos']} pts</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("</div>", unsafe_allow_html=True)
