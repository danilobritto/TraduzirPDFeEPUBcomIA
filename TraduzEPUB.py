import os
from ebooklib import epub
from bs4 import BeautifulSoup
from openai import OpenAI

client = OpenAI(
  api_key="CHAVE-API-AQUI"
)

def dividir_em_chunks(texto, max_chars=1500, limite_chunks=None):
    """
    Divide o texto em chunks respeitando parágrafos.
    Junta parágrafos até chegar perto do limite, 
    mas nunca quebra no meio do parágrafo.
    """
    
    paragrafos = texto.split("\n")
    chunks = []
    atual = ""

    for p in paragrafos:
        p = p.strip()
        if not p:
            continue

        if len(atual) + len(p) + 1 <= max_chars:
            atual += (p + "\n")
        else:
            if atual:
                chunks.append(atual.strip())
            # se o parágrafo for maior que max_chars, vai sozinho
            if len(p) > max_chars:
                chunks.append(p)
                atual = ""
            else:
                atual = p + "\n"

        if limite_chunks and len(chunks) >= limite_chunks:
            return chunks

    if atual:
        chunks.append(atual.strip())

    return chunks


def traduzir_chunk(texto, modelo="gpt-4o-mini"):
    """Envia chunk para API da OpenAI e retorna tradução."""
    resposta = client.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": "Você é um tradutor de inglês para português de documentos de tecnologia. Preserve quebras de parágrafo para leitura em e-readers. Não retorne nenhum texto além do traduzido, caso não consiga traduzir retorne o texto original."},
            {"role": "user", "content": f"Traduza o seguinte texto para português:\n\n{texto}"}
        ]
    )
    print("Chunk traduzido.")
    return resposta.choices[0].message.content.strip()

def traduzir_epub(caminho_entrada, caminho_saida, max_chars=1500):
    book = epub.read_epub(caminho_entrada)
    capitulos_traduzidos = {}
    outros_itens = []
    print(f"Traduzindo EPUB: {caminho_entrada}")

    # Traduz e armazena capítulos por id
    for item in book.items:
        if isinstance(item, epub.EpubHtml):
            print(f"Traduzindo capítulo: {item.get_name()}")
            soup = BeautifulSoup(item.content, "html.parser")
            textos = soup.find_all(text=True)
            textos_traduzidos = []
            for txt in textos:
                if txt.strip():
                    chunks = dividir_em_chunks(txt, max_chars, limite_chunks=5)
                    traducao = " ".join([traduzir_chunk(c) for c in chunks])
                    textos_traduzidos.append(traducao)
                else:
                    textos_traduzidos.append(txt)
            for original, traduzido in zip(textos, textos_traduzidos):
                original.replace_with(traduzido)
            item.content = str(soup).encode("utf-8")
            capitulos_traduzidos[item.get_id()] = item
        else:
            outros_itens.append(item)

    # Criar novo livro traduzido
    print("Criando novo livro EPUB...")
    novo_book = epub.EpubBook()
    novo_book.set_identifier("traduzido-" + (book.get_metadata("DC", "identifier")[0][0] if book.get_metadata("DC", "identifier") else "sem-id"))
    novo_book.set_title((book.get_metadata("DC", "title")[0][0] if book.get_metadata("DC", "title") else "Livro") + " (Traduzido)")
    novo_book.set_language("pt")

    for autor in book.get_metadata("DC", "creator"):
        novo_book.add_author(autor[0])

    # Adiciona capítulos traduzidos na ordem do spine original
    spine_objs = []
    for spine_item in book.spine:
        if isinstance(spine_item, tuple):
            spine_item = spine_item[0]
        if spine_item == 'nav':
            continue
        cap = capitulos_traduzidos.get(spine_item)
        if cap:
            novo_book.add_item(cap)
            spine_objs.append(cap)

    # Adiciona nav
    nav_item = None
    for item in outros_itens[:]:
        if item.get_name().endswith('nav.xhtml'):
            nav_item = item
            outros_itens.remove(item)
            break
    if nav_item:
        novo_book.add_item(nav_item)
        nav_obj = nav_item
    else:
        nav_obj = epub.EpubNav()
        novo_book.add_item(nav_obj)

    # Spine e TOC
    novo_book.spine = [nav_obj] + spine_objs
    novo_book.toc = tuple(spine_objs)

    # Adiciona imagens, CSS e outros recursos
    for item in outros_itens:
        novo_book.add_item(item)

    epub.write_epub(caminho_saida, novo_book)
    print(f"EPUB traduzido salvo em: {caminho_saida}")


if __name__ == "__main__":
    entrada = "Accelerate.epub"   # coloque o caminho do seu epub
    saida = "saida_traduzido.epub"
    traduzir_epub(entrada, saida)
