package io.github.itallomendes124.pycode;

import android.content.Context;
import android.content.Intent;

public final class Lancador {
    static volatile Context contexto;

    private Lancador() {
    }

    public static void iniciar(int porta, String token, String pasta, String arquivo, String erro) {
        Context aplicacao = contexto;
        if (aplicacao == null) {
            throw new IllegalStateException("o app ainda não terminou de abrir");
        }
        Intent intencao = new Intent();
        intencao.setClassName(aplicacao.getPackageName(), RunnerService.class.getName());
        intencao.putExtra("porta", porta);
        intencao.putExtra("token", token);
        intencao.putExtra("pasta", pasta);
        intencao.putExtra("arquivo", arquivo);
        intencao.putExtra("erro", erro);
        aplicacao.startService(intencao);
    }
}
