import base64
import json
import mimetypes
import os
import urllib.request
import urllib.error
from datetime import datetime
import streamlit as st

st.set_page_config(
    page_title="♻️ Coleta Seletiva Pro",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

PASTA_RAIZ = os.path.dirname(os.path.abspath(__file__))
PASTA_ASSETS = os.path.join(PASTA_RAIZ, "dependencias")

GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
GITHUB_REPO = st.secrets.get("GITHUB_REPO", "")
GITHUB_FILE_PATH = "ranking.json"


# ==============================================================================
# CAMADA DE PERSISTÊNCIA SEGURA NO PYTHON (O TOKEN NUNCA SAI DO SERVIDOR)
# ==============================================================================
def ler_ranking_github():
    """Lê o ranking.json da API do GitHub e retorna os 5 melhores únicos."""
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


def salvar_pontuacao_github(nome: str, pontos: int, fase: int, modo: str):
    """Valida, deduplica por jogador e grava o Top 5 diretamente pelo Python."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False, "Secrets do GitHub não configurados."

    modos_validos = {"campanha", "infinito", "tempo"}
    if modo not in modos_validos:
        modo = "campanha"

    limite_pts = 40 if modo == "campanha" else 999
    if not (0 <= pontos <= limite_pts and 1 <= fase <= 5):
        return False, "Pontuação fora dos limites permitidos."

    nome_limpo = (nome or "Jogador").strip()[:20] or "Jogador"
    dados_atuais, sha_atual, erro = ler_ranking_github()
    if dados_atuais is None:
        return False, erro or "Falha ao ler ranking atual."

    agora_str = datetime.now().strftime("%d/%m %H:%M")
    dados_atuais.append(
        {
            "nome": nome_limpo,
            "pontos": int(pontos),
            "fase": int(fase),
            "modo": modo,
            "data": agora_str,
        }
    )

    dados_atuais.sort(
        key=lambda x: (
            -int(x.get("pontos", 0)),
            -int(x.get("fase", 1)),
            x.get("data", ""),
        )
    )

    unicos = []
    vistos = set()
    for item in dados_atuais:
        chave = str(item.get("nome", "Jogador")).strip().lower()
        if chave not in vistos:
            vistos.add(chave)
            unicos.append(item)

    top5 = unicos[:5]
    conteudo_b64 = base64.b64encode(
        json.dumps(top5, ensure_ascii=False, indent=2).encode("utf-8")
    ).decode("utf-8")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"
    body = {
        "message": f"chore: registra {pontos} pts de {nome_limpo} ({modo})",
        "content": conteudo_b64,
    }
    if sha_atual:
        body["sha"] = sha_atual

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="PUT",
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status in (200, 201):
                return True, f"✅ {pontos} pts salvos no Top 5 com segurança!"
            return False, f"Status inesperado: {resp.status}"
    except Exception as e:
        return False, f"Erro ao salvar no GitHub: {e}"


# Intercepta envio seguro vindo do jogo via Query Params
if "save_score" in st.query_params:
    try:
        qp = st.query_params
        token_partida = qp.get("sid", "")
        if token_partida and token_partida != st.session_state.get("ultimo_sid_salvo"):
            st.session_state["ultimo_sid_salvo"] = token_partida
            ok, msg = salvar_pontuacao_github(
                nome=qp.get("nome", "Jogador"),
                pontos=int(qp.get("pts", "0")),
                fase=int(qp.get("fase", "1")),
                modo=qp.get("modo", "campanha"),
            )
            st.session_state["flash_podio"] = (ok, msg)
    except Exception as exc:
        st.session_state["flash_podio"] = (False, f"Erro ao processar placar: {exc}")
    finally:
        st.query_params.clear()
        st.rerun()


# ==============================================================================
# ESTILO E CABEÇALHO
# ==============================================================================
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
        padding: 14px 20px;
        margin-bottom: 12px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }
    .header-box h1 {
        margin: 0;
        font-size: 1.9rem;
        color: #a5d6a7;
    }
    .header-box p {
        margin: 4px 0 0 0;
        color: #dce775;
        font-size: 0.9rem;
    }
    .bin-card {
        border-radius: 10px;
        padding: 7px 6px;
        text-align: center;
        font-weight: bold;
        font-size: 0.85rem;
        color: white;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
        margin-bottom: 8px;
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
        <h1>♻️ Desafio da Coleta Seletiva — Edição Evoluída</h1>
        <p>📱 <b>Mobile:</b> Arraste e toque nas lixeiras • 💻 <b>PC:</b> Setas / A-D e teclas 1 a 5 • <b>P:</b> Pausar • <b>M:</b> Som</p>
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

# ==============================================================================
# CARREGAMENTO DE ASSETS EM BASE64 (INCLUINDO AS NOVAS IMAGENS .PNG)
# ==============================================================================
arquivos_em_falta = []


def asset_to_data_uri(nome_arquivo):
    caminho = os.path.join(PASTA_ASSETS, nome_arquivo)
    if not os.path.exists(caminho):
        arquivos_em_falta.append(nome_arquivo)
        return ""
    mime, _ = mimetypes.guess_type(caminho)
    if nome_arquivo.lower().endswith(".svg"):
        mime = "image/svg+xml"
    elif nome_arquivo.lower().endswith(".png"):
        mime = "image/png"
    elif nome_arquivo.lower().endswith(".wav"):
        mime = "audio/wav"
    elif not mime:
        mime = "application/octet-stream"

    with open(caminho, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
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
    "extras": {
        "coringa": asset_to_data_uri("coringa.png"),
        "vida": asset_to_data_uri("kit_restauracao.png"),
        "ima": asset_to_data_uri("ima_seletivo.png"),
        "escudo": asset_to_data_uri("escudo_ambiental.png"),
        "freeze": asset_to_data_uri("eco_freeze.png"),
        "pizza": asset_to_data_uri("caixa_pizza_realista.png"),
    },
    "som_acerto": asset_to_data_uri("cfc50a412483f6aadb83adeff596052e.wav"),
    "som_erro": asset_to_data_uri("768bd6a764ab62a6a6764e4147c3e615.wav"),
    "som_fim": asset_to_data_uri("e3635ab50a93193e53cd16f047446add.wav"),
    "som_vitoria": asset_to_data_uri("b8251bb11c300af3582aba1239082d41.wav"),
}

if not os.path.isdir(PASTA_ASSETS):
    st.error(f"Pasta 'dependencias' não encontrada em: {PASTA_ASSETS}")
elif arquivos_em_falta:
    st.warning(f"Arquivos ausentes ({len(arquivos_em_falta)}): " + ", ".join(arquivos_em_falta))


# ==============================================================================
# ABAS PRINCIPAIS: JOGO + PÓDIO | ENCICLOPÉDIA "APRENDA JOGANDO"
# ==============================================================================
aba_jogar, aba_guia = st.tabs(["🎮 Jogar & Pódio Oficial", "📚 Enciclopédia: Aprenda Jogando"])

with aba_jogar:
    col_jogo, col_ranking = st.columns([1.75, 1], gap="large")

    with col_jogo:
        c_nome, c_modo = st.columns([1.1, 1])
        with c_nome:
            nome_jogador = st.text_input(
                "👤 Seu apelido:",
                value="Jogador",
                max_chars=20,
                placeholder="Digite seu apelido...",
            )
        with c_modo:
            modo_label = st.selectbox(
                "🕹️ Modo de Jogo:",
                [
                    "🚩 Campanha (5 Fases · 40 pts)",
                    "♾️ Infinito (Arcade)",
                    "⏱️ Contra o Relógio (60s)",
                ],
            )

        nome_seguro = (nome_jogador or "Jogador").strip()[:20] or "Jogador"
        modo_codigo = (
            "campanha"
            if "Campanha" in modo_label
            else ("infinito" if "Infinito" in modo_label else "tempo")
        )

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
            max-width: 680px;
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
            bottom: 120px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(15, 30, 20, 0.96);
            color: #ffe082;
            font-weight: 700;
            font-size: 13px;
            padding: 10px 16px;
            border-radius: 12px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.65);
            border: 2px solid #4caf50;
            z-index: 20;
            white-space: nowrap;
          }
          .lixeiras-touch {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            width: 100%;
            margin-top: 10px;
          }
          .btn-lixeira {
            border: 2px solid transparent;
            border-radius: 10px;
            padding: 11px 2px;
            font-weight: 700;
            font-size: 13px;
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
            margin-top: 8px;
            width: 100%;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 6px;
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
            padding: 6px 12px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
          }
          .btn-mini:active {
            background: #354f3c;
          }
          .badges-strip {
            margin-top: 8px;
            width: 100%;
            display: flex;
            flex-wrap: wrap;
            gap: 5px;
            justify-content: center;
          }
          .badge-pill {
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.14);
            color: #9e9e9e;
          }
          .badge-pill.unlocked {
            background: rgba(76, 175, 80, 0.22);
            border-color: #81c784;
            color: #e8f5e9;
            font-weight: 600;
          }
        </style>
        </head>
        <body>
        <div class="game-wrapper">
          <canvas id="game" width="480" height="360" tabindex="0"></canvas>

          <div id="banner-status-podio">⏳ Enviando pontuação segura...</div>

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

          <div class="badges-strip" id="badges-container"></div>
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
        const badgesContainer = document.getElementById("badges-container");

        const W = 480, H = 360;
        const META_CAMPANHA = 40;
        const URIS = __ASSETS_URI__;
        const NOME_JOGADOR = __NOME_JOGADOR__;
        const MODO_JOGO = __MODO_JOGO__;
        const STORAGE_KEY = "coleta_seletiva_recorde_v4_" + MODO_JOGO;
        const BADGES_KEY = "coleta_seletiva_badges_v1";

        const FASES_CONFIG = [
          { numero: 1, nome: "Aquecimento", desc: "Todos os materiais • Ritmo inicial", minPts: 0, velBase: 2.0, spawnMin: 1400, spawnMax: 2050, ventoAmp: 0, maxSim: 2 },
          { numero: 2, nome: "Ritmo Urbano", desc: "Queda mais rápida + Itens especiais!", minPts: 5, velBase: 2.45, spawnMin: 1150, spawnMax: 1700, ventoAmp: 0, maxSim: 3 },
          { numero: 3, nome: "Fluxo Intenso", desc: "Mais resíduos e pilhas tóxicas!", minPts: 12, velBase: 2.85, spawnMin: 880, spawnMax: 1380, ventoAmp: 0, maxSim: 4 },
          { numero: 4, nome: "Rajadas de Vento", desc: "Itens balançam no ar!", minPts: 20, velBase: 3.15, spawnMin: 820, spawnMax: 1250, ventoAmp: 1.35, maxSim: 4 },
          { numero: 5, nome: "Desafio Máximo", desc: "Velocidade alta + vento forte!", minPts: 30, velBase: 3.6, spawnMin: 700, spawnMax: 1080, ventoAmp: 2.0, maxSim: 5 }
        ];

        const LISTA_BADGES = [
          { id: "mestre_vidro", label: "🟢 Mestre do Vidro (10 acertos)" },
          { id: "combo_3x", label: "🔥 Combo 3x (10 seguidos)" },
          { id: "pizza_expert", label: "🍕 Sem Engano na Pizza" },
          { id: "sobrevivente", label: "🌪️ Sobrevivente da Ventania" },
          { id: "precisao_100", label: "🎯 100% Precisão (Campanha)" },
          { id: "campeao", label: "👑 Campeão 40 pts" }
        ];

        function carregarBadges() {
          try {
            return JSON.parse(localStorage.getItem(BADGES_KEY) || "{}");
          } catch (e) {
            return {};
          }
        }

        let badgesDesbloqueadas = carregarBadges();

        function desbloquearBadge(id) {
          if (badgesDesbloqueadas[id]) return;
          badgesDesbloqueadas[id] = true;
          try {
            localStorage.setItem(BADGES_KEY, JSON.stringify(badgesDesbloqueadas));
          } catch (e) {}
          renderizarBadges();
        }

        function renderizarBadges() {
          badgesContainer.innerHTML = "";
          for (const b of LISTA_BADGES) {
            const span = document.createElement("span");
            const ok = Boolean(badgesDesbloqueadas[b.id]);
            span.className = "badge-pill" + (ok ? " unlocked" : "");
            span.textContent = ok ? b.label : "🔒 " + b.label.split("(")[0].trim();
            badgesContainer.appendChild(span);
          }
        }
        renderizarBadges();

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

        function enviarPlacarSeguroParaPython(ptsFinal, faseFinal) {
          const pts = Math.max(0, Math.round(ptsFinal));
          const faseAlcancada = Math.max(1, Math.min(5, faseFinal));

          bannerPodio.style.display = "block";
          bannerPodio.style.borderColor = "#69f0ae";
          bannerPodio.style.color = "#69f0ae";
          bannerPodio.textContent = "⏳ Registrando " + pts + " pts no Top 5...";

          setTimeout(() => {
            try {
              const sid = Date.now() + "_" + Math.floor(Math.random() * 10000);
              const url = new URL(window.parent.location.href);
              url.searchParams.set("save_score", "1");
              url.searchParams.set("sid", sid);
              url.searchParams.set("nome", NOME_JOGADOR);
              url.searchParams.set("pts", String(pts));
              url.searchParams.set("fase", String(faseAlcancada));
              url.searchParams.set("modo", MODO_JOGO);
              window.parent.location.href = url.toString();
            } catch (e) {
              bannerPodio.style.borderColor = "#ffb300";
              bannerPodio.textContent = "✅ Partida encerrada: " + pts + " pts!";
            }
          }, 1400);
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
          extras: {
            coringa: loadImg(URIS.extras.coringa),
            vida: loadImg(URIS.extras.vida),
            ima: loadImg(URIS.extras.ima),
            escudo: loadImg(URIS.extras.escudo),
            freeze: loadImg(URIS.extras.freeze),
            pizza: loadImg(URIS.extras.pizza),
          }
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
        let tempoRestante = 60.0;
        let ultimoTickTempo = 0;

        let faseAtual = FASES_CONFIG[0];
        let velocidade = faseAtual.velBase;
        let ultimoTipo = 1;

        let comboAtual = 0;
        let errosNaPartida = 0;
        let acertosVidro = 0;

        let imaAte = 0;
        let freezeAte = 0;
        let escudoAtivo = false;
        let congeladoAte = 0;

        let bannerFase = null;

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
          if (estado === "jogo" && performance.now() < congeladoAte) return;
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
          if (performance.now() < congeladoAte) return;
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
            ultimoTickTempo += delta;
            if (dicaVisivel) dicaAte += delta;
            if (flashErroAte > 0) flashErroAte += delta;
            if (imaAte > 0) imaAte += delta;
            if (freezeAte > 0) freezeAte += delta;
            if (congeladoAte > 0) congeladoAte += delta;
            if (bannerFase) bannerFase.ate += delta;
            for (const fb of feedbacks) fb.criadoEm += delta;
            pausado = false;
          }
          atualizarBotaoPausar();
          focarCanvas();
        }

        btnPausar.addEventListener("click", alternarPausa);

        function obterMultiplicadorCombo() {
          if (comboAtual >= 10) return 3;
          if (comboAtual >= 5) return 2;
          return 1;
        }

        function registrarAcerto(basePts = 1, tipoMaterial = 1, px = W / 2, py = H / 2, msgCustom = null) {
          comboAtual += 1;
          if (comboAtual >= 10) desbloquearBadge("combo_3x");

          if (tipoMaterial === 3) {
            acertosVidro += 1;
            if (acertosVidro >= 10) desbloquearBadge("mestre_vidro");
          }

          const mult = obterMultiplicadorCombo();
          const ganho = basePts * mult;
          pontos += ganho;

          if (MODO_JOGO === "campanha" && pontos > META_CAMPANHA) {
            pontos = META_CAMPANHA;
          }

          if (pontos > recorde) {
            recorde = pontos;
            salvarRecorde(recorde);
          }

          const txtFlutuante = msgCustom || ("+" + ganho + (mult > 1 ? " (" + mult + "x!)" : " ♻️"));
          adicionarFeedback(px, py, txtFlutuante, mult > 1 ? "#ffd54f" : "#69f0ae");
          playSound(sons.acerto);

          const novaFase = obterConfigFase(pontos);
          if (novaFase.numero > faseAtual.numero) {
            if (faseAtual.numero === 4) desbloquearBadge("sobrevivente");
            faseAtual = novaFase;
            velocidade = faseAtual.velBase;
            clones = [];
            const agora = performance.now();
            proximoSpawn = agora + 1400;

            let msgBonus = "";
            if (MODO_JOGO !== "tempo" && vidas < 5) {
              vidas += 1;
              msgBonus = " • +1 ❤️ Bônus!";
            } else if (MODO_JOGO === "tempo") {
              tempoRestante += 5;
              msgBonus = " • +5s Bônus!";
            }

            bannerFase = {
              texto: "✨ FASE " + faseAtual.numero + ": " + faseAtual.nome.toUpperCase() + " ✨",
              subtitulo: faseAtual.desc + msgBonus,
              ate: agora + 2100
            };
          }
        }

        function dispararErro(tipoCorreto, px = W / 2, py = H / 2) {
          const agora = performance.now();

          if (escudoAtivo) {
            escudoAtivo = false;
            adicionarFeedback(px, py, "🛡️ Escudo!", "#4fc3f7");
            playSound(sons.acerto);
            return;
          }

          comboAtual = 0;
          errosNaPartida += 1;

          if (MODO_JOGO === "tempo") {
            tempoRestante = Math.max(0, tempoRestante - 3);
            adicionarFeedback(px, py, "-3s ⏱️", "#ff5252");
          } else if (vidas > 0) {
            vidas -= 1;
            adicionarFeedback(px, py, "-1 ❤️", "#ff5252");
          }

          ultimoTipo = tipoCorreto;
          flashErroAte = agora + 240;
          playSound(sons.erro);

          if (tipoCorreto >= 1 && tipoCorreto <= 5) {
            dicaFantasia = tipoCorreto;
            dicaVisivel = true;
            dicaAte = agora + 2500;
          }
        }

        function gerarEntidadeSpawn() {
          const r = Math.random();
          const x = Math.floor(Math.random() * 380) - 190;
          const faseOnda = Math.random() * Math.PI * 2;

          // 1) Power-ups (12% de chance)
          if (r < 0.12) {
            const poolPwr = ["ima", "freeze", "escudo", "coringa"];
            if (MODO_JOGO !== "tempo" && vidas <= 2) {
              poolPwr.push("vida", "vida");
            }
            const pwr = poolPwr[Math.floor(Math.random() * poolPwr.length)];
            return { x, y: 175, kind: "powerup", subtipo: pwr, tipo: 0, faseOnda, fatorPeso: 0.6 };
          }

          // 2) Armadilha: Pilha Tóxica / Bomba (a partir de 3 pts, 9% de chance)
          if (pontos >= 3 && r < 0.21) {
            return { x, y: 175, kind: "bomba", subtipo: "pilha", tipo: 0, faseOnda, fatorPeso: 0.7 };
          }

          // 3) Itens Especiais: Caixa de Pizza Engordurada ou Saco Combo (16% de chance)
          if (r < 0.37) {
            if (Math.random() < 0.55) {
              // Caixa de pizza engordurada -> Orgânico (tipo 5)
              return { x, y: 175, kind: "especial", subtipo: "pizza", tipo: 5, faseOnda, fatorPeso: 1.2 };
            } else {
              // Saco de Reciclagem
              const tipoSaco = Math.floor(Math.random() * 5) + 1;
              return { x, y: 175, kind: "saco", subtipo: "saco", tipo: tipoSaco, faseOnda, fatorPeso: 0.9 };
            }
          }

          // 4) Itens Base (1 a 10 - todos disponíveis desde a Fase 1!)
          const item = Math.floor(Math.random() * 10) + 1;
          const tipo = ((item - 1) % 5) + 1;
          const fatorPeso = (tipo === 1 || tipo === 2) ? 1.35 : 0.75;
          return { x, y: 175, kind: "base", item, tipo, faseOnda, fatorPeso };
        }

        function abrirSacoNoAr(saco) {
          playSound(sons.acerto);
          const [sx, sy] = scratchToCanvas(saco.x, saco.y, 48, 48);
          adicionarFeedback(sx + 24, sy, "🛍️ +3 Itens!", "#81c784");
          const offsets = [-55, 0, 55];
          for (let i = 0; i < 3; i++) {
            const itemDoTipo = saco.tipo + (Math.random() < 0.5 ? 0 : 5);
            clones.push({
              x: Math.max(-195, Math.min(195, saco.x + offsets[i])),
              y: saco.y + (i === 1 ? 12 : 0),
              kind: "base",
              item: itemDoTipo,
              tipo: saco.tipo,
              faseOnda: Math.random() * Math.PI * 2,
              fatorPeso: 0.9
            });
          }
        }

        function aplicarPowerUp(subtipo, px, py) {
          const agora = performance.now();
          playSound(sons.acerto);

          if (subtipo === "ima") {
            imaAte = agora + 5000;
            adicionarFeedback(px, py, "🧲 Ímã (5s)!", "#64b5f6");
          } else if (subtipo === "freeze") {
            freezeAte = agora + 6000;
            adicionarFeedback(px, py, "⏳ Eco-Freeze (6s)!", "#80deea");
          } else if (subtipo === "escudo") {
            escudoAtivo = true;
            adicionarFeedback(px, py, "🛡️ Escudo Ativo!", "#4fc3f7");
          } else if (subtipo === "vida") {
            vidas = Math.min(5, vidas + 1);
            adicionarFeedback(px, py, "❤️ +1 Vida!", "#ff8a80");
          } else if (subtipo === "coringa") {
            let convertidos = 0;
            for (const c of clones) {
              if (c.kind === "base" || c.kind === "especial") {
                c.tipo = lixeiraFantasia;
                c.kind = "base";
                c.item = lixeiraFantasia;
                convertidos++;
              }
            }
            adicionarFeedback(px, py, "✨ Coringa (" + convertidos + ")!", "#ffd54f");
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
          tempoRestante = 60.0;
          ultimoTickTempo = agora;

          comboAtual = 0;
          errosNaPartida = 0;
          acertosVidro = 0;

          imaAte = 0;
          freezeAte = 0;
          escudoAtivo = false;
          congeladoAte = 0;

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
          proximoSpawn = agora + 1000;

          const tituloInicio = MODO_JOGO === "campanha"
            ? "FASE 1: " + faseAtual.nome.toUpperCase()
            : (MODO_JOGO === "infinito" ? "MODO INFINITO (ARCADE)" : "CONTRA O RELÓGIO (60s)");
          bannerFase = {
            texto: tituloInicio,
            subtitulo: "Desvie das pilhas 🔋 e pegue os bônus!",
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

        function rectsColidem(a, b) {
          return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
        }

        function desenharEntidadeCustom(c, cx, cy, cw, ch) {
          ctx.save();
          const centroX = cx + cw / 2;
          const centroY = cy + ch / 2;
          const raio = cw * 0.48;

          const imgExtra = imgs.extras[c.subtipo];
          if (imagemPronta(imgExtra)) {
            if (c.kind === "powerup") {
              ctx.beginPath();
              ctx.arc(centroX, centroY, raio + 2, 0, Math.PI * 2);
              ctx.fillStyle = "rgba(64, 196, 255, 0.25)";
              ctx.fill();
              ctx.lineWidth = 1.5;
              ctx.strokeStyle = "rgba(128, 222, 234, 0.85)";
              ctx.stroke();
            }
            ctx.drawImage(imgExtra, cx, cy, cw, ch);
            ctx.restore();
            return;
          }

          if (c.kind === "bomba") {
            ctx.fillStyle = "#212121";
            ctx.beginPath();
            ctx.arc(centroX, centroY, raio * 0.9, 0, Math.PI * 2);
            ctx.fill();
            ctx.lineWidth = 2.5;
            ctx.strokeStyle = "#ff1744";
            ctx.stroke();
            ctx.font = "22px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("🔋", centroX, centroY + 1);
          } else if (c.kind === "especial") {
            ctx.fillStyle = "#4e342e";
            ctx.beginPath();
            ctx.arc(centroX, centroY, raio * 0.9, 0, Math.PI * 2);
            ctx.fill();
            ctx.lineWidth = 2;
            ctx.strokeStyle = "#ffe082";
            ctx.stroke();
            ctx.font = "22px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("🍕", centroX, centroY + 1);
          } else if (c.kind === "saco") {
            const coresTipo = { 1: "#1565c0", 2: "#c62828", 3: "#2e7d32", 4: "#f9a825", 5: "#5d4037" };
            ctx.fillStyle = coresTipo[c.tipo] || "#37474f";
            ctx.beginPath();
            ctx.arc(centroX, centroY, raio * 0.9, 0, Math.PI * 2);
            ctx.fill();
            ctx.lineWidth = 2.5;
            ctx.strokeStyle = "#ffffff";
            ctx.stroke();
            ctx.font = "21px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText("🛍️", centroX, centroY + 1);
          } else if (c.kind === "powerup") {
            ctx.fillStyle = "rgba(13, 71, 161, 0.9)";
            ctx.beginPath();
            ctx.arc(centroX, centroY, raio * 0.9, 0, Math.PI * 2);
            ctx.fill();
            ctx.lineWidth = 2.5;
            ctx.strokeStyle = "#40c4ff";
            ctx.stroke();
            const icones = { ima: "🧲", freeze: "⏳", escudo: "🛡️", coringa: "✨", vida: "❤️" };
            ctx.font = "21px sans-serif";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            ctx.fillText(icones[c.subtipo] || "⭐", centroX, centroY + 1);
          }
          ctx.restore();
        }

        function encerrarPartida(vitoria) {
          estado = vitoria ? "vitoria" : "fim";
          pausado = false;
          atualizarBotaoPausar();
          lixeiraVisivel = false;
          dicaVisivel = false;
          clones = [];
          playSound(vitoria ? sons.vitoria : sons.fim);

          if (vitoria && MODO_JOGO === "campanha") {
            desbloquearBadge("campeao");
            if (errosNaPartida === 0) desbloquearBadge("precisao_100");
          }

          enviarPlacarSeguroParaPython(pontos, faseAtual.numero);
        }

        function loop(agora) {
          const tempoRef = pausado ? pausadoEm : agora;

          if (estado === "jogo" && !pausado) {
            if (MODO_JOGO === "tempo") {
              const dt = (agora - ultimoTickTempo) / 1000;
              tempoRestante = Math.max(0, tempoRestante - dt);
              ultimoTickTempo = agora;
              if (tempoRestante <= 0) {
                encerrarPartida(pontos >= 20);
              }
            }

            if (agora - ultimoAumentoVel >= 6500) {
              velocidade += MODO_JOGO === "infinito" ? 0.22 : 0.14;
              ultimoAumentoVel = agora;
            }

            const estaCongelado = agora < congeladoAte;
            if (!estaCongelado) {
              if (teclas["ArrowLeft"] || teclas["KeyA"]) lixeiraX -= 7.8;
              if (teclas["ArrowRight"] || teclas["KeyD"]) lixeiraX += 7.8;
              if (lixeiraX > 205) lixeiraX = 205;
              if (lixeiraX < -205) lixeiraX = -205;
            }

            if (agora >= proximoSpawn && clones.length < faseAtual.maxSim) {
              clones.push(gerarEntidadeSpawn());
              const intervalo = faseAtual.spawnMin + Math.random() * (faseAtual.spawnMax - faseAtual.spawnMin);
              proximoSpawn = agora + intervalo;
            }

            const imgL = imgs.lixeira[lixeiraFantasia - 1];
            const lw = (imgL && imgL.naturalWidth) || 80;
            const lh = (imgL && imgL.naturalHeight) || 84;
            const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);
            const rectLixeira = { x: lx, y: ly, w: lw, h: lh };

            const velEfetiva = agora < freezeAte ? velocidade * 0.5 : velocidade;
            const imaAtivo = agora < imaAte;

            const restantes = [];
            for (const c of clones) {
              c.y -= velEfetiva;

              if (faseAtual.ventoAmp > 0) {
                c.x += Math.sin((agora * 0.004) + c.faseOnda) * faseAtual.ventoAmp * c.fatorPeso;
              }

              if (imaAtivo && (c.kind === "base" || c.kind === "especial") && c.tipo === lixeiraFantasia) {
                c.x += (lixeiraX - c.x) * 0.07;
              }

              c.x = Math.max(-205, Math.min(205, c.x));

              let cw = 52, ch = 52;
              if (c.kind === "base") {
                const imgC = imgs.lixo[c.item - 1];
                cw = (imgC && imgC.naturalWidth) || 50;
                ch = (imgC && imgC.naturalHeight) || 50;
              }
              const [cx, cy] = scratchToCanvas(c.x, c.y, cw, ch);
              const rectItem = { x: cx, y: cy, w: cw, h: ch };

              if (rectsColidem(rectItem, rectLixeira)) {
                const px = lx + lw / 2;
                const py = ly - 6;

                if (c.kind === "powerup") {
                  aplicarPowerUp(c.subtipo, px, py);
                } else if (c.kind === "bomba") {
                  if (escudoAtivo) {
                    escudoAtivo = false;
                    adicionarFeedback(px, py, "🛡️ Bloqueada!", "#4fc3f7");
                  } else {
                    comboAtual = 0;
                    errosNaPartida += 1;
                    congeladoAte = agora + 2000;
                    flashErroAte = agora + 300;
                    playSound(sons.erro);
                    if (MODO_JOGO === "tempo") {
                      tempoRestante = Math.max(0, tempoRestante - 5);
                      adicionarFeedback(px, py, "🔋 -5s e Congelado!", "#ff5252");
                    } else {
                      vidas = Math.max(0, vidas - 2);
                      adicionarFeedback(px, py, "🔋 -2 ❤️ e Congelado!", "#ff5252");
                    }
                  }
                } else if (c.kind === "saco") {
                  abrirSacoNoAr(c);
                } else if (c.kind === "especial") {
                  if (lixeiraFantasia === c.tipo) {
                    desbloquearBadge("pizza_expert");
                    registrarAcerto(2, 5, px, py, "🍕 +2 Orgânico!");
                  } else {
                    dispararErro(c.tipo, px, py);
                  }
                } else {
                  if (lixeiraFantasia === c.tipo) {
                    registrarAcerto(1, c.tipo, px, py);
                  } else {
                    dispararErro(c.tipo, px, py);
                  }
                }
                continue;
              }

              if (c.y < -170) {
                if (c.kind === "base" || c.kind === "especial") {
                  dispararErro(c.tipo, cx + cw / 2, H - 30);
                }
                continue;
              }

              restantes.push(c);
            }
            clones = restantes;

            if (dicaVisivel && agora >= dicaAte) dicaVisivel = false;
            if (bannerFase && agora >= bannerFase.ate) bannerFase = null;

            if (MODO_JOGO !== "tempo" && vidas < 1) {
              encerrarPartida(false);
            } else if (MODO_JOGO === "campanha" && pontos >= META_CAMPANHA) {
              encerrarPartida(true);
            }
          }

          // ====================================================================
          // RENDERIZAÇÃO NO CANVAS
          // ====================================================================
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
            ctx.fillText("COLETA SELETIVA PRO", W / 2, 120);
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
            roundRect(W - 170, 8, 162, 28, 8);
            ctx.fill();
            ctx.fillStyle = "#ffe082";
            ctx.font = "bold 13px sans-serif";
            ctx.fillText("🏆 Recorde: " + recorde + " pts", W - 160, 27);
          } else if (estado === "jogo") {
            if (lixeiraVisivel) {
              const imgL = imgs.lixeira[lixeiraFantasia - 1];
              const lw = (imgL && imgL.naturalWidth) || 80;
              const lh = (imgL && imgL.naturalHeight) || 84;
              const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);

              if (escudoAtivo || tempoRef < imaAte || tempoRef < congeladoAte || comboAtual >= 5) {
                ctx.save();
                ctx.beginPath();
                ctx.arc(lx + lw / 2, ly + lh / 2, 48, 0, Math.PI * 2);
                if (tempoRef < congeladoAte) {
                  ctx.fillStyle = "rgba(0, 229, 255, 0.35)";
                } else if (escudoAtivo) {
                  ctx.fillStyle = "rgba(79, 195, 247, 0.28)";
                } else if (tempoRef < imaAte) {
                  ctx.fillStyle = "rgba(100, 181, 246, 0.28)";
                } else {
                  ctx.fillStyle = comboAtual >= 10 ? "rgba(255, 87, 34, 0.32)" : "rgba(255, 213, 79, 0.25)";
                }
                ctx.fill();
                ctx.restore();
              }

              if (imagemPronta(imgL)) {
                ctx.drawImage(imgL, lx, ly, lw, lh);
              } else {
                ctx.fillStyle = "#2e7d32";
                ctx.fillRect(lx, ly, lw, lh);
              }

              if (tempoRef < congeladoAte) {
                ctx.font = "22px sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("🧊", lx + lw / 2, ly + lh / 2);
                ctx.textAlign = "left";
              }
            }

            for (const c of clones) {
              if (c.kind === "base") {
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
              } else {
                const [cx, cy] = scratchToCanvas(c.x, c.y, 52, 52);
                desenharEntidadeCustom(c, cx, cy, 52, 52);
              }
            }

            if (dicaVisivel) {
              const imgD = imgs.dica[dicaFantasia - 1];
              const dw = (imgD && imgD.naturalWidth) || 440;
              const dh = (imgD && imgD.naturalHeight) || 60;
              const [dx, dy] = scratchToCanvas(0, 82, dw, dh, [220, 30]);
              if (imagemPronta(imgD)) {
                ctx.drawImage(imgD, dx, dy, dw, dh);
              }
            }

            if (bannerFase && tempoRef < bannerFase.ate) {
              ctx.save();
              ctx.fillStyle = "rgba(12, 28, 18, 0.92)";
              roundRect(W / 2 - 195, H / 2 - 42, 390, 68, 12);
              ctx.fill();
              ctx.strokeStyle = "#81c784";
              ctx.lineWidth = 2;
              ctx.stroke();

              ctx.textAlign = "center";
              ctx.fillStyle = "#ffe082";
              ctx.font = "bold 15px sans-serif";
              ctx.fillText(bannerFase.texto, W / 2, H / 2 - 14);

              ctx.fillStyle = "#c8e6c9";
              ctx.font = "12px sans-serif";
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
                ctx.font = "bold 15px sans-serif";
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
            roundRect(8, 8, 154, 28, 8);
            ctx.fill();
            roundRect(8, 40, 154, 28, 8);
            ctx.fill();
            roundRect(W - 162, 8, 154, 28, 8);
            ctx.fill();
            roundRect(W - 162, 40, 154, 28, 8);
            ctx.fill();

            ctx.fillStyle = "#ffffff";
            ctx.font = "bold 13px sans-serif";
            const labelPts = MODO_JOGO === "campanha"
              ? "♻️ Pontos: " + pontos + "/" + META_CAMPANHA
              : "♻️ Pontos: " + pontos;
            ctx.fillText(labelPts, 16, 27);

            if (MODO_JOGO === "tempo") {
              ctx.fillStyle = tempoRestante <= 10 ? "#ff5252" : "#80deea";
              ctx.fillText("⏱️ Tempo: " + Math.ceil(tempoRestante) + "s", 16, 59);
            } else {
              ctx.fillStyle = "#ffffff";
              ctx.fillText("❤️ Vidas: " + vidas + (escudoAtivo ? " 🛡️" : ""), 16, 59);
            }

            const mult = obterMultiplicadorCombo();
            ctx.fillStyle = mult > 1 ? "#ffd54f" : "#ffe082";
            ctx.fillText(
              mult > 1 ? "🔥 Combo " + mult + "x (" + comboAtual + ")" : "🏆 Recorde: " + recorde,
              W - 154,
              27
            );

            ctx.fillStyle = "#81c784";
            ctx.fillText("🚩 Fase " + faseAtual.numero + "/5", W - 154, 59);

            if (pausado) {
              ctx.fillStyle = "rgba(0, 0, 0, 0.62)";
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
            .replace("__MODO_JOGO__", json.dumps(modo_codigo))
        )

        if hasattr(st, "iframe"):
            st.iframe(html_jogo, height=640)
        else:
            import streamlit.components.v1 as components
            components.html(html_jogo, height=640, scrolling=False)

    # ==========================================================================
    # COLUNA DIREITA: TOP 5 OFICIAL
    # ==========================================================================
    with col_ranking:
        st.markdown('<div class="ranking-card">', unsafe_allow_html=True)
        r_top1, r_top2 = st.columns([1.6, 1])
        with r_top1:
            st.subheader("🏆 Top 5 Oficial")
        with r_top2:
            if st.button("🔄 Atualizar", use_container_width=True):
                st.rerun()

        if "flash_podio" in st.session_state:
            ok_flash, msg_flash = st.session_state.pop("flash_podio")
            if ok_flash:
                st.success(msg_flash)
            else:
                st.error(msg_flash)

        dados_gh, _, erro_gh = ler_ranking_github()
        if dados_gh is not None:
            st.caption("🔒 Salvamento seguro no servidor • Top 5 sem duplicados.")
        else:
            st.warning(f"⚠️ Modo offline: {erro_gh}")

        ranking_atual = dados_gh if dados_gh is not None else []
        nomes_modos = {"campanha": "Campanha", "infinito": "Infinito", "tempo": "60s"}

        if not ranking_atual:
            st.info("Nenhuma partida finalizada ainda. Jogue para inaugurar o Top 5!")
        else:
            medalhas = ["🥇", "🥈", "🥉"]
            for idx, item in enumerate(ranking_atual[:5]):
                pos = medalhas[idx] if idx < 3 else f"#{idx + 1}"
                fase_item = item.get("fase", 1)
                modo_item = nomes_modos.get(item.get("modo", "campanha"), "Campanha")
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
                            <small style="color:#a5d6a7;">{modo_item} · Fase {fase_item}/5 • {item['data']}</small>
                        </div>
                        <span style="font-weight:bold; color:#ffe082; font-size:1.05rem;">{item['pontos']} pts</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# ABA 2: ENCICLOPÉDIA "APRENDA JOGANDO"
# ==============================================================================
with aba_guia:
    st.subheader("📚 Guia Oficial da Coleta Seletiva & Mecânicas Especiais")
    st.write("Consulte o destino correto de cada resíduo, seu tempo de decomposição na natureza e os bônus do jogo.")

    st.markdown("### 1. Materiais Recicláveis e Orgânicos")
    st.table(
        [
            {"Ícone": "🔵 1 · Papel", "Exemplos no Jogo": "Jornal, folhas, caixa de papelão limpa", "Decomposição na Natureza": "3 a 6 meses", "Observação": "Deve estar seco e sem gordura."},
            {"Ícone": "🔴 2 · Plástico", "Exemplos no Jogo": "Garrafas plásticas e copos descartáveis", "Decomposição na Natureza": "Mais de 400 anos", "Observação": "Amasse embalagens para reduzir volume."},
            {"Ícone": "🟢 3 · Vidro", "Exemplos no Jogo": "Garrafas e potes de conserva", "Decomposição na Natureza": "Indeterminado (+4.000 anos)", "Observação": "100% reciclável infinitas vezes."},
            {"Ícone": "🟡 4 · Metal", "Exemplos no Jogo": "Latas de alumínio e aço", "Decomposição na Natureza": "100 a 500 anos", "Observação": "Reciclar alumínio economiza 95% de energia."},
            {"Ícone": "🟤 5 · Orgânico", "Exemplos no Jogo": "Maçã, casca de banana, 🍕 Caixa de Pizza com gordura", "Decomposição na Natureza": "2 semanas a 1 ano", "Observação": "Vira adubo rico via compostagem."},
        ]
    )

    c_arm, c_pwr = st.columns(2)
    with c_arm:
        st.markdown("### 2. Pegadinhas e Armadilhas")
        st.markdown(
            """
            * **🍕 Caixa de Pizza Engordurada:** Apesar de ser feita de papelão, a gordura contamina a reciclagem do papel. Jogue na lixeira **Marrom (Orgânico)** para ganhar **+2 pts**.
            * **🔋 Pilha Tóxica (Perigo!):** Metais pesados contaminam o solo. **Desvie dela!** Se cair na lixeira comum, tira **2 vidas** (ou 5s) e congela sua lixeira por 2 segundos.
            * **🛍️ Saco de Reciclagem:** Ao coletar, abre no ar e espalha **3 itens** do mesmo material.
            """
        )
    with c_pwr:
        st.markdown("### 3. Power-Ups Coletáveis")
        st.markdown(
            """
            * **🧲 Ímã Seletivo (5s):** Atrai automaticamente os lixos da cor selecionada.
            * **⏳ Eco-Freeze (6s):** Reduz a velocidade de queda pela metade.
            * **🛡️ Escudo Ambiental:** Absorve o próximo erro ou pilha tóxica sem perder vida.
            * **✨ Coringa:** Converte todos os lixos da tela para a cor da lixeira atual.
            * **❤️ Kit de Restauração:** Recupera +1 vida (aparece quando você tem $\le 2$ vidas).
            """
        )
