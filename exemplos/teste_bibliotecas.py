"""Teste das bibliotecas do APK "PyCode v2 Bib": NumPy, Pandas, Matplotlib e Pillow.

Rode no app. Mostra ✓ ou ✗ para cada biblioteca e abre uma janela com um gráfico feito
pelo Matplotlib. No PyCode normal (sem as bibliotecas), ele avisa que elas não estão instaladas.
"""
import importlib
import os
import tempfile

import tkinter as tk  # esta linha liga a ponte de janelas do PyCode

# O Matplotlib precisa de uma pasta para guardar o cache dele.
os.environ.setdefault("MPLCONFIGDIR", tempfile.gettempdir())

ESPERADAS = {"numpy": "1.26.2", "pandas": "2.1.3", "matplotlib": "3.8.4", "PIL": "11.0.0"}
RESULTADOS = {}


def nota(modulo_nome, versao):
    """Avisa se a versão é diferente da que este APK deveria ter."""
    esperada = ESPERADAS[modulo_nome]
    return "" if versao == esperada else f" (esperada {esperada})"


def verificar(nome, funcao):
    try:
        detalhe = funcao()
        RESULTADOS[nome] = (True, detalhe)
        print(f"✓ {nome}: {detalhe}")
    except ModuleNotFoundError as erro:
        RESULTADOS[nome] = (False, "não instalada neste app")
        print(f"✗ {nome}: não instalada neste app (falta {erro.name})")
    except Exception as erro:
        RESULTADOS[nome] = (False, f"{type(erro).__name__}: {erro}")
        print(f"✗ {nome}: {type(erro).__name__}: {str(erro)[:100]}")


def teste_numpy():
    import numpy as np
    a = np.array([[2.0, 1.0], [1.0, 3.0]])
    x = np.linalg.solve(a, np.array([3.0, 5.0]))
    assert np.allclose(a @ x, [3.0, 5.0])
    assert abs(np.fft.fft(np.ones(8))[0].real - 8) < 1e-9
    media = float(np.arange(10).mean())
    return f"versão {np.__version__}{nota('numpy', np.__version__)}; solve = {x.round(3).tolist()}; média 0..9 = {media}"


def teste_pandas():
    import pandas as pd
    df = pd.DataFrame({"turma": ["A", "A", "B", "B"], "nota": [7.0, 9.0, 6.0, 8.0]})
    medias = df.groupby("turma")["nota"].mean()
    assert medias["A"] == 8.0 and medias["B"] == 7.0
    datas = pd.to_datetime(["2026-11-06", "2026-11-07"])
    assert (datas[1] - datas[0]).days == 1
    assert df.to_csv(index=False).splitlines()[0] == "turma,nota"
    return f"versão {pd.__version__}{nota('pandas', pd.__version__)}; médias {medias.to_dict()}"


def teste_matplotlib():
    import matplotlib
    matplotlib.use("Agg")  # sem janela: o Android não tem Tk
    import matplotlib.pyplot as plt
    import numpy as np
    x = np.linspace(0, 2 * np.pi, 200)
    figura, eixo = plt.subplots(figsize=(4, 3), dpi=80)
    eixo.plot(x, np.sin(x), label="seno")
    eixo.plot(x, np.cos(x), label="cosseno")
    eixo.legend()
    eixo.set_title("Matplotlib no PyCode")
    figura.savefig("grafico_teste.png")
    plt.close(figura)
    with open("grafico_teste.png", "rb") as arquivo:
        assert arquivo.read(8) == b"\x89PNG\r\n\x1a\n"
    tamanho = os.path.getsize("grafico_teste.png")
    assert tamanho > 1000
    return f"versão {matplotlib.__version__}{nota('matplotlib', matplotlib.__version__)}; grafico_teste.png com {tamanho} bytes"


def teste_pillow():
    import numpy as np
    import PIL
    from PIL import Image, ImageDraw, ImageFilter
    gradiente = np.tile(np.linspace(0, 255, 64, dtype=np.uint8), (64, 1))
    imagem = Image.fromarray(gradiente).convert("RGB")
    ImageDraw.Draw(imagem).rectangle((8, 8, 40, 40), outline=(255, 0, 0), width=3)
    imagem = imagem.filter(ImageFilter.GaussianBlur(1))
    imagem.save("pillow_teste.png")
    reaberta = Image.open("pillow_teste.png")
    assert reaberta.size == (64, 64)
    return f"versão {PIL.__version__}{nota('PIL', PIL.__version__)}; imagem {reaberta.size} {reaberta.mode}"


print("Testando as bibliotecas...\n")
verificar("numpy", teste_numpy)
verificar("pandas", teste_pandas)
verificar("matplotlib", teste_matplotlib)
verificar("pillow", teste_pillow)

funcionando = sum(1 for aprovado, _ in RESULTADOS.values() if aprovado)
print(f"\n{funcionando} de {len(RESULTADOS)} bibliotecas funcionando.")
if funcionando == 0:
    print("Este app não tem as bibliotecas. Instale o APK PYcodeteste-bibliotecas (PyCode v2 Bib).")
else:
    janela = tk.Tk()
    janela.title("Teste das bibliotecas")
    resumo = "\n".join(("✓ " if aprovado else "✗ ") + nome for nome, (aprovado, _) in RESULTADOS.items())
    tk.Label(janela, text=resumo, justify="left", font=("Arial", 12)).pack(padx=12, pady=8)
    if RESULTADOS["matplotlib"][0]:
        grafico = tk.PhotoImage(file="grafico_teste.png")
        tk.Label(janela, image=grafico).pack(padx=8, pady=4)
    tk.Button(janela, text="Fechar", command=janela.destroy).pack(pady=8)
    janela.mainloop()

print("programa encerrado")
