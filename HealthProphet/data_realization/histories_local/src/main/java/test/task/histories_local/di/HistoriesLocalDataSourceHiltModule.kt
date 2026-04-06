package test.task.histories_local.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import test.task.histories_local.HistoriesLocalDataSource
import test.task.histories_local.HistoriesLocalDataSourceImpl
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
abstract class HistoriesLocalDataSourceHiltModule {
    @Binds
    @Singleton
    abstract fun bindHistoriesLocalDataSource(impl: HistoriesLocalDataSourceImpl): HistoriesLocalDataSource
}