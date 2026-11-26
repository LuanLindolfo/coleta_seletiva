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
# DESIGN SYSTEM GAMIFICADO (CSS COM ESCOPO .st-key-* + AUGMENTED-UI + ARCADE)
# ==============================================================================
st.html(
    """
    <link rel="stylesheet" href="https://unpkg.com/augmented-ui@2/augmented-ui.min.css">
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@600;700&family=Inter:wght@400;600;700&display=swap');

    :root {
        --eco-bg-deep: #09130e;
        --eco-bg-mid: #102419;
        --eco-neon: #4ade80;
        --eco-cyan: #22d3ee;
        --eco-gold: #fbbf24;
        --eco-silver: #cbd5e1;
        --eco-bronze: #d97706;
    }

    /* Fundo com grade sutil estilo HUD Eco-Tech */
    .stApp {
        background-color: var(--eco-bg-deep);
        background-image:
            radial-gradient(circle at 20% 15%, rgba(34, 197, 94, 0.14), transparent 45%),
            radial-gradient(circle at 85% 80%, rgba(34, 211, 238, 0.10), transparent 45%),
            linear-gradient(rgba(74, 222, 128, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(74, 222, 128, 0.03) 1px, transparent 1px);
        background-size: 100% 100%, 100% 100%, 32px 32px, 32px 32px;
        color: #f0fdf4;
        font-family: 'Inter', sans-serif;
    }

    /* Reduz padding superior excessivo do Streamlit */
    .block-container {
        padding-top: 1.4rem !important;
        padding-bottom: 2rem !important;
    }

    /* Cabeçalho HUD com recortes chanfrados (augmented-ui) */
    .hud-header {
        --aug-border-bg: linear-gradient(90deg, #22c55e, #22d3ee, #22c55e);
        --aug-border-all: 2px;
        --aug-inlay-bg: rgba(12, 26, 19, 0.92);
        --aug-inlay-all: 3px;
        padding: 16px 24px;
        margin-bottom: 14px;
        text-align: center;
        filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.45));
    }

    .hud-header h1 {
        font-family: 'Chakra Petch', sans-serif;
        font-weight: 700;
        letter-spacing: 1px;
        margin: 0;
        font-size: 1.85rem;
        background: linear-gradient(90deg, #86efac, #fde047);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .hud-header p {
        margin: 6px 0 0 0;
        color: #bbf7d0;
        font-size: 0.88rem;
    }

    .kbd-tag {
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(134, 239, 172, 0.35);
        border-radius: 5px;
        padding: 1px 6px;
        font-family: 'Chakra Petch', sans-serif;
        font-size: 0.8rem;
        color: #fef08a;
    }

    /* Legenda das 5 Lixeiras com visual de Cartucho / Tecla Arcade */
    .bin-legend-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin-bottom: 14px;
    }

    .bin-pill {
        font-family: 'Chakra Petch', sans-serif;
        font-weight: 700;
        font-size: 0.86rem;
        letter-spacing: 0.5px;
        text-align: center;
        padding: 8px 6px;
        border-radius: 8px;
        color: #ffffff;
        text-transform: uppercase;
        transition: transform 0.15s ease;
    }

    .bin-pill:hover { transform: translateY(-2px); }
    .bin-1 { background: #1d4ed8; box-shadow: 0 4px 0 #1e3a8a; }
    .bin-2 { background: #dc2626; box-shadow: 0 4px 0 #7f1d1d; }
    .bin-3 { background: #15803d; box-shadow: 0 4px 0 #14532d; }
    .bin-4 { background: #eab308; color: #18181b; box-shadow: 0 4px 0 #854d0e; }
    .bin-5 { background: #6d4c41; box-shadow: 0 4px 0 #3e2723; }

    /* Container nativo do Pódio estilizado via .st-key-ranking_panel */
    .st-key-ranking_panel {
        background: linear-gradient(165deg, rgba(16, 36, 25, 0.92), rgba(9, 19, 14, 0.96));
        border: 1px solid rgba(74, 222, 128, 0.35);
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45), inset 0 0 20px rgba(74, 222, 128, 0.06);
        backdrop-filter: blur(10px);
    }

    /* Botão Atualizar nativo estilizado via key */
    .st-key-btn_refresh_rank button {
        font-family: 'Chakra Petch', sans-serif;
        font-weight: 700;
        background: rgba(34, 197, 94, 0.16);
        border: 1px solid rgba(74, 222, 128, 0.5);
        color: #86efac;
        border-radius: 8px;
        transition: all 0.15s ease;
    }
    .st-key-btn_refresh_rank button:hover {
        background: rgba(34, 197, 94, 0.3);
        border-color: #4ade80;
        color: #ffffff;
    }

    /* Inputs de Apelido e Modo via .st-key-* */
    .st-key-input_apelido input,
    .st-key-select_modo div[data-baseweb="select"] > div {
        background-color: rgba(15, 32, 23, 0.9) !important;
        border: 1px solid rgba(74, 222, 128, 0.35) !important;
        border-radius: 10px !important;
        color: #f0fdf4 !important;
        font-family: 'Chakra Petch', sans-serif !important;
    }

    /* Cards do Top 5 (Estilo Trophy UI + Tiers Metálicos) */
    .podium-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 11px 14px;
        border-radius: 10px;
        margin-bottom: 9px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.08);
        transition: transform 0.15s ease, border-color 0.15s ease;
    }
    .podium-row:hover {
        transform: translateX(3px);
        border-color: rgba(74, 222, 128, 0.45);
    }
    .podium-1 {
        background: linear-gradient(90deg, rgba(251, 191, 36, 0.22), rgba(251, 191, 36, 0.05));
        border: 1px solid rgba(251, 191, 36, 0.65);
        box-shadow: 0 0 15px rgba(251, 191, 36, 0.15);
    }
    .podium-2 {
        background: linear-gradient(90deg, rgba(203, 213, 225, 0.16), rgba(203, 213, 225, 0.04));
        border: 1px solid rgba(203, 213, 225, 0.45);
    }
    .podium-3 {
        background: linear-gradient(90deg, rgba(217, 119, 6, 0.18), rgba(217, 119, 6, 0.04));
        border: 1px solid rgba(217, 119, 6, 0.45);
    }
    .podium-pts {
        font-family: 'Chakra Petch', sans-serif;
        font-weight: 700;
        font-size: 1.1rem;
        color: #fde047;
        background: rgba(0, 0, 0, 0.35);
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid rgba(253, 224, 71, 0.25);
    }

    /* Abas estilizadas */
    button[data-baseweb="tab"] {
        font-family: 'Chakra Petch', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.98rem !important;
    }

    /* Cards da Enciclopédia */
    .wiki-card {
        background: rgba(16, 36, 25, 0.85);
        border: 1px solid rgba(74, 222, 128, 0.28);
        border-radius: 12px;
        padding: 16px;
        height: 100%;
    }
    .wiki-card h4 {
        font-family: 'Chakra Petch', sans-serif;
        color: #86efac;
        margin-top: 0;
    }
    </style>
    """
)

st.html(
    """
    <div class="hud-header" data-augmented-ui="tl-clip tr-clip br-clip bl-clip both">
        <h1>♻️ DESAFIO DA COLETA SELETIVA — EDIÇÃO EVOLUÍDA</h1>
        <p>
            📱 <b>Mobile:</b> Arraste e toque nas lixeiras &nbsp;•&nbsp;
            💻 <b>PC:</b> <span class="kbd-tag">◀ ▶</span> / <span class="kbd-tag">A-D</span> e <span class="kbd-tag">1</span> a <span class="kbd-tag">5</span> &nbsp;•&nbsp;
            <span class="kbd-tag">P</span> Pausar &nbsp;•&nbsp; <span class="kbd-tag">M</span> Som
        </p>
    </div>

    <div class="bin-legend-grid">
        <div class="bin-pill bin-1">1 · Papel</div>
        <div class="bin-pill bin-2">2 · Plástico</div>
        <div class="bin-pill bin-3">3 · Vidro</div>
        <div class="bin-pill bin-4">4 · Metal</div>
        <div class="bin-pill bin-5">5 · Orgânico</div>
    </div>
    """
)

# ==============================================================================
# CARREGAMENTO DE ASSETS EM BASE64
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
        "saco": asset_to_data_uri("saco_reciclagem.png"),
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
                key="input_apelido",
            )
        with c_modo:
            modo_label = st.selectbox(
                "🕹️ Modo de Jogo:",
                [
                    "🚩 Campanha (5 Fases · 40 pts)",
                    "♾️ Infinito (Arcade)",
                    "⏱️ Contra o Relógio (60s)",
                ],
                key="select_modo",
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
        <link rel="stylesheet" href="https://unpkg.com/augmented-ui@2/augmented-ui.min.css">
        <style>
          @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@600;700&family=Inter:wght@500;700&display=swap');

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
            font-family: 'Inter', sans-serif;
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
          /* Moldura Sci-Fi ao redor do Canvas (augmented-ui) */
          .canvas-frame {
            width: 100%;
            --aug-border-bg: linear-gradient(135deg, #4ade80, #22d3ee);
            --aug-border-all: 2px;
            --aug-inlay-bg: #102016;
            --aug-inlay-all: 2px;
            padding: 4px;
            filter: drop-shadow(0 12px 28px rgba(0, 0, 0, 0.55));
          }
          canvas {
            width: 100%;
            height: auto;
            aspect-ratio: 4 / 3;
            background: #1b2a1e;
            outline: none;
            touch-action: none;
            display: block;
          }
          #banner-status-podio {
            display: none;
            position: absolute;
            bottom: 130px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(10, 24, 16, 0.96);
            color: #fde047;
            font-family: 'Chakra Petch', sans-serif;
            font-weight: 700;
            font-size: 13px;
            padding: 10px 18px;
            border-radius: 10px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.75);
            border: 2px solid #4ade80;
            z-index: 20;
            white-space: nowrap;
          }

          /* Botões de Lixeira com Peso Físico Arcade (inspirado em RPGUI / NES.css) */
          .lixeiras-touch {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            width: 100%;
            margin-top: 12px;
          }
          .btn-lixeira {
            border: 2px solid rgba(255,255,255,0.18);
            border-radius: 10px;
            padding: 11px 2px;
            font-family: 'Chakra Petch', sans-serif;
            font-weight: 700;
            font-size: 13px;
            letter-spacing: 0.4px;
            color: #fff;
            cursor: pointer;
            transition: transform 0.08s ease, box-shadow 0.08s ease, border-color 0.15s ease;
            text-align: center;
          }
          .b1 { background: #1d4ed8; box-shadow: 0 4px 0 #1e3a8a; }
          .b2 { background: #dc2626; box-shadow: 0 4px 0 #7f1d1d; }
          .b3 { background: #15803d; box-shadow: 0 4px 0 #14532d; }
          .b4 { background: #eab308; color: #18181b; box-shadow: 0 4px 0 #854d0e; }
          .b5 { background: #6d4c41; box-shadow: 0 4px 0 #3e2723; }

          .btn-lixeira:active {
            transform: translateY(3px);
            box-shadow: 0 1px 0 rgba(0,0,0,0.6);
          }
          .btn-lixeira.ativa {
            border-color: #ffffff;
            transform: translateY(-2px);
            filter: brightness(1.15);
            box-shadow: 0 6px 0 rgba(0,0,0,0.55), 0 0 14px rgba(255, 255, 255, 0.55);
          }

          .barra-inferior {
            margin-top: 12px;
            width: 100%;
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 6px;
            font-size: 12px;
            color: #bbf7d0;
          }
          .acoes {
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
          }
          .btn-mini {
            background: #14291d;
            color: #dcfce7;
            border: 1px solid #4ade80;
            border-radius: 8px;
            padding: 6px 12px;
            font-family: 'Chakra Petch', sans-serif;
            font-size: 12px;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 3px 0 #0a1710;
            transition: transform 0.08s ease;
          }
          .btn-mini:active {
            transform: translateY(2px);
            box-shadow: 0 1px 0 #0a1710;
          }

          /* Conquistas estilo Trophy UI com animação ao desbloquear */
          @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 0 6px rgba(74, 222, 128, 0.35); }
            50% { box-shadow: 0 0 14px rgba(250, 204, 21, 0.65); }
          }
          .badges-strip {
            margin-top: 10px;
            width: 100%;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            justify-content: center;
          }
          .badge-pill {
            font-family: 'Chakra Petch', sans-serif;
            font-size: 11px;
            padding: 4px 10px;
            border-radius: 999px;
            background: rgba(15, 23, 42, 0.65);
            border: 1px dashed rgba(148, 163, 184, 0.3);
            color: #94a3b8;
          }
          .badge-pill.unlocked {
            background: linear-gradient(90deg, rgba(22, 101, 52, 0.85), rgba(21, 128, 61, 0.85));
            border: 1px solid #fde047;
            color: #fef9c3;
            font-weight: 700;
            animation: pulseGlow 2.8s infinite ease-in-out;
          }
        </style>
        </head>
        <body>
        <div class="game-wrapper">
          <div class="canvas-frame" data-augmented-ui="tl-clip tr-clip br-clip bl-clip both">
            <canvas id="game" width="480" height="360" tabindex="0"></canvas>
          </div>

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
        /* [O SEU SCRIPT JAVASCRIPT COMPLETO PERMANECE EXATAMENTE IGUAL AQUI] */
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
          try { return JSON.parse(localStorage.getItem(BADGES_KEY) || "{}"); } catch (e) { return {}; }
        }
        let badgesDesbloqueadas = carregarBadges();

        function desbloquearBadge(id) {
          if (badgesDesbloqueadas[id]) return;
          badgesDesbloqueadas[id] = true;
          try { localStorage.setItem(BADGES_KEY, JSON.stringify(badgesDesbloqueadas)); } catch (e) {}
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
          for (const f of FASES_CONFIG) { if (pts >= f.minPts) atual = f; }
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
          } catch (e) { return 0; }
        }
        function salvarRecorde(novoRecorde) {
          try { localStorage.setItem(STORAGE_KEY, String(novoRecorde)); } catch (e) {}
        }
        function enviarPlacarSeguroParaPython(ptsFinal, faseFinal) {
          const pts = Math.max(0, Math.round(ptsFinal));
          const faseAlcancada = Math.max(1, Math.min(5, faseFinal));
          bannerPodio.style.display = "block";
          bannerPodio.style.borderColor = "#4ade80";
          bannerPodio.style.color = "#4ade80";
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
              bannerPodio.style.borderColor = "#fbbf24";
              bannerPodio.textContent = "✅ Partida encerrada: " + pts + " pts!";
            }
          }, 1400);
        }
        function loadImg(src) { const img = new Image(); if (src) img.src = src; return img; }
        function loadAudio(src) { return src ? new Audio(src) : null; }
        let mudo = false;
        function alternarMute() { mudo = !mudo; btnMute.textContent = mudo ? "🔇 Mudo" : "🔊 Som"; focarCanvas(); }
        btnMute.addEventListener("click", alternarMute);
        function playSound(aud) { if (!aud || mudo) return; try { aud.currentTime = 0; aud.play().catch(() => {}); } catch (e) {} }

        const imgs = {
          bg: { instrucoes: loadImg(URIS.bg_instrucoes), jogo: loadImg(URIS.bg_jogo), fim: loadImg(URIS.bg_fim), vitoria: loadImg(URIS.bg_vitoria) },
          botao: loadImg(URIS.botao_iniciar),
          lixeira: URIS.lixeira.map(loadImg),
          lixo: URIS.lixo.map(loadImg),
          dica: URIS.dica.map(loadImg),
          extras: { coringa: loadImg(URIS.extras.coringa), vida: loadImg(URIS.extras.vida), ima: loadImg(URIS.extras.ima), escudo: loadImg(URIS.extras.escudo), freeze: loadImg(URIS.extras.freeze), pizza: loadImg(URIS.extras.pizza), saco: loadImg(URIS.extras.saco) }
        };
        const sons = { acerto: loadAudio(URIS.som_acerto), erro: loadAudio(URIS.som_erro), fim: loadAudio(URIS.som_fim), vitoria: loadAudio(URIS.som_vitoria) };

        function scratchToCanvas(x, y, w, h, rotCenter = null) { return rotCenter ? [W / 2 + x - rotCenter[0], H / 2 - y - rotCenter[1]] : [W / 2 + x - w / 2, H / 2 - y - h / 2]; }
        function imagemPronta(img) { return Boolean(img && img.complete && img.naturalWidth > 0 && img.naturalHeight > 0); }
        function roundRect(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }

        let estado = "instrucoes", pausado = false, pausadoEm = 0, pontos = 0, recorde = lerRecorde(), vidas = 5, tempoRestante = 60.0, ultimoTickTempo = 0;
        let faseAtual = FASES_CONFIG[0], velocidade = faseAtual.velBase, ultimoTipo = 1, comboAtual = 0, errosNaPartida = 0, acertosVidro = 0;
        let imaAte = 0, freezeAte = 0, escudoAtivo = false, congeladoAte = 0, bannerFase = null;
        let lixeiraX = 0, lixeiraY = -135, lixeiraFantasia = 1, lixeiraVisivel = false, dicaVisivel = false, dicaFantasia = 1, dicaAte = 0;
        let clones = [], feedbacks = [], flashErroAte = 0, proximoSpawn = 0, ultimoAumentoVel = 0;
        const teclas = {};

        function selecionarLixeira(tipo) {
          if (estado === "jogo" && performance.now() < congeladoAte) return;
          lixeiraFantasia = tipo;
          botoesLixeira.forEach((btn) => btn.classList.toggle("ativa", Number(btn.dataset.tipo) === tipo));
        }
        botoesLixeira.forEach((btn) => btn.addEventListener("pointerdown", (e) => { e.preventDefault(); selecionarLixeira(Number(btn.dataset.tipo)); if (estado === "instrucoes") iniciarPartida(); focarCanvas(); }));

        let arrastando = false;
        function atualizarPosicaoPorPonteiro(clientX) {
          if (performance.now() < congeladoAte) return;
          const rect = canvas.getBoundingClientRect();
          const relX = (clientX - rect.left) / rect.width;
          lixeiraX = Math.max(-205, Math.min(205, (relX * W) - (W / 2)));
        }
        canvas.addEventListener("pointerdown", (e) => { focarCanvas(); if (estado === "instrucoes") { iniciarPartida(); return; } if (estado === "jogo" && !pausado) { arrastando = true; atualizarPosicaoPorPonteiro(e.clientX); } });
        canvas.addEventListener("pointermove", (e) => { if (arrastando && estado === "jogo" && !pausado) atualizarPosicaoPorPonteiro(e.clientX); });
        window.addEventListener("pointerup", () => { arrastando = false; });

        function atualizarBotaoPausar() { btnPausar.textContent = pausado ? "▶ Continuar" : "⏸ Pausar"; }
        function alternarPausa() {
          if (estado !== "jogo") return;
          const agora = performance.now();
          if (!pausado) { pausado = true; pausadoEm = agora; } else {
            const delta = agora - pausadoEm;
            ultimoAumentoVel += delta; proximoSpawn += delta; ultimoTickTempo += delta;
            if (dicaVisivel) dicaAte += delta; if (flashErroAte > 0) flashErroAte += delta;
            if (imaAte > 0) imaAte += delta; if (freezeAte > 0) freezeAte += delta; if (congeladoAte > 0) congeladoAte += delta;
            if (bannerFase) bannerFase.ate += delta;
            for (const fb of feedbacks) fb.criadoEm += delta;
            pausado = false;
          }
          atualizarBotaoPausar(); focarCanvas();
        }
        btnPausar.addEventListener("click", alternarPausa);

        function obterMultiplicadorCombo() { return comboAtual >= 10 ? 3 : (comboAtual >= 5 ? 2 : 1); }
        function registrarAcerto(basePts = 1, tipoMaterial = 1, px = W / 2, py = H / 2, msgCustom = null) {
          comboAtual += 1;
          if (comboAtual >= 10) desbloquearBadge("combo_3x");
          if (tipoMaterial === 3) { acertosVidro += 1; if (acertosVidro >= 10) desbloquearBadge("mestre_vidro"); }
          const mult = obterMultiplicadorCombo(), ganho = basePts * mult;
          pontos += ganho;
          if (MODO_JOGO === "campanha" && pontos > META_CAMPANHA) pontos = META_CAMPANHA;
          if (pontos > recorde) { recorde = pontos; salvarRecorde(recorde); }
          adicionarFeedback(px, py, msgCustom || ("+" + ganho + (mult > 1 ? " (" + mult + "x!)" : " ♻️")), mult > 1 ? "#ffd54f" : "#69f0ae");
          playSound(sons.acerto);
          const novaFase = obterConfigFase(pontos);
          if (novaFase.numero > faseAtual.numero) {
            if (faseAtual.numero === 4) desbloquearBadge("sobrevivente");
            faseAtual = novaFase; velocidade = faseAtual.velBase; clones = [];
            const agora = performance.now(); proximoSpawn = agora + 1400;
            let msgBonus = "";
            if (MODO_JOGO !== "tempo" && vidas < 5) { vidas += 1; msgBonus = " • +1 ❤️ Bônus!"; }
            else if (MODO_JOGO === "tempo") { tempoRestante += 5; msgBonus = " • +5s Bônus!"; }
            bannerFase = { texto: "✨ FASE " + faseAtual.numero + ": " + faseAtual.nome.toUpperCase() + " ✨", subtitulo: faseAtual.desc + msgBonus, ate: agora + 2100 };
          }
        }
        function dispararErro(tipoCorreto, px = W / 2, py = H / 2) {
          const agora = performance.now();
          if (escudoAtivo) { escudoAtivo = false; adicionarFeedback(px, py, "🛡️ Escudo!", "#4fc3f7"); playSound(sons.acerto); return; }
          comboAtual = 0; errosNaPartida += 1;
          if (MODO_JOGO === "tempo") { tempoRestante = Math.max(0, tempoRestante - 3); adicionarFeedback(px, py, "-3s ⏱️", "#ff5252"); }
          else if (vidas > 0) { vidas -= 1; adicionarFeedback(px, py, "-1 ❤️", "#ff5252"); }
          ultimoTipo = tipoCorreto; flashErroAte = agora + 240; playSound(sons.erro);
          if (tipoCorreto >= 1 && tipoCorreto <= 5) { dicaFantasia = tipoCorreto; dicaVisivel = true; dicaAte = agora + 2500; }
        }
        function gerarEntidadeSpawn() {
          const r = Math.random(), x = Math.floor(Math.random() * 380) - 190, faseOnda = Math.random() * Math.PI * 2;
          if (r < 0.12) {
            const poolPwr = ["ima", "freeze", "escudo", "coringa"];
            if (MODO_JOGO !== "tempo" && vidas <= 2) poolPwr.push("vida", "vida");
            return { x, y: 175, kind: "powerup", subtipo: poolPwr[Math.floor(Math.random() * poolPwr.length)], tipo: 0, faseOnda, fatorPeso: 0.6 };
          }
          if (pontos >= 3 && r < 0.21) return { x, y: 175, kind: "bomba", subtipo: "pilha", tipo: 0, faseOnda, fatorPeso: 0.7 };
          if (r < 0.37) {
            return Math.random() < 0.55
              ? { x, y: 175, kind: "especial", subtipo: "pizza", tipo: 5, faseOnda, fatorPeso: 1.2 }
              : { x, y: 175, kind: "saco", subtipo: "saco", tipo: Math.floor(Math.random() * 5) + 1, faseOnda, fatorPeso: 0.9 };
          }
          const item = Math.floor(Math.random() * 10) + 1, tipo = ((item - 1) % 5) + 1;
          return { x, y: 175, kind: "base", item, tipo, faseOnda, fatorPeso: (tipo === 1 || tipo === 2) ? 1.35 : 0.75 };
        }
        function abrirSacoNoAr(saco) {
          playSound(sons.acerto);
          const [sx, sy] = scratchToCanvas(saco.x, saco.y, 52, 52);
          adicionarFeedback(sx + 26, sy, "🛍️ +3 Itens no topo!", "#81c784");
          const posicoesX = [-125, 0, 125], alturasY = [175, 205, 235];
          for (let i = 0; i < 3; i++) {
            clones.push({ x: posicoesX[i], y: alturasY[i], kind: "base", item: saco.tipo + (Math.random() < 0.5 ? 0 : 5), tipo: saco.tipo, faseOnda: Math.random() * Math.PI * 2, fatorPeso: 0.85 });
          }
          proximoSpawn = Math.max(proximoSpawn, performance.now() + 1400);
        }
        function aplicarPowerUp(subtipo, px, py) {
          const agora = performance.now(); playSound(sons.acerto);
          if (subtipo === "ima") { imaAte = agora + 5000; adicionarFeedback(px, py, "🧲 Ímã (5s)!", "#64b5f6"); }
          else if (subtipo === "freeze") { freezeAte = agora + 6000; adicionarFeedback(px, py, "⏳ Eco-Freeze (6s)!", "#80deea"); }
          else if (subtipo === "escudo") { escudoAtivo = true; adicionarFeedback(px, py, "🛡️ Escudo Ativo!", "#4fc3f7"); }
          else if (subtipo === "vida") { vidas = Math.min(5, vidas + 1); adicionarFeedback(px, py, "❤️ +1 Vida!", "#ff8a80"); }
          else if (subtipo === "coringa") {
            let convertidos = 0;
            for (const c of clones) { if (c.kind === "base" || c.kind === "especial") { c.tipo = lixeiraFantasia; c.kind = "base"; c.item = lixeiraFantasia; convertidos++; } }
            adicionarFeedback(px, py, "✨ Coringa (" + convertidos + ")!", "#ffd54f");
          }
        }
        function iniciarPartida() {
          const agora = performance.now();
          estado = "jogo"; pausado = false; bannerPodio.style.display = "none"; atualizarBotaoPausar();
          pontos = 0; vidas = 5; tempoRestante = 60.0; ultimoTickTempo = agora;
          comboAtual = 0; errosNaPartida = 0; acertosVidro = 0;
          imaAte = 0; freezeAte = 0; escudoAtivo = false; congeladoAte = 0;
          faseAtual = FASES_CONFIG[0]; velocidade = faseAtual.velBase; ultimoTipo = 1;
          lixeiraX = 0; lixeiraY = -135; selecionarLixeira(1); lixeiraVisivel = true; dicaVisivel = false;
          clones = []; feedbacks = []; flashErroAte = 0; ultimoAumentoVel = agora; proximoSpawn = agora + 1000;
          const tituloInicio = MODO_JOGO === "campanha" ? "FASE 1: " + faseAtual.nome.toUpperCase() : (MODO_JOGO === "infinito" ? "MODO INFINITO (ARCADE)" : "CONTRA O RELÓGIO (60s)");
          bannerFase = { texto: tituloInicio, subtitulo: "Desvie das pilhas 🔋 e pegue os bônus!", ate: agora + 1800 };
        }
        btnIniciarTop.addEventListener("click", () => { iniciarPartida(); focarCanvas(); });
        window.addEventListener("keydown", (e) => {
          teclas[e.code] = true;
          if (["Space", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.code)) e.preventDefault();
          if (e.key && e.key.toLowerCase() === "m") { alternarMute(); return; }
          if (e.key && e.key.toLowerCase() === "p") { alternarPausa(); return; }
          if (estado === "instrucoes" && e.code === "Space") iniciarPartida();
          else if (estado === "jogo" && !pausado && ["1", "2", "3", "4", "5"].includes(e.key)) selecionarLixeira(Number(e.key));
        });
        window.addEventListener("keyup", (e) => { teclas[e.code] = false; });
        function adicionarFeedback(x, y, texto, cor) { feedbacks.push({ x, y, texto, cor, criadoEm: performance.now() }); }
        function rectsColidem(a, b) { return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y; }

        function desenharEntidadeCustom(c, cx, cy, cw, ch) {
          ctx.save();
          const centroX = cx + cw / 2, centroY = cy + ch / 2, raio = cw * 0.48;
          const coresTipo = { 1: "#1565c0", 2: "#c62828", 3: "#2e7d32", 4: "#f9a825", 5: "#5d4037" };
          const imgExtra = imgs.extras[c.subtipo];
          if (imagemPronta(imgExtra)) {
            if (c.kind === "powerup") {
              ctx.beginPath(); ctx.arc(centroX, centroY, raio + 2, 0, Math.PI * 2);
              ctx.fillStyle = "rgba(64, 196, 255, 0.25)"; ctx.fill();
              ctx.lineWidth = 1.5; ctx.strokeStyle = "rgba(128, 222, 234, 0.85)"; ctx.stroke();
            }
            ctx.drawImage(imgExtra, cx, cy, cw, ch);
            if (c.kind === "saco") {
              ctx.beginPath(); ctx.arc(cx + cw - 9, cy + ch - 9, 8, 0, Math.PI * 2);
              ctx.fillStyle = coresTipo[c.tipo] || "#2e7d32"; ctx.fill();
              ctx.lineWidth = 1.5; ctx.strokeStyle = "#ffffff"; ctx.stroke();
              ctx.fillStyle = c.tipo === 4 ? "#1b1b1b" : "#ffffff";
              ctx.font = "bold 10px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
              ctx.fillText(String(c.tipo), cx + cw - 9, cy + ch - 8.5);
            }
            ctx.restore(); return;
          }
          ctx.beginPath(); ctx.arc(centroX, centroY, raio * 0.9, 0, Math.PI * 2);
          ctx.fillStyle = c.kind === "bomba" ? "#212121" : (c.kind === "especial" ? "#4e342e" : (c.kind === "saco" ? (coresTipo[c.tipo] || "#37474f") : "rgba(13, 71, 161, 0.9)"));
          ctx.fill();
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = c.kind === "bomba" ? "#ff1744" : (c.kind === "especial" ? "#ffe082" : (c.kind === "saco" ? "#ffffff" : "#40c4ff"));
          ctx.stroke();
          const icones = { ima: "🧲", freeze: "⏳", escudo: "🛡️", coringa: "✨", vida: "❤️" };
          const emoji = c.kind === "bomba" ? "🔋" : (c.kind === "especial" ? "🍕" : (c.kind === "saco" ? "🛍️" : (icones[c.subtipo] || "⭐")));
          ctx.font = "21px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.fillText(emoji, centroX, centroY + 1);
          ctx.restore();
        }

        function encerrarPartida(vitoria) {
          estado = vitoria ? "vitoria" : "fim"; pausado = false; atualizarBotaoPausar();
          lixeiraVisivel = false; dicaVisivel = false; clones = [];
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
              if (tempoRestante <= 0) encerrarPartida(pontos >= 20);
            }
            if (agora - ultimoAumentoVel >= 6500) {
              velocidade += MODO_JOGO === "infinito" ? 0.22 : 0.14;
              ultimoAumentoVel = agora;
            }
            if (agora >= congeladoAte) {
              if (teclas["ArrowLeft"] || teclas["KeyA"]) lixeiraX -= 7.8;
              if (teclas["ArrowRight"] || teclas["KeyD"]) lixeiraX += 7.8;
              lixeiraX = Math.max(-205, Math.min(205, lixeiraX));
            }
            if (agora >= proximoSpawn && clones.length < faseAtual.maxSim) {
              clones.push(gerarEntidadeSpawn());
              proximoSpawn = agora + faseAtual.spawnMin + Math.random() * (faseAtual.spawnMax - faseAtual.spawnMin);
            }
            const imgL = imgs.lixeira[lixeiraFantasia - 1];
            const lw = (imgL && imgL.naturalWidth) || 80, lh = (imgL && imgL.naturalHeight) || 84;
            const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);
            const rectLixeira = { x: lx, y: ly, w: lw, h: lh };
            const velEfetiva = agora < freezeAte ? velocidade * 0.5 : velocidade;
            const imaAtivo = agora < imaAte;
            const restantes = [];

            for (const c of clones) {
              c.y -= velEfetiva;
              if (faseAtual.ventoAmp > 0) c.x += Math.sin((agora * 0.004) + c.faseOnda) * faseAtual.ventoAmp * c.fatorPeso;
              if (imaAtivo && (c.kind === "base" || c.kind === "especial") && c.tipo === lixeiraFantasia) c.x += (lixeiraX - c.x) * 0.07;
              c.x = Math.max(-205, Math.min(205, c.x));

              let cw = 52, ch = 52;
              if (c.kind === "base") {
                const imgC = imgs.lixo[c.item - 1];
                cw = (imgC && imgC.naturalWidth) || 50; ch = (imgC && imgC.naturalHeight) || 50;
              }
              const [cx, cy] = scratchToCanvas(c.x, c.y, cw, ch);
              if (rectsColidem({ x: cx, y: cy, w: cw, h: ch }, rectLixeira)) {
                const px = lx + lw / 2, py = ly - 6;
                if (c.kind === "powerup") aplicarPowerUp(c.subtipo, px, py);
                else if (c.kind === "bomba") {
                  if (escudoAtivo) { escudoAtivo = false; adicionarFeedback(px, py, "🛡️ Bloqueada!", "#4fc3f7"); }
                  else {
                    comboAtual = 0; errosNaPartida += 1; congeladoAte = agora + 2000; flashErroAte = agora + 300; playSound(sons.erro);
                    if (MODO_JOGO === "tempo") { tempoRestante = Math.max(0, tempoRestante - 5); adicionarFeedback(px, py, "🔋 -5s e Congelado!", "#ff5252"); }
                    else { vidas = Math.max(0, vidas - 2); adicionarFeedback(px, py, "🔋 -2 ❤️ e Congelado!", "#ff5252"); }
                  }
                } else if (c.kind === "saco") abrirSacoNoAr(c);
                else if (c.kind === "especial") {
                  if (lixeiraFantasia === c.tipo) { desbloquearBadge("pizza_expert"); registrarAcerto(2, 5, px, py, "🍕 +2 Orgânico!"); }
                  else dispararErro(c.tipo, px, py);
                } else {
                  if (lixeiraFantasia === c.tipo) registrarAcerto(1, c.tipo, px, py);
                  else dispararErro(c.tipo, px, py);
                }
                continue;
              }
              if (c.y < -170) {
                if (c.kind === "base" || c.kind === "especial") dispararErro(c.tipo, cx + cw / 2, H - 30);
                continue;
              }
              restantes.push(c);
            }
            clones = restantes;
            if (dicaVisivel && agora >= dicaAte) dicaVisivel = false;
            if (bannerFase && agora >= bannerFase.ate) bannerFase = null;
            if (MODO_JOGO !== "tempo" && vidas < 1) encerrarPartida(false);
            else if (MODO_JOGO === "campanha" && pontos >= META_CAMPANHA) encerrarPartida(true);
          }

          ctx.save();
          if (!pausado && tempoRef < flashErroAte) ctx.translate(Math.sin(tempoRef * 0.08) * 3, 0);
          ctx.clearRect(-10, -10, W + 20, H + 20);
          ctx.fillStyle = "#1b2a1e"; ctx.fillRect(0, 0, W, H);

          const bgAtual = imgs.bg[estado];
          if (imagemPronta(bgAtual)) ctx.drawImage(bgAtual, 0, 0, W, H);
          else if (estado === "instrucoes") {
            ctx.fillStyle = "#ffffff"; ctx.font = "bold 22px sans-serif"; ctx.textAlign = "center";
            ctx.fillText("COLETA SELETIVA PRO", W / 2, 120);
            ctx.font = "15px sans-serif"; ctx.fillStyle = "#a5d6a7";
            ctx.fillText("Toque na tela ou aperte ESPAÇO", W / 2, 160); ctx.textAlign = "left";
          }

          if (estado === "instrucoes") {
            if (imagemPronta(imgs.botao)) {
              const escala = Math.floor(agora / 300) % 2 === 1 ? 1.08 : 1.0;
              const bw = imgs.botao.naturalWidth * escala, bh = imgs.botao.naturalHeight * escala;
              const [bx, by] = scratchToCanvas(36, 28, bw, bh, [147.5 * escala, -121.4 * escala]);
              ctx.drawImage(imgs.botao, bx, by, bw, bh);
            }
            ctx.fillStyle = "rgba(15, 25, 18, 0.88)"; roundRect(W - 170, 8, 162, 28, 8); ctx.fill();
            ctx.fillStyle = "#ffe082"; ctx.font = "bold 13px sans-serif";
            ctx.fillText("🏆 Recorde: " + recorde + " pts", W - 160, 27);
          } else if (estado === "jogo") {
            if (lixeiraVisivel) {
              const imgL = imgs.lixeira[lixeiraFantasia - 1];
              const lw = (imgL && imgL.naturalWidth) || 80, lh = (imgL && imgL.naturalHeight) || 84;
              const [lx, ly] = scratchToCanvas(lixeiraX, lixeiraY, lw, lh, [40, 42]);
              if (escudoAtivo || tempoRef < imaAte || tempoRef < congeladoAte || comboAtual >= 5) {
                ctx.save(); ctx.beginPath(); ctx.arc(lx + lw / 2, ly + lh / 2, 48, 0, Math.PI * 2);
                ctx.fillStyle = tempoRef < congeladoAte ? "rgba(0, 229, 255, 0.35)" : (escudoAtivo ? "rgba(79, 195, 247, 0.28)" : (tempoRef < imaAte ? "rgba(100, 181, 246, 0.28)" : (comboAtual >= 10 ? "rgba(255, 87, 34, 0.32)" : "rgba(255, 213, 79, 0.25)")));
                ctx.fill(); ctx.restore();
              }
              if (imagemPronta(imgL)) ctx.drawImage(imgL, lx, ly, lw, lh);
              else { ctx.fillStyle = "#2e7d32"; ctx.fillRect(lx, ly, lw, lh); }
              if (tempoRef < congeladoAte) { ctx.font = "22px sans-serif"; ctx.textAlign = "center"; ctx.fillText("🧊", lx + lw / 2, ly + lh / 2); ctx.textAlign = "left"; }
            }
            for (const c of clones) {
              if (c.kind === "base") {
                const imgC = imgs.lixo[c.item - 1];
                const cw = (imgC && imgC.naturalWidth) || 50, ch = (imgC && imgC.naturalHeight) || 50;
                const [cx, cy] = scratchToCanvas(c.x, c.y, cw, ch);
                if (imagemPronta(imgC)) ctx.drawImage(imgC, cx, cy, cw, ch);
                else { ctx.fillStyle = "#fbc02d"; ctx.fillRect(cx, cy, cw, ch); }
              } else {
                const [cx, cy] = scratchToCanvas(c.x, c.y, 52, 52);
                desenharEntidadeCustom(c, cx, cy, 52, 52);
              }
            }
            if (dicaVisivel) {
              const imgD = imgs.dica[dicaFantasia - 1];
              const dw = (imgD && imgD.naturalWidth) || 440, dh = (imgD && imgD.naturalHeight) || 60;
              const [dx, dy] = scratchToCanvas(0, 82, dw, dh, [220, 30]);
              if (imagemPronta(imgD)) ctx.drawImage(imgD, dx, dy, dw, dh);
            }
            if (bannerFase && tempoRef < bannerFase.ate) {
              ctx.save(); ctx.fillStyle = "rgba(12, 28, 18, 0.92)"; roundRect(W / 2 - 195, H / 2 - 42, 390, 68, 12); ctx.fill();
              ctx.strokeStyle = "#81c784"; ctx.lineWidth = 2; ctx.stroke();
              ctx.textAlign = "center"; ctx.fillStyle = "#ffe082"; ctx.font = "bold 15px sans-serif"; ctx.fillText(bannerFase.texto, W / 2, H / 2 - 14);
              ctx.fillStyle = "#c8e6c9"; ctx.font = "12px sans-serif"; ctx.fillText(bannerFase.subtitulo, W / 2, H / 2 + 10); ctx.restore();
            }
            const proxFeedbacks = [];
            for (const fb of feedbacks) {
              const elapsed = tempoRef - fb.criadoEm;
              if (elapsed < 750) {
                ctx.save(); ctx.globalAlpha = Math.max(0, 1 - (elapsed / 750)); ctx.font = "bold 15px sans-serif";
                ctx.textAlign = "center"; ctx.fillStyle = fb.cor; ctx.fillText(fb.texto, fb.x, fb.y - (elapsed * 0.04)); ctx.restore();
                proxFeedbacks.push(fb);
              }
            }
            feedbacks = proxFeedbacks;

            ctx.fillStyle = "rgba(15, 25, 18, 0.88)";
            roundRect(8, 8, 154, 28, 8); ctx.fill(); roundRect(8, 40, 154, 28, 8); ctx.fill();
            roundRect(W - 162, 8, 154, 28, 8); ctx.fill(); roundRect(W - 162, 40, 154, 28, 8); ctx.fill();

            ctx.fillStyle = "#ffffff"; ctx.font = "bold 13px sans-serif";
            ctx.fillText(MODO_JOGO === "campanha" ? "♻️ Pontos: " + pontos + "/" + META_CAMPANHA : "♻️ Pontos: " + pontos, 16, 27);
            if (MODO_JOGO === "tempo") { ctx.fillStyle = tempoRestante <= 10 ? "#ff5252" : "#80deea"; ctx.fillText("⏱️ Tempo: " + Math.ceil(tempoRestante) + "s", 16, 59); }
            else { ctx.fillStyle = "#ffffff"; ctx.fillText("❤️ Vidas: " + vidas + (escudoAtivo ? " 🛡️" : ""), 16, 59); }
            const mult = obterMultiplicadorCombo();
            ctx.fillStyle = mult > 1 ? "#ffd54f" : "#ffe082";
            ctx.fillText(mult > 1 ? "🔥 Combo " + mult + "x (" + comboAtual + ")" : "🏆 Recorde: " + recorde, W - 154, 27);
            ctx.fillStyle = "#81c784"; ctx.fillText("🚩 Fase " + faseAtual.numero + "/5", W - 154, 59);

            if (pausado) {
              ctx.fillStyle = "rgba(0, 0, 0, 0.62)"; ctx.fillRect(0, 0, W, H);
              ctx.fillStyle = "#ffffff"; ctx.font = "bold 26px sans-serif"; ctx.textAlign = "center";
              ctx.fillText("PAUSADO", W / 2, H / 2 - 6);
              ctx.font = "14px sans-serif"; ctx.fillStyle = "#cfd8dc"; ctx.fillText("Toque em Continuar ou aperte P", W / 2, H / 2 + 22); ctx.textAlign = "left";
            }
          }
          ctx.restore(); requestAnimationFrame(loop);
        }
        focarCanvas(); requestAnimationFrame(loop);
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
            st.iframe(html_jogo, height=655)
        else:
            import streamlit.components.v1 as components
            components.html(html_jogo, height=655, scrolling=False)

    # ==========================================================================
    # COLUNA DIREITA: TOP 5 OFICIAL (CONTAINER COM ESCOPO .st-key-ranking_panel)
    # ==========================================================================
    with col_ranking:
        with st.container(key="ranking_panel"):
            r_top1, r_top2 = st.columns([1.6, 1])
            with r_top1:
                st.markdown(
                    "<h3 style='font-family:\"Chakra Petch\",sans-serif; margin:0; color:#fde047;'>🏆 TOP 5 OFICIAL</h3>",
                    unsafe_allow_html=True,
                )
            with r_top2:
                if st.button("🔄 Atualizar", key="btn_refresh_rank", use_container_width=True):
                    st.rerun()

            if "flash_podio" in st.session_state:
                ok_flash, msg_flash = st.session_state.pop("flash_podio")
                if ok_flash:
                    st.success(msg_flash)
                else:
                    st.error(msg_flash)

            dados_gh, _, erro_gh = ler_ranking_github()
            if dados_gh is not None:
                st.caption("🔒 Placar verificado no servidor • Sem duplicados.")
            else:
                st.warning(f"⚠️ Modo offline: {erro_gh}")

            ranking_atual = dados_gh if dados_gh is not None else []
            nomes_modos = {"campanha": "Campanha", "infinito": "Infinito", "tempo": "60s"}

            if not ranking_atual:
                st.info("Nenhuma partida finalizada ainda. Jogue para inaugurar o Top 5!")
            else:
                medalhas = ["🥇", "🥈", "🥉"]
                cards_html = []
                for idx, item in enumerate(ranking_atual[:5]):
                    pos = medalhas[idx] if idx < 3 else f"#{idx + 1}"
                    fase_item = item.get("fase", 1)
                    modo_item = nomes_modos.get(item.get("modo", "campanha"), "Campanha")
                    tier_cls = f"podium-{idx + 1}" if idx < 3 else ""
                    cards_html.append(
                        f"""
                        <div class="podium-row {tier_cls}">
                            <div>
                                <div style="font-weight:700; font-size:0.96rem; color:#f8fafc;">{pos} {item['nome']}</div>
                                <div style="font-size:0.78rem; color:#86efac;">{modo_item} · Fase {fase_item}/5 • {item['data']}</div>
                            </div>
                            <span class="podium-pts">{item['pontos']} pts</span>
                        </div>
                        """
                    )
                st.html("".join(cards_html))


# ==============================================================================
# ABA 2: ENCICLOPÉDIA "APRENDA JOGANDO"
# ==============================================================================
with aba_guia:
    st.markdown(
        "<h3 style='font-family:\"Chakra Petch\",sans-serif; color:#86efac;'>📚 Guia Oficial da Coleta Seletiva & Mecânicas Especiais</h3>",
        unsafe_allow_html=True,
    )
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
        st.html(
            """
            <div class="wiki-card">
                <h4>⚠️ 2. Pegadinhas e Armadilhas</h4>
                <ul style="padding-left:18px; line-height:1.6; color:#dcfce7; font-size:0.92rem;">
                    <li><b>🍕 Caixa de Pizza Engordurada:</b> A gordura contamina a reciclagem do papel. Jogue na lixeira <b>Marrom (Orgânico)</b> para ganhar <b>+2 pts</b>.</li>
                    <li><b>🔋 Pilha Tóxica (Perigo!):</b> Metais pesados contaminam o solo. <b>Desvie dela!</b> Tira <b>2 vidas</b> (ou 5s) e congela sua lixeira por 2s.</li>
                    <li><b>🛍️ Saco de Reciclagem:</b> Ao coletar, lança <b>3 itens</b> do mesmo material no topo da tela.</li>
                </ul>
            </div>
            """
        )
    with c_pwr:
        st.html(
            """
            <div class="wiki-card">
                <h4>⚡ 3. Power-Ups Coletáveis</h4>
                <ul style="padding-left:18px; line-height:1.6; color:#dcfce7; font-size:0.92rem;">
                    <li><b>🧲 Ímã Seletivo (5s):</b> Atrai automaticamente os lixos da cor selecionada.</li>
                    <li><b>⏳ Eco-Freeze (6s):</b> Reduz a velocidade de queda pela metade.</li>
                    <li><b>🛡️ Escudo Ambiental:</b> Absorve o próximo erro ou pilha tóxica sem perder vida.</li>
                    <li><b>✨ Coringa:</b> Converte todos os lixos da tela para a cor da lixeira atual.</li>
                    <li><b>❤️ Kit de Restauração:</b> Recupera +1 vida (aparece quando você tem ≤ 2 vidas).</li>
                </ul>
            </div>
            """
        )
