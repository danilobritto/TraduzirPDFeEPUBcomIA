import pdfplumber
from fpdf import FPDF
from ebooklib import epub
from openai import OpenAI
from pdf2image import convert_from_path
from PIL import Image
import os

client = OpenAI(
  api_key="CHAEVE-API-AQUI"
)

# -------------------
# Função calculo de custo
# -------------------
def simular_custo(blocos: list[str], preco_por_1k_tokens=0.00075):
    total_tokens = 0
    for b in blocos:
        # aproximação: 1 token ≈ 4 caracteres
        total_tokens += len(b) / 4  

    custo = (total_tokens / 1000) * preco_por_1k_tokens
    print(f"🔎 Estimativa de tokens: {int(total_tokens)}")
    print(f"💰 Custo estimado: ${custo:.4f} USD")


# -------------------
# Função de tradução
# -------------------
def traduzir_texto(texto: str) -> str:
    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Você é um tradutor de inglês para português de documentos de tecnologia. Preserve quebras de parágrafo para leitura em e-readers."},
            {"role": "user", "content": f"Traduza o seguinte texto para português:\n\n{texto}"}
        ]
    )
    return resposta.choices[0].message.content.strip()

# -------------------
# Extração do PDF
# -------------------
def extrair_paragrafos(caminho_pdf: str) -> list[str]:
    paragrafos = []
    with pdfplumber.open(caminho_pdf) as pdf:
        total_paginas = len(pdf.pages)

        opcao = input("Quer processar o PDF inteiro (I) ou só as 10 primeiras páginas (T de teste)? [I/T]: ").strip().upper()

        if opcao == "T":
            paginas = pdf.pages[:10]
            print("⚡ Modo teste ativado: apenas as 10 primeiras páginas serão processadas.")
        else:
            paginas = pdf.pages
            print(f"📄 Modo completo: {total_paginas} páginas serão processadas.")

        for pagina in paginas:
            texto = pagina.extract_text()
            if texto:
                for p in texto.split("\n\n"):
                    if p.strip():
                        paragrafos.append(p.strip())
    return paragrafos

def extrair_chunks(caminho_pdf: str, tamanho_max: int = 1500) -> list[str]:
    chunks = []
    texto_total = []
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if texto:
                texto_total.append(texto)

    texto_unico = "\n".join(texto_total)
    palavras = texto_unico.split()

    chunk = []
    count = 0
    for palavra in palavras:
        chunk.append(palavra)
        count += len(palavra) + 1
        if count >= tamanho_max:
            chunks.append(" ".join(chunk))
            chunk = []
            count = 0

    if chunk:
        chunks.append(" ".join(chunk))

    return chunks

# -------------------
# Geração PDF
# -------------------
def gerar_pdf(paragrafos: list[str], caminho_saida: str):
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Adiciona a fonte UTF-8
    # Tente primeiro DejaVuSans
    pdf.add_font("DejaVu", "", "/System/Library/Fonts/Supplemental/DejaVuSans.ttf", uni=True)
    pdf.set_font("DejaVu", size=12)

    # Adiciona a fonte TrueType com suporte a UTF-8
    pdf.add_font("DejaVu", "", "/System/Library/Fonts/Supplemental/DejaVuSans.ttf", uni=True)

    for p in paragrafos:
        pdf.multi_cell(0, 8, p, align="J")
        pdf.ln(4)

    pdf.output(caminho_saida)

# -------------------
# Geração EPUB com capa
# -------------------
def gerar_epub(paragrafos: list[str], caminho_saida: str, caminho_pdf: str, titulo="Tradução", autor="IA Translator"):
    book = epub.EpubBook()
    book.set_identifier("id123456")
    book.set_title(titulo)
    book.set_language("pt")
    book.add_author(autor)

    # Converte a primeira página do PDF em imagem
    print("Gerando capa a partir da primeira página do PDF...")
    paginas = convert_from_path(caminho_pdf, first_page=1, last_page=1)
    capa_temp = "capa_temp.jpg"
    paginas[0].save(capa_temp, "JPEG")

    # Adiciona a capa ao EPUB
    with open(capa_temp, "rb") as img_file:
        book.set_cover("cover.jpg", img_file.read())

    # Cria capítulos (um por parágrafo ou chunk traduzido)
    chapters = []
    for i, p in enumerate(paragrafos):
        c = epub.EpubHtml(title=f"Capítulo {i+1}", file_name=f"chap_{i+1}.xhtml", lang="pt")
        texto = p.replace("\n", "<br/>")
        c.content = f"<p>{texto}</p>"
        book.add_item(c)
        chapters.append(c)

    # Define a ordem de leitura
    book.toc = tuple(chapters)
    book.spine = ["cover", "nav"] + chapters

    # Recursos obrigatórios
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Salva o arquivo EPUB
    epub.write_epub(caminho_saida, book, {})

    # Remove arquivo temporário
    if os.path.exists(capa_temp):
        os.remove(capa_temp)

# -----------------------
# Execução do programa
# -----------------------
if __name__ == "__main__":
    entrada = "Accelerate.pdf"

    print("Escolha o modo de processamento:")
    print("1 - Traduzir parágrafo por parágrafo")
    print("2 - Traduzir em chunks (recomendado para PDFs grandes)")
    print("3 - Simular custo sem traduzir")
    escolha = input("Digite 1, 2 ou 3: ").strip()

    if escolha == "1":
        print("Extraindo parágrafos...")
        blocos = extrair_paragrafos(entrada)
    elif escolha == "2":
        print("Extraindo chunks...")
        blocos = extrair_chunks(entrada)
    elif escolha == "3":
        print("Extraindo parágrafos para simulação...")
        blocos = extrair_paragrafos(entrada)
        simular_custo(blocos)
        exit()
    else:
        print("Opção inválida, saindo.")
        exit()

    print(f"Traduzindo {len(blocos)} blocos de texto...")
    traduzidos = [traduzir_texto(b) for b in blocos]

    print("Escolha o formato de saída:")
    print("1 - PDF")
    print("2 - EPUB (recomendado para Kindle)")
    print("3 - PDF e EPUB (gera ambos os formatos)")
    formato = input("Digite 1, 2 ou 3: ").strip()

    if formato == "1":
        saida = "arquivo_traduzido.pdf"
        gerar_pdf(traduzidos, saida)
    elif formato == "2":
        saida = "arquivo_traduzido.epub"
        gerar_epub(traduzidos, saida, entrada)
    elif formato == "3":
        saida_pdf = "arquivo_traduzido.pdf"
        saida_epub = "arquivo_traduzido.epub"
        gerar_pdf(traduzidos, saida_pdf)
        print(f"PDF salvo como {saida_pdf}")
        gerar_epub(traduzidos, saida_epub, entrada)
        print(f"EPUB salvo como {saida_epub}")
    else:
        print("Formato inválido, saindo.")
        exit()

    print(f"✅ Tradução concluída!")
    