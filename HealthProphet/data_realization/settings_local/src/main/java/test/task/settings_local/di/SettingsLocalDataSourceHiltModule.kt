package test.task.settings_local.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import test.task.settings_local.SettingsLocalDataSource
import test.task.settings_local.SettingsLocalDataSourceImpl
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class SettingsLocalDataSourceHiltModule {
    @Binds
    @Singleton
    abstract fun bindSettingsLocalDataSource(impl: SettingsLocalDataSourceImpl): SettingsLocalDataSource
}