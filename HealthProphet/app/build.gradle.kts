plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)

    //alias(libs.plugins.google.services)
    //alias(libs.plugins.firebase.crashlytics.gradle)

    kotlin("kapt")
    id("com.google.dagger.hilt.android")
}

android {
    namespace = "test.task.healthprophet"
    compileSdk = 35

    defaultConfig {
        applicationId = "test.task.healthprophet"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
    buildFeatures {
        compose = true
    }
}

dependencies {
    implementation(project(":core:ui"))
    implementation(project(":core:model"))
    implementation(project(":feature"))
    implementation(project(":feature:splash"))
    implementation(project(":feature:predict_simple"))
    implementation(project(":feature:predict_with_check"))
    implementation(project(":feature:settings"))

    implementation(project(":domain_usecases"))

    implementation(project(":domain_realization:health_predictor"))
    implementation(project(":domain_realization:histories"))
    implementation(project(":domain_realization:histories_with_targets"))
    implementation(project(":domain_realization:settings"))
    implementation(project(":data_realization:health_predictor"))
    implementation(project(":data_realization:histories_local"))
    implementation(project(":data_realization:settings_local"))


    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.appcompat)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)

    implementation(libs.firebase.messaging)
    implementation(libs.firebase.crashlytics)
    androidTestImplementation(platform(libs.androidx.compose.bom))

    implementation(libs.androidx.navigation.compose)
    implementation(libs.hilt.android)
    kapt(libs.hilt.android.compiler)
    implementation(libs.androidx.hilt.navigation.compose)


    implementation(platform(libs.firebase.bom))

    implementation(libs.firebase.auth)
    implementation(libs.firebase.firestore)
    implementation(libs.firebase.storage)
    implementation(libs.firebase.analytics)
    implementation(libs.firebase.messaging)
    implementation(libs.firebase.config)
    implementation(libs.firebase.crashlytics)
    implementation(libs.firebase.appcheck.debug)
    implementation(libs.firebase.appcheck.playintegrity)
}