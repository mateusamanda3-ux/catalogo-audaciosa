import re
import sys
import urllib.request

FONTE = "https://audaciosamultimarcas.webloja.app/xml"
SAIDA = "feed.xml"
RELATORIO = "relatorio.txt"

# Categorias que NUNCA entram no catalogo (comparacao sem acento e sem maiusculas)
CATEGORIAS_FORA = ["intimidades"]
# Palavras no nome que tiram o produto do catalogo (opcional, comece vazio)
PALAVRAS_FORA = []


def limpar(t):
    t = t.lower()
    for a, b in (("á", "a"), ("ã", "a"), ("â", "a"), ("é", "e"), ("ê", "e"),
                 ("í", "i"), ("ó", "o"), ("õ", "o"), ("ô", "o"), ("ú", "u"), ("ç", "c")):
        t = t.replace(a, b)
    return t


def campo(item, nome):
    m = re.search(r"<g:%s>(.*?)</g:%s>" % (nome, nome), item, re.S)
    if not m:
        return ""
    v = m.group(1).strip()
    v = re.sub(r"^<!\[CDATA\[(.*)\]\]>$", r"\1", v, flags=re.S)
    return v.strip()


def baixar():
    req = urllib.request.Request(FONTE, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8")


def main():
    xml = sys.argv[1] and open(sys.argv[1], encoding="utf-8").read() if len(sys.argv) > 1 else baixar()
    if "</rss>" not in xml:
        sys.exit("ERRO: o XML da loja veio cortado. Nada foi alterado.")

    inicio = xml.find("<item>")
    if inicio < 0:
        sys.exit("ERRO: nenhum produto encontrado. Nada foi alterado.")
    cabecalho = xml[:inicio].replace("https://https://", "https://")
    itens = re.findall(r"<item>.*?</item>", xml, re.S)

    mantidos, fora = [], {}
    cats_mantidas = {}
    for it in itens:
        cat = campo(it, "google_product_category")
        titulo = campo(it, "title")
        status = campo(it, "status")
        motivo = None
        if status and status != "active":
            motivo = "arquivado"
        elif any(c in limpar(cat) for c in CATEGORIAS_FORA):
            motivo = "categoria intima"
        elif any(p in limpar(titulo) for p in PALAVRAS_FORA):
            motivo = "palavra bloqueada"
        if motivo:
            fora.setdefault(motivo, []).append(titulo)
        else:
            mantidos.append(it)
            cats_mantidas[cat] = cats_mantidas.get(cat, 0) + 1

    if len(mantidos) < 20:
        sys.exit("ERRO: restaram poucos produtos (%d). Nada foi alterado." % len(mantidos))

    saida = cabecalho + "\n".join(mantidos) + "\n</channel>\n</rss>\n"
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(saida)

    with open(RELATORIO, "w", encoding="utf-8") as f:
        f.write("Produtos na loja: %d\n" % len(itens))
        f.write("Produtos no catalogo: %d\n\n" % len(mantidos))
        f.write("Categorias que ficaram:\n")
        for c, n in sorted(cats_mantidas.items()):
            f.write("  %s: %d\n" % (c, n))
        f.write("\nRemovidos:\n")
        for m, lst in fora.items():
            f.write("  %s: %d\n" % (m, len(lst)))
            for t in lst:
                f.write("    - %s\n" % t)
    print(open(RELATORIO, encoding="utf-8").read())


main()
