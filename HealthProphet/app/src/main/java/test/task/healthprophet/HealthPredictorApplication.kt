package test.task.healthprophet


import android.app.Application
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.widget.Toast
import com.google.firebase.FirebaseApp
import com.google.firebase.appcheck.FirebaseAppCheck
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class HealthPredictorApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        //FirebaseApp.initializeApp(this)
        //setupAppCheck()
    }

    private fun setupAppCheck() {
        // Устанавливаем debug провайдер
        FirebaseAppCheck.getInstance().installAppCheckProviderFactory(
            DebugAppCheckProviderFactory.getInstance()
        )

        // Получаем и логируем токен через 3 секунды (даем время на инициализацию)
        Handler(Looper.getMainLooper()).postDelayed({
            getAndLogDebugToken()
        }, 3000)
    }

    private fun getAndLogDebugToken() {
        FirebaseAppCheck.getInstance().getAppCheckToken(false).addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result?.token
                Log.d("DEBUG_TOKEN", "=== COPY THIS TOKEN ===")
                Log.d("DEBUG_TOKEN", token ?: "empty token")
                Log.d("DEBUG_TOKEN", "=== PASTE IN FIREBASE CONSOLE ===")

                // Можно показать Toast для удобства
                Toast.makeText(this, "Debug token ready - check logs", Toast.LENGTH_LONG).show()
            } else {
                Log.e("DEBUG_TOKEN", "Failed to get token: ${task.exception?.message}")
            }
        }
    }
}