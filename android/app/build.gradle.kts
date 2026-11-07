plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

// Variante de teste com bibliotecas científicas (NumPy, Pandas, Matplotlib e Pillow).
// Só existe quando o build recebe -Pbibliotecas. Sem isso, o APK sai igual ao de sempre.
val comBibliotecas = project.hasProperty("bibliotecas")

android {
    namespace = "io.github.itallomendes124.pycode"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.itallomendes124.pycode"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        manifestPlaceholders["appLabel"] = "PyCode v2"
        if (comBibliotecas) {
            // outro identificador: instala ao lado do PyCode principal, sem sobrescrevê-lo
            applicationIdSuffix = ".bib"
            versionNameSuffix = "-bibliotecas"
            manifestPlaceholders["appLabel"] = "PyCode v2 Bib"
        }
        ndk {
            abiFilters += listOf("arm64-v8a")
        }
    }

    signingConfigs {
        getByName("debug") {
            storeFile = file("debug.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

chaquopy {
    defaultConfig {
        version = "3.13"
        if (comBibliotecas) {
            // Versões fixas: são as únicas que existem para Python 3.13 em arm64
            // no repositório de pacotes do Chaquopy.
            pip {
                install("numpy==1.26.2")
                install("pandas==2.1.3")
                install("matplotlib==3.8.4")
                install("pillow==11.0.0")
            }
        }
    }
}
