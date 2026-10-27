package io.github.itallomendes124.pycode;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ContentValues;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.DocumentsContract;
import android.provider.MediaStore;
import android.provider.Settings;
import android.text.TextUtils;
import android.view.ViewGroup;
import android.view.WindowInsets;
import android.webkit.JavascriptInterface;
import android.webkit.URLUtil;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {
    private static final int PEDIDO_ARQUIVO = 10;
    private static final int PEDIDO_PERMISSAO = 11;
    private static final int PEDIDO_PASTA = 12;
    private static final int COR_FUNDO = Color.rgb(30, 30, 30);
    private static final String PAGINA = "<html><head><meta name='viewport' content='width=device-width'></head>"
            + "<body style='margin:0;height:100vh;display:flex;align-items:center;justify-content:center;"
            + "background:#1e1e1e;color:#cccccc;font:16px sans-serif;text-align:center;padding:24px;box-sizing:border-box'>"
            + "%s</body></html>";

    private static int porta = 0;

    private WebView tela;
    private ValueCallback<Uri[]> escolha;
    private boolean esperandoPermissao = false;
    private boolean iniciou = false;

    @Override
    protected void onCreate(Bundle estado) {
        super.onCreate(estado);
        FrameLayout raiz = new FrameLayout(this);
        raiz.setBackgroundColor(COR_FUNDO);
        tela = new WebView(this);
        tela.setBackgroundColor(COR_FUNDO);
        raiz.addView(tela, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        setContentView(raiz);
        if (Build.VERSION.SDK_INT >= 30) {
            getWindow().setDecorFitsSystemWindows(false);
            raiz.setOnApplyWindowInsetsListener((vista, margens) -> {
                android.graphics.Insets m = margens.getInsets(WindowInsets.Type.systemBars()
                        | WindowInsets.Type.ime() | WindowInsets.Type.displayCutout());
                vista.setPadding(m.left, m.top, m.right, m.bottom);
                return WindowInsets.CONSUMED;
            });
        }
        configurarTela();
        if (porta > 0) {
            abrirEditor();
        } else {
            mostrar("Iniciando o Python…");
            prepararArmazenamento();
        }
    }

    private void configurarTela() {
        WebSettings ajustes = tela.getSettings();
        ajustes.setJavaScriptEnabled(true);
        ajustes.setDomStorageEnabled(true);
        ajustes.setAllowFileAccess(false);
        ajustes.setAllowContentAccess(false);
        ajustes.setTextZoom(100);
        tela.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView vista, WebResourceRequest pedido) {
                Uri endereco = pedido.getUrl();
                if ("127.0.0.1".equals(endereco.getHost())) {
                    return false;
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, endereco));
                } catch (ActivityNotFoundException erro) {
                    avisar("Nenhum app abre este link.");
                }
                return true;
            }
        });
        tela.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView vista, ValueCallback<Uri[]> retorno,
                                             FileChooserParams parametros) {
                if (escolha != null) {
                    escolha.onReceiveValue(null);
                }
                escolha = retorno;
                try {
                    startActivityForResult(parametros.createIntent(), PEDIDO_ARQUIVO);
                    return true;
                } catch (ActivityNotFoundException erro) {
                    escolha = null;
                    avisar("Nenhum app para escolher arquivos.");
                    return false;
                }
            }
        });
        tela.setDownloadListener((endereco, agente, disposicao, tipo, tamanho) -> baixar(endereco, disposicao, tipo));
        tela.addJavascriptInterface(new PonteJs(), "AndroidPyCode");
    }

    private class PonteJs {
        @JavascriptInterface
        public void escolherPasta() {
            runOnUiThread(MainActivity.this::abrirSeletor);
        }
    }

    private boolean podeUsar(File pasta) {
        return (pasta.isDirectory() || pasta.mkdirs()) && pasta.canWrite();
    }

    private File caminhoDaArvore(Uri arvore) {
        if (!"com.android.externalstorage.documents".equals(arvore.getAuthority())) {
            return null;
        }
        String id = DocumentsContract.getTreeDocumentId(arvore);
        int separador = id.indexOf(':');
        if (separador < 0) {
            return null;
        }
        String volume = id.substring(0, separador);
        String relativo = id.substring(separador + 1);
        File raiz = "primary".equals(volume)
                ? Environment.getExternalStorageDirectory()
                : new File("/storage/" + volume);
        return relativo.isEmpty() ? raiz : new File(raiz, relativo);
    }

    private void abrirSeletor() {
        if (Build.VERSION.SDK_INT >= 30 && !Environment.isExternalStorageManager()) {
            new AlertDialog.Builder(this)
                    .setTitle("Falta uma permissão")
                    .setMessage("Para guardar os projetos numa pasta de sua escolha, o PyCode precisa de "
                            + "\"Acesso a todos os arquivos\". Depois de permitir, toque em Mudar de novo.")
                    .setPositiveButton("Permitir", (dialogo, botao) -> pedirAcessoTotal())
                    .setNegativeButton("Cancelar", null)
                    .show();
            return;
        }
        try {
            startActivityForResult(new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE), PEDIDO_PASTA);
        } catch (ActivityNotFoundException erro) {
            avisar("Nenhum app para escolher pastas.");
        }
    }

    private void confirmarTroca(File pasta) {
        if (!podeUsar(pasta)) {
            avisar("Não consegui escrever nessa pasta. Escolha outra.");
            return;
        }
        new AlertDialog.Builder(this)
                .setTitle("Mudar a pasta dos projetos")
                .setMessage("Os projetos ficarão em:\n" + new File(pasta, "projetos").getAbsolutePath()
                        + "\n\nCopiar os projetos atuais para lá? Nada é apagado da pasta antiga.")
                .setPositiveButton("Copiar e mudar", (dialogo, botao) -> trocar(pasta, true))
                .setNeutralButton("Só mudar", (dialogo, botao) -> trocar(pasta, false))
                .setNegativeButton("Cancelar", null)
                .show();
    }

    private void trocar(File pasta, boolean copiar) {
        new Thread(() -> {
            try {
                PyObject modulo = Python.getInstance().getModule("pycode_android");
                int copiados = modulo.callAttr("trocar_pasta", pasta.getAbsolutePath(), copiar).toInt();
                SharedPreferences.Editor editor = getSharedPreferences("pycode", MODE_PRIVATE).edit();
                editor.putString("pasta", pasta.getAbsolutePath());
                editor.apply();
                avisar(copiados > 0 ? "Pasta trocada. Projetos copiados: " + copiados : "Pasta trocada.");
                runOnUiThread(() -> tela.reload());
            } catch (Throwable erro) {
                avisar("Não consegui trocar a pasta: " + erro.getMessage());
            }
        }).start();
    }

    private void mostrar(String texto) {
        tela.loadDataWithBaseURL(null, String.format(PAGINA, texto), "text/html", "utf-8", null);
    }

    private void abrirEditor() {
        tela.loadUrl("http://127.0.0.1:" + porta + "/");
    }

    private File pastaDocumentos() {
        return new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOCUMENTS), "PyCode");
    }

    private File pastaDoApp() {
        File base = getExternalFilesDir(null);
        return new File(base != null ? base : getFilesDir(), "PyCode");
    }

    private void prepararArmazenamento() {
        String salva = getSharedPreferences("pycode", MODE_PRIVATE).getString("pasta", null);
        if (salva != null) {
            File escolhida = new File(salva);
            if (podeUsar(escolhida)) {
                iniciar(escolhida);
                return;
            }
            avisar("A pasta escolhida não está acessível. Usando a padrão.");
        }
        if (Build.VERSION.SDK_INT >= 30) {
            if (Environment.isExternalStorageManager()) {
                iniciar(pastaDocumentos());
                return;
            }
            new AlertDialog.Builder(this)
                    .setTitle("Pasta dos projetos")
                    .setMessage("Para guardar seus projetos em Documents/PyCode, onde o gerenciador de arquivos "
                            + "enxerga, o PyCode precisa de \"Acesso a todos os arquivos\". "
                            + "Sem isso, os projetos ficam numa pasta interna do app.")
                    .setPositiveButton("Permitir", (dialogo, botao) -> pedirAcessoTotal())
                    .setNegativeButton("Agora não", (dialogo, botao) -> iniciar(pastaDoApp()))
                    .setCancelable(false)
                    .show();
        } else if (checkSelfPermission(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.WRITE_EXTERNAL_STORAGE}, PEDIDO_PERMISSAO);
        } else {
            iniciar(pastaDocumentos());
        }
    }

    private void pedirAcessoTotal() {
        esperandoPermissao = true;
        try {
            startActivity(new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                    Uri.parse("package:" + getPackageName())));
        } catch (ActivityNotFoundException erro) {
            try {
                startActivity(new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));
            } catch (ActivityNotFoundException erro2) {
                esperandoPermissao = false;
                iniciar(pastaDoApp());
            }
        }
    }

    @Override
    public void onRequestPermissionsResult(int pedido, String[] permissoes, int[] resultados) {
        super.onRequestPermissionsResult(pedido, permissoes, resultados);
        if (pedido == PEDIDO_PERMISSAO) {
            boolean ok = resultados.length > 0 && resultados[0] == PackageManager.PERMISSION_GRANTED;
            iniciar(ok ? pastaDocumentos() : pastaDoApp());
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        tela.onResume();
        if (esperandoPermissao && Build.VERSION.SDK_INT >= 30) {
            esperandoPermissao = false;
            iniciar(Environment.isExternalStorageManager() ? pastaDocumentos() : pastaDoApp());
        }
    }

    @Override
    protected void onPause() {
        tela.onPause();
        super.onPause();
    }

    private void iniciar(File pasta) {
        if (iniciou) {
            return;
        }
        iniciou = true;
        new Thread(() -> {
            try {
                if (!pasta.isDirectory() && !pasta.mkdirs()) {
                    throw new IOException("não consegui criar " + pasta);
                }
                if (!Python.isStarted()) {
                    Python.start(new AndroidPlatform(this));
                }
                PyObject modulo = Python.getInstance().getModule("pycode_android");
                porta = modulo.callAttr("iniciar", pasta.getAbsolutePath()).toInt();
                runOnUiThread(this::abrirEditor);
            } catch (Throwable erro) {
                String mensagem = "Erro ao iniciar o PyCode:<br><br>" + TextUtils.htmlEncode(String.valueOf(erro));
                runOnUiThread(() -> mostrar(mensagem));
            }
        }).start();
    }

    @Override
    protected void onActivityResult(int pedido, int resultado, Intent dados) {
        super.onActivityResult(pedido, resultado, dados);
        if (pedido == PEDIDO_PASTA) {
            if (resultado == RESULT_OK && dados != null && dados.getData() != null) {
                File pasta = caminhoDaArvore(dados.getData());
                if (pasta == null) {
                    avisar("Escolha uma pasta do armazenamento do aparelho.");
                } else {
                    confirmarTroca(pasta);
                }
            }
            return;
        }
        if (pedido == PEDIDO_ARQUIVO && escolha != null) {
            escolha.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(resultado, dados));
            escolha = null;
        }
    }

    private void baixar(String endereco, String disposicao, String tipo) {
        String nome = URLUtil.guessFileName(endereco, disposicao, tipo);
        String mime = TextUtils.isEmpty(tipo) ? "application/zip" : tipo;
        new Thread(() -> {
            try {
                HttpURLConnection conexao = (HttpURLConnection) new URL(endereco).openConnection();
                try (InputStream entrada = conexao.getInputStream()) {
                    if (Build.VERSION.SDK_INT >= 29) {
                        ContentValues valores = new ContentValues();
                        valores.put(MediaStore.Downloads.DISPLAY_NAME, nome);
                        valores.put(MediaStore.Downloads.MIME_TYPE, mime);
                        Uri destino = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, valores);
                        if (destino == null) {
                            throw new IOException("Downloads indisponível");
                        }
                        try (OutputStream saida = getContentResolver().openOutputStream(destino)) {
                            if (saida == null) {
                                throw new IOException("Downloads indisponível");
                            }
                            copiar(entrada, saida);
                        }
                    } else {
                        File pasta = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                        if (!pasta.isDirectory() && !pasta.mkdirs()) {
                            throw new IOException("Downloads indisponível");
                        }
                        try (OutputStream saida = new FileOutputStream(new File(pasta, nome))) {
                            copiar(entrada, saida);
                        }
                    }
                } finally {
                    conexao.disconnect();
                }
                avisar("Salvo em Downloads: " + nome);
            } catch (Exception erro) {
                avisar("Não consegui salvar: " + erro.getMessage());
            }
        }).start();
    }

    private static void copiar(InputStream entrada, OutputStream saida) throws IOException {
        byte[] bloco = new byte[65536];
        int lidos;
        while ((lidos = entrada.read(bloco)) > 0) {
            saida.write(bloco, 0, lidos);
        }
    }

    private void avisar(String texto) {
        runOnUiThread(() -> Toast.makeText(this, texto, Toast.LENGTH_LONG).show());
    }

    @Override
    public void onBackPressed() {
        moveTaskToBack(true);
    }
}
