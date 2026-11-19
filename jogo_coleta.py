import io
import os
import random
import fitz  # PyMuPDF
import pygame

# Inicialização
pygame.init()
pygame.mixer.init()

LARGURA, ALTURA = 480, 360
tela = pygame.display.set_mode((LARGURA, ALTURA))
pygame.display.set_caption("Coleta Seletiva")
relogio = pygame.time.Clock()
fonte_hud = pygame.font.SysFont("arial", 18, bold=True)

PASTA_ASSETS = os.path.dirname(os.path.abspath(__file__))

def carregar_imagem(nome_arquivo, escala_divisor=1, zoom_svg=1.0):
    caminho = os.path.join(PASTA_ASSETS, nome_arquivo)
    ext = os.path.splitext(nome_arquivo)[1].lower()

    if ext == ".svg":
        doc = fitz.open(caminho)
        pagina = doc.load_page(0)
        matriz = fitz.Matrix(zoom_svg, zoom_svg)
        pix = pagina.get_pixmap(matrix=matriz, alpha=True)
        dados_png = pix.tobytes("png")
        doc.close()
        img = pygame.image.load(io.BytesIO(dados_png)).convert_alpha()
    else:
        img = pygame.image.load(caminho).convert_alpha()

    if escala_divisor != 1:
        w, h = img.get_size()
        img = pygame.transform.smoothscale(img, (int(w / escala_divisor), int(h / escala_divisor)))
    return img

def carregar_som(nome_arquivo):
    caminho = os.path.join(PASTA_ASSETS, nome_arquivo)
    return pygame.mixer.Sound(caminho)

def scratch_para_pygame(x, y, largura_img, altura_img, rot_center=None):
    """Converte coordenadas do Scratch (centro = 0,0) para Pygame (topo-esquerdo = 0,0)."""
    if rot_center is not None:
        px = (LARGURA / 2) + x - rot_center[0]
        py = (ALTURA / 2) - y - rot_center[1]
    else:
        px = (LARGURA / 2) + x - (largura_img / 2)
        py = (ALTURA / 2) - y - (altura_img / 2)
    return px, py

# --- Carregamento de Cenários (Stage Costumes) ---
cenarios = {
    "instrucoes": carregar_imagem("49c8433626dd2759e7cea2697335b886.svg"),
    "jogo": carregar_imagem("693507866d39d7257377845b34fa7426.png", escala_divisor=2),
    "fim": carregar_imagem("1c3010490bfc4f7d96f7f1756c21f9de.svg"),
    "vitoria": carregar_imagem("7e15832ed1b37bd73d3418030b27bc8e.svg"),
}

# --- Carregamento de Sons ---
sons = {
    "fim": carregar_som("e3635ab50a93193e53cd16f047446add.wav"),
    "vitoria": carregar_som("b8251bb11c300af3582aba1239082d41.wav"),
    "acerto": carregar_som("cfc50a412483f6aadb83adeff596052e.wav"),
    "erro": carregar_som("768bd6a764ab62a6a6764e4147c3e615.wav"),
}

# --- Fantasias dos Atores ---
fantasias_lixeira = [
    carregar_imagem("e0abe584a75ba6c8c5dbff995d9be90a.svg"),  # 1: papel
    carregar_imagem("4bfcb0e25246a5ac747ae14778b9e751.svg"),  # 2: plastico
    carregar_imagem("d610b30c19b7e082ed98d0597592531b.svg"),  # 3: vidro
    carregar_imagem("d388958fbb03f3ac73d464126f2b11f8.svg"),  # 4: metal
    carregar_imagem("506b5e3fb9f22601584dd04468c217c7.svg"),  # 5: organico
]

fantasias_lixo = [
    carregar_imagem("750b6d248d55e43f035febc2ee61b693.svg"),  # lixo1 (papel)
    carregar_imagem("b2946c689f98c56cc2ada16de60018b6.svg"),  # lixo2 (plastico)
    carregar_imagem("b5ac32ca01d749ce3b57e19b1ebcf8b0.svg"),  # lixo3 (vidro)
    carregar_imagem("9e6a1febff68f2f7427c406b27a378c8.svg"),  # lixo4 (metal)
    carregar_imagem("d08c060f34f414e5d4274a1fe74c57c3.svg"),  # lixo5 (organico)
    carregar_imagem("a380e70730f191243ddb989d1be972ea.svg"),  # lixo6 (papel)
    carregar_imagem("c4f8588495bad0fb9cf808597db39fc3.svg"),  # lixo7 (plastico)
    carregar_imagem("e78af7aec183657375aff54ad57fefa9.svg"),  # lixo8 (vidro)
    carregar_imagem("80a6400b5fd9929c929a52b0aba67957.svg"),  # lixo9 (metal)
    carregar_imagem("b8b976c0e35ef9fe7d816751c09aabc5.svg"),  # lixo10 (organico)
]

fantasias_dica = [
    carregar_imagem("943525abb609ad165c88c55dd37bc555.svg"),  # dica1 (papel)
    carregar_imagem("561f2c58021e4ec10b58f009ef391431.svg"),  # dica2 (plastico)
    carregar_imagem("77c71fc36e7f8d5e6f9b239f1aa6ef0a.svg"),  # dica3 (vidro)
    carregar_imagem("7f683ab17ac6b7aac94b7af86074fbaa.svg"),  # dica4 (metal)
    carregar_imagem("a7b7b55ac7696e64f8dfcd5102922329.svg"),  # dica5 (organico)
]

img_botao_iniciar = carregar_imagem("83289741ad14f2292187479156d68b15.svg")

# --- Variáveis Globais do Jogo ---
estado = "instrucoes"  # "instrucoes", "jogo", "fim", "vitoria"
pontos = 0
vidas = 5
velocidade = 3.0
ultimo_tipo = 1

tempo_ultimo_aumento_vel = 0
tempo_proximo_spawn = 0
tempo_fim_dica = 0
tempo_encerramento = 0

lixeira_x = 0
lixeira_y = -135
lixeira_fantasia = 1
lixeira_visivel = False

dica_visivel = False
dica_fantasia = 1

clones_lixo = []

def iniciar_partida():
    global estado, pontos, vidas, velocidade, ultimo_tipo
    global lixeira_x, lixeira_y, lixeira_fantasia, lixeira_visivel
    global dica_visivel, clones_lixo, tempo_ultimo_aumento_vel, tempo_proximo_spawn

    agora = pygame.time.get_ticks()
    estado = "jogo"
    pontos = 0
    vidas = 5
    velocidade = 3.0
    ultimo_tipo = 1

    lixeira_x = 0
    lixeira_y = -135
    lixeira_fantasia = 1
    lixeira_visivel = True

    dica_visivel = False
    clones_lixo.clear()

    tempo_ultimo_aumento_vel = agora
    tempo_proximo_spawn = agora + 1000 + int(random.uniform(1.1, 2.0) * 1000)

def disparar_erro(tipo_errado):
    global vidas, ultimo_tipo, dica_visivel, dica_fantasia, tempo_fim_dica
    if vidas > 0:
        vidas -= 1
        ultimo_tipo = tipo_errado
    sons["erro"].play()
    dica_fantasia = ultimo_tipo
    dica_visivel = True
    tempo_fim_dica = pygame.time.get_ticks() + 2600

# --- Loop Principal (30 FPS) ---
rodando = True
while rodando:
    agora = pygame.time.get_ticks()

    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False

        elif evento.type == pygame.KEYDOWN:
            if estado == "instrucoes" and evento.key == pygame.K_SPACE:
                iniciar_partida()

            elif estado == "jogo":
                if evento.key == pygame.K_1:
                    lixeira_fantasia = 1
                elif evento.key == pygame.K_2:
                    lixeira_fantasia = 2
                elif evento.key == pygame.K_3:
                    lixeira_fantasia = 3
                elif evento.key == pygame.K_4:
                    lixeira_fantasia = 4
                elif evento.key == pygame.K_5:
                    lixeira_fantasia = 5

    if estado == "jogo":
        if agora - tempo_ultimo_aumento_vel >= 6000:
            velocidade += 0.4
            tempo_ultimo_aumento_vel = agora

        teclas = pygame.key.get_pressed()
        if teclas[pygame.K_LEFT] or teclas[pygame.K_a]:
            lixeira_x -= 14
        if teclas[pygame.K_RIGHT] or teclas[pygame.K_d]:
            lixeira_x += 14

        if lixeira_x > 205:
            lixeira_x = 205
        if lixeira_x < -205:
            lixeira_x = -205

        if agora >= tempo_proximo_spawn:
            item_sorteado = random.randint(1, 10)
            tipo_calculado = ((item_sorteado - 1) % 5) + 1
            clones_lixo.append({
                "x": random.randint(-200, 200),
                "y": 175.0,
                "item": item_sorteado,
                "tipo": tipo_calculado,
            })
            tempo_proximo_spawn = agora + int(random.uniform(1.1, 2.0) * 1000)

        img_lix_atual = fantasias_lixeira[lixeira_fantasia - 1]
        lx_pg, ly_pg = scratch_para_pygame(
            lixeira_x, lixeira_y, img_lix_atual.get_width(), img_lix_atual.get_height(), (40, 42)
        )
        rect_lixeira = pygame.Rect(lx_pg, ly_pg, img_lix_atual.get_width(), img_lix_atual.get_height())

        novos_clones = []
        for clone in clones_lixo:
            clone["y"] -= velocidade
            img_item = fantasias_lixo[clone["item"] - 1]
            ix_pg, iy_pg = scratch_para_pygame(
                clone["x"], clone["y"], img_item.get_width(), img_item.get_height()
            )
            rect_item = pygame.Rect(ix_pg, iy_pg, img_item.get_width(), img_item.get_height())

            if rect_item.colliderect(rect_lixeira):
                if lixeira_fantasia == clone["tipo"]:
                    pontos += 1
                    sons["acerto"].play()
                else:
                    disparar_erro(clone["tipo"])
                continue

            if clone["y"] < -170:
                vidas -= 1
                sons["erro"].play()
                continue

            novos_clones.append(clone)

        clones_lixo = novos_clones

        if dica_visivel and agora >= tempo_fim_dica:
            dica_visivel = False

        if vidas < 1:
            estado = "fim"
            lixeira_visivel = False
            dica_visivel = False
            clones_lixo.clear()
            sons["fim"].play()
            tempo_encerramento = agora + 2500
        elif pontos > 19:
            estado = "vitoria"
            lixeira_visivel = False
            dica_visivel = False
            clones_lixo.clear()
            sons["vitoria"].play()
            tempo_encerramento = agora + 2500

    elif estado in ("fim", "vitoria"):
        if agora >= tempo_encerramento:
            rodando = False

    # --- Renderização ---
    tela.blit(cenarios[estado], (0, 0))

    if estado == "instrucoes":
        escala = 1.1 if (agora // 300) % 2 == 1 else 1.0
        w_btn = int(img_botao_iniciar.get_width() * escala)
        h_btn = int(img_botao_iniciar.get_height() * escala)
        btn_escalado = pygame.transform.smoothscale(img_botao_iniciar, (w_btn, h_btn))
        bx, by = scratch_para_pygame(36, 28, w_btn, h_btn, (147.5 * escala, -121.4 * escala))
        tela.blit(btn_escalado, (bx, by))

    elif estado == "jogo":
        if lixeira_visivel:
            img_l = fantasias_lixeira[lixeira_fantasia - 1]
            px, py = scratch_para_pygame(lixeira_x, lixeira_y, img_l.get_width(), img_l.get_height(), (40, 42))
            tela.blit(img_l, (px, py))

        for clone in clones_lixo:
            img_c = fantasias_lixo[clone["item"] - 1]
            px, py = scratch_para_pygame(clone["x"], clone["y"], img_c.get_width(), img_c.get_height())
            tela.blit(img_c, (px, py))

        if dica_visivel:
            img_d = fantasias_dica[dica_fantasia - 1]
            px, py = scratch_para_pygame(0, 95, img_d.get_width(), img_d.get_height(), (220, 30))
            tela.blit(img_d, (px, py))

        txt_pontos = fonte_hud.render(f"Pontos: {pontos}", True, (255, 255, 255))
        txt_vidas = fonte_hud.render(f"Vidas: {vidas}", True, (255, 255, 255))
        pygame.draw.rect(tela, (30, 30, 30), (5, 5, 110, 24), border_radius=5)
        pygame.draw.rect(tela, (30, 30, 30), (5, 32, 110, 24), border_radius=5)
        tela.blit(txt_pontos, (12, 7))
        tela.blit(txt_vidas, (12, 34))

    pygame.display.flip()
    relogio.tick(30)

pygame.quit()
