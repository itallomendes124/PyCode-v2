package io.github.itallomendes124.pycode;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.util.Log;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.FileWriter;
import java.io.PrintWriter;
import java.io.StringWriter;

public class RunnerService extends Service {
    private static final String ETIQUETA = "pycode";

    @Override
    public IBinder onBind(Intent intencao) {
        return null;
    }

    @Override
    public int onStartCommand(Intent intencao, int flags, int idPedido) {
        if (intencao == null) {
            stopSelf();
            return START_NOT_STICKY;
        }
        final int porta = intencao.getIntExtra("porta", 0);
        final String token = intencao.getStringExtra("token");
        final String pasta = intencao.getStringExtra("pasta");
        final String arquivo = intencao.getStringExtra("arquivo");
        final String erro = intencao.getStringExtra("erro");
        Thread fio = new Thread(() -> {
            try {
                if (!Python.isStarted()) {
                    Python.start(new AndroidPlatform(this));
                }
                Python.getInstance().getModule("pycode_runner").callAttr("executar", porta, token, pasta, arquivo, erro);
            } catch (Throwable falha) {
                Log.e(ETIQUETA, "executor falhou", falha);
                registrar(erro, falha);
            } finally {
                stopSelf();
                android.os.Process.killProcess(android.os.Process.myPid());
            }
        }, "pycode-executor");
        fio.start();
        return START_NOT_STICKY;
    }

    private static void registrar(String caminho, Throwable falha) {
        if (caminho == null) {
            return;
        }
        try (FileWriter arquivo = new FileWriter(caminho, true)) {
            StringWriter texto = new StringWriter();
            falha.printStackTrace(new PrintWriter(texto));
            arquivo.write(texto.toString());
        } catch (Exception ignorada) {
            Log.e(ETIQUETA, "não consegui gravar o erro", ignorada);
        }
    }
}
