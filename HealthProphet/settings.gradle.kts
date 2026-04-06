pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "HealthProphet"
include(":app")
include(":feature")
include(":feature:settings")
include(":feature:predict_with_check")
include(":feature:predict_simple")
include(":domain")
include(":domain:settings")
include(":domain:histories_with_targets")
include(":domain:histories")
include(":feature:splash")
include(":domain:health_predictor")
include(":domain_realization")
include(":data")
include(":data_realization")
include(":core")
include(":core:model")
include(":core:networking")
include(":core:ui")
include(":domain_usecases")
include(":domain_realization:settings")
include(":domain_realization:histories")
include(":domain_realization:histories_with_targets")
include(":domain_realization:health_predictor")
include(":data:settings_local")
include(":data:health_predictor")
include(":data:histories_local")
include(":core:datastore")
include(":data_realization:health_predictor")
include(":data_realization:histories_local")
include(":data_realization:settings_local")
