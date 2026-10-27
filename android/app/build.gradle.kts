plugins {
    id("com.android.application")
    id("com.chaquo.python")
}

android {
    namespace = "io.github.itallomendes124.pycode"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.itallomendes124.pycode"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
        ndk {
            abiFilters += listOf("arm64-v8a")
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
    }
}
