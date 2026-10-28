**Versão de teste.** A execução de programas foi testada em simulação, mas ainda precisa de testes em aparelho real.

Feita automaticamente pelo GitHub a partir do código deste repositório.

## Instalar

1. Baixe o `PyCode-v2.apk` abaixo, em **Assets**.
2. Abra o arquivo e permita "instalar apps desconhecidos" para o app de onde abriu.
3. O aviso do Play Protect é normal: o app não está na Play Store.
4. Na primeira abertura, o PyCode pede **Acesso a todos os arquivos** para guardar os projetos em `Documents/PyCode`.

**Atualizar:** a partir desta versão, o APK novo instala por cima do antigo, sem desinstalar. Se você tem o APK da primeira versão de teste, desinstale-o uma única vez (ele foi assinado com outra chave). Seus projetos em `Documents/PyCode` não são apagados.

A chave de assinatura é a **chave de teste do Android, pública** (está no repositório). Serve só para testes: não use este APK como se fosse uma versão oficial assinada.

## Nesta versão

- Funciona: editor, abas, projetos, erros enquanto digita, importar e exportar `.zip`, sem internet.
- **Pasta dos projetos à sua escolha:** Configurações → *Pasta dos projetos* → *Mudar…*. Os projetos ficam em `<pasta escolhida>/projetos`. Você pode copiar os atuais para lá; nada é apagado da pasta antiga. Exige "Acesso a todos os arquivos".
- **Executar (▶):** roda o arquivo aberto como um programa separado, com `print`, `input()` (pela caixa embaixo do terminal), erros com a linha certa e o botão ■ que realmente encerra o programa.
- **`tkinter`:** as janelas aparecem dentro do PyCode. Funcionam `Label`, `Button`, `Entry`, `Text`, `Canvas`, `Frame`, `Listbox`, `grid`, `pack`, `place`, `bind` e `after`. Faltam `Checkbutton`, `Radiobutton`, `Scale`, `Menu` e imagens.
- **Limites:** sem `pip`. Se você sair do app, o Android pode encerrar o programa depois de alguns minutos.

Requer Android 7.0 ou mais novo, arquitetura arm64.
