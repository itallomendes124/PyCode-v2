# PyCode v2 Bib: APK de teste com bibliotecas

Este APK é o PyCode v2 com **NumPy 1.26.2, Pandas 2.1.3, Matplotlib 3.8.4 e Pillow 11.0.0** (mais o `pyparsing` 3.1.4, que o Matplotlib usa).

- Ele instala **ao lado** do PyCode normal (outro identificador, `...pycode.bib`) e aparece como **PyCode v2 Bib**.
- É um APK de teste. O PyCode normal não muda.
- Para testar, rode `exemplos/teste_bibliotecas.py` dentro do app.
- Os dois apps compartilham a pasta `Documents/PyCode`, então veem os mesmos projetos.
- O Matplotlib não tem janela no Android. Use `matplotlib.use("Agg")` e grave o gráfico em PNG.
